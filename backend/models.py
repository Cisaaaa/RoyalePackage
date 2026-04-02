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
    
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)

    # Relacja zwrotna
    role = relationship("Role", back_populates="users")

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


# ==========================================
# WARSTWA 2: SERCE SYSTEMU - PACZKI
# ==========================================

class Parcel(Base):
    __tablename__ = "parcels"
    
    parcel_id = Column(Integer, primary_key=True, index=True)
    tracking_number = Column(String(50), unique=True, index=True, nullable=False)
    
    # Klucze obce - trzymają paczkę w ryzach
    sender_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    sender_address_id = Column(Integer, ForeignKey("addresses.address_id"), nullable=False)
    recipient_address_id = Column(Integer, ForeignKey("addresses.address_id"), nullable=False)
    tariff_id = Column(Integer, ForeignKey("dimensional_tariffs.tariff_id"), nullable=False)
    current_warehouse_id = Column(Integer, ForeignKey("warehouses.warehouse_id"), nullable=True)
    
    recipient_phone = Column(String(20), nullable=False)
    calculated_price = Column(Float, nullable=False)
    is_cod = Column(Boolean, default=False) # Cash on Delivery (Pobranie)
    cod_amount = Column(Float, nullable=True)


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