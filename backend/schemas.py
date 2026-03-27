from pydantic import BaseModel

# 1. Schemat wejściowy (czego oczekujemy przy rejestracji)
class UserCreate(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    role_id: int # 1 = Klient, 2 = Kurier, 3 = Dyspozytor
    phone: str | None = None

# 2. Schemat wyjściowy (co zwracamy po rejestracji)
class UserResponse(BaseModel):
    user_id: int
    email: str
    first_name: str
    last_name: str
    role_id: int

    # Konfiguracja Pydantic do pracy z SQLAlchemy
    class Config:
        from_attributes = True