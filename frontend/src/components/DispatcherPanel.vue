<template>
  <div class="dispatcher-container">
    <v-tabs v-model="activeTab" color="#E5B338" class="mb-6">
      <v-tab value="planner" class="font-weight-bold">
        <v-icon start>mdi-car-hatchback</v-icon>
        Kurierzy Lokalni (VROOM)
      </v-tab>
      <v-tab value="linehaul" class="font-weight-bold">
        <v-icon start>mdi-truck-cargo-container</v-icon>
        Wysyłka TIR (Line-Haul)
      </v-tab>
      <v-tab value="reports" class="font-weight-bold">
        <v-icon start>mdi-chart-bar</v-icon>
        Raporty i Koszty
      </v-tab>
      <v-tab value="complaints">
        <v-icon start>mdi-alert-circle-outline</v-icon>
        Reklamacje
      </v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      
      <!-- ========================================== -->
      <!-- ZAKŁADKA 1: VROOM (OSTATNIA MILA / BUSY)   -->
      <!-- ========================================== -->
      <v-window-item value="planner">
        <v-row>
          <v-col cols="12" md="8">
            <v-card class="rounded-xl elevation-6 overflow-hidden mb-4" border style="border-color: rgba(255,255,255,0.1) !important; background-color: #0F172A;">
              <v-toolbar color="transparent" flat class="border-b border-opacity-25">
                <v-toolbar-title class="font-weight-bold text-white">
                  <v-icon icon="mdi-home-city" color="#E5B338" class="mr-2"></v-icon>
                  Paczki Lokalne ({{ localParcels.length }})
                </v-toolbar-title>
                <v-spacer></v-spacer>
                <v-btn icon color="#E5B338" @click="fetchData" :loading="loading">
                  <v-icon>mdi-refresh</v-icon>
                </v-btn>
              </v-toolbar>

              <v-data-table
                :headers="headers"
                :items="localParcels"
                class="bg-transparent text-white"
                no-data-text="Brak paczek do doręczenia w Twoim regionie"
              >
                <template v-slot:item.calculated_price="{ item }">
                  <span class="font-weight-bold text-gold">{{ item.calculated_price.toFixed(2) }} zł</span>
                </template>
              </v-data-table>
            </v-card>

            <!-- Widok wygenerowanych tras lokalnych -->
            <v-card v-if="generatedRoutes.length > 0" class="rounded-xl elevation-6 mt-4 pa-2" color="#1E293B" border>
               <v-toolbar color="transparent" flat>
                <v-toolbar-title class="font-weight-bold text-success">
                  <v-icon icon="mdi-check-circle" color="success" class="mr-2"></v-icon>
                  Wygenerowane Trasy Lokalne ({{ generatedRoutes.length }})
                </v-toolbar-title>
              </v-toolbar>
              <v-expansion-panels variant="accordion" class="bg-transparent">
                <v-expansion-panel v-for="(route, i) in generatedRoutes" :key="i" class="bg-transparent text-white">
                  <v-expansion-panel-title>
                    Trasa #{{ route.route_id }} — {{ route.courier_name }} ({{ route.vehicle_reg }})
                    <template v-slot:actions>
                      <v-chip color="#E5B338" class="font-weight-bold ml-4 text-black">
                        {{ route.parcels_count }} paczek
                      </v-chip>
                    </template>
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <v-list density="compact" class="bg-transparent">
                      <v-list-item v-for="(parcel, j) in route.parcels" :key="j">
                        <template v-slot:prepend>
                          <v-avatar color="#E5B338" size="24" class="text-black font-weight-bold mr-3">{{ j + 1 }}</v-avatar>
                        </template>
                        <v-list-item-title class="text-white">{{ parcel.tracking_number }} — {{ parcel.recipient_city }}, {{ parcel.recipient_street }}</v-list-item-title>
                      </v-list-item>
                    </v-list>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
            </v-card>
          </v-col>

          <v-col cols="12" md="4">
            <v-card class="rounded-xl elevation-6 pa-4" color="#1E293B" border style="border-color: rgba(229,179,56,0.2) !important;">
              <h3 class="text-h6 font-weight-bold text-white mb-4">
                <v-icon icon="mdi-engine-outline" color="#E5B338" class="mr-2"></v-icon>
                Silnik Logistyczny (VROOM)
              </h3>
              
              <div class="d-flex justify-space-between mb-2 text-grey-lighten-1">
                <span>Dostępni Kurierzy:</span><span class="text-white font-weight-bold">{{ fleet.couriers.filter(c => c.role_id === 2).length }}</span>
              </div>
              <div class="d-flex justify-space-between mb-4 text-grey-lighten-1">
                <span>Wolne VAN-y (Lokalne):</span><span class="text-white font-weight-bold">{{ fleet.vehicles.filter(v => v.vehicle_type === 'VAN').length }}</span>
              </div>

              <v-btn
                block
                color="#E5B338"
                size="large"
                class="font-weight-bold rounded-lg text-black mt-4"
                :disabled="localParcels.length === 0"
                :loading="optimizingLocal"
                @click="autoOptimizeRoutes"
              >
                URUCHOM AUTOPLANOWANIE
                <v-icon right class="ml-2">mdi-auto-fix</v-icon>
              </v-btn>
            </v-card>
          </v-col>
        </v-row>
      </v-window-item>

      <!-- ========================================== -->
      <!-- ZAKŁADKA 2: LINE-HAUL (TIRY MIĘDZYMIASTOWE)-->
      <!-- ========================================== -->
      <v-window-item value="linehaul">
        <v-row>
          <v-col cols="12" md="8">
            <v-card class="rounded-xl elevation-6 overflow-hidden mb-4" border style="border-color: rgba(255,255,255,0.1) !important; background-color: #0F172A;">
              <v-toolbar color="transparent" flat class="border-b border-opacity-25">
                <v-toolbar-title class="font-weight-bold text-white">
                  <v-icon icon="mdi-earth" color="#E5B338" class="mr-2"></v-icon>
                  Paczki Tirowe ({{ lineHaulParcels.length }})
                </v-toolbar-title>
                 <v-spacer></v-spacer>
                 <v-btn icon color="#E5B338" @click="fetchData" :loading="loading">
                  <v-icon>mdi-refresh</v-icon>
                </v-btn>
              </v-toolbar>

              <v-data-table
                :headers="headersLineHaul"
                :items="lineHaulParcels"
                class="bg-transparent text-white"
                no-data-text="Brak paczek do innych regionów"
              >
                <!-- Grupowanie paczek po mieście docelowym -->
                <template v-slot:group-header="{ item, columns, toggleGroup, isGroupOpen }">
                  <tr>
                    <td :colspan="columns.length" class="bg-blue-grey-darken-4">
                      <v-btn variant="text" color="#E5B338" :icon="isGroupOpen(item) ? 'mdi-chevron-up' : 'mdi-chevron-down'" @click="toggleGroup(item)"></v-btn>
                      Kierunek: <strong class="text-gold ml-2">{{ item.value }}</strong>
                    </td>
                  </tr>
                </template>
              </v-data-table>
            </v-card>
          </v-col>

          <v-col cols="12" md="4">
            <v-card class="rounded-xl elevation-6 pa-4" color="#1E293B" border style="border-color: rgba(229,179,56,0.2) !important;">
              <h3 class="text-h6 font-weight-bold text-white mb-4">
                <v-icon icon="mdi-truck-fast" color="#E5B338" class="mr-2"></v-icon>
                Wyślij Transport (TIR)
              </h3>

              <v-select
                v-model="selectedDestinationId"
                :items="filteredDestinations"
                item-title="name"
                item-value="warehouse_id"
                label="Wybierz magazyn docelowy"
                variant="outlined"
                color="#E5B338"
                base-color="grey"
                class="mb-2"
              ></v-select>

              <v-select
                v-model="selectedTirDriverId"
                :items="fleet.couriers.filter(c => c.role_id === 5)"
                item-title="first_name"
                item-value="user_id"
                label="Wybierz Kierowcę"
                variant="outlined"
                color="#E5B338"
                base-color="grey"
                class="mb-2"
                no-data-text="Brak wolnych kierowców TIR"
              ></v-select>

               <v-select
                v-model="selectedTirVehicleId"
                :items="fleet.vehicles.filter(v => v.vehicle_type === 'TRUCK')"
                item-title="registration_number"
                item-value="vehicle_id"
                label="Wybierz Ciężarówkę (TIR)"
                variant="outlined"
                color="#E5B338"
                base-color="grey"
                class="mb-4"
              ></v-select>

              <v-btn
                block
                color="success"
                size="large"
                class="font-weight-bold rounded-lg text-white"
                :disabled="!selectedDestinationId || !selectedTirDriverId || !selectedTirVehicleId || lineHaulParcels.length === 0"
                :loading="sendingTir"
                @click="dispatchLineHaul"
              >
                ZAPAKUJ I WYŚLIJ TIRA
              </v-btn>
            </v-card>
          </v-col>
        </v-row>
      </v-window-item>

      <!-- ZAKŁADKA 3: RAPORTY -->
      <v-window-item value="reports">
        <FinancialReports /> 
      </v-window-item>
      
      <v-window-item value="complaints">
  <v-card flat>
    <v-card-title>Zgłoszenia reklamacyjne</v-card-title>
    <v-card-text>
      <v-data-table
        :headers="complaintHeaders"
        :items="complaintsList"
        :loading="loadingComplaints"
        class="elevation-1"
      >
        <template v-slot:item.status="{ item }">
          <v-chip
            :color="item.status === 'PENDING' ? 'warning' : item.status === 'ACCEPTED' ? 'success' : 'error'"
            size="small"
            text-color="white"
          >
            {{ item.status === 'PENDING' ? 'Oczekująca' : item.status === 'ACCEPTED' ? 'Uznana' : 'Odrzucona' }}
          </v-chip>
        </template>
        
        <template v-slot:item.actions="{ item }">
          <div v-if="item.status === 'PENDING'">
             <v-btn size="small" color="success" class="mr-2" @click="handleResolveComplaint(item.complaint_id, 'ACCEPTED')">
               <v-icon left>mdi-check</v-icon> Uznaj
             </v-btn>
             <v-btn size="small" color="error" @click="handleResolveComplaint(item.complaint_id, 'REJECTED')">
               <v-icon left>mdi-close</v-icon> Odrzuć
             </v-btn>
          </div>
          <div v-else>
            <span v-if="item.status === 'ACCEPTED'" class="text-success font-weight-bold">
              Zwrot: {{ item.refund_amount }} zł
            </span>
            <span v-else class="text-grey">Rozpatrzona</span>
          </div>
        </template>
      </v-data-table>
    </v-card-text>
  </v-card>
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
import { getComplaints, resolveComplaint } from '../api/axios';

