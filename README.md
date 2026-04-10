# RoyalePackage

🛠 Praca z migracjami (Alembic)
W projekcie używamy Alembic do zarządzania schematem bazy danych. Dzięki temu każda zmiana w models.py jest śledzona i może być łatwo odtworzona na innych maszynach.

Jak zaktualizować bazę danych:
Jeśli pobrałeś nową wersję kodu, uruchom poniższą komendę, aby zaktualizować swoją lokalną bazę danych:

----
docker-compose exec backend alembic upgrade head
----

Jak dodać nową zmianę w bazie:
Wprowadź zmiany w backend/models.py.

Wygeneruj plik migracji:

----
docker-compose exec backend alembic revision --autogenerate -m "Opis zmian"
----

Sprawdź wygenerowany plik w backend/alembic/versions/.
Zatwierdź zmiany w bazie:

----
docker-compose exec backend alembic upgrade head
----