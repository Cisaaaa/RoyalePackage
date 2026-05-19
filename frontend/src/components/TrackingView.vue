<template>
  <v-container fluid class="tracking-bg fill-height align-start pa-0">
    <v-app-bar color="transparent" flat height="80" class="px-md-10">
      <div class="d-flex align-center cursor-pointer" @click="$router.push('/')">
        <v-icon icon="mdi-crown" color="#E5B338" size="36" class="mr-2"></v-icon>
        <div class="d-flex flex-column">
          <span class="text-white font-weight-bold text-h6 lh-1">ROYALE PACKAGE</span>
        </div>
      </div>
      <v-spacer></v-spacer>
      <v-btn color="#E5B338" class="text-black font-weight-bold rounded-lg px-6" to="/login">Zaloguj się</v-btn>
    </v-app-bar>

    <v-container class="mt-10 max-width-800">
      <v-card class="pa-6 pa-md-8 rounded-xl" color="#0F172A" elevation="12" border>
        
        <v-row align="center" class="mb-8">
          <v-col cols="12" md="8">
            <v-text-field 
              v-model="searchQuery" 
              placeholder="Wpisz numer paczki (np. RP1234567PL)" 
              variant="solo-filled" 
              bg-color="#1E293B" 
              color="#E5B338" 
              hide-details
              class="custom-input"
              @keyup.enter="trackParcel"
            ></v-text-field>
          </v-col>
          <v-col cols="12" md="4">
            <v-btn block color="#E5B338" height="56" class="rounded-lg text-black font-weight-bold" @click="trackParcel" :loading="isLoading">
              SZUKAJ
            </v-btn>
          </v-col>
        </v-row>

        <div v-if="errorMsg" class="text-center text-red-500 py-4 font-weight-bold">
          <v-icon size="40" class="mb-2">mdi-alert-circle-outline</v-icon>
          <p>{{ errorMsg }}</p>
        </div>

        <div v-else-if="trackingData">
          <div class="d-flex justify-space-between align-center mb-6 border-b pb-4 border-opacity-25">
            <div>
              <h2 class="text-h4 font-weight-black text-white">{{ trackingData.tracking_number }}</h2>
              <p class="text-grey-lighten-1 mt-1">
                Kierunek: <span class="text-white font-weight-bold">{{ trackingData.recipient_city }}</span>
              </p>
            </div>
            <v-chip size="x-large" :color="getStatusColor(trackingData.current_status)" class="font-weight-bold">
              {{ trackingData.current_status }}
            </v-chip>
          </div>

          <v-alert v-if="trackingData.eta && trackingData.current_status !== 'Dostarczona'" color="#1E293B" class="mb-8 rounded-lg border border-opacity-25 text-gold text-center">
            <v-icon start>mdi-clock-fast</v-icon>
            Przewidywany czas doręczenia: <strong>{{ formatTime(trackingData.eta) }}</strong>
          </v-alert>

          <h3 class="text-white mb-6 font-weight-bold">Historia Przesyłki</h3>
          <v-timeline density="compact" truncate-line="start" align="start" line-color="#1E293B">
            <v-timeline-item
              v-for="(event, i) in trackingData.timeline"
              :key="i"
              :dot-color="i === trackingData.timeline.length - 1 ? '#E5B338' : '#334155'"
              size="small"
            >
              <div class="d-flex flex-column">
                <strong class="text-white">{{ event.status }}</strong>
                <span class="text-grey-lighten-1 text-caption">{{ formatDate(event.date) }}</span>
              </div>
            </v-timeline-item>
          </v-timeline>
          <div class="mt-6">
            <h3 class="text-white mb-3 font-weight-bold">Lokalizacja kuriera (live)</h3>
            <div id="tracking-map" class="tracking-map"></div>
          </div>
        </div>

        <div v-else class="text-center py-12 text-grey-darken-1">
          <v-icon size="64" class="mb-4 opacity-50">mdi-package-variant</v-icon>
          <p>Wpisz numer przesyłki, aby sprawdzić jej status.</p>
        </div>

      </v-card>
    </v-container>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { useRoute } from 'vue-router';
import api from '../api/axios';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const route = useRoute();
const searchQuery = ref('');
const trackingData = ref<any>(null);
const isLoading = ref(false);
const errorMsg = ref('');
const map = ref<L.Map | null>(null);
const courierMarker = ref<L.Marker | null>(null);
const ws = ref<WebSocket | null>(null);

const trackParcel = async () => {
  if (!searchQuery.value) return;
  isLoading.value = true;
  errorMsg.value = '';
  trackingData.value = null;
  courierMarker.value = null;

  try {
    const tn = searchQuery.value.trim();
    const response = await api.get(`/tracking/${tn}`);
    trackingData.value = response.data;

    await initMap();
    connectTrackingSocket(tn);
  } catch (error: any) {
    errorMsg.value = error.response?.status === 404
      ? 'Nie znaleziono przesyłki o podanym numerze.'
      : 'Wystąpił błąd serwera.';
  } finally {
    isLoading.value = false;
  }
};

const initMap = async () => {
  await nextTick();

  if (map.value) {
    map.value.remove();
    map.value = null;
  }

  map.value = L.map('tracking-map').setView([52.2297, 21.0122], 12);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map.value);
};

const updateCourierMarker = (lat: number, lon: number) => {
  if (!map.value) return;

  if (!courierMarker.value) {
    courierMarker.value = L.marker([lat, lon]).addTo(map.value).bindPopup('Kurier');
  } else {
    courierMarker.value.setLatLng([lat, lon]);
  }

  map.value.setView([lat, lon], 14);
};

const connectTrackingSocket = (trackingNumber: string) => {
  if (ws.value) {
    ws.value.close();
    ws.value = null;
  }

  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const socketUrl = `${protocol}://localhost:8000/api/v1/tracking/ws/${trackingNumber}`;
  ws.value = new WebSocket(socketUrl);

  ws.value.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      const loc = data?.courier_location;
      if (loc?.latitude != null && loc?.longitude != null) {
        updateCourierMarker(loc.latitude, loc.longitude);
      }
    } catch (e) {
      console.error('Blad parsowania WS:', e);
    }
  };

  ws.value.onerror = (e) => console.error('WS error:', e);
  ws.value.onclose = () => console.log('WS closed');
};

onMounted(() => {
  // Jeśli weszliśmy tu np. przez /tracking/RP1234567PL
  if (route.params.number) {
    searchQuery.value = route.params.number as string;
    trackParcel();
  }
});

onBeforeUnmount(() => {
  if (ws.value) ws.value.close();
  if (map.value) map.value.remove();
});

const getStatusColor = (status: string) => {
  if (status === 'Dostarczona') return 'success';
  if (status === 'W drodze' || status === 'Wydana kurierowi') return 'info';
  return 'grey-darken-2';
};

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString('pl-PL', {
    day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit'
  });
};

const formatTime = (dateString: string) => {
  return new Date(dateString).toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' });
};
</script>

<style scoped>
.tracking-bg {
  background: radial-gradient(circle at top, #0B172A 0%, #020617 100%);
  min-height: 100vh;
}
.max-width-800 { max-width: 800px; margin: 0 auto; }
.text-gold { color: #E5B338 !important; }
.custom-input :deep(.v-field) { border-radius: 12px; }
.custom-input :deep(.v-field__input) { color: white !important; font-weight: bold; }
.tracking-map {
  width: 100%;
  height: 360px;
  border-radius: 12px;
  overflow: hidden;
}
</style>