const activeTab = ref('planner');
const loading = ref(false);
const optimizingLocal = ref(false);
const sendingTir = ref(false);

const unassignedParcels = ref([]);
const generatedRoutes = ref([]);

const selectedDestinationId = ref(null);
const selectedTirDriverId = ref(null);
const selectedTirVehicleId = ref(null);

// NOWE ZMIENNE: Zapamiętają "kim" jest zalogowany dyspozytor
const dispatcherRegionId = ref(null);
const dispatcherWarehouseId = ref(null);

const availableDestinations = ref([
    { warehouse_id: 1, name: "HUB Warszawa" },
    { warehouse_id: 2, name: "HUB Kraków" }
]);

const fleet = ref({ couriers: [], vehicles: [] });
const snackbar = ref({ show: false, text: '', color: 'success' });

const headers = [
  { title: 'Nr Trackingowy', key: 'tracking_number', align: 'start' },
  { title: 'Miasto', key: 'recipient_city' },
  { title: 'Ulica', key: 'recipient_street' },
  { title: 'Cena', key: 'calculated_price', align: 'end' },
];

const headersLineHaul = [
  { title: 'Kierunek', key: 'recipient_city', align: 'start' },
  { title: 'Nr Trackingowy', key: 'tracking_number' },
  { title: 'Status', key: 'status_name' },
];

