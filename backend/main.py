import os
from fastapi import FastAPI
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import schemas
import security
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

# Importujemy bazę danych i modele
from database import engine, Base, get_db, SessionLocal
import models 

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

@app.post("/api/v1/login", summary="Logowanie i pobranie tokena JWT")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Endpoint weryfikujący email i hasło. Jeśli poprawne, zwraca Token JWT.
    """
    # 1. Szukamy użytkownika po adresie email (Swagger podaje go w polu 'username')
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    # 2. Sprawdzamy czy user istnieje i czy hasło się zgadza
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy email lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Tworzymy paczkę danych do tokena (dodajemy rolę, przyda się Dominikowi na frontendzie!)
    token_data = {
        "sub": user.email,
        "role_id": user.role_id
    }
    
    # 4. Drukujemy token
    access_token = security.create_access_token(data=token_data)
    
    return {"access_token": access_token, "token_type": "bearer"}

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
           
