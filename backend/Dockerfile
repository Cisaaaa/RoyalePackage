# 1. Wybieramy oficjalny i odchudzony obraz Pythona
FROM python:3.11-slim

# 2. Ustawiamy katalog roboczy wewnątrz kontenera
WORKDIR /app

# 3. Kopiujemy TYLKO plik z listami bibliotek
COPY requirements.txt .

# 4. Instalujemy biblioteki
RUN pip install --no-cache-dir -r requirements.txt

# 5. Kopiujemy całą resztę kodu do kontenera
COPY . .

# 6. Komenda startowa uruchamiająca serwer
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]