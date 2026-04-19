import os
from fastapi import FastAPI
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import schemas
import security
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, func
import random
import asyncio

import requests

# Importujemy bazę danych i modele
from database import engine, Base, get_db, SessionLocal
import models 

# Importujemy bibliotekę do obsługi JWT refresh
import jwt

#Generowanie tabel w bazie danych na podstawie modeli (jeśli jeszcze nie istnieją)
models.Base.metadata.create_all(bind=engine) 

# Funkcja AUTO-SEEDINGU
def seed_db():
    db = SessionLocal()
    try:
        # 1. ROLE UŻYTKOWNIKÓW
        if db.query(models.Role).count() == 0:
            print("INFO: Tabela ról jest pusta. Dodaję role...")
            db.add_all([
                models.Role(role_name="Klient"),
                models.Role(role_name="Kurier"),
                models.Role(role_name="Dyspozytor")
            ])
            db.commit()
            print("SUCCESS: Role dodane!")

        # 2. STATUSY PACZEK
        if db.query(models.Status).count() == 0:
            print("INFO: Tabela statusów jest pusta. Dodaję statusy...")
            db.add_all([
                models.Status(status_name="Zarejestrowana"),
                models.Status(status_name="W magazynie nadawczym"),
                models.Status(status_name="W drodze"),
                models.Status(status_name="Wydana kurierowi"),
                models.Status(status_name="Dostarczona")
            ])
            db.commit()
            print("SUCCESS: Statusy dodane!")

        # 3. TARYFY / GABARYTY
        if db.query(models.DimensionalTariff).count() == 0:
            print("INFO: Tabela taryf jest pusta. Dodaję cennik...")
            db.add_all([
                models.DimensionalTariff(size_category="A", max_weight_kg=5.0, base_price=15.99),
                models.DimensionalTariff(size_category="B", max_weight_kg=15.0, base_price=20.99),
                models.DimensionalTariff(size_category="C", max_weight_kg=30.0, base_price=29.99)
            ])
            db.commit()
            print("SUCCESS: Taryfy dodane!")

        # 4. DOMYŚLNY MAGAZYN (Wymagany do logistyki)
        if db.query(models.Warehouse).count() == 0:
            print("INFO: Brak magazynów. Tworzę główny HUB...")
            
            # Najpierw tworzymy Region
            region = models.Region(region_name="Mazowieckie")
            db.add(region)
            db.commit()
            db.refresh(region)

            # Potem tworzymy fizyczny adres dla Magazynu (bez współrzędnych na razie)
            address = models.Address(
                street="ul. Logistyczna",
                building_number="1",
                city="Warszawa",
                postal_code="00-001"
            )
            db.add(address)
            db.commit()
            db.refresh(address)

            # Na końcu sam Magazyn, przypinając do niego ID adresu i regionu
            warehouse = models.Warehouse(
                address_id=address.address_id,
                region_id=region.region_id,
                name="HUB Centralny Warszawa",
                type="HUB"
            )
            db.add(warehouse)
            db.commit()
            print("SUCCESS: Główny HUB dodany!")

    except Exception as e:
        print(f"ERROR: Błąd podczas seedingu: {e}")
        db.rollback()
    finally:
        db.close()

