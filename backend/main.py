import os
from fastapi import FastAPI
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import schemas
import security
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import random

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
            print("INFO: Tabela ról jest pusta. Dodaję role...")
            db.add_all([
                models.Role(role_name="Klient"),
                models.Role(role_name="Kurier"),
                models.Role(role_name="Dyspozytor")
            ])
            db.commit()
            print("SUCCESS: Role dodane!")

        # 2. STATUSY PACZEK
        if db.query(models.Status).count() == 0:
            print("INFO: Tabela statusów jest pusta. Dodaję statusy...")
            db.add_all([
                models.Status(status_name="Zarejestrowana"),
                models.Status(status_name="W magazynie nadawczym"),
                models.Status(status_name="W drodze"),
                models.Status(status_name="Wydana kurierowi"),
                models.Status(status_name="Dostarczona")
            ])
            db.commit()
            print("SUCCESS: Statusy dodane!")

        # 3. TARYFY / GABARYTY
        if db.query(models.DimensionalTariff).count() == 0:
            print("INFO: Tabela taryf jest pusta. Dodaję cennik...")
            db.add_all([
                models.DimensionalTariff(size_category="A", max_weight_kg=5.0, base_price=15.99),
                models.DimensionalTariff(size_category="B", max_weight_kg=15.0, base_price=20.99),
                models.DimensionalTariff(size_category="C", max_weight_kg=30.0, base_price=29.99)
            ])
            db.commit()
            print("SUCCESS: Taryfy dodane!")

        # 4. DOMYŚLNY MAGAZYN (Wymagany do logistyki)
        if db.query(models.Warehouse).count() == 0:
            print("INFO: Brak magazynów. Tworzę główny HUB...")
            
            # Najpierw tworzymy Region
            region = models.Region(region_name="Mazowieckie")
            db.add(region)
            db.commit()
            db.refresh(region)

            # Potem tworzymy fizyczny adres dla Magazynu (bez współrzędnych na razie)
            address = models.Address(
                street="ul. Logistyczna",
                building_number="1",
                city="Warszawa",
                postal_code="00-001"
            )
            db.add(address)
            db.commit()
            db.refresh(address)

            # Na końcu sam Magazyn, przypinając do niego ID adresu i regionu
            warehouse = models.Warehouse(
                address_id=address.address_id,
                region_id=region.region_id,
                name="HUB Centralny Warszawa",
                type="HUB"
            )
            db.add(warehouse)
            db.commit()
            print("SUCCESS: Główny HUB dodany!")

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
    current_user_email: str = Depends(security.get_current_user_email) # Ochroniarz: tylko zalogowani!
):
    """
    Endpoint do tworzenia nowej przesyłki przez zalogowanego klienta.
    Zapisuje adresy, wylicza cenę i tworzy główny rekord.
    """
    # 1. Identyfikacja klienta
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Nie znaleziono użytkownika")
    
    # 2. Pobranie cennika (żeby frontend nas nie oszukał wysyłając własną cenę)
    tariff = db.query(models.DimensionalTariff).filter(models.DimensionalTariff.tariff_id == parcel_data.tariff_id).first()
    if not tariff:
        raise HTTPException(status_code=404, detail="Wybrany gabaryt nie istnieje")
    
    # 3. Tworzymy i zapisujemy adresy
    sender_address = models.Address(
        street=parcel_data.sender_address.street,
        building_number=parcel_data.sender_address.building_number, 
        city=parcel_data.sender_address.city,
        postal_code=parcel_data.sender_address.postal_code
    )
    recipient_address = models.Address(
        street=parcel_data.recipient_address.street,
        building_number=parcel_data.recipient_address.building_number,
        city=parcel_data.recipient_address.city,
        postal_code=parcel_data.recipient_address.postal_code
    )

    db.add(sender_address)
    db.add(recipient_address)
    db.flush() # Wymuszamy wygenerowanie ID dla adresów, zanim stworzymy paczkę

    # 4. generowanie unikalnego numeru przesyłki
    while True:
        tracking_num = f"RP{random.randint(1000000, 9999999)}PL"
        existing_parcel = db.query(models.Parcel).filter(models.Parcel.tracking_number == tracking_num).first()
        if not existing_parcel:
            break # Numer jest wolny, wychodzimy z pętli!

    # --- NOWA LOGIKA CENNIKA ---
    final_price = float(tariff.base_price)
    COD_FEE = 5.00 # Stała dopłata za pobranie

    # Jeśli klient NIE opłaca z góry (czyli wybiera pobranie), doliczamy 5 zł
    if not parcel_data.simulate_payment:
        final_price += COD_FEE

    # 5. Złożenie paczki w całość
    new_parcel = models.Parcel(
        tracking_number=tracking_num,
        sender_id=user.user_id,
        sender_address_id=sender_address.address_id,
        recipient_address_id=recipient_address.address_id,
        recipient_phone=parcel_data.recipient_phone,
        tariff_id=parcel_data.tariff_id,
        calculated_price=final_price, # Zapisujemy całkowitą cenę!
        current_warehouse_id=1, 
        status_id=1 
    )
    db.add(new_parcel)
    db.commit()
    db.refresh(new_parcel)

    # 7. Symulacja płatności i Pobranie (COD)
    if parcel_data.simulate_payment:
        # Płaci z góry (bez dopłaty)
        payment = models.Payment(
            parcel_id=new_parcel.parcel_id,
            payer_id=user.user_id,
            amount=final_price, 
            status="PAID" 
        )
        db.add(payment)
        new_parcel.is_cod = False 
        new_parcel.cod_amount = None

    else:
        # Płaci przy odbiorze (z dopłatą 5 zł)
        payment = models.Payment(
            parcel_id=new_parcel.parcel_id,
            payer_id=user.user_id,
            amount=final_price, 
            status="PENDING" 
        )
        db.add(payment)
        
        new_parcel.is_cod = True
        # Kurier musi pobrać od klienta całkowitą kwotę (cena bazowa + 5 zł dopłaty)
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
    current_user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="Nie znaleziono użytkownika")
    # Pobieramy wszystkie paczki, gdzie zalogowany użytkownik jest nadawcą
    parcels = db.query(models.Parcel).filter(models.Parcel.sender_id == current_user.user_id).all()
    return parcels