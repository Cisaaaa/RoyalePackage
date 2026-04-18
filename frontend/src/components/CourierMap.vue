<template>
  <v-card class="custom-card pa-4 pa-md-6 mb-6" elevation="10">
    <v-card-title class="text-h4 font-weight-bold text-white mb-4 d-flex align-center">
      <v-icon color="#E5B338" size="40" class="mr-3">mdi-map-marker-path</v-icon>
      Moja Trasa na Dziś
    </v-card-title>
    
    <div id="courier-map" style="height: 500px; width: 100%; border-radius: 12px; z-index: 1;"></div>
  </v-card>

  <v-card class="custom-card pa-4 pa-md-6" elevation="10">
    <h3 class="text-gold mb-4 text-h5 font-weight-bold">Lista Przesyłek (Zoptymalizowana)</h3>
    
    <v-list bg-color="transparent" class="pa-0">
      <v-list-item 
        v-for="(stop, index) in routeStops" 
        :key="stop.stop_id"
        class="mb-4 rounded-xl border pa-4"
        :style="{ 
          backgroundColor: stop.status === 'COMPLETED' ? '#0F172A' : '#1E293B',
          borderColor: stop.status === 'COMPLETED' ? 'rgba(255,255,255,0.05)' : 'rgba(229, 179, 56, 0.3)',
          opacity: stop.status === 'COMPLETED' ? 0.6 : 1
        }"
      >
        <div class="d-flex flex-column flex-md-row justify-space-between align-md-center w-100">
          
          <div class="mb-4 mb-md-0">
            <div class="d-flex align-center mb-1">
              <v-chip size="small" :color="stop.status === 'COMPLETED' ? 'grey' : '#E5B338'" class="mr-3 font-weight-bold">
                {{ index + 1 }}
              </v-chip>
              <span class="text-white font-weight-bold text-h6">{{ stop.tracking_number }}</span>
            </div>
            <p class="text-grey-lighten-1 mb-1 text-body-2 mt-2">
              <v-icon size="small" class="mr-1">mdi-account</v-icon> {{ stop.recipient_name }} ({{ stop.recipient_phone }})
            </p>
            <p class="text-grey-lighten-1 mb-0 text-body-2">
              <v-icon size="small" class="mr-1">mdi-map-marker</v-icon> {{ stop.street }} {{ stop.building_number }}, {{ stop.city }}
            </p>
          </div>

          <div class="d-flex flex-wrap gap-2">
            <v-btn 
              v-if="stop.operation_type === 'DROP_OFF' && stop.status !== 'COMPLETED'"
              color="error" variant="outlined" class="mr-2 font-weight-bold" prepend-icon="mdi-alert-circle-outline"
            >
              PROBLEM
            </v-btn>
            
            <v-btn 
              v-if="stop.status !== 'COMPLETED'"
              color="#E5B338" class="text-black font-weight-bold" prepend-icon="mdi-check-circle-outline"
              @click="markAsDelivered(index)"
            >
              {{ stop.operation_type === 'WAREHOUSE_TRANSFER' ? 'START TRASY' : 'DORĘCZONO' }}
            </v-btn>
            
            <v-chip v-else color="success" variant="flat" class="font-weight-bold">
              <v-icon start>mdi-check-all</v-icon> 
              {{ stop.operation_type === 'WAREHOUSE_TRANSFER' ? 'W TRASIE' : 'DORĘCZONA' }}
            </v-chip>
          </div>

        </div>
      </v-list-item>
    </v-list>
  </v-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import api from '../api/axios';

const routeStops = ref<any[]>([]);
let map: L.Map | null = null; 
let layerGroup: L.LayerGroup | null = null; 
let currentStopCount = 0; // Pamiętamy ilość paczek do Long Pollingu

onMounted(async () => {
  try {
    const response = await api.get('/courier/route');
    let fetchedStops = response.data.map((stop: any) => ({ ...stop, status: 'PLANNED' }));
    currentStopCount = fetchedStops.length;

    fetchedStops = await optimizeRoute(fetchedStops);

    routeStops.value = fetchedStops;
    initMap();
    
    // Startujemy nasłuchiwanie na nowe paczki
    startLongPolling();

  } catch (error) {
    console.error("Błąd pobierania/optymalizacji trasy:", error);
  }
});

// Funkcja pomocnicza: Wyciągnięta logika OSRM, żeby użyć jej też przy Long Pollingu
const optimizeRoute = async (stops: any[]) => {
  if (stops.length < 2) return stops;
  try {
    const coords = stops.map((s: any) => `${s.lon},${s.lat}`).join(';');
    const tripUrl = `https://router.project-osrm.org/trip/v1/driving/${coords}?source=first&destination=any&roundtrip=false`;
    
    const tripResp = await fetch(tripUrl);
    const tripData = await tripResp.json();

    if (tripData.code === "Ok" && tripData.waypoints) {
      const optimized = new Array(stops.length);
      tripData.waypoints.forEach((wp: any, index: number) => {
        optimized[wp.waypoint_index] = stops[index];
      });
      return optimized;
    }
  } catch(e) {
    console.error("Błąd optymalizacji OSRM", e);
  }
  return stops;
};

