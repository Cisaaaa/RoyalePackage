import os
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext

# -- KONFIGURACJA JWT - -
SECRET_KEY = os.getenv("SECRET_KEY", "super-tajny-klucz-royale-package")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Token ważny przez 60 minut


# Konfiguracja algorytmu haszującego
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Szyfruje hasło czystym tekstem do bezpiecznego hasha"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Sprawdza, czy podane hasło pasuje do hasha w bazie"""
    return pwd_context.verify(plain_password, hashed_password)

# --- NOWA FUNKCJA DO GENEROWANIA TOKENA ---
def create_access_token(data: dict) -> str:
    """Generuje token JWT z danymi użytkownika (payload)"""
    to_encode = data.copy()
    # Ustawiamy czas wygaśnięcia przepustki
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    # Podpisujemy token naszym tajnym kluczem
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt