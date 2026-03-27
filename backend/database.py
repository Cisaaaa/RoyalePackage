import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Pobieramy adres URL z pliku .env (np. postgresql://user:haslo@db:5432/baza)
DATABASE_URL = os.getenv("DATABASE_URL")

# 2. Tworzymy silnik bazy danych
# echo=True sprawi, że w konsoli Dockera zobaczycie generowane zapytania SQL (bardzo pomocne przy nauce!)
engine = create_engine(DATABASE_URL, echo=True)

# 3. Tworzymy fabrykę sesji (SessionLocal)
# Sesja to nasze "okno" na bazę danych. Każde żądanie z przeglądarki otrzyma własną sesję.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Klasa bazowa dla wszystkich naszych modeli
# Każda tabela (Users, Roles, Parcels) będzie dziedziczyć z tej klasy
Base = declarative_base()

# 5. Zależność (Dependency) do wstrzykiwania sesji w FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()