import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1', // Adres backendu FastAPI
  headers: {
    'Content-Type': 'application/json',
  },
});

// 1. Obserwacja żądań wychodzących (doklejacz tokena)
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// 2. Obserwacja odpowiedzi przychodzących (obsługa błędów 401)
api.interceptors.response.use(
    (response) => response, // Zwracamy odpowiedź, jeśli jest poprawna
    async (error) => {
        // Łapiemy konfigurację zapytania, które właśnie "odbiło się" od serwera
        const originalRequest = error.config;

        // JEŚLI: dostaliśmy błąd 401 (Wygasły Access Token) ORAZ nie próbowaliśmy go jeszcze odświeżyć
        if (error.response && error.response.status === 401 && !originalRequest._retry) {

            // Zaznaczamy flage _retry, żeby nie wpadać w nieskończoną pętlę
            originalRequest._retry = true;
            console.log('Access token wygasł. Próba odświeżenia...');

            try {
                // Pobieramy refresh token z localStorage
                const refreshToken = localStorage.getItem('refresh_token');
                if (!refreshToken) throw new Error('Brak refresh tokena. Użytkownik musi się zalogować ponownie.');

                // Używamy czystego axiosa, a nie naszego api, żeby ten request się nei zapętlił w tym samym obserwatorze
                const response = await axios.post('http://localhost:8000/api/v1/refresh', {
                    refresh_token: refreshToken,
                });

                // Sukces - otrzymaliśmy nowe tokeny
                const newAccessToken = response.data.access_token;
                localStorage.setItem('access_token', newAccessToken); // Aktualizujemy access token w localStorage

                // Podmieniamy stary token w zablokowanym żądaniu na nowy
                originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;

                // Ponawiamy zablokowane żądanie z nowym tokenem
                console.log('Obserwator: Sukces! Ponawiam zablokowane żądanie z nowym access tokenem.');
                return api(originalRequest);

            } catch (refreshError) {
                // Jeśli nasz Refresh Token też wygasł (np. minęło 7 dni), wyrzucamy usera z aplikacji
                console.error('Obserwator: Odświeżenie tokena nie powiodło się. Użytkownik musi się zalogować ponownie.', refreshError);
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                window.location.reload();   // Przekierowanie do strony logowania
                return Promise.reject(refreshError);
            }
        }

        // Jeśli błąd nie jest 401 lub już próbowaliśmy odświeżyć token, po prostu odrzucamy błąd dalej
        return Promise.reject(error);
    }
);  

// --- REKLAMACJE (COMPLAINTS) ---

// Dla Klienta: Zgłaszanie nowej reklamacji
export const submitComplaint = async (complaintData: { parcel_id: number, reason: string, description?: string }) => {
  const response = await api.post('/client/complaints', complaintData);
  return response.data;
};

// Dla Klienta: Pobieranie listy własnych reklamacji
export const getMyComplaints = async () => {
  const response = await api.get('/client/complaints');
  return response.data;
};

// Dla Pracownika (Dyspozytora/Admina): Pobieranie listy wszystkich reklamacji
export const getComplaints = async () => {
  const response = await api.get('/dispatcher/complaints');
  return response.data;
};

// Dla Pracownika (Dyspozytora/Admina): Rozpatrywanie reklamacji (Akceptacja/Odrzucenie)
export const resolveComplaint = async (complaintId: number, status: string) => {
  const response = await api.patch(`/dispatcher/complaints/${complaintId}/resolve`, { status });
  return response.data;
};

export default api;