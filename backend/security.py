import os
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError, ExpiredSignatureError


# -- KONFIGURACJA JWT - -
SECRET_KEY = os.getenv("SECRET_KEY", "super-tajny-klucz-royale-package")
ALGORITHM = "HS256"

# Czas ważności tokenów
ACCESS_TOKEN_EXPIRE_MINUTES = 5 # Acces token ważny 5 minut
REFRESH_TOKEN_EXPIRE_DAYS = 7   # Refresh token ważny 7 dni

# Bramkarz - mówi FastAPI, gdzie szukać logowania
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")

# Konfiguracja algorytmu haszującego
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Szyfruje hasło czystym tekstem do bezpiecznego hasha"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Sprawdza, czy podane hasło pasuje do hasha w bazie"""
    return pwd_context.verify(plain_password, hashed_password)

# 1. GENEROWANIE KRÓTKIEGO TOKENA (Do autoryzacji zapytań)
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"}) # Dodajemy typ dla pewności
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# 2. GENEROWANIE DŁUGIEGO TOKENA (Do odnawiania sesji)
def create_refresh_token(data: dict) -> str:
    to_encode = {"sub": data.get("sub")} # Refresh token potrzebuje tylko identyfikatora (emaila)
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Bramkarz (weryfikacja Access Tokena)
def get_current_user_email(token: str = Depends(oauth2_scheme)) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nie można zweryfikować uprawnień",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Sprawdzamy czy ktoś nie próbuje nas oszukać i wysłać Refresh Tokena zamiast Access Tokena!
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Nieprawidłowy typ tokena. Oczekiwano Access Token.")
            
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return email
        
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token wygasł.", # Złapiemy to na frontendzie, żeby po cichu odświeżyć!
            headers={"WWW-Authenticate": "Bearer"},
        )
    except PyJWTError:
        raise credentials_exception