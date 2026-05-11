from datetime import datetime
import re
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional

# --- FUNKCJA POMOCNICZA DLA TELEFONÓW ---
def normalize_polish_phone(v: str | None) -> str | None:
    if not v:
        return v
    
    # Usuwamy wszystkie znaki z wyjątkiem cyfr
    cleaned = re.sub(r'\D', '', v)
    
    # Usunięcie polskiego kierunkowego (gdyby frontend jednak go przysłał)
    if cleaned.startswith('48') and len(cleaned) == 11:
        cleaned = cleaned[2:]
    elif cleaned.startswith('0048') and len(cleaned) == 13:
        cleaned = cleaned[4:]

    if len(cleaned) != 9:
        raise ValueError('Numer telefonu musi mieć dokładnie 9 cyfr')
    
    return cleaned


# --- 1. SCHEMATY UŻYTKOWNIKA ---
class UserCreate(BaseModel):
    email: str = Field(..., max_length=100, description="Adres email użytkownika")
    password: str = Field(..., min_length=8, max_length=128, description="Hasło użytkownika")
    first_name: str = Field(..., max_length=50, description="Imię użytkownika")
    last_name: str = Field(..., max_length=50, description="Nazwisko użytkownika")
    role_id: int = Field(..., description="ID roli użytkownika")
    phone: str | None = Field(None, max_length=20, description="Numer telefonu użytkownika")

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        return normalize_polish_phone(v)

    # Automatyczne rozdzielanie imienia i nazwiska w razie potrzeby
    @model_validator(mode='before')
    @classmethod
    def split_names(cls, data: dict) -> dict:
        if isinstance(data, dict):
            first = data.get('first_name', '').strip()
            last = data.get('last_name', '').strip()

            if (not last or last == '-') and ' ' in first:
                parts = first.split(maxsplit=1)
                data['first_name'] = parts[0]
                if len(parts) > 1:
                    data['last_name'] = parts[1]
        return data

class UserResponse(BaseModel):
    user_id: int
    email: str
    first_name: str
    last_name: str
    role_id: int

    class Config:
        from_attributes = True


# --- 2. SCHEMATY ADRESÓW (z GPS z Google) ---
class AddressBase(BaseModel):
    street: str = Field(..., max_length=255, description="Nazwa ulicy")
    building_number: str = Field(..., max_length=20, description="Numer budynku/lokalu") 
    city: str = Field(..., max_length=100, description="Miasto")
    postal_code: str = Field(..., max_length=20, description="Kod pocztowy")
    
    # NOWE POLA NA WSPÓŁRZĘDNE:
    lat: float | None = Field(None, description="Szerokość geograficzna (z Google Places)")
    lon: float | None = Field(None, description="Długość geograficzna (z Google Places)")


# --- 3. SCHEMATY PACZEK ---
class ParcelCreate(BaseModel):
    # ROZDZIELONE DANE NADAWCY
    sender_first_name: str = Field(..., max_length=100, description="Imię nadawcy")
    sender_last_name: str = Field(..., max_length=100, description="Nazwisko nadawcy")
    sender_phone: str = Field(..., max_length=20, description="Telefon nadawcy")
    sender_address: AddressBase 

    # ROZDZIELONE DANE ODBIORCY
    recipient_first_name: str = Field(..., max_length=100, description="Imię odbiorcy")
    recipient_last_name: str = Field(..., max_length=100, description="Nazwisko odbiorcy")
    recipient_phone: str = Field(..., max_length=20, description="Telefon odbiorcy")
    recipient_address: AddressBase 

    tariff_id: int = Field(..., description="ID wybranego gabarytu")
    simulate_payment: bool = Field(False, description="Czy klient opłaca z góry")
    save_recipient_to_contacts: bool = Field(False, description="Zapisz do kontaktów")
    declared_value: Optional[float] = 0.0

    @field_validator('sender_phone', 'recipient_phone')
    @classmethod
    def clean_parcel_phones(cls, v: str) -> str:
        result = normalize_polish_phone(v)
        if result is None:
            raise ValueError('Numer telefonu jest wymagany')
        return result
    
class ParcelResponse(BaseModel):
    parcel_id: int
    tracking_number: str
    status_id: int
    calculated_price: float
    status_name: str | None = None

    class Config:
        from_attributes = True


# --- 4. INNE ---
class RefreshTokenRequest(BaseModel):
    refresh_token: str

class CourierStopResponse(BaseModel):
    stop_id: int
    parcel_id: int
    tracking_number: str
    operation_type: str
    recipient_name: str
    recipient_phone: str
    street: str
    building_number: str
    city: str
    lat: float | None
    lon: float | None
    stop_order: int

    class Config:
        from_attributes = True


# --- 5. SCHEMATY DYSPOZYTORA (Tworzenie Tras) ---

class DispatcherParcelResponse(BaseModel):
    parcel_id: int
    tracking_number: str
    recipient_city: str
    recipient_street: str
    recipient_name: str
    calculated_price: float

    class Config:
        from_attributes = True

class FleetResponse(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    
class VehicleResponse(BaseModel):
    vehicle_id: int
    registration_number: str
    capacity_kg: float

class RouteCreateRequest(BaseModel):
    courier_id: int = Field(..., description="ID wybranego kuriera")
    vehicle_id: int = Field(..., description="ID wybranego pojazdu")
    parcel_ids: list[int] = Field(..., description="Lista ID paczek zaznaczonych checkboxami")

class RouteReportResponse(BaseModel):
    route_id: int
    courier_name: str
    vehicle_registration: str
    total_distance_km: float
    total_revenue: float
    route_cost: float
    net_profit: float  # Czysty zysk (Przychód - Koszt)
    parcels_delivered: int

    class Config:
        from_attributes = True

# --- SCHEMATY LOKALNE DLA EDYCJI (ADMIN) ---
class AdminUserUpdate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str | None = None  # Pozwalamy na brak telefonu
    role_id: int
    warehouse_id: int
    password: str | None = None  # Hasło jest opcjonalne przy edycji!

class AdminVehicleUpdate(BaseModel):
    registration_number: str
    capacity_kg: float
    capacity_m3: float
    vehicle_type: str
    warehouse_id: int
    status: str


# --- REKLAMACJE ---

class ComplaintBase(BaseModel):
    parcel_id: int
    reason: str
    description: Optional[str] = None

class ComplaintCreate(ComplaintBase):
    pass

class ComplaintUpdate(BaseModel):
    status: str  # ACCEPTED lub REJECTED
    
class Complaint(ComplaintBase):
    complaint_id: int
    user_id: int
    status: str
    refund_amount: Optional[float] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True