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

# Schemat dla paczek
# 1. Model Adresu (dla nadawcy i odbiorcy)
class AddressBase(BaseModel):
    street: str = Field(..., max_length=255, description="Nazwa ulicy")
    building_number: str = Field(..., max_length=20, description="Numer budynku i/lub lokalu") 
    city: str = Field(..., max_length=100, description="Miasto")
    postal_code: str = Field(..., max_length=20, description="Kod pocztowy (np. 00-000)")

# 2. Główny Payload
class ParcelCreate(BaseModel):
    sender_name: str = Field(..., max_length=200, description="Imię i nazwisko nadawcy")
    sender_phone: str = Field(..., max_length=20, description="Telefon nadawcy")
    sender_address: AddressBase # Zagnieżdżony model!

    recipient_name: str = Field(..., max_length=200, description="Imię i nazwisko odbiorcy")
    recipient_phone: str = Field(..., max_length=20, description="Telefon odbiorcy")
    recipient_address: AddressBase # Zagnieżdżony model!

    tariff_id: int = Field(..., description="ID wybranego gabarytu (1=A, 2=B, 3=C)")
    
    # Symulacja płatności PENDING/PAID
    simulate_payment: bool = Field(False, description="Zaznacz, jeśli klient opłaca z góry")

    #walidator dla numerów telefonów
    @field_validator('sender_phone', 'recipient_phone')
    @classmethod
    def clean_phone(cls, v: str) -> str:
        cleaned = re.sub(r'\D', '', v)
        if len(cleaned) < 9 or len(cleaned) > 15:
            raise ValueError('Numer telefonu musi mieć od 9 do 15 cyfr')
        return cleaned
    
# 3. Model wyjściowy
class ParcelResponse(BaseModel):
    parcel_id: int
    tracking_number: str
    status_id: int
    calculated_price: float

    class Config:
        from_attributes = True