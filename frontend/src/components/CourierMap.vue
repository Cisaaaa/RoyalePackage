<template>
  <v-card class="custom-card pa-4 pa-md-6" elevation="10">
    <v-card-title class="text-h4 font-weight-bold text-white mb-4 d-flex align-center">
      <v-icon color="#E5B338" size="40" class="mr-3">mdi-map-marker-path</v-icon>
      Moja Trasa na Dziś
    </v-card-title>
    
    <div id="courier-map" style="height: 600px; width: 100%; border-radius: 12px; z-index: 1;"></div>
  </v-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import 'leaflet/dist/leaflet.css'; // Bardzo ważne: style mapy
import L from 'leaflet';
import api from '../api/axios';

const routeStops = ref<any[]>([]);

onMounted(async () => {
  try {
    // 1. Pobieramy Twoje paczki z backendu (te, które widziałeś w Swaggerze)
    const response = await api.get('/courier/route');
    routeStops.value = response.data;
    
    // 2. Ożywiamy mapę
    initMap();
  } catch (error) {
    console.error("Błąd podczas pobierania trasy:", error);
  }
});

const initMap = () => {
  // Domyślny środek mapy (jeśli kurier ma paczki, wyśrodkuj na pierwszej, jeśli nie - np. na Warszawie)
  let centerLat = 52.237;
  let centerLon = 21.011;

  if (routeStops.value.length > 0 && routeStops.value[0].lat) {
      centerLat = routeStops.value[0].lat;
      centerLon = routeStops.value[0].lon;
  }

  // Tworzymy instancję mapy
  const map = L.map('courier-map').setView([centerLat, centerLon], 13);

  // Zaciągamy darmowe kafelki z OpenStreetMap
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);

  // Protip: fix na znikające ikonki w Vue + Vite
  const customIcon = L.icon({
    iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
  });

  // 3. Pętla: rzucamy pinezki na mapę!
  routeStops.value.forEach((stop, index) => {
    if (stop.lat && stop.lon) {
      const marker = L.marker([stop.lat, stop.lon], { icon: customIcon }).addTo(map);

      // Popup, który kurier widzi po kliknięciu w pinezkę
      const popupContent = `
        <div style="font-family: sans-serif; color: #0F172A; min-width: 200px;">
          <h4 style="margin: 0 0 8px 0; color: #E5B338;">Przystanek #${index + 1}</h4>
          <p style="margin: 4px 0;"><b>Paczka:</b> ${stop.tracking_number}</p>
          <p style="margin: 4px 0;"><b>Odbiorca:</b> ${stop.recipient_name} (${stop.recipient_phone})</p>
          <p style="margin: 4px 0;"><b>Adres:</b> ${stop.street} ${stop.building_number}, ${stop.city}</p>
          
          <button style="margin-top: 12px; width: 100%; padding: 8px; background: #E5B338; color: black; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;">
            DORĘCZONO
          </button>
        </div>
      `;
      marker.bindPopup(popupContent);
    }
  });
};
</script>

<style scoped>
.custom-card {
  background-color: #0F172A !important;
  border: 1px solid rgba(229, 179, 56, 0.1);
  border-radius: 20px;
}
.text-gold { color: #E5B338 !important; }

/* Lekki lifting popupa Leafleta, żeby lepiej pasował do Waszego dark-theme */
:deep(.leaflet-popup-content-wrapper) {
  border-radius: 12px;
  box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}
</style>