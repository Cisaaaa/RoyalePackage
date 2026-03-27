# 1. Wybieramy oficjalny, lekki obraz środowiska Node.js
FROM node:20-slim

# 2. Ustawiamy katalog roboczy wewnątrz kontenera
WORKDIR /app

# 3. Kopiujemy pliki z listą zależności (package.json i package-lock.json)
COPY package*.json ./

# 4. Instalujemy biblioteki
RUN npm install

# 5. Kopiujemy całą resztę kodu aplikacji
COPY . .

# 6. Komenda startowa (uruchamia serwer deweloperski Vite)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]