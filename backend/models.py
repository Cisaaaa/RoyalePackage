import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry # Nasz pomost do map i współrzędnych geograficznych
from database import Base

# 1. Model dla tabeli ROLES
class Role(Base):
    __tablename__ = "roles"

    role_id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String(50), unique=True, nullable=False)

    # Relacja ułatwiająca poruszanie się w kodzie
    users = relationship("User", back_populates="role")


# 2. Model dla tabeli USERS
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.role_id"), nullable=False)

    # --- NOWOŚĆ: Powiązanie z Magazynem ---
    warehouse_id = Column(Integer, ForeignKey("warehouses.warehouse_id"), nullable=True) # VRP: Użytkownik może być przypisany do magazynu
    
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)

    is_active = Column(Boolean, default=True)
    refresh_token = Column(String(255), nullable=True) # Do przechowywania tokena odświeżającego

    # Relacja zwrotna
    role = relationship("Role", back_populates="users")
    warehouse = relationship("Warehouse", back_populates="users") #VRP: Relacja do magazynu

# ==========================================
# WARSTWA 0: TABELE SŁOWNIKOWE (Niezależne)
# ==========================================

class Status(Base):
    __tablename__ = "statuses"
    
    status_id = Column(Integer, primary_key=True, index=True)
    status_name = Column(String(100), unique=True, nullable=False)

class DimensionalTariff(Base):
    __tablename__ = "dimensional_tariffs"
    
    tariff_id = Column(Integer, primary_key=True, index=True)
    size_category = Column(String(10), unique=True, nullable=False) # np. 'A', 'B', 'C'
    max_weight_kg = Column(Float, nullable=False)
    max_volume_m3 = Column(Float, nullable=False, server_default="0.1") # NOWE POLE DLA VROOM
    base_price = Column(Float, nullable=False)

class Region(Base):
    __tablename__ = "regions"
    
    region_id = Column(Integer, primary_key=True, index=True)
    region_name = Column(String(100), unique=True, nullable=False)
    # Zapisujemy obszar (wielokąt) na mapie. SRID 4326 to standardowy system GPS (WGS84)
    polygon_geom = Column(Geometry('POLYGON', srid=4326), nullable=True)


# ==========================================
# WARSTWA 1: INFRASTRUKTURA (Zależna od W0)
# ==========================================

class Address(Base):
    __tablename__ = "addresses"
    
    address_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True) # Może być puste dla magazynu
    street = Column(String(255), nullable=False)
    building_number = Column(String(20), nullable=False)
    city = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=False)
    # Punkt na mapie (Szerokość i długość geograficzna)
    geom = Column(Geometry('POINT', srid=4326), nullable=True)

