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

# Importujemy bazę danych i modele
from database import engine, Base, get_db, SessionLocal
import models 

# Importujemy bibliotekę do obsługi JWT refresh
import jwt

#Generowanie tabel w bazie danych na podstawie modeli (jeśli jeszcze nie istnieją)
models.Base.metadata.create_all(bind=engine) 

# Funkcja AUTO-SEEDINGU
def seed_db():
    db = SessionLocal()
    try:
        # 1. ROLE UŻYTKOWNIKÓW
        if db.query(models.Role).count() == 0:
            db.add_all([
                models.Role(role_name="Klient"),
                models.Role(role_name="Kurier"),
                models.Role(role_name="Dyspozytor")
            ])
            db.commit()

        # 2. STATUSY PACZEK
        if db.query(models.Status).count() == 0:
            db.add_all([
                models.Status(status_name="Zarejestrowana"),
                models.Status(status_name="W magazynie nadawczym"),
                models.Status(status_name="W drodze"),
                models.Status(status_name="Wydana kurierowi"),
                models.Status(status_name="Dostarczona")
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
            reg_waw = models.Region(region_name="Mazowieckie")
            reg_krk = models.Region(region_name="Małopolskie")
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
            # Dzięki temu nie musisz ich zakładać ręcznie. Hasło to: "password123"
            import security
            hashed_pw = security.hash_password("password123")
            
            disp_waw = models.User(email="waw@royale.pl", password_hash=hashed_pw, first_name="Jan", last_name="Warszawski", role_id=3, warehouse_id=hub_waw.warehouse_id)
            disp_krk = models.User(email="krk@royale.pl", password_hash=hashed_pw, first_name="Anna", last_name="Krakowska", role_id=3, warehouse_id=hub_krk.warehouse_id)
            
            # Oraz testowy kurier i pojazd
            courier = models.User(email="kurier@royale.pl", password_hash=hashed_pw, first_name="Szybki", last_name="Bill", role_id=2, warehouse_id=hub_waw.warehouse_id)
            vehicle = models.Vehicle(registration_number="WA 12345", capacity_kg=1000.0, capacity_m3=10.0, status="ACTIVE")
            
            db.add_all([disp_waw, disp_krk, courier, vehicle])
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
        raise HTTPException(status_code=400, detail="Użytkownik o takim adresie email juz istnieje")
    
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
        current_warehouse_id=1, 
        status_id=1 
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
    
    if user.role_id != 2:
        raise HTTPException(status_code=403, detail="Brak uprawnień. Ten widok jest tylko dla kurierów.")

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
                "lon": lon
            })
        
        # SCENARIUSZ B: Start z Magazynu (HUB)
        elif stop.warehouse_id and stop.operation_type == "WAREHOUSE_TRANSFER":
            warehouse = db.query(models.Warehouse).filter(models.Warehouse.warehouse_id == stop.warehouse_id).first()
            address = db.query(models.Address).filter(models.Address.address_id == warehouse.address_id).first()
            
            # Pobieramy współrzędne surowym SQL-em
            lat, lon = None, None
            if address:
                coords = db.execute(sql_coords, {"id": address.address_id}).fetchone()
                if coords and coords[0] is not None and coords[1] is not None:
                    lon, lat = coords[0], coords[1]
            
            results.append({
                "stop_id": stop.stop_id,
                "parcel_id": 0, 
                "tracking_number": "START TRASY",
                "operation_type": stop.operation_type,
                "recipient_name": warehouse.name,
                "recipient_phone": "-",
                "street": address.street,
                "building_number": address.building_number,
                "city": address.city,
                "lat": lat,
                "lon": lon
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

    # 2. Szukamy paczek ze statusem 2 ("W magazynie nadawczym"), które NIE MAJĄ jeszcze rekordu w route_stops
    unassigned_parcels = db.query(models.Parcel).outerjoin(
        models.RouteStop, models.Parcel.parcel_id == models.RouteStop.parcel_id
    ).filter(
        models.Parcel.status_id == 2,
        models.RouteStop.stop_id == None # Magia SQL: Zwróć tylko te, które nie połączyły się z trasą
    ).all()

    # 3. Składamy dane dla widoku tabeli na frontendzie
    results = []
    for parcel in unassigned_parcels:
        address = db.query(models.Address).filter(models.Address.address_id == parcel.recipient_address_id).first()
        results.append({
            "parcel_id": parcel.parcel_id,
            "tracking_number": parcel.tracking_number,
            "recipient_city": address.city if address else "Brak danych",
            "recipient_street": address.street if address else "Brak danych",
            "recipient_name": parcel.recipient_custom_name,
            "calculated_price": parcel.calculated_price
        })
    return results

@app.get("/api/v1/dispatcher/fleet", summary="Pobierz listę kurierów i pojazdów")
def get_fleet(
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    # 1. Sprawdzamy uprawnienia (Tylko Dyspozytor - rola 3)
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user or user.role_id != 3:
        raise HTTPException(status_code=403, detail="Brak uprawnień.")
    
    # 2. Pobieramy listę aktywnych kurierów i pojazdów z bazy danych
    couriers = db.query(models.User).filter(models.User.role_id == 2).all()
    vehicles = db.query(models.Vehicle).filter(models.Vehicle.status == "ACTIVE").all()

    # 3. Składamy dane do zwrócenia na frontend
    return {
        "couriers": [{"user_id": c.user_id, "first_name": c.first_name, "last_name": c.last_name} for c in couriers],
        "vehicles": [{"vehicle_id": v.vehicle_id, "registration_number": v.registration_number, "capacity_kg": v.capacity_kg} for v in vehicles]
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
            db.query(models.Parcel).filter(models.Parcel.parcel_id == step["id"]).update({"status_id": 4})

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
    if not user or user.role_id != 2:
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
    parcel.status_id = 5

    stop = db.query(models.RouteStop).filter(
        models.RouteStop.parcel_id == parcel_id,
        models.RouteStop.status == "PLANNED"
    ).first()
    
    if stop:
        stop.status = "COMPLETED"
        db.flush() 

    # Zapisujemy zmianę statusu paczki i przystanku
    db.commit()

    return {"message": "Paczka doręczona pomyślnie."}

# RĘCZNE ZAKOŃCZENIE TRASY PRZEZ KURIERA
@app.put("/api/v1/courier/routes/complete", summary="Zakończ aktywną trasę i wróć do bazy")
def complete_active_route(
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user or user.role_id != 2:
        raise HTTPException(status_code=403, detail="Brak uprawnień.")

    # Szukamy trasy tego kuriera, która jest "W trakcie"
    route = db.query(models.Route).filter(
        models.Route.courier_id == user.user_id,
        models.Route.status == "IN_PROGRESS"
    ).first()
    
    if not route:
        raise HTTPException(status_code=404, detail="Brak aktywnej trasy do zakończenia.")
        
    route.status = "COMPLETED"
    db.commit()
    
    return {"message": "Trasa oficjalnie zakończona!"}

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
    warehouse = db.query(models.Warehouse).filter(models.Warehouse.warehouse_id == 1).first()
    if not warehouse:
        raise HTTPException(status_code=400, detail="Brak magazynu HUB (warehouse_id=1).")

    sql_coords = text("SELECT ST_X(geom) as lon, ST_Y(geom) as lat FROM addresses WHERE address_id = :id AND geom IS NOT NULL")
    hub_coords = db.execute(sql_coords, {"id": warehouse.address_id}).fetchone()
    if not hub_coords:
        raise HTTPException(status_code=400, detail="HUB nie posiada współrzędnych GPS.")

    hub_lon_lat = [hub_coords[0], hub_coords[1]]

    # 3. Paczki do przypisania: status=2 i brak przypisania w route_stops
    parcels = db.query(models.Parcel).outerjoin(
        models.RouteStop, models.Parcel.parcel_id == models.RouteStop.parcel_id
    ).filter(
        models.Parcel.status_id == 2,
        models.RouteStop.stop_id == None
    ).all()

    if not parcels:
        raise HTTPException(status_code=400, detail="Brak paczek w magazynie do przypisania.")

    # 4. Dostępni kurierzy i aktywne pojazdy (1:1 do min długości)
    couriers = db.query(models.User).filter(models.User.role_id == 2).order_by(models.User.user_id).all()
    vehicles = db.query(models.Vehicle).filter(models.Vehicle.status == "ACTIVE").order_by(models.Vehicle.vehicle_id).all()

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

            db.query(models.Parcel).filter(models.Parcel.parcel_id == parcel_id).update({"status_id": 4})

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