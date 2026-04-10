import re
from pydantic import BaseModel, Field, field_validator

# 1. Schemat wejściowy (czego oczekujemy przy rejestracji)
class UserCreate(BaseModel):
    email: str = Field(..., max_length=100, description="Adres email użytkownika")
    password: str = Field(..., min_length=8, max_length=128, description="Hasło użytkownika")
    first_name: str = Field(..., max_length=50, description="Imię użytkownika")
    last_name: str = Field(..., max_length=50, description="Nazwisko użytkownika")
    role_id: int = Field(..., description="ID roli użytkownika") # 1 = Klient, 2 = Kurier, 3 = Dyspozytor
    phone: str | None = Field(None, max_length=20, description="Numer telefonu użytkownika")

    @field_validator('phone')
    @classmethod
    def validate_and_normalize_phone(cls, v: str | None) -> str | None:
        if not v:
            return v
        
        # Wyrazenie regularne do usunięcia wszystkich znaków oprócz cyfr
        cleaned_phone = re.sub(r'\D', '', v)

        if len(cleaned_phone) < 9 or len(cleaned_phone) > 15:
            raise ValueError('Numer telefonu musi mieć od 9 do 15 cyfr')
        
        return cleaned_phone

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