// --- LOGIKA ROZDZIELANIA PACZEK ---
const localParcels = computed(() => {
    // Paczka jest lokalna TYLKO gdy jej region docelowy to MÓJ region!
    return unassignedParcels.value.filter(p => p.target_region_id === dispatcherRegionId.value);
});

const lineHaulParcels = computed(() => {
    // Paczka jedzie TIRem, jeśli jedzie gdziekolwiek indziej, niż MÓJ region
    return unassignedParcels.value.filter(p => p.target_region_id && p.target_region_id !== dispatcherRegionId.value);
});

// NOWOŚĆ: Filtrujemy dropdown, żeby dyspozytor nie mógł wysłać TIRa sam do siebie
const filteredDestinations = computed(() => {
    return availableDestinations.value.filter(d => d.warehouse_id !== dispatcherWarehouseId.value);
});


// --- Stan dla Reklamacji ---
const complaintsList = ref([]);
const loadingComplaints = ref(false);

const complaintHeaders = [
  { title: 'ID Reklamacji', key: 'complaint_id' },
  { title: 'ID Paczki', key: 'parcel_id' },
  { title: 'Powód', key: 'reason' },
  { title: 'Opis klienta', key: 'description' },
  { title: 'Status', key: 'status' },
  { title: 'Akcje', key: 'actions', sortable: false }
];

