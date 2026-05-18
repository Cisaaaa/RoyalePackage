import os
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import schemas
import security
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, func
import random
import asyncio
from datetime import datetime, timezone

import requests
# Importujemy funkcję do wysyłania maili
from email_utils import send_status_email

# Importujemy bazę danych i modele
from database import engine, Base, get_db, SessionLocal
import models 

# Importujemy bibliotekę do obsługi JWT refresh
import jwt

from pydantic import BaseModel
from typing import Optional

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A6
from fastapi.responses import Response
import io

#Generowanie tabel w bazie danych na podstawie modeli (jeśli jeszcze nie istnieją)
models.Base.metadata.create_all(bind=engine) 

# Funkcja AUTO-SEEDINGU
def seed_db():
    db = SessionLocal()
    try:
        # 1. ROLE UŻYTKOWNIKÓW
        if db.query(models.Role).count() == 0:
            db.add_all([
                models.Role(role_name="Klient"),       # role_id = 1
                models.Role(role_name="Kurier"),       # role_id = 2
                models.Role(role_name="Dyspozytor"),   # role_id = 3
                models.Role(role_name="Administrator"),# role_id = 4
                models.Role(role_name="Kierowca TIR")  # role_id = 5 
            ])
            db.commit()

        # 2. STATUSY PACZEK
        if db.query(models.Status).count() == 0:
            db.add_all([
                models.Status(status_name="Zarejestrowana"),                   # 1
                models.Status(status_name="W magazynie nadawczym"),            # 2
                models.Status(status_name="W trasie między oddziałami"),       # 3 (NOWY - Line-Haul)
                models.Status(status_name="W magazynie docelowym"),            # 4 (Tu czeka na kuriera lokalnego)
                models.Status(status_name="Wydana kurierowi do doręczenia"),   # 5 (Ostatnia mila)
                models.Status(status_name="Dostarczona")                       # 6
            ])
            db.commit()

        # 3. TARYFY / GABARYTY
        if db.query(models.DimensionalTariff).count() == 0:
            db.add_all([
                models.DimensionalTariff(size_category="A", max_weight_kg=5.0, max_volume_m3=0.05, base_price=15.99),
                models.DimensionalTariff(size_category="B", max_weight_kg=15.0, max_volume_m3=0.15, base_price=20.99),
                models.DimensionalTariff(size_category="C", max_weight_kg=30.0, max_volume_m3=0.35, base_price=29.99)
            ])
            db.commit()

        # 4. REGIONALIZACJA I MAGAZYNY (HUB & SPOKE)
        if db.query(models.Warehouse).count() == 0:
            # Tworzymy Regiony
            reg_waw = models.Region(region_name="Mazowieckie", polygon_geom="SRID=4326;POLYGON((20.8 52.1, 21.2 52.1, 21.2 52.3, 20.8 52.3, 20.8 52.1))")
            reg_krk = models.Region(region_name="Małopolskie", polygon_geom="SRID=4326;POLYGON((19.8 49.9, 20.1 49.9, 20.1 50.2, 19.8 50.2, 19.8 49.9))")
            db.add_all([reg_waw, reg_krk])
            db.commit()

            # Adresy Magazynów z GPS (Wymagane przez VROOM)
            addr_waw = models.Address(street="Logistyczna", building_number="1", city="Warszawa", postal_code="00-001", geom="SRID=4326;POINT(21.0122 52.2297)")
            addr_krk = models.Address(street="Wielicka", building_number="250", city="Kraków", postal_code="30-001", geom="SRID=4326;POINT(19.9449 50.0647)")
            db.add_all([addr_waw, addr_krk])
            db.commit()

            # Tworzymy Huby
            hub_waw = models.Warehouse(address_id=addr_waw.address_id, region_id=reg_waw.region_id, name="HUB Warszawa", type="HUB")
            hub_krk = models.Warehouse(address_id=addr_krk.address_id, region_id=reg_krk.region_id, name="HUB Kraków", type="HUB")
            db.add_all([hub_waw, hub_krk])
            db.commit()
            
            # --- DODANIE DYSPOZYTORÓW DO HUBÓW ---
            import security
            hashed_pw = security.hash_password("password123")

            disp_waw = models.User(email="waw@royale.pl", password_hash=hashed_pw, first_name="Jan", last_name="Warszawski", role_id=3, warehouse_id=hub_waw.warehouse_id)
            disp_krk = models.User(email="krk@royale.pl", password_hash=hashed_pw, first_name="Anna", last_name="Krakowska", role_id=3, warehouse_id=hub_krk.warehouse_id)
            
            # --- WARSZAWA: Lokalny kurier (VAN) oraz Kierowca TIR-a (TRUCK) ---
            courier_local = models.User(email="kurier@royale.pl", password_hash=hashed_pw, first_name="Szybki", last_name="Bill", role_id=2, warehouse_id=hub_waw.warehouse_id)
            van = models.Vehicle(registration_number="WA 12345", capacity_kg=1000.0, capacity_m3=10.0, status="ACTIVE", vehicle_type="VAN", warehouse_id=hub_waw.warehouse_id)
            
            courier_linehaul = models.User(email="tir@royale.pl", password_hash=hashed_pw, first_name="Twardy", last_name="Roman", role_id=5, warehouse_id=hub_waw.warehouse_id)
            truck = models.Vehicle(registration_number="TIR 99999", capacity_kg=24000.0, capacity_m3=80.0, status="ACTIVE", vehicle_type="TRUCK", warehouse_id=hub_waw.warehouse_id)
            
            # --- KRAKÓW: Lokalny kurier (VAN) ---
            courier_krk = models.User(email="krk_kurier@royale.pl", password_hash=hashed_pw, first_name="Lajkonik", last_name="Wawelski", role_id=2, warehouse_id=hub_krk.warehouse_id)
            van_krk = models.Vehicle(registration_number="KR 54321", capacity_kg=1000.0, capacity_m3=10.0, status="ACTIVE", vehicle_type="VAN", warehouse_id=hub_krk.warehouse_id)
            
            # --- DODANIE ADMINISTRATORA ---
            super_admin = models.User(email="admin@royale.pl", password_hash=hashed_pw, first_name="Super", last_name="Admin", role_id=4)
            db.add(super_admin)

            db.add_all([disp_waw, disp_krk, courier_local, van, courier_linehaul, truck, courier_krk, van_krk, super_admin])
            db.commit()
            print("SUCCESS: Struktura Regionalna (Hub & Spoke) została wgrana!")

    except Exception as e:
        print(f"ERROR: Błąd podczas seedingu: {e}")
        db.rollback()
    finally:
        db.close()

