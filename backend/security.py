from passlib.context import CryptContext

# Konfiguracja algorytmu haszującego
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Szyfruje hasło czystym tekstem do bezpiecznego hasha"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Sprawdza, czy podane hasło pasuje do hasha w bazie"""
    return pwd_context.verify(plain_password, hashed_password)