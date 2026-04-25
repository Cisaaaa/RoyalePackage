<template>
  <div class="dispatcher-container">
    <v-tabs v-model="activeTab" color="#E5B338" class="mb-6">
      <v-tab value="planner" class="font-weight-bold">
        <v-icon start>mdi-robot-outline</v-icon>
        Automatyczne Planowanie
      </v-tab>
      <v-tab value="reports" class="font-weight-bold">
        <v-icon start>mdi-chart-bar</v-icon>
        Raporty i Koszty
      </v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      
      <v-window-item value="planner">
        <v-row>
          <v-col cols="12" md="8">
            <v-card class="rounded-xl elevation-6 overflow-hidden mb-4" border>
              <v-toolbar color="white" flat>
                <v-toolbar-title class="font-weight-bold">
                  <v-icon icon="mdi-package-variant-closed" color="#0B172A" class="mr-2"></v-icon>
                  Paczki Oczekujące ({{ unassignedParcels.length }})
                </v-toolbar-title>
                <v-spacer></v-spacer>
                <v-btn icon @click="fetchData" :loading="loading">
                  <v-icon>mdi-refresh</v-icon>
                </v-btn>
              </v-toolbar>

              <v-data-table
                :headers="headers"
                :items="unassignedParcels"
                class="elevation-0"
                no-data-text="Brak paczek oczekujących na trasę"
              >
                <template v-slot:item.calculated_price="{ item }">
                  <span class="font-weight-bold">{{ item.calculated_price.toFixed(2) }} zł</span>
                </template>
              </v-data-table>
            </v-card>

            <v-card v-if="generatedRoutes.length > 0" class="rounded-xl elevation-6 mt-4" border>
              <v-toolbar color="white" flat>
                <v-toolbar-title class="font-weight-bold text-success">
                  <v-icon icon="mdi-check-circle" color="success" class="mr-2"></v-icon>
                  Wygenerowane Trasy ({{ generatedRoutes.length }})
                </v-toolbar-title>
              </v-toolbar>
              
              <v-expansion-panels variant="accordion">
                <v-expansion-panel v-for="(route, i) in generatedRoutes" :key="i">
                  <v-expansion-panel-title>
                    Trasa #{{ route.route_id }} — {{ route.courier_name }} ({{ route.vehicle_reg }})
                    <template v-slot:actions>
                      <v-chip color="#E5B338" class="font-weight-bold ml-4">
                        {{ route.parcels_count }} paczek
                      </v-chip>
                    </template>
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <v-list density="compact">
                      <v-list-item v-for="(parcel, j) in route.parcels" :key="j">
                        <template v-slot:prepend>
                          <v-avatar color="#0B172A" size="24" class="text-white mr-3">{{ j + 1 }}</v-avatar>
                        </template>
                        <v-list-item-title>{{ parcel.tracking_number }} — {{ parcel.recipient_city }}, {{ parcel.recipient_street }}</v-list-item-title>
                      </v-list-item>
                    </v-list>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
            </v-card>

          </v-col>

          <v-col cols="12" md="4">
            <v-card class="rounded-xl elevation-6 pa-4" color="#0B172A" theme="dark">
              <h3 class="text-h6 font-weight-bold text-white mb-4">
                <v-icon icon="mdi-engine-outline" color="#E5B338" class="mr-2"></v-icon>
                Silnik Logistyczny (VROOM)
              </h3>

              <v-list bg-color="transparent" class="mb-4">
                <v-list-item>
                  <template v-slot:prepend>
                    <v-icon icon="mdi-account-hard-hat" color="info"></v-icon>
                  </template>
                  <v-list-item-title>Dostępni Kurierzy</v-list-item-title>
                  <template v-slot:append>
                    <span class="font-weight-bold text-h6">{{ fleet.couriers.length }}</span>
                  </template>
                </v-list-item>
                
                <v-divider color="white" class="my-2"></v-divider>

                <v-list-item>
                  <template v-slot:prepend>
                    <v-icon icon="mdi-truck-fast" color="info"></v-icon>
                  </template>
                  <v-list-item-title>Wolne Pojazdy</v-list-item-title>
                  <template v-slot:append>
                    <span class="font-weight-bold text-h6">{{ fleet.vehicles.length }}</span>
                  </template>
                </v-list-item>
              </v-list>

              <v-alert v-if="unassignedParcels.length === 0" type="info" variant="tonal" density="compact" class="mb-4">
                Brak paczek do rozwiezienia.
              </v-alert>

              <v-alert v-if="fleet.couriers.length === 0 || fleet.vehicles.length === 0" type="warning" variant="tonal" density="compact" class="mb-4">
                Brakuje wolnych kurierów lub pojazdów do obsługi tras.
              </v-alert>

              <v-btn
                block
                color="#E5B338"
                size="large"
                class="font-weight-bold rounded-lg text-black mt-4"
                style="white-space: normal; height: auto; padding: 12px;"
                :disabled="!isReadyToOptimize"
                :loading="optimizing"
                @click="autoOptimizeRoutes"
              >
                URUCHOM AUTOPLANOWANIE
                <v-icon right class="ml-2">mdi-auto-fix</v-icon>
              </v-btn>
            </v-card>
          </v-col>
        </v-row>
      </v-window-item>

      <v-window-item value="reports">
        <FinancialReports /> 
      </v-window-item>

    </v-window>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="4000">
      {{ snackbar.text }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import api from '../api/axios';
import FinancialReports from './FinancialReports.vue'; 

const activeTab = ref('planner');
const loading = ref(false);
const optimizing = ref(false);

const unassignedParcels = ref([]);
const generatedRoutes = ref([]);

const fleet = ref({
  couriers: [],
  vehicles: []
});

const snackbar = ref({ show: false, text: '', color: 'success' });

const headers = [
  { title: 'Numer Trackingowy', key: 'tracking_number', align: 'start' },
  { title: 'Odbiorca', key: 'recipient_name' },
  { title: 'Miasto', key: 'recipient_city' },
  { title: 'Ulica', key: 'recipient_street' },
  { title: 'Cena', key: 'calculated_price', align: 'end' },
];

// Sprawdzamy, czy można odpalić algorytm
const isReadyToOptimize = computed(() => {
  return unassignedParcels.value.length > 0 && fleet.value.couriers.length > 0 && fleet.value.vehicles.length > 0;
});

const fetchData = async () => {
  loading.value = true;
  try {
    const [parcelsRes, fleetRes] = await Promise.all([
      api.get('/dispatcher/unassigned-parcels'),
      api.get('/dispatcher/fleet')
    ]);
    
    unassignedParcels.value = parcelsRes.data;
    
    fleet.value.couriers = fleetRes.data.couriers;
    fleet.value.vehicles = fleetRes.data.vehicles;
  } catch (error) {
    showSnackbar('Błąd podczas pobierania danych z serwera', 'error');
  } finally {
    loading.value = false;
  }
};

// Nowa funkcja do obsługi automatyzacji
const autoOptimizeRoutes = async () => {
  optimizing.value = true;
  generatedRoutes.value = []; // Czyścimy stare wyniki
  
  try {
    // Strzelamy do nowego endpointu, który obsłuży logikę VROOM dla całej floty
    const response = await api.post('/dispatcher/routes/auto');
    
    if (response.data.unassigned > 0) {
      showSnackbar(`Sukces, ale uwaga: ${response.data.unassigned} paczek nie zmieściło się do aut.`, 'warning');
    } else {
      showSnackbar('VROOM pomyślnie wygenerował trasy dla wszystkich paczek!', 'success');
    }

    generatedRoutes.value = response.data.routes;
    await fetchData(); // Odświeżamy magazyn (powinien być pusty, jeśli wszystko poszło ok)

  } catch (error) {
    showSnackbar(error.response?.data?.detail || 'Błąd podczas optymalizacji tras przez VROOM', 'error');
  } finally {
    optimizing.value = false;
  }
};

const showSnackbar = (text, color) => {
  snackbar.value = { show: true, text, color };
};

onMounted(fetchData);
</script>

<style scoped>
.text-gold {
  color: #E5B338;
}
</style>