const initMap = () => {
  let centerLat = 52.237; let centerLon = 21.011;
  if (routeStops.value.length > 0 && routeStops.value[0].lat) {
      centerLat = routeStops.value[0].lat; centerLon = routeStops.value[0].lon;
  }

  map = L.map('courier-map').setView([centerLat, centerLon], 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap contributors' }).addTo(map);
  layerGroup = L.layerGroup().addTo(map);

  renderRouteAndMarkers();
};

const renderRouteAndMarkers = async () => {
  if (!map || !layerGroup) return;
  layerGroup.clearLayers();

  const activeIcon = L.icon({ iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png', shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png', iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34] });
  const completedIcon = L.icon({ iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-grey.png', shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png', iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34] });
  const hubIcon = L.icon({ iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-gold.png', shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png', iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34] });

  // 1. Rysowanie pinezek
  routeStops.value.forEach((stop, index) => {
    if (stop.lat && stop.lon) {
      let currentIcon = stop.status === 'COMPLETED' ? completedIcon : activeIcon;
      if (stop.operation_type === 'WAREHOUSE_TRANSFER' && stop.status !== 'COMPLETED') currentIcon = hubIcon;

      const marker = L.marker([stop.lat, stop.lon], { icon: currentIcon }).addTo(layerGroup!); 
      marker.bindPopup(`<div style="text-align: center;"><b>${stop.tracking_number}</b><br>Przystanek #${index + 1}</div>`);
    }
  });

  // --- LOGIKA TRASOWANIA (Początek od ostatniego punktu) ---
  const firstPendingIndex = routeStops.value.findIndex(s => s.status !== 'COMPLETED');
  let routingStops = [];

  if (firstPendingIndex === -1) {
    routingStops = []; // Wszystko doręczone
  } else if (firstPendingIndex === 0) {
    routingStops = routeStops.value; // Jeszcze nie wyruszyliśmy
  } else {
    // Wyruszyliśmy - bierzemy ostatni punkt jako pozycję i wyznaczamy trasę do reszty
    routingStops = routeStops.value.slice(firstPendingIndex - 1);
  }

  routingStops = routingStops.filter(s => s.lat !== null && s.lon !== null);

  // 2. Rysowanie linii OSRM
  if (routingStops.length >= 2) {
    try {
      // Aktualny cel (Niebieski)
      const currentLegUrl = `https://router.project-osrm.org/route/v1/driving/${routingStops[0].lon},${routingStops[0].lat};${routingStops[1].lon},${routingStops[1].lat}?overview=full&geometries=geojson`;
      const currentResp = await fetch(currentLegUrl);
      const currentData = await currentResp.json();
      
      if (currentData.routes && currentData.routes[0]) {
        L.geoJSON(currentData.routes[0].geometry, {
          style: { color: '#3B82F6', weight: 6, opacity: 0.9 } 
        }).addTo(layerGroup!);
      }

      // Przyszłe cele (Szary przerywany)
      if (routingStops.length > 2) {
        const futureCoords = routingStops.slice(1).map(s => `${s.lon},${s.lat}`).join(';');
        const futureUrl = `https://router.project-osrm.org/route/v1/driving/${futureCoords}?overview=full&geometries=geojson`;
        
        const futureResp = await fetch(futureUrl);
        const futureData = await futureResp.json();
        
        if (futureData.routes && futureData.routes[0]) {
          L.geoJSON(futureData.routes[0].geometry, {
            style: { color: '#94A3B8', weight: 4, opacity: 0.6, dashArray: '5, 10' } 
          }).addTo(layerGroup!);
        }
      }
    } catch (error) {
      console.error("Błąd rysowania tras OSRM:", error);
    }
  }
};

const markAsDelivered = (index: number) => {
  routeStops.value[index].status = 'COMPLETED';
  renderRouteAndMarkers(); 
};

// --- LONG POLLING ---
const startLongPolling = async () => {
  try {
    const response = await api.get(`/courier/long-poll?last_known_count=${currentStopCount}`);
    
    if (response.data.updated) {
      console.log("Dyspozytor dodał nową paczkę!");
      currentStopCount = response.data.new_count;
      
      const freshRouteResponse = await api.get('/courier/route');
      
      // Zabezpieczenie przed utratą zrobionego postępu (statusów COMPLETED)
      let newStops = freshRouteResponse.data.map((stop: any) => {
        const existingStop = routeStops.value.find(s => s.stop_id === stop.stop_id);
        return {
          ...stop,
          status: existingStop ? existingStop.status : 'PLANNED'
        };
      });
      
      newStops = await optimizeRoute(newStops);
      routeStops.value = newStops;
      
      renderRouteAndMarkers();
    }
  } catch (error) {
    console.error("Błąd Long Pollingu. Ponawiam za 5 sekund...", error);
    await new Promise(resolve => setTimeout(resolve, 5000)); 
  } finally {
    startLongPolling();
  }
};
</script>

<style scoped>
.custom-card {
  background-color: #0F172A !important;
  border: 1px solid rgba(229, 179, 56, 0.1);
  border-radius: 20px;
}
.text-gold { color: #E5B338 !important; }
.gap-2 { gap: 8px; }
</style>