import os
from fastapi import FastAPI
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import schemas
import security

# Importujemy bazę danych i modele
from database import engine, Base, get_db, SessionLocal
import models 

#Generowanie tabel w bazie danych na podstawie modeli (jeśli jeszcze nie istnieją)
models.Base.metadata.create_all(bind=engine) 

#Funkcja AUTO-SEEDINGU
def seed_db():
    # Tworzymy ręcznie sesję tylko na potrzeby startu aplikacji
    db = SessionLocal()
    try:
        # Sprawdzamy, czy w tabeli roles są już jakieś rekordy
        role_count = db.query(models.Role).count()
        if role_count == 0:
            print("INFO: Tabela ról jest pusta. Rozpoczynam seeding...")
            default_roles = [
                models.Role(role_name="Klient"),
                models.Role(role_name="Kurier"),
                models.Role(role_name="Dyspozytor")
            ]
            db.add_all(default_roles)
            db.commit()
            print("SUCCESS: Role zostały dodane pomyślnie!")
        else:
            print(f"INFO: Znaleziono {role_count} ról. Pomijam seeding.")
    except Exception as e:
        print(f"ERROR: Błąd podczas seedingu: {e}")
        db.rollback()
    finally:
        db.close()

# Wykonujemy seeding zaraz po stworzeniu tabel
seed_db()

# Inicjalizacja aplikacji FastAPI
app = FastAPI(
    title="Royale Package API",
    description="API dla systemu logistycznego",
    version="1.0.0"
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
           