const fetchData = async () => {
  loading.value = true;
  try {
    const [parcelsRes, fleetRes] = await Promise.all([
      api.get('/dispatcher/unassigned-parcels'),
      api.get('/dispatcher/fleet')
    ]);
    
    // Zapisujemy, kim jesteśmy
    dispatcherRegionId.value = fleetRes.data.dispatcher_region_id;
    dispatcherWarehouseId.value = fleetRes.data.dispatcher_warehouse_id;

    unassignedParcels.value = parcelsRes.data;
    fleet.value.couriers = fleetRes.data.couriers;
    fleet.value.vehicles = fleetRes.data.vehicles;
  } catch (error) {
    showSnackbar('Błąd pobierania danych', 'error');
  } finally {
    loading.value = false;
  }
};

const autoOptimizeRoutes = async () => {
  optimizingLocal.value = true;
  generatedRoutes.value = []; 
  try {
    const response = await api.post('/dispatcher/routes/auto');
    if (response.data.unassigned > 0) {
      showSnackbar(`Gotowe, ale ${response.data.unassigned} paczek zostało w HUBie.`, 'warning');
    } else {
      showSnackbar('Sukces! Zoptymalizowano trasy VROOM.', 'success');
    }
    generatedRoutes.value = response.data.routes;
    await fetchData(); 
  } catch (error) {
    showSnackbar(error.response?.data?.detail || 'Błąd algorytmu VROOM', 'error');
  } finally {
    optimizingLocal.value = false;
  }
};

// Funkcja pobierająca listę reklamacji
const fetchComplaints = async () => {
  loadingComplaints.value = true;
  try {
    complaintsList.value = await getComplaints();
  } catch (error) {
    console.error("Błąd podczas pobierania reklamacji:", error);
    showSnackbar('Nie udało się pobrać listy reklamacji.', 'error');
  } finally {
    loadingComplaints.value = false;
  }
};

// Funkcja wywoływana po kliknięciu Uznaj/Odrzuć
const handleResolveComplaint = async (complaintId, newStatus) => {
  try {
    const response = await resolveComplaint(complaintId, newStatus);
    
    // Pokaż powiadomienie z informacją o kwocie zwrotu
    showSnackbar(response.message + (response.refund > 0 ? ` Zwrócono: ${response.refund} zł` : ''), 'success');

    // Odśwież tabelę
    await fetchComplaints();
    
  } catch (error) {
    console.error("Błąd podczas rozpatrywania:", error);
    showSnackbar('Błąd podczas zmiany statusu reklamacji.', 'error');
  }
};




const dispatchLineHaul = async () => {
    sendingTir.value = true;
    try {
        await api.post(`/dispatcher/routes/line-haul?target_warehouse_id=${selectedDestinationId.value}&courier_id=${selectedTirDriverId.value}&vehicle_id=${selectedTirVehicleId.value}`);
        showSnackbar('TIR wyruszył w trasę!', 'success');
        selectedDestinationId.value = null;
        selectedTirDriverId.value = null;
        selectedTirVehicleId.value = null;
        await fetchData();
    } catch(error) {
         showSnackbar(error.response?.data?.detail || 'Błąd wysyłki TIRa', 'error');
    } finally {
        sendingTir.value = false;
    }
}

const showSnackbar = (text, color) => {
  snackbar.value = { show: true, text, color };
};

onMounted(async () => {
  await fetchData();
  await fetchComplaints();
});
</script>

<style scoped>
.text-gold { color: #E5B338 !important; }
:deep(.v-data-table) { background-color: transparent !important; }
</style>