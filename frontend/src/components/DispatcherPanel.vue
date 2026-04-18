<template>
  <v-row>
    <v-col cols="12" md="8">
      <v-card class="rounded-xl elevation-6 overflow-hidden" border>
        <v-toolbar color="white" flat>
          <v-toolbar-title class="font-weight-bold">
            <v-icon icon="mdi-package-variant-closed" color="#0B172A" class="mr-2"></v-icon>
            Paczki w magazynie (Do przypisania)
          </v-toolbar-title>
          <v-spacer></v-spacer>
          <v-btn icon @click="fetchData" :loading="loading">
            <v-icon>mdi-refresh</v-icon>
          </v-btn>
        </v-toolbar>

        <v-data-table
          v-model="selectedParcels"
          :headers="headers"
          :items="unassignedParcels"
          show-select
          item-value="parcel_id"
          class="elevation-0"
          no-data-text="Brak paczek oczekujących na trasę"
        >
          <template v-slot:item.calculated_price="{ item }">
            <span class="font-weight-bold">{{ item.calculated_price.toFixed(2) }} zł</span>
          </template>
        </v-data-table>
      </v-card>
    </v-col>

    <v-col cols="12" md="4">
      <v-card class="rounded-xl elevation-6 pa-4" color="#0B172A" theme="dark">
        <h3 class="text-h6 font-weight-bold text-white mb-4">
          <v-icon icon="mdi-map-marker-path" color="#E5B338" class="mr-2"></v-icon>
          Planowanie Trasy
        </h3>

        <v-alert v-if="selectedParcels.length === 0" type="info" variant="tonal" density="compact" class="mb-4">
          Wybierz paczki z listy obok, aby zacząć planowanie.
        </v-alert>

        <v-select
          v-model="selectedCourier"
          :items="fleet.couriers"
          label="Wybierz Kuriera"
          item-title="full_name"
          item-value="user_id"
          variant="outlined"
          color="#E5B338"
          class="mb-2"
        ></v-select>

        <v-select
          v-model="selectedVehicle"
          :items="fleet.vehicles"
          label="Wybierz Pojazd"
          item-title="display_name"
          item-value="vehicle_id"
          variant="outlined"
          color="#E5B338"
          class="mb-4"
        ></v-select>

        <v-divider class="mb-4" color="#E5B338"></v-divider>

        <div class="d-flex justify-space-between mb-4">
          <span>Wybrane paczki:</span>
          <span class="font-weight-bold text-gold">{{ selectedParcels.length }}</span>
        </div>

        <v-btn
          block
          color="#E5B338"
          size="large"
          class="text-none font-weight-bold rounded-lg"
          :disabled="!isReadyToCreate"
          :loading="creating"
          @click="createNewRoute"
        >
          UTWÓRZ TRASĘ I WYŚLIJ
        </v-btn>
      </v-card>
    </v-col>
  </v-row>

  <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000">
    {{ snackbar.text }}
  </v-snackbar>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import api from '../api/axios';

const loading = ref(false);
const creating = ref(false);
const unassignedParcels = ref([]);
const selectedParcels = ref([]);
const selectedCourier = ref(null);
const selectedVehicle = ref(null);

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

const isReadyToCreate = computed(() => {
  return selectedParcels.value.length > 0 && selectedCourier.value && selectedVehicle.value;
});

const fetchData = async () => {
  loading.value = true;
  try {
    const [parcelsRes, fleetRes] = await Promise.all([
      api.get('/dispatcher/unassigned-parcels'),
      api.get('/dispatcher/fleet')
    ]);
    
    unassignedParcels.value = parcelsRes.data;
    
    // Mapujemy dane kurierów i pojazdów dla lepszego wyświetlania
    fleet.value.couriers = fleetRes.data.couriers.map(c => ({
      ...c,
      full_name: `${c.first_name} ${c.last_name}`
    }));
    fleet.value.vehicles = fleetRes.data.vehicles.map(v => ({
      ...v,
      display_name: `${v.registration_number} (${v.capacity_kg}kg)`
    }));
  } catch (error) {
    showSnackbar('Błąd podczas pobierania danych', 'error');
  } finally {
    loading.value = false;
  }
};

const createNewRoute = async () => {
  creating.value = true;
  try {
    await api.post('/dispatcher/routes', {
      courier_id: selectedCourier.value,
      vehicle_id: selectedVehicle.value,
      parcel_ids: selectedParcels.value
    });
    
    showSnackbar('Trasa została pomyślnie utworzona!', 'success');
    // Resetujemy wybór i odświeżamy listę
    selectedParcels.value = [];
    selectedCourier.value = null;
    selectedVehicle.value = null;
    await fetchData();
  } catch (error) {
    showSnackbar('Nie udało się utworzyć trasy', 'error');
  } finally {
    creating.value = false;
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