class Warehouse(Base):
    __tablename__ = "warehouses"
    
    warehouse_id = Column(Integer, primary_key=True, index=True)
    address_id = Column(Integer, ForeignKey("addresses.address_id"), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.region_id"), nullable=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False) # np. 'HUB', 'DEPOT'

    users = relationship("User", back_populates="warehouse") # Relacja powrotna

# ==========================================
# WARSTWA 2: SERCE SYSTEMU - PACZKI
# ==========================================

class Parcel(Base):
    __tablename__ = "parcels"
    
    parcel_id = Column(Integer, primary_key=True, index=True)
    tracking_number = Column(String(50), unique=True, index=True, nullable=False)
    status_id = Column(Integer, ForeignKey("statuses.status_id"), nullable=False, default=1)

    sender_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    sender_address_id = Column(Integer, ForeignKey("addresses.address_id"), nullable=False)
    recipient_address_id = Column(Integer, ForeignKey("addresses.address_id"), nullable=False)
    tariff_id = Column(Integer, ForeignKey("dimensional_tariffs.tariff_id"), nullable=False)
    current_warehouse_id = Column(Integer, ForeignKey("warehouses.warehouse_id"), nullable=True)

    target_region_id = Column(Integer, ForeignKey("regions.region_id"), nullable=True) # Gdzie paczka ma ostatecznie trafić
    
    # --- NOWE/ZMODYFIKOWANE POLA ---
    # Zapisujemy rzeczywiste dane z etykiety, niezależnie od tego kto jest zalogowany
    sender_custom_name = Column(String(200), nullable=False)
    sender_phone = Column(String(20), nullable=False)
    
    recipient_custom_name = Column(String(200), nullable=False)
    recipient_phone = Column(String(20), nullable=False)
    # -------------------------------

    calculated_price = Column(Float, nullable=False)
    is_cod = Column(Boolean, default=False)
    cod_amount = Column(Float, nullable=True)

    # NOWE POLE: Wartość przedmiotów w paczce 
    declared_value = Column(Float, nullable=True, default=0.0)


# ==========================================
# WARSTWA 3: AUDYT I LOGISTYKA
# ==========================================

class ParcelHistory(Base):
    __tablename__ = "parcel_history"
    
    history_id = Column(Integer, primary_key=True, index=True)
    parcel_id = Column(Integer, ForeignKey("parcels.parcel_id"), nullable=False)
    status_id = Column(Integer, ForeignKey("statuses.status_id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.warehouse_id"), nullable=True)
    courier_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    
    # Automatyczny znacznik czasu - serwer DB sam wklepie aktualną datę co do milisekundy
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


# ==========================================
#                Płatności
# ==========================================

class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(Integer, primary_key=True, index=True)
    parcel_id = Column(Integer, ForeignKey("parcels.parcel_id"))
    payer_id = Column(Integer, ForeignKey("users.user_id"))
    amount = Column(Float)
    status = Column(String(50), default="PENDING") # PENDING lub PAID
    transaction_date = Column(DateTime(timezone=True), server_default=func.now())

# ==========================================
# WARSTWA 4: FLOTA I TRASY (Logistyka Kurierska)
# ==========================================

class Vehicle(Base):
    __tablename__ = "vehicles"
    
    vehicle_id = Column(Integer, primary_key=True, index=True)
    registration_number = Column(String(20), unique=True, nullable=False)
    capacity_kg = Column(Float, nullable=False)
    capacity_m3 = Column(Float, nullable=True)
    status = Column(String(50), default="ACTIVE") 
    vehicle_type = Column(String(50), nullable=False, server_default='VAN')

    # --- NOWA KOLUMNA: Pojazd należy do konkretnego HUBu ---
    warehouse_id = Column(Integer, ForeignKey("warehouses.warehouse_id"), nullable=True)
    
class Route(Base):
    __tablename__ = "routes"
    
    route_id = Column(Integer, primary_key=True, index=True)
    courier_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.vehicle_id"), nullable=False)
    
    route_date = Column(DateTime(timezone=True), server_default=func.now())
    route_type = Column(String(50), nullable=False) # np. 'LAST_MILE', 'LINE_HAUL'
    status = Column(String(50), default="PLANNED") # PLANNED, IN_PROGRESS, COMPLETED

    # --- NOWOŚĆ: Finanse i VRP ---
    total_distance_km = Column(Float, nullable=True) # Dystans z OSRM
    total_revenue = Column(Float, nullable=True)     # Przychód z paczek na trasie
    route_cost = Column(Float, nullable=True)        # Koszt paliwa i kuriera
    
    # Relacja pozwalająca na łatwe wyciąganie przystanków dla danej trasy
    stops = relationship("RouteStop", back_populates="route")

class RouteStop(Base):
    __tablename__ = "route_stops"
    
    stop_id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.route_id"), nullable=False)
    parcel_id = Column(Integer, ForeignKey("parcels.parcel_id"), nullable=True) 
    warehouse_id = Column(Integer, ForeignKey("warehouses.warehouse_id"), nullable=True)
    
    stop_order = Column(Integer, nullable=False) 
    operation_type = Column(String(50), nullable=False) 
    status = Column(String(50), default="PLANNED") 
    actual_arrival = Column(DateTime(timezone=True), nullable=True)
    
    # --- NOWE POLE POD TRACKING (ETA) ---
    estimated_arrival = Column(DateTime(timezone=True), nullable=True)

    route = relationship("Route", back_populates="stops")

# ==========================================
# WARSTWA 5: KSIĄŻKA ADRESOWA
# ==========================================
class SavedContact(Base):
    __tablename__ = "saved_contacts"
    
    contact_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False) # Kto jest właścicielem kontaktu
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    address_id = Column(Integer, ForeignKey("addresses.address_id"), nullable=False) # Podpinamy istniejącą strukturę adresów!
    
    address = relationship("Address")


class Complaint(Base):
    __tablename__ = "complaints"

    complaint_id = Column(Integer, primary_key=True, index=True)
    parcel_id = Column(Integer, ForeignKey("parcels.parcel_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)  # Kto zgłasza
    
    reason = Column(String, nullable=False)  # np. "Uszkodzenie", "Zaginięcie"
    description = Column(String, nullable=True) # Dłuższy opis od klienta
    
    # Status reklamacji: PENDING, ACCEPTED, REJECTED
    status = Column(String, default="PENDING", nullable=False)
    
    # Kwota, którą ostatecznie zwrócimy (wyliczana przy akceptacji: declared_value + calculated_price)
    refund_amount = Column(Float, nullable=True) 
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True) # Kiedy pracownik kliknął "Rozpatrz"

    # Relacje, żeby SQLAlchemy mogło łatwo pobierać powiązane obiekty
    parcel = relationship("Parcel")
    user = relationship("User")