# Funkcja instalująca Triggery w PostgreSQL
def setup_triggers():
    db = SessionLocal()
    try:
        print("INFO: Instalowanie triggerów bazy danych...")
        
        # 1. Tworzymy funkcję w języku bazy danych (PL/pgSQL)
        db.execute(text("""
            CREATE OR REPLACE FUNCTION log_parcel_history()
            RETURNS TRIGGER AS $$
            BEGIN
                -- Wykonaj tylko przy nowej paczce (INSERT) LUB gdy zmienił się status (UPDATE)
                IF (TG_OP = 'INSERT') OR (TG_OP = 'UPDATE' AND NEW.status_id IS DISTINCT FROM OLD.status_id) THEN
                    INSERT INTO parcel_history (parcel_id, status_id, warehouse_id, updated_at)
                    VALUES (NEW.parcel_id, NEW.status_id, NEW.current_warehouse_id, NOW());
                END IF;
                
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        
        # 2. Tworzymy sam wyzwalacz, który 'nasłuchuje' tabeli parcels
        db.execute(text("""
            DROP TRIGGER IF EXISTS trigger_log_parcel_history ON parcels;
            CREATE TRIGGER trigger_log_parcel_history
            AFTER INSERT OR UPDATE ON parcels
            FOR EACH ROW
            EXECUTE FUNCTION log_parcel_history();
        """))
        
        db.commit()
        print("SUCCESS: Magia bazy danych (Triggery) działa!")
    except Exception as e:
        print(f"ERROR: Błąd instalacji triggerów: {e}")
        db.rollback()
    finally:
        db.close()

# W tym miejscu wywołujesmy nasze funkcje
seed_db()
setup_triggers()

# Inicjalizacja aplikacji FastAPI
app = FastAPI(
    title="Royale Package API",
    description="API dla systemu logistycznego",
    version="1.0.0"
)

# Dodajemy obsługę CORS, żeby frontend (Vue.js) mógł z nami gadać
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # Wpuszczamy tylko nasz frontend!
    allow_credentials=True,
    allow_methods=["*"], # Pozwalamy na wszystko
    allow_headers=["*"], # Pozwalamy na przesyłanie tokenów
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

@app.post("/api/v1/login", summary="Logowanie (Generowanie Access i Refresh Token)")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy email lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Tworzymy paczkę dla Access Tokena (z rolami)
    token_data = {"sub": user.email, "role_id": user.role_id}
    
    # GENERUJEMY OBA TOKENY
    access_token = security.create_access_token(data=token_data)
    refresh_token = security.create_refresh_token(data=token_data)
    
    # Zapisujemy Refresh Token bezpiecznie w bazie danych
    user.refresh_token = refresh_token
    db.commit()
    
    # Zwracamy zestaw klientowi (Frontendowi)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
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



# Endpoint do odświeżania tokena JWT
@app.post("/api/v1/refresh", summary="Odśwież Access Token za pomocą Refresh Tokena")
def refresh_token(request: schemas.RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Endpoint przyjmuje Refresh Token i jeśli jest ważny, wydaje nowy Access Token
    """
    # 1. Weryfikujemy Refresh Token
    try:
        # Sprawdzamy poprawność tokena i wyciągamy z niego dane
        payload = jwt.decode(request.refresh_token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        # Sprawdzamy czy ktoś nie próbuje oszukać nas z nieprawidłowym tokenem
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Nieprawidłowy token")
        
        email = payload.get("sub")
        # Suzkamy użytkownika w bazie danych i weryfikujemy, czy token się zgadza z tym, co mamy zapisane
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user or user.refresh_token != request.refresh_token:
            raise HTTPException(status_code=401, detail="Token unieważniony lub użytkownik nie istnieje")
        # Jeśli wszystko się zgadza, generujemy nowy Access Token
        new_access_token = security.create_access_token(data={"sub": user.email, "role_id": user.role_id})
        return {"access_token": new_access_token, "token_type": "bearer"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token wygasł")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Nieważny token")




# NADAWANIE PACZEK!!!!!!!!

@app.post("/api/v1/parcels", response_model=schemas.ParcelResponse, status_code=status.HTTP_201_CREATED, summary="Nadaj nową paczkę")
def create_parcel(
    parcel_data: schemas.ParcelCreate, 
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    # 1. Identyfikacja klienta (płatnika)
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Nie znaleziono użytkownika")
    
    # 2. Pobranie cennika
    tariff = db.query(models.DimensionalTariff).filter(models.DimensionalTariff.tariff_id == parcel_data.tariff_id).first()
    if not tariff:
        raise HTTPException(status_code=404, detail="Wybrany gabaryt nie istnieje")
    
    # --- PRZYGOTOWANIE WSPÓŁRZĘDNYCH (Magia PostGIS) ---
    sender_geom = None
    if parcel_data.sender_address.lon and parcel_data.sender_address.lat:
        # Format WKT (Well-Known Text). Ważne: najpierw Długość (lon/X), potem Szerokość (lat/Y)
        sender_geom = f"SRID=4326;POINT({parcel_data.sender_address.lon} {parcel_data.sender_address.lat})"
        
    recipient_geom = None
    if parcel_data.recipient_address.lon and parcel_data.recipient_address.lat:
        recipient_geom = f"SRID=4326;POINT({parcel_data.recipient_address.lon} {parcel_data.recipient_address.lat})"

    # 3. Tworzymy i zapisujemy adresy (z punktami GPS!)
    sender_address = models.Address(
        street=parcel_data.sender_address.street,
        building_number=parcel_data.sender_address.building_number, 
        city=parcel_data.sender_address.city,
        postal_code=parcel_data.sender_address.postal_code,
        geom=sender_geom # Wstrzykujemy współrzędne
    )
    recipient_address = models.Address(
        street=parcel_data.recipient_address.street,
        building_number=parcel_data.recipient_address.building_number,
        city=parcel_data.recipient_address.city,
        postal_code=parcel_data.recipient_address.postal_code,
        geom=recipient_geom # Wstrzykujemy współrzędne
    )

    db.add(sender_address)
    db.add(recipient_address)
    db.flush() 

    # 4. Generowanie numeru przesyłki
    while True:
        tracking_num = f"RP{random.randint(1000000, 9999999)}PL"
        existing_parcel = db.query(models.Parcel).filter(models.Parcel.tracking_number == tracking_num).first()
        if not existing_parcel:
            break 

    # 5. Logika cennika
    final_price = float(tariff.base_price)
    COD_FEE = 5.00 
    if not parcel_data.simulate_payment:
        final_price += COD_FEE

    # --- PRZYGOTOWANIE DANYCH Z ETYKIETY ---
    sender_full_name = f"{parcel_data.sender_first_name} {parcel_data.sender_last_name}"
    recipient_full_name = f"{parcel_data.recipient_first_name} {parcel_data.recipient_last_name}"

    # 6. Złożenie paczki w całość
    new_parcel = models.Parcel(
        tracking_number=tracking_num,
        sender_id=user.user_id, # Ten kto zapłacił
        
        # Zapisujemy rzeczywiste dane z formularza
        sender_custom_name=sender_full_name,
        sender_phone=parcel_data.sender_phone,
        recipient_custom_name=recipient_full_name,
        recipient_phone=parcel_data.recipient_phone,
        
        sender_address_id=sender_address.address_id,
        recipient_address_id=recipient_address.address_id,
        tariff_id=parcel_data.tariff_id,
        calculated_price=final_price,
        current_warehouse_id=1, 
        status_id=1 
    )
    
    db.add(new_parcel)
    db.commit()
    db.refresh(new_parcel)

    # 7. Symulacja płatności
    if parcel_data.simulate_payment:
        payment = models.Payment(parcel_id=new_parcel.parcel_id, payer_id=user.user_id, amount=final_price, status="PAID")
        db.add(payment)
        new_parcel.is_cod = False 
        new_parcel.cod_amount = None
    else:
        payment = models.Payment(parcel_id=new_parcel.parcel_id, payer_id=user.user_id, amount=final_price, status="PENDING")
        db.add(payment)
        new_parcel.is_cod = True
        new_parcel.cod_amount = final_price 

    db.commit()
    db.refresh(new_parcel)

    return new_parcel

# POBIERANIE HISTORII PACZKI (dla klienta i kuriera)
@app.get("/api/v1/parcels", response_model=list[schemas.ParcelResponse])
def get_user_parcels(
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    # 1. Identyfikujemy zalogowanego użytkownika (bez zmian)
    current_user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="Nie znaleziono użytkownika")
    
    # 2. Zmieniamy zapytanie: prosimy o paczkę ORAZ nazwę statusu.
    # .join łączy tabelę Parcel z tabelą Status tam, gdzie zgadzają się ID statusów.
    results = db.query(models.Parcel, models.Status.status_name).join(
        models.Status, models.Parcel.status_id == models.Status.status_id
    ).filter(models.Parcel.sender_id == current_user.user_id).all()
    
    # 3. Ponieważ wynik z JOINa to lista krotek (parcel, status_name), 
    # musimy je "przepakować" do formatu, który rozumie schemat ParcelResponse.
    response = []
    for parcel, status_name in results:
        response.append({
            "parcel_id": parcel.parcel_id,
            "tracking_number": parcel.tracking_number,
            "status_id": parcel.status_id,
            "calculated_price": parcel.calculated_price,
            "status_name": status_name  # Przekazujemy tekstową nazwę do frontendu
        })
    
    return response

# WIDOK KURIERA - TRASY I PINEZKI NA MAPIE

@app.get("/api/v1/courier/route", response_model=list[schemas.CourierStopResponse], summary="Pobierz dzisiejszą trasę kuriera")
def get_courier_route(
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    # 1. Sprawdzamy kim jest użytkownik i czy to na pewno Kurier
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Nie znaleziono użytkownika")
    
    if user.role_id != 2:
        raise HTTPException(status_code=403, detail="Brak uprawnień. Ten widok jest tylko dla kurierów.")

    # 2. Szukamy aktywnej trasy dla tego kuriera (zaplanowanej lub w trakcie)
    route = db.query(models.Route).filter(
        models.Route.courier_id == user.user_id,
        models.Route.status.in_(["PLANNED", "IN_PROGRESS"])
    ).first()

    # Jeśli dyspozytor nie przydzielił mu jeszcze trasy, zwracamy pustą listę
    if not route:
        return []

    # 3. Pobieramy przystanki dla tej trasy, posortowane według kolejności (stop_order)
    stops = db.query(models.RouteStop).filter(
        models.RouteStop.route_id == route.route_id,
        models.RouteStop.status == "PLANNED"
    ).order_by(models.RouteStop.stop_order).all()

    # Przygotowujemy kuloodporne zapytanie SQL do wyciągania GPS z PostGIS
    sql_coords = text("SELECT ST_X(geom) as lon, ST_Y(geom) as lat FROM addresses WHERE address_id = :id AND geom IS NOT NULL")

    # 4. Składamy dane dla Frontendu i Leafleta
    results = []
    for stop in stops:
        # SCENARIUSZ A: Zwykła paczka do doręczenia
        if stop.parcel_id and stop.operation_type == "DROP_OFF":
            parcel = db.query(models.Parcel).filter(models.Parcel.parcel_id == stop.parcel_id).first()
            address = db.query(models.Address).filter(models.Address.address_id == parcel.recipient_address_id).first()

            # Pobieramy współrzędne surowym SQL-em
            lat, lon = None, None
            if address:
                coords = db.execute(sql_coords, {"id": address.address_id}).fetchone()
                if coords and coords[0] is not None and coords[1] is not None:
                    lon, lat = coords[0], coords[1]

            results.append({
                "stop_id": stop.stop_id,
                "parcel_id": parcel.parcel_id,
                "tracking_number": parcel.tracking_number,
                "operation_type": stop.operation_type,
                "recipient_name": parcel.recipient_custom_name,
                "recipient_phone": parcel.recipient_phone,
                "street": address.street,
                "building_number": address.building_number,
                "city": address.city,
                "lat": lat,
                "lon": lon
            })
        
        # SCENARIUSZ B: Start z Magazynu (HUB)
        elif stop.warehouse_id and stop.operation_type == "WAREHOUSE_TRANSFER":
            warehouse = db.query(models.Warehouse).filter(models.Warehouse.warehouse_id == stop.warehouse_id).first()
            address = db.query(models.Address).filter(models.Address.address_id == warehouse.address_id).first()
            
            # Pobieramy współrzędne surowym SQL-em
            lat, lon = None, None
            if address:
                coords = db.execute(sql_coords, {"id": address.address_id}).fetchone()
                if coords and coords[0] is not None and coords[1] is not None:
                    lon, lat = coords[0], coords[1]
            
            results.append({
                "stop_id": stop.stop_id,
                "parcel_id": 0, 
                "tracking_number": "START TRASY",
                "operation_type": stop.operation_type,
                "recipient_name": warehouse.name,
                "recipient_phone": "-",
                "street": address.street,
                "building_number": address.building_number,
                "city": address.city,
                "lat": lat,
                "lon": lon
            })

    return results


# PANEL DYSPOZYTORA - ZARZĄDZANIE TRASAMI


@app.get("/api/v1/dispatcher/unassigned-parcels", summary="Pobierz paczki do przypisania")
def get_unassigned_parcels(
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    # 1. Sprawdzamy uprawnienia (Tylko Dyspozytor - rola 3)
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user or user.role_id != 3:
        raise HTTPException(status_code=403, detail="Brak uprawnień. Widok tylko dla Dyspozytora.")

    # 2. Szukamy paczek ze statusem 2 ("W magazynie nadawczym"), które NIE MAJĄ jeszcze rekordu w route_stops
    unassigned_parcels = db.query(models.Parcel).outerjoin(
        models.RouteStop, models.Parcel.parcel_id == models.RouteStop.parcel_id
    ).filter(
        models.Parcel.status_id == 2,
        models.RouteStop.stop_id == None # Magia SQL: Zwróć tylko te, które nie połączyły się z trasą
    ).all()

    # 3. Składamy dane dla widoku tabeli na frontendzie
    results = []
    for parcel in unassigned_parcels:
        address = db.query(models.Address).filter(models.Address.address_id == parcel.recipient_address_id).first()
        results.append({
            "parcel_id": parcel.parcel_id,
            "tracking_number": parcel.tracking_number,
            "recipient_city": address.city if address else "Brak danych",
            "recipient_street": address.street if address else "Brak danych",
            "recipient_name": parcel.recipient_custom_name,
            "calculated_price": parcel.calculated_price
        })
    return results

@app.get("/api/v1/dispatcher/fleet", summary="Pobierz listę kurierów i pojazdów")
def get_fleet(
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    # 1. Sprawdzamy uprawnienia (Tylko Dyspozytor - rola 3)
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user or user.role_id != 3:
        raise HTTPException(status_code=403, detail="Brak uprawnień.")
    
    # 2. Pobieramy listę aktywnych kurierów i pojazdów z bazy danych
    couriers = db.query(models.User).filter(models.User.role_id == 2).all()
    vehicles = db.query(models.Vehicle).filter(models.Vehicle.status == "ACTIVE").all()

    # 3. Składamy dane do zwrócenia na frontend
    return {
        "couriers": [{"user_id": c.user_id, "first_name": c.first_name, "last_name": c.last_name} for c in couriers],
        "vehicles": [{"vehicle_id": v.vehicle_id, "registration_number": v.registration_number, "capacity_kg": v.capacity_kg} for v in vehicles]
    }



@app.post("/api/v1/dispatcher/routes", status_code=status.HTTP_201_CREATED, summary="Utwórz i zoptymalizuj trasę")
def create_route(
    request: schemas.RouteCreateRequest,
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user or user.role_id != 3:
        raise HTTPException(status_code=403, detail="Brak uprawnień.")

    if not request.parcel_ids:
        raise HTTPException(status_code=400, detail="Nie wybrano paczek do trasy.")

    # ==========================================
    # 1. ZBIERANIE GPS - OPCJA ATOMOWA (RAW SQL)
    # ==========================================
    warehouse = db.query(models.Warehouse).filter(models.Warehouse.warehouse_id == 1).first()
    if not warehouse:
        raise HTTPException(status_code=500, detail="Brak Magazynu (ID=1) w bazie danych.")
    
    # Surowe zapytanie SQL, które omija błędy biblioteki GeoAlchemy2
    sql_coords = text("SELECT ST_X(geom) as lon, ST_Y(geom) as lat FROM addresses WHERE address_id = :id AND geom IS NOT NULL")
    
    wh_result = db.execute(sql_coords, {"id": warehouse.address_id}).fetchone()
    if not wh_result or wh_result[0] is None or wh_result[1] is None:
        raise HTTPException(status_code=500, detail="Brak współrzędnych Magazynu (ID=1) w bazie.")

    wh_lon, wh_lat = wh_result[0], wh_result[1]
    coords = [f"{wh_lon},{wh_lat}"] # Indeks 0 to nasz Magazyn
    
    parcels = db.query(models.Parcel).filter(models.Parcel.parcel_id.in_(request.parcel_ids)).all()
    parcel_mapping = {}

    for idx, parcel in enumerate(parcels, start=1):
        p_result = db.execute(sql_coords, {"id": parcel.recipient_address_id}).fetchone()
        
        if p_result and p_result[0] is not None and p_result[1] is not None:
            coords.append(f"{p_result[0]},{p_result[1]}")
            parcel_mapping[idx] = parcel.parcel_id
        else:
            raise HTTPException(status_code=400, detail=f"Paczka {parcel.tracking_number} nie ma wpisanych współrzędnych GPS!")

    # ==========================================
    # 2. KOMUNIKACJA Z OSRM (Algorytm VRP)
    # ==========================================
    coords_str = ";".join(coords)
    osrm_url = f"http://router.project-osrm.org/trip/v1/driving/{coords_str}?source=first&roundtrip=false"

    try:
        osrm_response = requests.get(osrm_url, timeout=10)
        osrm_data = osrm_response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Błąd łączenia z silnikiem optymalizacji OSRM.")

    if osrm_data.get("code") != "Ok":
        raise HTTPException(status_code=500, detail="OSRM nie potrafił wyznaczyć trasy dla podanych adresów.")

    # ==========================================
    # 3. WYLICZENIA FINANSOWE
    # ==========================================
    trip = osrm_data["trips"][0]
    total_distance_km = trip["distance"] / 1000.0
    total_revenue = sum(p.calculated_price for p in parcels)

    FUEL_PRICE = 6.50         
    BURN_RATE = 10.0 / 100.0  
    COURIER_FLAT_FEE = 50.0   
    COURIER_PER_PARCEL = 2.0  

    cost_fuel = total_distance_km * BURN_RATE * FUEL_PRICE
    cost_courier = COURIER_FLAT_FEE + (len(parcels) * COURIER_PER_PARCEL)
    route_cost = cost_fuel + cost_courier

    # ==========================================
    # 4. ZAPIS DO BAZY DANYCH
    # ==========================================
    new_route = models.Route(
        courier_id=request.courier_id,
        vehicle_id=request.vehicle_id,
        route_type="LAST_MILE",
        status="PLANNED",
        total_distance_km=total_distance_km,
        total_revenue=total_revenue,
        route_cost=route_cost
    )
    db.add(new_route)
    db.flush()

    # Magia Pythona - enumerate automatycznie przypisze nam indeks 0, 1, 2... jako orig_idx
    for orig_idx, waypoint in enumerate(osrm_data["waypoints"]):
        if orig_idx == 0:
            continue # Pomijamy punkt zerowy (nasz Magazyn)
            
        p_id = parcel_mapping[orig_idx]
        optimal_stop_order = waypoint["waypoint_index"] 

        stop = models.RouteStop(
            route_id=new_route.route_id,
            parcel_id=p_id,
            stop_order=optimal_stop_order,
            operation_type="DROP_OFF",
            status="PLANNED"
        )
        db.add(stop)

        parcel_to_update = next(p for p in parcels if p.parcel_id == p_id)
        parcel_to_update.status_id = 4 

    db.commit()
    
    return {
        "message": "Trasa zoptymalizowana i zapisana.",
        "route_id": new_route.route_id
    }






# OBSŁUGA KURIERA - DORĘCZENIE PACZKI
@app.put("/api/v1/courier/parcels/{parcel_id}/deliver", summary="Oznacz paczkę jako doręczoną")
def mark_parcel_delivered(
    parcel_id: int,
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user or user.role_id != 2:
        raise HTTPException(status_code=403, detail="Brak uprawnień.")

    parcel = db.query(models.Parcel).filter(models.Parcel.parcel_id == parcel_id).first()
    if not parcel:
        raise HTTPException(status_code=404, detail="Nie znaleziono paczki")

    parcel.status_id = 5

    stop = db.query(models.RouteStop).filter(
        models.RouteStop.parcel_id == parcel_id,
        models.RouteStop.status == "PLANNED"
    ).first()
    
    if stop:
        stop.status = "COMPLETED"
        
        # --- AUTOMATYCZNE ZAMYKANIE TRASY ---
        # Sprawdzamy, czy na tej trasie zostały jeszcze jakieś paczki do doręczenia (PLANNED lub IN_PROGRESS)
        remaining_stops = db.query(models.RouteStop).filter(
            models.RouteStop.route_id == stop.route_id,
            models.RouteStop.status.in_(["PLANNED", "IN_PROGRESS"])
        ).count()
        
        if remaining_stops == 0:
            # Jeśli to była ostatnia paczka (zwróciło 0), zamykamy całą trasę!
            route = db.query(models.Route).filter(models.Route.route_id == stop.route_id).first()
            if route:
                route.status = "COMPLETED"
        # --------------------------------------------

    db.commit()

    return {"message": "Paczka doręczona pomyślnie. Jeśli to była ostatnia, trasa została zamknięta."}





# LONG POLLING - AKTUALIZACJA TRASY NA ŻYWO

@app.get("/api/v1/courier/long-poll", summary="Long Polling dla trasy kuriera")
async def courier_long_poll(
    last_known_count: int, # Frontend mówi nam, ile paczek aktualnie widzi
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user or user.role_id != 2:
        raise HTTPException(status_code=403, detail="Brak uprawnień")

    route = db.query(models.Route).filter(
        models.Route.courier_id == user.user_id,
        models.Route.status.in_(["PLANNED", "IN_PROGRESS"])
    ).first()

    if not route:
        return {"updated": False}

    # Pętla Long Pollingu: Czekamy maksymalnie 20 sekund
    for _ in range(20):
        # BARDZO WAŻNE: Wymuszamy na bazie odświeżenie transakcji. 
        # Bez tego SQLAlchemy nie zobaczyłoby paczek dodanych w DBeaverze!
        db.commit() 
        
        # Sprawdzamy, ile aktualnie przypisanych jest paczek do tej trasy
        current_count = db.query(models.RouteStop).filter(
            models.RouteStop.route_id == route.route_id,
            models.RouteStop.status == "PLANNED"
        ).count()

        # Jeśli ilość w bazie jest większa niż to, co widzi kurier -> ALARM! Nowa paczka!
        if current_count > last_known_count:
            return {"updated": True, "new_count": current_count}
        
        # Usypiamy pętlę na 1 sekundę i sprawdzamy znowu
        await asyncio.sleep(1)

    # Jeśli przez 20 sekund nic się nie wydarzyło, zamykamy połączenie (Frontend otworzy nowe)
    return {"updated": False}


@app.get("/api/v1/dispatcher/reports", response_model=list[schemas.RouteReportResponse], summary="Pobierz raporty finansowe tras")
def get_route_reports(
    db: Session = Depends(get_db),
    current_user_email: str = Depends(security.get_current_user_email)
):
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not user or user.role_id != 3:
        raise HTTPException(status_code=403, detail="Brak uprawnień.")

    # Pobieramy tylko trasy, które mają policzone kilometry
    routes = db.query(models.Route).filter(models.Route.total_distance_km != None).order_by(models.Route.route_id.desc()).all()
    
    reports = []
    for r in routes:
        # Szukamy imienia kuriera
        courier = db.query(models.User).filter(models.User.user_id == r.courier_id).first()
        courier_name = f"{courier.first_name} {courier.last_name}" if courier else "Nieznany Kurier"
        
        # Szukamy rejestracji pojazdu
        vehicle = db.query(models.Vehicle).filter(models.Vehicle.vehicle_id == r.vehicle_id).first()
        vehicle_reg = vehicle.registration_number if vehicle else "Brak Danych"
        
        # Liczymy ile paczek przypisano do tej trasy
        parcels_count = db.query(models.RouteStop).filter(
            models.RouteStop.route_id == r.route_id,
            models.RouteStop.operation_type == "DROP_OFF"
        ).count()

        reports.append({
            "route_id": r.route_id,
            "courier_name": courier_name,
            "vehicle_registration": vehicle_reg,
            "total_distance_km": round(r.total_distance_km, 2),
            "total_revenue": round(r.total_revenue, 2),
            "route_cost": round(r.route_cost, 2),
            "net_profit": round(r.total_revenue - r.route_cost, 2), # Czysty zysk
            "parcels_delivered": parcels_count
        })
        
    return reports