# Funkcja instalująca Triggery w PostgreSQL
def setup_triggers():
    db = SessionLocal()
    try:
        print("INFO: Instalowanie triggerów bazy danych...")
        
        # 1. Tworzymy funkcję w języku bazy danych (PL/pgSQL)
        db.execute(text("""
            CREATE OR REPLACE FUNCTION log_parcel_history()
            RETURNS TRIGGER AS $$
            BEGIN
                -- Wykonaj tylko przy nowej paczce (INSERT) LUB gdy zmienił się status (UPDATE)
                IF (TG_OP = 'INSERT') OR (TG_OP = 'UPDATE' AND NEW.status_id IS DISTINCT FROM OLD.status_id) THEN
                    INSERT INTO parcel_history (parcel_id, status_id, warehouse_id, updated_at)
                    VALUES (NEW.parcel_id, NEW.status_id, NEW.current_warehouse_id, NOW());
                END IF;
                
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        
        # 2. Tworzymy sam wyzwalacz, który 'nasłuchuje' tabeli parcels
        db.execute(text("""
            DROP TRIGGER IF EXISTS trigger_log_parcel_history ON parcels;
            CREATE TRIGGER trigger_log_parcel_history
            AFTER INSERT OR UPDATE ON parcels
            FOR EACH ROW
            EXECUTE FUNCTION log_parcel_history();
        """))

        # Trigger zapisu historii zmian profilu klienta
        db.execute(text("""
            CREATE OR REPLACE FUNCTION log_user_changes()
            RETURNS TRIGGER AS $$
            BEGIN
                IF OLD.first_name IS DISTINCT FROM NEW.first_name OR
                   OLD.last_name IS DISTINCT FROM NEW.last_name OR
                   OLD.email IS DISTINCT FROM NEW.email OR
                   OLD.phone IS DISTINCT FROM NEW.phone OR
                   OLD.password_hash IS DISTINCT FROM NEW.password_hash THEN

                    INSERT INTO user_audit_log (
                        user_id,
                        old_first_name, new_first_name,
                        old_last_name, new_last_name,
                        old_email, new_email,
                        old_phone, new_phone,
                        old_password_hash, new_password_hash,
                        changed_at
                    ) VALUES (
                        OLD.user_id,
                        OLD.first_name, NEW.first_name,
                        OLD.last_name, NEW.last_name,
                        OLD.email, NEW.email,
                        OLD.phone, NEW.phone,
                        OLD.password_hash, NEW.password_hash,
                        NOW()
                    );
                END IF;

                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS user_changes_trigger ON users;
            CREATE TRIGGER user_changes_trigger
            AFTER UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION log_user_changes();
        """))

        db.commit()
        print("SUCCESS: Magia bazy danych (Triggery) działa!")
    except Exception as e:
        print(f"ERROR: Błąd instalacji triggerów: {e}")
        db.rollback()
    finally:
        db.close()

# W tym miejscu wywołujesmy nasze funkcje
seed_db()
setup_triggers()

# Inicjalizacja aplikacji FastAPI
app = FastAPI(
    title="Royale Package API",
    description="API dla systemu logistycznego",
    version="1.0.0"
)

# WERYFIKACJA UPRAWNIEŃ ADMINISTRATORA
def get_current_admin(current_user_email: str = Depends(security.get_current_user_email), db: Session = Depends(get_db)):
    """
    Sprawdza, czy zalogowany użytkownik ma rolę Administratora (role_id == 4).
    Jeśli nie, natychmiast odrzuca żądanie.
    """
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user or user.role_id != 4:
        raise HTTPException(status_code=403, detail="Brak uprawnień. Dostęp tylko dla Administratora.")
    return user

# WEBSOCKET MANAGER
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, courier_id: int):
        await websocket.accept()
        self.active_connections[courier_id] = websocket
        print(f"INFO: Kurier {courier_id} połączył się przez WebSocket.")

    def disconnect(self, courier_id: int, websocket: WebSocket):
        # Usuń tylko wtedy, gdy to DOKŁADNIE to samo połączenie
        if courier_id in self.active_connections and self.active_connections[courier_id] == websocket:
            del self.active_connections[courier_id]
            print(f"INFO: Kurier {courier_id} rozłączony.")

    async def send_personal_message(self, message: str, courier_id: int):
        websocket = self.active_connections.get(courier_id)
        if websocket:
            await websocket.send_text(message)

manager = ConnectionManager()

# Dodajemy obsługę CORS, żeby frontend (Vue.js) mógł z nami gadać
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # Wpuszczamy tylko nasz frontend!
    allow_credentials=True,
    allow_methods=["*"], # Pozwalamy na wszystko
    allow_headers=["*"], # Pozwalamy na przesyłanie tokenów
)

# Pobieranie adresu bazy danych ze zmiennych środowiskowych (przekazanych przez Dockera)
DATABASE_URL = os.getenv("DATABASE_URL")

@app.get("/")
async def root():
    """
    Główny endpoint testowy sprawdzający, czy API działa.
    """
    return {
        "status": "online",
        "message": "Witaj w API Royale Package!",
        "db_configured": DATABASE_URL is not None
    }

@app.get("/api/v1/health")
async def health_check():
    """
    Endpoint sprawdzający stan zdrowia (health check) aplikacji.
    """
    return {"status": "ok"}

@app.post("/api/v1/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Endpoint do rejestracji nowego użytkownika.
    """
    # 1. Sprawdzamy czy użytkownik o podanym adresie email juz istnieje
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        if db_user.is_active:
            raise HTTPException(status_code=400, detail="Użytkownik o takim adresie email już istnieje")
        raise HTTPException(
            status_code=400,
            detail="Konto z tym adresem email istnieje, ale jest zarchiwizowane. Skontaktuj się z administratorem, aby je przywrócić."
        )
    
    # 2. Haszujemy hasło
    hashed_password = security.hash_password(user.password)

    # 3. Tworzymy nowego użytkownika w bazie danych
    new_user = models.User(
        email=user.email,
        password_hash=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        role_id=user.role_id,
        phone=user.phone
    )

    # 4. Zapisujemy w bazie danych
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@app.post("/api/v1/login", summary="Logowanie (Generowanie Access i Refresh Token)")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy email lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active: # <--- DODANE
        raise HTTPException(status_code=403, detail="Konto zostało zablokowane (Pracownik zwolniony).")
    
    # Tworzymy paczkę dla Access Tokena (z rolami)
    token_data = {"sub": user.email, "role_id": user.role_id}
    
    # GENERUJEMY OBA TOKENY
    access_token = security.create_access_token(data=token_data)
    refresh_token = security.create_refresh_token(data=token_data)
    
    # Zapisujemy Refresh Token bezpiecznie w bazie danych
    user.refresh_token = refresh_token
    db.commit()
    
    # Zwracamy zestaw klientowi (Frontendowi)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
# Przykładowy chroniony endpoint, który wymaga tokena JWT
@app.get("/api/v1/users/me", summary="Pobierz dane aktualnie zalogowanego użytkownika")
def get_me(current_user_email: str = Depends(security.get_current_user_email)): 
    """
    Endpoint chroniony - wymaga tokena JWT.
    """

    return {
        "status": "authorized",
        "user_email": current_user_email,
        "message": "To jest chroniony endpoint. Jeśli widzisz ten komunikat, token JWT jest poprawny!"
    }



# Endpoint do odświeżania tokena JWT
@app.post("/api/v1/refresh", summary="Odśwież Access Token za pomocą Refresh Tokena")
def refresh_token(request: schemas.RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Endpoint przyjmuje Refresh Token i jeśli jest ważny, wydaje nowy Access Token
    """
    # 1. Weryfikujemy Refresh Token
    try:
        # Sprawdzamy poprawność tokena i wyciągamy z niego dane
        payload = jwt.decode(request.refresh_token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        # Sprawdzamy czy ktoś nie próbuje oszukać nas z nieprawidłowym tokenem
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Nieprawidłowy token")
        
        email = payload.get("sub")
        # Suzkamy użytkownika w bazie danych i weryfikujemy, czy token się zgadza z tym, co mamy zapisane
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user or user.refresh_token != request.refresh_token:
            raise HTTPException(status_code=401, detail="Token unieważniony lub użytkownik nie istnieje")
        # Jeśli wszystko się zgadza, generujemy nowy Access Token
        new_access_token = security.create_access_token(data={"sub": user.email, "role_id": user.role_id})
        return {"access_token": new_access_token, "token_type": "bearer"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token wygasł")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Nieważny token")




# NADAWANIE PACZEK!!!!!!!!

@app.post("/api/v1/parcels", response_model=schemas.ParcelResponse, status_code=status.HTTP_201_CREATED, summary="Nadaj nową paczkę")
def create_parcel(
    parcel_data: schemas.ParcelCreate, 
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    # 1. Identyfikacja klienta (płatnika)
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Nie znaleziono użytkownika")
    
    # 2. Pobranie cennika
    tariff = db.query(models.DimensionalTariff).filter(models.DimensionalTariff.tariff_id == parcel_data.tariff_id).first()
    if not tariff:
        raise HTTPException(status_code=404, detail="Wybrany gabaryt nie istnieje")
    
    # --- PRZYGOTOWANIE WSPÓŁRZĘDNYCH (Magia PostGIS) ---
    sender_geom = None
    if parcel_data.sender_address.lon and parcel_data.sender_address.lat:
        # Format WKT (Well-Known Text). Ważne: najpierw Długość (lon/X), potem Szerokość (lat/Y)
        sender_geom = f"SRID=4326;POINT({parcel_data.sender_address.lon} {parcel_data.sender_address.lat})"
        
    recipient_geom = None
    if parcel_data.recipient_address.lon and parcel_data.recipient_address.lat:
        recipient_geom = f"SRID=4326;POINT({parcel_data.recipient_address.lon} {parcel_data.recipient_address.lat})"

    # 3. Tworzymy i zapisujemy adresy (z punktami GPS!)
    sender_address = models.Address(
        street=parcel_data.sender_address.street,
        building_number=parcel_data.sender_address.building_number, 
        city=parcel_data.sender_address.city,
        postal_code=parcel_data.sender_address.postal_code,
        geom=sender_geom # Wstrzykujemy współrzędne
    )
    recipient_address = models.Address(
        street=parcel_data.recipient_address.street,
        building_number=parcel_data.recipient_address.building_number,
        city=parcel_data.recipient_address.city,
        postal_code=parcel_data.recipient_address.postal_code,
        geom=recipient_geom # Wstrzykujemy współrzędne
    )

    db.add(sender_address)
    db.add(recipient_address)
    db.flush() 

    # 4. Generowanie numeru przesyłki
    while True:
        tracking_num = f"RP{random.randint(1000000, 9999999)}PL"
        existing_parcel = db.query(models.Parcel).filter(models.Parcel.tracking_number == tracking_num).first()
        if not existing_parcel:
            break 

    # 5. Logika cennika
    final_price = float(tariff.base_price)
    COD_FEE = 5.00 
    if not parcel_data.simulate_payment:
        final_price += COD_FEE

    # --- PRZYGOTOWANIE DANYCH Z ETYKIETY ---
    sender_full_name = f"{parcel_data.sender_first_name} {parcel_data.sender_last_name}"
    recipient_full_name = f"{parcel_data.recipient_first_name} {parcel_data.recipient_last_name}"

    # REGIONALIZACJA: Magia PostGIS (ST_Contains)
    target_region_id = None
    start_warehouse_id = 1 # Domyślnie przypisujemy do Warszawy, w razie błędu GPS

    # ZAPYTANIE BAZOWE: W którym poligonie z tabeli 'regions' mieści się ten punkt?
    sql_region = text("""
        SELECT region_id 
        FROM regions 
        WHERE polygon_geom IS NOT NULL 
          AND ST_Contains(polygon_geom, ST_GeomFromEWKT(:point))
        LIMIT 1
    """)

    # 1. Gdzie jest ODBIORCA? (Ustawiamy Region Docelowy)
    if recipient_geom:
        region_result = db.execute(sql_region, {"point": recipient_geom}).fetchone()
        if region_result:
            target_region_id = region_result[0]
            print(f"INFO: Odbiorca w regionie docelowym ID {target_region_id}")

    # 2. Gdzie jest NADAWCA? (Ustawiamy Magazyn Startowy)
    if sender_geom:
        start_region_result = db.execute(sql_region, {"point": sender_geom}).fetchone()
        if start_region_result:
            # Jeśli znamy region nadawcy (np. 2 - Kraków), szukamy magazynu, który obsługuje ten region
            start_region_id = start_region_result[0]
            local_warehouse = db.query(models.Warehouse).filter(models.Warehouse.region_id == start_region_id).first()
            if local_warehouse:
                start_warehouse_id = local_warehouse.warehouse_id
                print(f"INFO: Nadawca przypisany do magazynu początkowego ID {start_warehouse_id} w regionie {start_region_id}")

    # 6. Złożenie paczki w całość
    new_parcel = models.Parcel(
        tracking_number=tracking_num,
        sender_id=user.user_id, # Ten kto zapłacił
        
        # Zapisujemy rzeczywiste dane z formularza
        sender_custom_name=sender_full_name,
        sender_phone=parcel_data.sender_phone,
        recipient_custom_name=recipient_full_name,
        recipient_phone=parcel_data.recipient_phone,
        
        sender_address_id=sender_address.address_id,
        recipient_address_id=recipient_address.address_id,
        tariff_id=parcel_data.tariff_id,
        calculated_price=final_price,
        declared_value=parcel_data.declared_value,
        current_warehouse_id=start_warehouse_id, 
        status_id=1,

        target_region_id=target_region_id
    )
    
    db.add(new_parcel)
    db.commit()
    db.refresh(new_parcel)

    # 7. Symulacja płatności
    if parcel_data.simulate_payment:
        payment = models.Payment(parcel_id=new_parcel.parcel_id, payer_id=user.user_id, amount=final_price, status="PAID")
        db.add(payment)
        new_parcel.is_cod = False 
        new_parcel.cod_amount = None
    else:
        payment = models.Payment(parcel_id=new_parcel.parcel_id, payer_id=user.user_id, amount=final_price, status="PENDING")
        db.add(payment)
        new_parcel.is_cod = True
        new_parcel.cod_amount = final_price 

    db.commit()
    db.refresh(new_parcel)

    # Zapis do książki adresowej (jeśli klient zaznaczył taką opcję)
    if parcel_data.save_recipient_to_contacts:
        # Sprawdzamy, czy takiego kontaktu już nie zapisaliśmy, by unikać duplikatów
        existing_contact = db.query(models.SavedContact).filter(
            models.SavedContact.user_id == user.user_id,
            models.SavedContact.phone == parcel_data.recipient_phone,
            models.SavedContact.first_name == parcel_data.recipient_first_name
        ).first()
        
        if not existing_contact:
            new_contact = models.SavedContact(
                user_id=user.user_id,
                first_name=parcel_data.recipient_first_name,
                last_name=parcel_data.recipient_last_name,
                phone=parcel_data.recipient_phone,
                address_id=recipient_address.address_id
            )
            db.add(new_contact)
            db.commit()

    return new_parcel

# POBIERANIE HISTORII PACZKI (dla klienta i kuriera)
@app.get("/api/v1/parcels", response_model=list[schemas.ParcelResponse])
def get_user_parcels(
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    # 1. Identyfikujemy zalogowanego użytkownika (bez zmian)
    current_user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="Nie znaleziono użytkownika")
    
    # 2. Zmieniamy zapytanie: prosimy o paczkę ORAZ nazwę statusu.
    # .join łączy tabelę Parcel z tabelą Status tam, gdzie zgadzają się ID statusów.
    results = db.query(models.Parcel, models.Status.status_name).join(
        models.Status, models.Parcel.status_id == models.Status.status_id
    ).filter(models.Parcel.sender_id == current_user.user_id).all()
    
    # 3. Ponieważ wynik z JOINa to lista krotek (parcel, status_name), 
    # musimy je "przepakować" do formatu, który rozumie schemat ParcelResponse.
    response = []
    for parcel, status_name in results:
        response.append({
            "parcel_id": parcel.parcel_id,
            "tracking_number": parcel.tracking_number,
            "status_id": parcel.status_id,
            "calculated_price": parcel.calculated_price,
            "status_name": status_name  # Przekazujemy tekstową nazwę do frontendu
        })
    
    return response

# WIDOK KURIERA - TRASY I PINEZKI NA MAPIE

@app.get("/api/v1/courier/route", response_model=list[schemas.CourierStopResponse], summary="Pobierz dzisiejszą trasę kuriera")
def get_courier_route(
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    # 1. Sprawdzamy kim jest użytkownik i czy to na pewno Kurier
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Nie znaleziono użytkownika")
    
    if user.role_id not in [2, 5]: 
        raise HTTPException(status_code=403, detail="Brak uprawnień. Ten widok jest tylko dla kurierów i kierowców TIR.")

    # 2. Szukamy aktywnej trasy dla tego kuriera (zaplanowanej lub w trakcie)
    route = db.query(models.Route).filter(
        models.Route.courier_id == user.user_id,
        models.Route.status.in_(["PLANNED", "IN_PROGRESS"])
    ).first()

    # Jeśli dyspozytor nie przydzielił mu jeszcze trasy, zwracamy pustą listę
    if not route:
        return []

    # 3. Pobieramy przystanki dla tej trasy, posortowane według kolejności (stop_order)
    stops = db.query(models.RouteStop).filter(
        models.RouteStop.route_id == route.route_id,
        models.RouteStop.status == "PLANNED"
    ).order_by(models.RouteStop.stop_order).all()

    # Przygotowujemy kuloodporne zapytanie SQL do wyciągania GPS z PostGIS
    sql_coords = text("SELECT ST_X(geom) as lon, ST_Y(geom) as lat FROM addresses WHERE address_id = :id AND geom IS NOT NULL")

    # 4. Składamy dane dla Frontendu i Leafleta
    results = []
    for stop in stops:
        # SCENARIUSZ A: Zwykła paczka do doręczenia
        if stop.parcel_id and stop.operation_type == "DROP_OFF":
            parcel = db.query(models.Parcel).filter(models.Parcel.parcel_id == stop.parcel_id).first()
            address = db.query(models.Address).filter(models.Address.address_id == parcel.recipient_address_id).first()

            # Pobieramy współrzędne surowym SQL-em
            lat, lon = None, None
            if address:
                coords = db.execute(sql_coords, {"id": address.address_id}).fetchone()
                if coords and coords[0] is not None and coords[1] is not None:
                    lon, lat = coords[0], coords[1]

            results.append({
                "stop_id": stop.stop_id,
                "parcel_id": parcel.parcel_id,
                "tracking_number": parcel.tracking_number,
                "operation_type": stop.operation_type,
                "recipient_name": parcel.recipient_custom_name,
                "recipient_phone": parcel.recipient_phone,
                "street": address.street,
                "building_number": address.building_number,
                "city": address.city,
                "lat": lat,
                "lon": lon,
                "stop_order": stop.stop_order # <--- DODANO
            })
        
        # SCENARIUSZ B: Start z Magazynu (HUB) lub Rozładunek w HUBie
        elif stop.warehouse_id and stop.operation_type == "WAREHOUSE_TRANSFER":
            warehouse = db.query(models.Warehouse).filter(models.Warehouse.warehouse_id == stop.warehouse_id).first()
            address = db.query(models.Address).filter(models.Address.address_id == warehouse.address_id).first()
            
            # Pobieramy współrzędne surowym SQL-em
            lat, lon = None, None
            if address:
                coords = db.execute(sql_coords, {"id": address.address_id}).fetchone()
                if coords and coords[0] is not None and coords[1] is not None:
                    lon, lat = coords[0], coords[1]
            
            # Dynamiczna nazwa etykiety zamiast sztywnego "START TRASY"
            tracking_label = "START TRASY" if stop.stop_order == 0 else "ROZŁADUNEK (HUB)"

            results.append({
                "stop_id": stop.stop_id,
                "parcel_id": 0, 
                "tracking_number": tracking_label, # <--- ZMIANA
                "operation_type": stop.operation_type,
                "recipient_name": warehouse.name,
                "recipient_phone": "-",
                "street": address.street,
                "building_number": address.building_number,
                "city": address.city,
                "lat": lat,
                "lon": lon,
                "stop_order": stop.stop_order # <--- DODANO
            })

    return results


# PANEL DYSPOZYTORA - ZARZĄDZANIE TRASAMI


@app.get("/api/v1/dispatcher/unassigned-parcels", summary="Pobierz paczki do przypisania")
def get_unassigned_parcels(
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    # 1. Sprawdzamy uprawnienia (Tylko Dyspozytor - rola 3)
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user or user.role_id != 3:
        raise HTTPException(status_code=403, detail="Brak uprawnień. Widok tylko dla Dyspozytora.")

    # 2. Szukamy paczek ze statusem 2 ("W magazynie nadawczym") ORAZ 4 ("W magazynie docelowym")
    unassigned_parcels = db.query(models.Parcel).outerjoin(
        models.RouteStop, models.Parcel.parcel_id == models.RouteStop.parcel_id
    ).filter(
        models.Parcel.status_id.in_([2, 4]), # <--- KLUCZOWA ZMIANA: .in_([2, 4]) zamiast == 2
        models.Parcel.current_warehouse_id == user.warehouse_id,
        models.RouteStop.stop_id == None
    ).all()

    # 3. Składamy dane dla widoku tabeli na frontendzie
    results = []
    results = []
    for parcel in unassigned_parcels:
        address = db.query(models.Address).filter(models.Address.address_id == parcel.recipient_address_id).first()
        
        # Pobieramy też nazwę statusu do wyświetlenia w tabeli
        status_obj = db.query(models.Status).filter(models.Status.status_id == parcel.status_id).first()
        
        results.append({
            "parcel_id": parcel.parcel_id,
            "tracking_number": parcel.tracking_number,
            "recipient_city": address.city if address else "Brak danych",
            "recipient_street": address.street if address else "Brak danych",
            "recipient_name": parcel.recipient_custom_name,
            "calculated_price": parcel.calculated_price,
            
            "target_region_id": parcel.target_region_id, 
            "status_name": status_obj.status_name if status_obj else "Nieznany"
        })
    return results

@app.get("/api/v1/dispatcher/fleet", summary="Pobierz listę kurierów i pojazdów")
def get_fleet(
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user or user.role_id != 3:
        raise HTTPException(status_code=403, detail="Brak uprawnień.")
    
    # NOWOŚĆ: Wyciągamy dane magazynu dyspozytora
    warehouse = db.query(models.Warehouse).filter(models.Warehouse.warehouse_id == user.warehouse_id).first()
    
    couriers = db.query(models.User).filter(
        models.User.role_id.in_([2, 5]),
        models.User.warehouse_id == user.warehouse_id,
        models.User.is_active == True
    ).all()
    
    vehicles = db.query(models.Vehicle).filter(
        models.Vehicle.status == "ACTIVE",
        models.Vehicle.warehouse_id == user.warehouse_id
    ).all()

    return {
        "dispatcher_warehouse_id": warehouse.warehouse_id if warehouse else None, # Dodano
        "dispatcher_region_id": warehouse.region_id if warehouse else None,       # Dodano
        "couriers": [{"user_id": c.user_id, "first_name": c.first_name, "last_name": c.last_name, "role_id": c.role_id} for c in couriers],
        "vehicles": [{"vehicle_id": v.vehicle_id, "registration_number": v.registration_number, "capacity_kg": v.capacity_kg, "vehicle_type": v.vehicle_type} for v in vehicles]
    }

@app.post("/api/v1/dispatcher/routes/line-haul", status_code=status.HTTP_201_CREATED, summary="Wyślij TIRa do innego Magazynu (Line-Haul)")
def create_line_haul_route(
    target_warehouse_id: int, 
    courier_id: int, 
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user or user.role_id != 3:
        raise HTTPException(status_code=403, detail="Tylko dyspozytor może planować trasy.")
        
    source_warehouse_id = user.warehouse_id
    if not source_warehouse_id:
        raise HTTPException(status_code=400, detail="Nie jesteś przypisany do żadnego magazynu.")

    target_warehouse = db.query(models.Warehouse).filter(models.Warehouse.warehouse_id == target_warehouse_id).first()
    if not target_warehouse:
        raise HTTPException(status_code=404, detail="Magazyn docelowy nie istnieje.")

    # 1. SZUKAMY PACZEK: Bierzemy wszystkie paczki z naszego magazynu, które chcą jechać do tego regionu
    parcels_to_ship = db.query(models.Parcel).filter(
        models.Parcel.current_warehouse_id == source_warehouse_id,
        models.Parcel.target_region_id == target_warehouse.region_id,
        models.Parcel.status_id == 2 # Z magazynu nadawczego
    ).all()

    if not parcels_to_ship:
        raise HTTPException(status_code=400, detail=f"Brak paczek do wysłania do magazynu {target_warehouse.name}.")

    # (Symulujemy dystans, np. 300 km)
    simulated_distance = 300.0 
    
    # 2. Tworzymy nową trasę "Ciężką" (LINE_HAUL)
    new_route = models.Route(
        courier_id=courier_id,
        vehicle_id=vehicle_id,
        route_type="LINE_HAUL",
        status="PLANNED",
        total_distance_km=simulated_distance,
        total_revenue=0, # Line-haul nie generuje bezpośrednio zysku (robią to kurierzy u docelowego klienta)
        route_cost=(simulated_distance * 0.3 * 6.50) + 150 # Droższy koszt kilometra + stała stawka dla kierowcy
    )
    db.add(new_route)
    db.flush()

    # 3. Zapisujemy zaledwie DWA przystanki (To nie jest rozwożenie po domach!)
    # Przystanek 0: Start w naszym magazynie (Warszawa)
    db.add(models.RouteStop(
        route_id=new_route.route_id,
        warehouse_id=source_warehouse_id,
        stop_order=0,
        operation_type="WAREHOUSE_TRANSFER",
        status="PLANNED"
    ))
    
    # Przystanek 1: Koniec w magazynie docelowym (Kraków)
    db.add(models.RouteStop(
        route_id=new_route.route_id,
        warehouse_id=target_warehouse_id,
        stop_order=1,
        operation_type="WAREHOUSE_TRANSFER", # Oznacza zrzut w magazynie, a nie w domu klienta
        status="PLANNED"
    ))

    # 4. Magia: Aktualizujemy paczki!
    for p in parcels_to_ship:
        p.status_id = 3 # "W trasie między oddziałami"
        # BARDZO WAŻNE: Dodajemy powiązanie paczki z "dużą trasą", ale bez dodawania dla niej RouteStop.
        # W MVP wystarczy, że uaktualnimy jej status, a paczka i tak dotrze na miejsce docelowe po zamknięciu trasy.
        
    db.commit()
    return {
        "message": f"TIR zaplanowany do {target_warehouse.name} z {len(parcels_to_ship)} paczkami!",
        "route_id": new_route.route_id
    }

@app.post("/api/v1/dispatcher/routes", status_code=status.HTTP_201_CREATED, summary="Utwórz i zoptymalizuj trasę")
def create_route(
    # Otrzymujemy listę ID paczek, ID kuriera i ID pojazdu do stworzenia trasy
    request: schemas.RouteCreateRequest,
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    # Sprawdzamy uprawnienia (Tylko Dyspozytor - rola 3)
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user or user.role_id != 3:
        raise HTTPException(status_code=403, detail="Brak uprawnień.")

    if not request.parcel_ids:
        raise HTTPException(status_code=400, detail="Nie wybrano paczek do trasy.")

    # 1. Dane pojazdu i limity (VROOM wymaga [waga, objętość])
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.vehicle_id == request.vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Nie znaleziono pojazdu.")
    
    # Przeliczamy m3 na int (x100) dla VROOM
    vroom_capacity = [int(vehicle.capacity_kg), int((vehicle.capacity_m3 or 0.1) * 100)]

    # 2. Współrzędne Magazynu (Start/End)
    warehouse = db.query(models.Warehouse).filter(models.Warehouse.warehouse_id == 1).first()
    sql_coords = text("SELECT ST_X(geom) as lon, ST_Y(geom) as lat FROM addresses WHERE address_id = :id AND geom IS NOT NULL")
    wh_result = db.execute(sql_coords, {"id": warehouse.address_id}).fetchone()
    
    if not wh_result:
        raise HTTPException(status_code=500, detail="Brak współrzędnych Magazynu (ID=1).")
    # VROOM wymaga formatu [lon, lat] dla współrzędnych
    vroom_vehicle = {
        "id": vehicle.vehicle_id,
        "profile": "car",
        "start": [wh_result[0], wh_result[1]],
        "end": [wh_result[0], wh_result[1]],
        "capacity": vroom_capacity
    }

    # 3. Zadania (Paczki)
    parcels = db.query(models.Parcel).filter(models.Parcel.parcel_id.in_(request.parcel_ids)).all()
    vroom_jobs = []
    total_revenue = 0.0
    # Pobieramy współrzędne odbiorców i przygotowujemy dane dla VROOM
    for parcel in parcels:
        p_result = db.execute(sql_coords, {"id": parcel.recipient_address_id}).fetchone()
        if not p_result:
            continue
        # Pobieramy taryfę, żeby wiedzieć, ile "zajmuje" paczka w sensie wagi i objętości dla VROOM
        tariff = db.query(models.DimensionalTariff).filter(models.DimensionalTariff.tariff_id == parcel.tariff_id).first()
        job_delivery = [int(tariff.max_weight_kg), int(tariff.max_volume_m3 * 100)]
        
        vroom_jobs.append({
            "id": parcel.parcel_id,
            "location": [p_result[0], p_result[1]],
            "delivery": job_delivery
        })
        total_revenue += parcel.calculated_price

    # 4. Strzał do VROOM
    payload = {"vehicles": [vroom_vehicle], "jobs": vroom_jobs}
    try:
        response = requests.post("http://vroom:3000/", json=payload, timeout=20) # VROOM jest w innym kontenerze, więc używamy nazwy usługi "vroom"
        vroom_data = response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd silnika VROOM: {e}")
    # VROOM zwraca "code": 0, gdy wszystko poszło dobrze. Inaczej jest jakiś problem z danymi lub konfiguracją.
    if vroom_data.get("code") != 0:
        raise HTTPException(status_code=500, detail=f"VROOM Error: {vroom_data.get('error')}")

    # 5. Zapis trasy (Bierzemy pod uwagę nową kolejność!)
    route_info = vroom_data["routes"][0]
    total_distance_km = route_info["distance"] / 1000.0
    
    # Koszty (prosta symulacja: paliwo + stawka kuriera) [cite: 144, 145]
    route_cost = (total_distance_km * 0.1 * 6.50) + 50.0 + (len(vroom_jobs) * 2.0)
    # Tworzymy rekord trasy w bazie danych
    new_route = models.Route(
        courier_id=request.courier_id,
        vehicle_id=request.vehicle_id,
        route_type="LAST_MILE",
        status="PLANNED",
        total_distance_km=total_distance_km,
        total_revenue=total_revenue,
        route_cost=route_cost
    )
    db.add(new_route)
    db.flush()
    # VROOM zwraca kolejność przystanków w "steps", więc iterujemy po niej i tworzymy RouteStop dla każdej paczki
    for step in route_info["steps"]:
        if step["type"] == "job":
            stop = models.RouteStop(
                route_id=new_route.route_id,
                parcel_id=step["id"],
                stop_order=step["arrival"], # VROOM podaje czas/kolejność
                operation_type="DROP_OFF"
            )
            db.add(stop)
            db.query(models.Parcel).filter(models.Parcel.parcel_id == step["id"]).update({"status_id": 5})

    db.commit()
    return {"message": "VRP Success", "route_id": new_route.route_id, "unassigned": vroom_data["summary"]["unassigned"]}

# OZNACZANIE STARTU TRASY (Wyjazd z HUBu)
@app.put("/api/v1/courier/stops/{stop_id}/complete", summary="Oznacz przystanek magazynowy jako ukończony")
def complete_route_stop(
    stop_id: int,
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user or user.role_id not in [2, 5]:
        raise HTTPException(status_code=403, detail="Brak uprawnień.")

    stop = db.query(models.RouteStop).filter(models.RouteStop.stop_id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Nie znaleziono przystanku.")

    # 1. Zmieniamy status przystanku magazynowego na ukończony
    stop.status = "COMPLETED"
    stop.actual_arrival = func.now()
    
    # 2. Skoro kurier wyjechał z magazynu, zmieniamy status CAŁEJ TRASY na "W trakcie"
    route = db.query(models.Route).filter(models.Route.route_id == stop.route_id).first()
    if route and route.status == "PLANNED":
        route.status = "IN_PROGRESS"

    db.commit()
    return {"message": "Wyjazd z magazynu zarejestrowany. Trasa rozpoczęta!"}

# OBSŁUGA KURIERA - DORĘCZENIE PACZKI
@app.put("/api/v1/courier/parcels/{parcel_id}/deliver", summary="Oznacz paczkę jako doręczoną")
def mark_parcel_delivered(
    parcel_id: int,
    background_tasks: BackgroundTasks, # Dodajemy BackgroundTasks do obsługi maili po doręczeniu
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user or user.role_id != 2:
        raise HTTPException(status_code=403, detail="Brak uprawnień.")

    parcel = db.query(models.Parcel).filter(models.Parcel.parcel_id == parcel_id).first()
    if not parcel:
        raise HTTPException(status_code=404, detail="Nie znaleziono paczki")

    # Zmiana statusu paczki
    parcel.status_id = 6

    stop = db.query(models.RouteStop).filter(
        models.RouteStop.parcel_id == parcel_id,
        models.RouteStop.status == "PLANNED"
    ).first()
    
    if stop:
        stop.status = "COMPLETED"
        db.flush() 

    # --- 2. DODANA LOGIKA MAILA (Wysłanie powiadomienia o doręczeniu) ---
    sender = db.query(models.User).filter(models.User.user_id == parcel.sender_id).first()
    if sender and sender.email:
        background_tasks.add_task(
            send_status_email,
            email=sender.email,
            tracking_number=parcel.tracking_number,
            new_status="Dostarczona"
        )

    # Zapisujemy zmianę statusu paczki i przystanku
    db.commit()

    return {"message": "Paczka doręczona pomyślnie."}

# RĘCZNE ZAKOŃCZENIE TRASY PRZEZ KURIERA LUB KIEROWCĘ TIRa
@app.put("/api/v1/courier/routes/complete", summary="Zakończ aktywną trasę i wróć do bazy")
def complete_active_route(
    background_tasks: BackgroundTasks, # Dodajemy BackgroundTasks do obsługi maili po zakończeniu trasy
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user or user.role_id not in [2, 5]: # Wpuszczamy ZARÓWNO Kurierów (2) jak i Kierowców TIR (5)
        raise HTTPException(status_code=403, detail="Brak uprawnień.")

    route = db.query(models.Route).filter(
        models.Route.courier_id == user.user_id,
        models.Route.status == "IN_PROGRESS"
    ).first()
    
    if not route:
        raise HTTPException(status_code=404, detail="Brak aktywnej trasy do zakończenia.")
        
    # --- LOGIKA A: Kierowca TIRa zamyka trasę "LINE_HAUL" ---
    if route.route_type == "LINE_HAUL":
        # Wyciągamy ostatni przystanek tej trasy, żeby dowiedzieć się, DO JAKIEGO magazynu dojechał
        last_stop = db.query(models.RouteStop).filter(
            models.RouteStop.route_id == route.route_id
        ).order_by(models.RouteStop.stop_order.desc()).first()

        parcels_in_transit = db.query(models.Parcel).filter(models.Parcel.status_id == 3).all()
        for p in parcels_in_transit:
            p.status_id = 4 # W magazynie docelowym
            p.current_warehouse_id = last_stop.warehouse_id # Przypisujemy fizycznie paczki do Krakowa!


            # --- DODANA LOGIKA MAILA (Paczka w HUBie docelowym) ---
            sender = db.query(models.User).filter(models.User.user_id == p.sender_id).first()
            if sender and sender.email:
                background_tasks.add_task(
                    send_status_email,
                    email=sender.email,
                    tracking_number=p.tracking_number,
                    new_status="W magazynie docelowym",
                    eta="w następny dzień roboczy" # 
                )
            
        # Oznaczamy przystanek docelowy jako wykonany
        if last_stop:
            last_stop.status = "COMPLETED"
            
            # --- ZMIANA: PRZENIESIENIE KIEROWCY I POJAZDU DO NOWEGO HUBu ---
            # Przypisujemy kierowcę TIRa do magazynu docelowego, do którego właśnie dojechał
            user.warehouse_id = last_stop.warehouse_id
            
            # Znajdujemy i przepisujemy też jego ciężarówkę, którą przyjechał
            vehicle = db.query(models.Vehicle).filter(models.Vehicle.vehicle_id == route.vehicle_id).first()
            if vehicle:
                vehicle.warehouse_id = last_stop.warehouse_id
            # ---------------------------------------------------------------

    # --- LOGIKA B: Zwykły kurier kończy zwożenie paczek do domów ---
    else:
        # Zwykła trasa nie wymaga dodatkowych operacji na paczkach, doręczenia oznaczano na bieżąco
        pass

    # Zamykamy samą trasę
    route.status = "COMPLETED"
    db.commit()
    
    return {"message": "Trasa oficjalnie zakończona. Paczki rozładowane, a pojazd zameldowany w nowym HUBie!"}

@app.websocket("/api/v1/courier/ws/{token}")
async def courier_websocket(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    # 1. AKCEPTUJEMY POŁĄCZENIE OD RAZU (To zapobiega błędom "Finished" w przeglądarce)
    await websocket.accept()
    
    try:
        # 2. Ręczna weryfikacja tokena JWT
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email = payload.get("sub")
        user = db.query(models.User).filter(models.User.email == email).first()
        
        if not user or user.role_id != 2: # Wpuszczamy tylko Kuriera
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        # 3. Zapisujemy aktywną "słuchawkę" w menedżerze
        manager.active_connections[user.user_id] = websocket
        print(f"INFO: Kurier {user.user_id} połączył się przez WebSocket.")
        
        # 4. Nieskończona pętla utrzymująca otwarty tunel
        try:
            while True:
                data = await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(user.user_id, websocket)
            
    except Exception as e:
        print(f"WS ERROR: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)

@app.post("/api/v1/dispatcher/routes/auto", summary="Automatyczna optymalizacja floty przez VROOM")
def auto_optimize_fleet(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    # 1. Weryfikacja uprawnień (tylko Dyspozytor)
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user or user.role_id != 3:
        raise HTTPException(status_code=403, detail="Tylko dyspozytor może planować trasy.")

    # 2. HUB (start i koniec każdej trasy)
    # 2. HUB (start i koniec każdej trasy) -> Zmieniamy sztywną "1" na dynamiczny magazyn dyspozytora
    warehouse = db.query(models.Warehouse).filter(models.Warehouse.warehouse_id == user.warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=400, detail="Twój dyspozytor nie ma przypisanego magazynu.")
    
    sql_coords = text("SELECT ST_X(geom) as lon, ST_Y(geom) as lat FROM addresses WHERE address_id = :id AND geom IS NOT NULL")
    hub_coords = db.execute(sql_coords, {"id": warehouse.address_id}).fetchone()
    if not hub_coords:
        raise HTTPException(status_code=400, detail="HUB nie posiada współrzędnych GPS.")

    hub_lon_lat = [hub_coords[0], hub_coords[1]]

    # 3. Paczki do przypisania: status=2 (lub 4) i brak przypisania w route_stops
    parcels = db.query(models.Parcel).outerjoin(
        models.RouteStop, models.Parcel.parcel_id == models.RouteStop.parcel_id
    ).filter(
        models.Parcel.status_id.in_([2, 4]), # Może być świeżo nadana (2) lub przywieziona z innego miasta (4)
        models.Parcel.current_warehouse_id == user.warehouse_id, # Fizycznie leży u mnie
        models.Parcel.target_region_id == warehouse.region_id, # TYLKO paczki przeznaczone do doręczenia w moim regionie!
        models.RouteStop.stop_id == None
    ).all()

    if not parcels:
        raise HTTPException(status_code=400, detail="Brak paczek w magazynie do przypisania.")

    # 4. Dostępni kurierzy i aktywne pojazdy (Tylko lokalne!)
    couriers = db.query(models.User).filter(
        models.User.role_id == 2,
        models.User.warehouse_id == user.warehouse_id,
        models.User.is_active == True
    ).order_by(models.User.user_id).all()
    
    # Tylko VANy i tylko z naszego magazynu!
    vehicles = db.query(models.Vehicle).filter(
        models.Vehicle.status == "ACTIVE",
        models.Vehicle.warehouse_id == user.warehouse_id,
        models.Vehicle.vehicle_type == "VAN" 
    ).order_by(models.Vehicle.vehicle_id).all()

    fleet_size = min(len(couriers), len(vehicles))
    if fleet_size == 0:
        raise HTTPException(status_code=400, detail="Brak dostępnych kurierów lub aktywnych pojazdów.")

    # 5. Budujemy dane wejściowe dla VROOM
    parcel_map = {p.parcel_id: p for p in parcels}
    vroom_jobs = []
    for p in parcels:
        coords = db.execute(sql_coords, {"id": p.recipient_address_id}).fetchone()
        tariff = db.query(models.DimensionalTariff).filter(models.DimensionalTariff.tariff_id == p.tariff_id).first()
        if not coords or not tariff:
            continue

        vroom_jobs.append({
            "id": p.parcel_id,
            "location": [coords[0], coords[1]],
            # VROOM pracuje na integerach, skala objętości x100 dla m3
            "delivery": [int(tariff.max_weight_kg), int(tariff.max_volume_m3 * 100)]
        })

    if not vroom_jobs:
        raise HTTPException(status_code=400, detail="Brak paczek z kompletnymi danymi GPS/taryfą do optymalizacji.")

    vehicle_binding = {}
    vroom_vehicles = []
    for idx in range(fleet_size):
        courier = couriers[idx]
        vehicle = vehicles[idx]
        vroom_vehicle_id = idx + 1

        capacity_m3 = vehicle.capacity_m3 if vehicle.capacity_m3 and vehicle.capacity_m3 > 0 else 0.1
        vroom_vehicles.append({
            "id": vroom_vehicle_id,
            "profile": "car",
            "start": hub_lon_lat,
            "end": hub_lon_lat,
            "capacity": [int(vehicle.capacity_kg), int(capacity_m3 * 100)]
        })
        vehicle_binding[vroom_vehicle_id] = {
            "courier": courier,
            "vehicle": vehicle
        }

    payload = {
        "jobs": vroom_jobs,
        "vehicles": vroom_vehicles,
        "options": {"g": True}
    }

    try:
        response = requests.post("http://vroom:3000/", json=payload, timeout=20)
        response.raise_for_status()
        result = response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd silnika VROOM: {str(e)}")

    if result.get("code") != 0:
        raise HTTPException(status_code=400, detail=f"VROOM Error: {result.get('error')}")

    # 6. Zapis tras i przystanków
    created_routes = []
    for v_route in result.get("routes", []):
        binding = vehicle_binding.get(v_route.get("vehicle"))
        if not binding:
            continue

        courier = binding["courier"]
        vehicle = binding["vehicle"]

        job_steps = [s for s in v_route.get("steps", []) if s.get("type") == "job"]
        parcel_ids = [step["id"] for step in job_steps]

        total_distance_km = round(v_route.get("distance", 0) / 1000.0, 2)
        total_revenue = sum(parcel_map[pid].calculated_price for pid in parcel_ids if pid in parcel_map)
        route_cost = (total_distance_km * 0.1 * 6.50) + 50.0 + (len(parcel_ids) * 2.0)

        new_route = models.Route(
            courier_id=courier.user_id,
            vehicle_id=vehicle.vehicle_id,
            route_type="LAST_MILE",
            status="PLANNED",
            total_distance_km=total_distance_km,
            total_revenue=total_revenue,
            route_cost=route_cost
        )
        db.add(new_route)
        db.flush()

        # Zapisujemy HUB jako punkt startowy (Przystanek #0)
        now = datetime.now(timezone.utc)
        db.add(models.RouteStop(
            route_id=new_route.route_id,
            warehouse_id=warehouse.warehouse_id, # Pobiera ID magazynu dyspozytora
            stop_order=0,
            operation_type="WAREHOUSE_TRANSFER",
            status="PLANNED",
            estimated_arrival=now # ETA dla startu to "teraz"
        ))

        route_parcels = []
        for order, step in enumerate(job_steps, start=1):
            parcel_id = step["id"]
            db.add(models.RouteStop(
                route_id=new_route.route_id,
                parcel_id=parcel_id,
                stop_order=order,
                operation_type="DROP_OFF",
                status="PLANNED"
            ))

            db.query(models.Parcel).filter(models.Parcel.parcel_id == parcel_id).update({"status_id": 5})

            # --- NOWY KOD DO WYSYŁANIA MAILA (wewnątrz pętli) ---
            parcel = parcel_map.get(parcel_id)
            if parcel:
                sender = db.query(models.User).filter(models.User.user_id == parcel.sender_id).first()  
                if sender and sender.email:
                    background_tasks.add_task(
                        send_status_email,
                        email=sender.email,
                        tracking_number=parcel.tracking_number,
                        new_status="Wydana kurierowi do doręczenia",
                        eta="dziś między 9:00 a 12:00", 
                        courier_name=f"{courier.first_name} {courier.last_name}" 
                    )

            parcel = parcel_map.get(parcel_id)
            if parcel:
                address = db.query(models.Address).filter(models.Address.address_id == parcel.recipient_address_id).first()
                route_parcels.append({
                    "parcel_id": parcel.parcel_id,
                    "tracking_number": parcel.tracking_number,
                    "recipient_city": address.city if address else "Brak danych",
                    "recipient_street": address.street if address else "Brak danych"
                })

        created_routes.append({
            "route_id": new_route.route_id,
            "courier_name": f"{courier.first_name} {courier.last_name}",
            "vehicle_reg": vehicle.registration_number,
            "parcels_count": len(route_parcels),
            "parcels": route_parcels
        })

        # Zlecamy serwerowi, aby wysłał wiadomość w tle, nie blokując bazy danych
        background_tasks.add_task(manager.send_personal_message, "ROUTE_UPDATED", courier.user_id)

    db.commit()
    return {
        "message": "Optymalizacja zakończona",
        "routes": created_routes,
        "unassigned": len(result.get("unassigned", []))
    }

@app.get("/api/v1/dispatcher/reports", response_model=list[schemas.RouteReportResponse], summary="Pobierz raporty finansowe tras")
def get_route_reports(
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user or user.role_id != 3:
        raise HTTPException(status_code=403, detail="Brak uprawnień.")

    # Pobieramy tylko trasy, które mają policzone kilometry
    routes = db.query(models.Route).filter(models.Route.total_distance_km != None).order_by(models.Route.route_id.desc()).all()
    
    reports = []
    for r in routes:
        # Szukamy imienia kuriera
        courier = db.query(models.User).filter(models.User.user_id == r.courier_id).first()
        courier_name = f"{courier.first_name} {courier.last_name}" if courier else "Nieznany Kurier"
        
        # Szukamy rejestracji pojazdu
        vehicle = db.query(models.Vehicle).filter(models.Vehicle.vehicle_id == r.vehicle_id).first()
        vehicle_reg = vehicle.registration_number if vehicle else "Brak Danych"
        
        # Liczymy ile paczek przypisano do tej trasy
        parcels_count = db.query(models.RouteStop).filter(
            models.RouteStop.route_id == r.route_id,
            models.RouteStop.operation_type == "DROP_OFF"
        ).count()

        reports.append({
            "route_id": r.route_id,
            "courier_name": courier_name,
            "vehicle_registration": vehicle_reg,
            "total_distance_km": round(r.total_distance_km, 2),
            "total_revenue": round(r.total_revenue, 2),
            "route_cost": round(r.route_cost, 2),
            "net_profit": round(r.total_revenue - r.route_cost, 2), # Czysty zysk
            "parcels_delivered": parcels_count
        })
        
    return reports

# PUBLICZNY SYSTEM ŚLEDZENIA (TRACKING)
@app.get("/api/v1/tracking/{tracking_number}", summary="Publiczne śledzenie paczki")
def track_parcel(tracking_number: str, db: Session = Depends(get_db)):
    # 1. Szukamy paczki po unikalnym numerze
    parcel = db.query(models.Parcel).filter(models.Parcel.tracking_number == tracking_number).first()
    if not parcel:
        raise HTTPException(status_code=404, detail="Paczka o podanym numerze nie istnieje.")
    
    # 2. Pobieramy aktualny status i adres docelowy
    status_obj = db.query(models.Status).filter(models.Status.status_id == parcel.status_id).first()
    address = db.query(models.Address).filter(models.Address.address_id == parcel.recipient_address_id).first()
    
    # 3. Pobieramy pełną oś czasu (Timeline) wygenerowaną przez Triggery w bazie!
    history_records = db.query(models.ParcelHistory).filter(
        models.ParcelHistory.parcel_id == parcel.parcel_id
    ).order_by(models.ParcelHistory.updated_at).all()
    
    timeline = []
    for h in history_records:
        s = db.query(models.Status).filter(models.Status.status_id == h.status_id).first()
        timeline.append({
            "status": s.status_name if s else "Zaktualizowano",
            "date": h.updated_at
        })
        
    # 4. Wyciągamy ETA
    eta = None
    active_stop = db.query(models.RouteStop).join(
        models.Route, models.RouteStop.route_id == models.Route.route_id
    ).filter(
        models.RouteStop.parcel_id == parcel.parcel_id,
        models.Route.status.in_(["PLANNED", "IN_PROGRESS"])
    ).first()
    
    if active_stop and active_stop.estimated_arrival:
        eta = active_stop.estimated_arrival
        
    # 5. Składamy to w jedną paczkę danych dla Frontendu
    return {
        "tracking_number": parcel.tracking_number,
        "current_status": status_obj.status_name if status_obj else "Nieznany",
        "recipient_city": address.city if address else "Brak danych",
        "eta": eta,
        "timeline": timeline
    }

# ==========================================
# PANEL ADMINISTRATORA (SUPER ADMIN)
# ==========================================

@app.get("/api/v1/admin/users", summary="Pobierz listę pracowników")
def get_all_employees(admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    """
    Pobiera wszystkich dyspozytorów i kurierów (role_id > 1) wraz z ich przypisaniem do magazynu.
    """
    # Używamy złączenia (JOIN), żeby od razu pobrać nazwę magazynu, w którym pracują
    results = db.query(models.User, models.Warehouse.name).outerjoin(
        models.Warehouse, models.User.warehouse_id == models.Warehouse.warehouse_id
    ).filter(models.User.role_id.in_([2, 3, 4, 5])).all()
    
    employees = []
    for user, warehouse_name in results:
        employees.append({
            "user_id": user.user_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "role_id": user.role_id,
            "warehouse_name": warehouse_name if warehouse_name else "Centrala (Brak HUBu)",
            "is_active": user.is_active
        })
    return employees

@app.post("/api/v1/admin/users", status_code=status.HTTP_201_CREATED, summary="Utwórz nowego pracownika")
def create_employee(
    user_data: schemas.UserCreate, # Wykorzystujemy stary schemat rejestracji!
    warehouse_id: int, 
    admin: models.User = Depends(get_current_admin), 
    db: Session = Depends(get_db)
):
    """
    Zatrudnia nowego pracownika (Kuriera lub Dyspozytora) i przypisuje go do HUBu.
    """
    # 1. Sprawdzenie, czy email jest wolny
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        if existing_user.is_active:
            raise HTTPException(status_code=400, detail="Użytkownik o takim emailu już istnieje!")
        raise HTTPException(
            status_code=400,
            detail="Konto z tym adresem email jest w archiwum. Użyj opcji przywracania pracownika zamiast tworzyć nowe konto."
        )
        
    # 2. Utworzenie pracownika z przypisanym magazynem
    new_employee = models.User(
        email=user_data.email,
        password_hash=security.hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        role_id=user_data.role_id, # Admin z frontendu wyśle tu 2 (Kurier) lub 3 (Dyspozytor)
        warehouse_id=warehouse_id  # Przypisujemy pracownika do konkretnego miasta
    )
    db.add(new_employee)
    db.commit()
    
    return {"message": f"Pracownik {user_data.first_name} został dodany do systemu!"}

@app.get("/api/v1/admin/vehicles", summary="Pobierz całą flotę firmy")
def get_all_vehicles(admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    """
    Pobiera wszystkie pojazdy w firmie wraz z przypisanymi do nich magazynami.
    """
    results = db.query(models.Vehicle, models.Warehouse.name).outerjoin(
        models.Warehouse, models.Vehicle.warehouse_id == models.Warehouse.warehouse_id
    ).all()
    
    vehicles = []
    for vehicle, warehouse_name in results:
        vehicles.append({
            "vehicle_id": vehicle.vehicle_id,
            "registration_number": vehicle.registration_number,
            "capacity_kg": vehicle.capacity_kg,
            "capacity_m3": vehicle.capacity_m3,
            "status": vehicle.status,
            "vehicle_type": vehicle.vehicle_type,
            "warehouse_name": warehouse_name if warehouse_name else "Nieprzypisany"
        })
    return vehicles

@app.post("/api/v1/admin/vehicles", status_code=status.HTTP_201_CREATED, summary="Dodaj nowy pojazd do floty")
def create_vehicle(
    registration_number: str,
    capacity_kg: float,
    capacity_m3: float,
    vehicle_type: str,
    warehouse_id: int,
    admin: models.User = Depends(get_current_admin), 
    db: Session = Depends(get_db)
):
    """
    Kupuje/dodaje nowy pojazd (VAN lub TRUCK) i przypisuje go do HUBu.
    """
    # Sprawdzamy, czy rejestracja już istnieje
    if db.query(models.Vehicle).filter(models.Vehicle.registration_number == registration_number).first():
        raise HTTPException(status_code=400, detail="Pojazd o takiej rejestracji już istnieje w bazie!")

    if vehicle_type not in ["VAN", "TRUCK"]:
        raise HTTPException(status_code=400, detail="Dozwolone typy pojazdów to VAN lub TRUCK.")

    new_vehicle = models.Vehicle(
        registration_number=registration_number,
        capacity_kg=capacity_kg,
        capacity_m3=capacity_m3,
        status="ACTIVE",
        vehicle_type=vehicle_type,
        warehouse_id=warehouse_id
    )
    
    db.add(new_vehicle)
    db.commit()
    
    return {"message": f"Pojazd {registration_number} dodany do floty!"}

@app.get("/api/v1/admin/tariffs", summary="Pobierz cennik (taryfy)")
def get_tariffs(admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    """
    Pobiera wszystkie aktualne taryfy z bazy.
    """
    return db.query(models.DimensionalTariff).order_by(models.DimensionalTariff.tariff_id).all()

@app.put("/api/v1/admin/tariffs/{tariff_id}", summary="Zmień cenę gabarytu")
def update_tariff_price(
    tariff_id: int, 
    new_price: float, 
    admin: models.User = Depends(get_current_admin), 
    db: Session = Depends(get_db)
):
    """
    Zmienia cenę bazową wybranego gabarytu.
    """
    tariff = db.query(models.DimensionalTariff).filter(models.DimensionalTariff.tariff_id == tariff_id).first()
    if not tariff:
        raise HTTPException(status_code=404, detail="Taryfa nie znaleziona")
    
    tariff.base_price = new_price
    db.commit()
    
    return {"message": f"Cena gabarytu {tariff.size_category} zaktualizowana do {new_price} zł!"}

# --- ENDPOINTY DO EDYCJI PRACOWNIKÓW I POJAZDÓW ---
@app.put("/api/v1/admin/users/{user_id}", summary="Edytuj pracownika")
def update_employee(user_id: int, data: schemas.AdminUserUpdate, admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Nie znaleziono pracownika")
    
    user.first_name = data.first_name
    user.last_name = data.last_name
    user.email = data.email
    user.phone = data.phone
    user.role_id = data.role_id
    user.warehouse_id = data.warehouse_id
    
    if data.password:
        user.password_hash = security.hash_password(data.password)
        
    db.commit()
    return {"message": "Zaktualizowano pracownika"}

@app.put("/api/v1/admin/vehicles/{vehicle_id}", summary="Edytuj pojazd")
def update_vehicle(vehicle_id: int, data: schemas.AdminVehicleUpdate, admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Nie znaleziono pojazdu")
    
    vehicle.registration_number = data.registration_number
    vehicle.capacity_kg = data.capacity_kg
    vehicle.capacity_m3 = data.capacity_m3
    vehicle.vehicle_type = data.vehicle_type
    vehicle.warehouse_id = data.warehouse_id
    vehicle.status = data.status
    
    db.commit()
    return {"message": "Zaktualizowano pojazd"}

@app.delete("/api/v1/admin/users/{user_id}", summary="Usuń pracownika (Soft Delete)")
def delete_employee(user_id: int, admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Nie znaleziono pracownika")
    
    user.is_active = False 
    db.commit()
    return {"message": "Pracownik zwolniony"}

@app.delete("/api/v1/admin/vehicles/{vehicle_id}", summary="Usuń pojazd (Soft Delete)")
def delete_vehicle(vehicle_id: int, admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Nie znaleziono pojazdu")
    
    vehicle.status = "INACTIVE"
    db.commit()
    return {"message": "Pojazd wycofany"}

# --- ENDPOINTY DO PRZYWRACANIA Z ARCHIWUM (Cofanie Soft Delete) ---
@app.patch("/api/v1/admin/users/{user_id}/restore", summary="Przywróć pracownika")
def restore_employee(user_id: int, admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Nie znaleziono pracownika")
    
    user.is_active = True # Cofamy zwolnienie
    db.commit()
    return {"message": "Pracownik został przywrócony!"}

@app.patch("/api/v1/admin/vehicles/{vehicle_id}/restore", summary="Przywróć pojazd")
def restore_vehicle(vehicle_id: int, admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Nie znaleziono pojazdu")
    
    vehicle.status = "ACTIVE" # Wracamy auto do floty
    db.commit()
    return {"message": "Pojazd powrócił do aktywnej floty!"}

# --- HELPER: Pozbywamy się polskich znaków, żeby domyślna czcionka PDF (Helvetica) nie wybuchła ---
def strip_accents(text: str) -> str:
    replacements = {'ą':'a', 'ć':'c', 'ę':'e', 'ł':'l', 'ń':'n', 'ó':'o', 'ś':'s', 'ź':'z', 'ż':'z',
                    'Ą':'A', 'Ć':'C', 'Ę':'E', 'Ł':'L', 'Ń':'N', 'Ó':'O', 'Ś':'S', 'Ź':'Z', 'Ż':'Z'}
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

@app.get("/api/v1/parcels/{parcel_id}/label", summary="Pobierz etykietę PDF")
def get_parcel_label(parcel_id: int, db: Session = Depends(get_db), current_user_email: str = Depends(security.get_current_user_email)):
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    parcel = db.query(models.Parcel).filter(models.Parcel.parcel_id == parcel_id, models.Parcel.sender_id == user.user_id).first()
    
    if not parcel:
        raise HTTPException(status_code=404, detail="Paczka nie znaleziona lub brak dostępu.")
        
    rec_addr = db.query(models.Address).filter(models.Address.address_id == parcel.recipient_address_id).first()
    sen_addr = db.query(models.Address).filter(models.Address.address_id == parcel.sender_address_id).first()

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A6) # Format A6 (Standardowa etykieta 105 x 148 mm)
    
    # Rysujemy etykietę na wirtualnym płótnie
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20, 390, "ROYALE PACKAGE")
    
    c.setFont("Helvetica", 10)
    c.drawString(20, 365, "NADAWCA:")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20, 350, strip_accents(parcel.sender_custom_name))
    c.setFont("Helvetica", 10)
    c.drawString(20, 335, strip_accents(f"{sen_addr.street} {sen_addr.building_number}"))
    c.drawString(20, 320, strip_accents(f"{sen_addr.postal_code} {sen_addr.city}"))
    
    c.line(20, 305, 270, 305) # Linia oddzielająca
    
    c.setFont("Helvetica", 12)
    c.drawString(20, 280, "ODBIORCA:")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20, 260, strip_accents(parcel.recipient_custom_name))
    c.setFont("Helvetica", 12)
    c.drawString(20, 240, strip_accents(f"{rec_addr.street} {rec_addr.building_number}"))
    c.drawString(20, 220, strip_accents(f"{rec_addr.postal_code} {rec_addr.city}"))
    c.drawString(20, 200, f"Tel: {parcel.recipient_phone}")
    
    c.line(20, 180, 270, 180) # Linia oddzielająca
    
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(145, 140, parcel.tracking_number)
    
    # Symulacja Kodu Kreskowego (Ramka + Pionowe kreski)
    c.rect(45, 80, 200, 40)
    c.setFont("Helvetica", 12)
    c.drawCentredString(145, 95, "|| ||| | || ||| || | ||| ||")
    
    c.save()
    buffer.seek(0)
    
    return Response(
        content=buffer.getvalue(), 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename=etykieta_{parcel.tracking_number}.pdf"}
    )

@app.get("/api/v1/contacts", summary="Pobierz książkę adresową klienta")
def get_contacts(current_user_email: str = Depends(security.get_current_user_email), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    contacts = db.query(models.SavedContact).filter(models.SavedContact.user_id == user.user_id).all()
    
    results = []
    # Pobieramy koordynaty z PostGIS za pomocą bezpiecznego SQLa
    sql_coords = text("SELECT ST_X(geom) as lon, ST_Y(geom) as lat FROM addresses WHERE address_id = :id AND geom IS NOT NULL")
    for c in contacts:
        coords = db.execute(sql_coords, {"id": c.address_id}).fetchone()
        lat, lon = (coords[1], coords[0]) if coords else (None, None)
        
        results.append({
            "contact_id": c.contact_id,
            "first_name": c.first_name,
            "last_name": c.last_name,
            "phone": c.phone,
            "address": {
                "street": c.address.street,
                "building_number": c.address.building_number,
                "city": c.address.city,
                "postal_code": c.address.postal_code,
                "lat": lat,
                "lon": lon
            }
        })
    return results

@app.delete("/api/v1/contacts/{contact_id}", summary="Usuń kontakt z książki adresowej")
def delete_contact(
    contact_id: int, 
    current_user_email: str = Depends(security.get_current_user_email), 
    db: Session = Depends(get_db)
):
    # Znajdujemy użytkownika
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    
    # Szukamy kontaktu, upewniając się, że należy on do zalogowanego klienta (bezpieczeństwo!)
    contact = db.query(models.SavedContact).filter(
        models.SavedContact.contact_id == contact_id, 
        models.SavedContact.user_id == user.user_id
    ).first()
    
    if not contact:
        raise HTTPException(status_code=404, detail="Nie znaleziono kontaktu")
        
    db.delete(contact)
    db.commit()
    return {"message": "Kontakt usunięty z książki adresowej."}



# Zgłaszanie reklamacji przez klienta (np. paczka uszkodzona, nie dostarczona, itp.)

@app.post("/api/v1/client/complaints", response_model=schemas.Complaint, summary="Zgłoś reklamację do paczki")
def create_complaint(
    complaint_in: schemas.ComplaintCreate,
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email) # Pobieramy email zalogowanego klienta, żeby znaleźć jego ID i zweryfikować, że reklamuje własną paczkę
):
    user = db.query(models.User).filter(models.User.email == current_user_email).first() # Pobieramy dane zalogowanego klienta
    parcel = db.query(models.Parcel).filter(models.Parcel.parcel_id == complaint_in.parcel_id).first() # Pobieramy paczkę, do której klient chce zgłosić reklamację
    
    if not parcel:
        raise HTTPException(status_code=404, detail="Nie znaleziono paczki")
    
    # Sprawdzam, czy to na pewno paczka tego użytkownika
    if parcel.sender_id != user.user_id:
        raise HTTPException(status_code=403, detail="Możesz reklamować tylko własne paczki")

    # Reklamację można zgłosić dopiero po dostarczeniu paczki
    if parcel.status_id != 6:
        raise HTTPException(status_code=400, detail="Reklamację można zgłosić tylko dla paczki dostarczonej")

    # Jedna paczka = jedna reklamacja klienta (bez duplikatów)
    existing_complaint = db.query(models.Complaint).filter(
        models.Complaint.parcel_id == complaint_in.parcel_id,
        models.Complaint.user_id == user.user_id
    ).first()
    if existing_complaint:
        raise HTTPException(status_code=400, detail="Dla tej paczki istnieje już zgłoszona reklamacja")
    
    
    new_complaint = models.Complaint(
        parcel_id=complaint_in.parcel_id,
        user_id=user.user_id,
        reason=complaint_in.reason,
        description=complaint_in.description,
        status="PENDING"
    )
    db.add(new_complaint)
    db.commit()
    db.refresh(new_complaint)
    return new_complaint

@app.get("/api/v1/client/complaints", response_model=list[schemas.Complaint], summary="Pobierz moje reklamacje")
def get_my_complaints(
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Nie znaleziono użytkownika")

    return db.query(models.Complaint).filter(models.Complaint.user_id == user.user_id).all()

# Endpoint dla pracowników (Dyspozytorów) do przeglądania wszystkich zgłoszonych reklamacji

@app.get("/api/v1/dispatcher/complaints", response_model=list[schemas.Complaint])
def get_all_complaints(db: Session = Depends(get_db)):
    # Pobieram wszystkie reklamacje do panelu pracownika
    return db.query(models.Complaint).all()


# Endpoint dla pracowników (Dyspozytorów) do rozpatrywania reklamacji (akceptacja lub odrzucenie) i ewentualnego wyliczenia kwoty zwrotu dla klienta

@app.patch("/api/v1/dispatcher/complaints/{complaint_id}/resolve")
def resolve_complaint(
    complaint_id: int,
    update_data: schemas.ComplaintUpdate,
    db: Session = Depends(get_db)
):
    complaint = db.query(models.Complaint).filter(models.Complaint.complaint_id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Reklamacja nie istnieje")

    complaint.status = update_data.status
    complaint.resolved_at = datetime.utcnow()

    # Jeśli uznaję reklamację, wyliczam kwotę zwrotu
    if update_data.status == "ACCEPTED":
        parcel = db.query(models.Parcel).filter(models.Parcel.parcel_id == complaint.parcel_id).first()
        # Zwracam wartość towaru + koszt przesyłki
        complaint.refund_amount = (parcel.declared_value or 0.0) + parcel.calculated_price
    else:
        complaint.refund_amount = 0.0

    db.commit()
    return {"message": f"Reklamacja została {update_data.status.lower()}.", "refund": complaint.refund_amount}


# Endpoint modyfikacji profilu klienta
@app.patch("/api/v1/client/profile", summary="Edytuj mój profil")
def update_user_profile(
    profile_data: schemas.UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
   # Pobieramy rekord zalogowanego użytkownika w celu wyciągniecia tokenu JWT
   user =db.query(models.User).filter(models.User.email == current_user_email).first()
   if not user:
       raise HTTPException(status_code=404, detail="Nie znaleziono użytkownika")
   
   # Zaszyfrowanie hasła, jeśli klient chce je zmienić
   hashed_password = None
   if profile_data.password:
    hashed_password = security.hash_password(profile_data.password)

   # Używamy surowego SQL, żeby móc korzystać z funkcji COALESCE i aktualizować tylko podane pola (reszta pozostaje bez zmian)
   update_query = text("""
        UPDATE users 
        SET 
            first_name = COALESCE(:first_name, first_name),
            last_name = COALESCE(:last_name, last_name),
            phone = COALESCE(:phone, phone),
            email = COALESCE(:email, email),
            password_hash = COALESCE(:password_hash, password_hash)
        WHERE user_id = :user_id 
    """)
   
   # Wykonanie zapytania z przekazaniem nowych danych lub NULL, jeśli pole nie zostało podane
   try:
       db.execute(update_query, {
             "first_name": profile_data.first_name,
             "last_name": profile_data.last_name,
             "phone": profile_data.phone,
             "email": profile_data.email,
             "password_hash": hashed_password,
             "user_id": user.user_id
        })
       
       db.commit()
       return {"message": "Profil zaktualizowany pomyślnie!", "status": "success"}
   except Exception as e:
       db.rollback()
       if "unique constraint" in str(e).lower():
           raise HTTPException(status_code=400, detail="Adres e-mail już istnieje w systemie.")
       raise HTTPException(status_code=500, detail=f"Błąd podczas aktualizacji profilu: {str(e)}")

