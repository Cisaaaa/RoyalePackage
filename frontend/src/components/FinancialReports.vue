<template>
  <div class="financial-reports bg-white p-6 rounded-lg shadow-md">
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold text-gray-800">Raporty Zamkniętych Tras</h2>
      <button @click="fetchReports" class="bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold py-2 px-4 rounded transition-colors">
        Odśwież dane
      </button>
    </div>

    <div v-if="loading" class="text-center py-4">
      Ładowanie danych finansowych...
    </div>

    <div v-else-if="error" class="text-red-600 text-center py-4">
      {{ error }}
    </div>

    <div v-else class="overflow-x-auto">
      <table class="min-w-full bg-white border border-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="py-3 px-4 border-b text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">ID Trasy</th>
            <th class="py-3 px-4 border-b text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Kurier</th>
            <th class="py-3 px-4 border-b text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Pojazd</th>
            <th class="py-3 px-4 border-b text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">Dystans</th>
            <th class="py-3 px-4 border-b text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">Paczki</th>
            <th class="py-3 px-4 border-b text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Przychód</th>
            <th class="py-3 px-4 border-b text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Koszty</th>
            <th class="py-3 px-4 border-b text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Zysk Netto</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="report in reports" :key="report.route_id" class="hover:bg-gray-50 transition-colors">
            <td class="py-3 px-4 border-b text-gray-800 font-medium">#{{ report.route_id }}</td>
            <td class="py-3 px-4 border-b text-gray-600">{{ report.courier_name }}</td>
            <td class="py-3 px-4 border-b text-gray-600">{{ report.vehicle_registration }}</td>
            <td class="py-3 px-4 border-b text-center text-gray-600">{{ report.total_distance_km }} km</td>
            <td class="py-3 px-4 border-b text-center text-gray-600">{{ report.parcels_delivered }}</td>
            <td class="py-3 px-4 border-b text-right text-gray-600">{{ report.total_revenue }} zł</td>
            <td class="py-3 px-4 border-b text-right text-red-500">-{{ report.route_cost }} zł</td>
            <td class="py-3 px-4 border-b text-right font-bold" 
                :class="report.net_profit > 0 ? 'text-green-600' : 'text-red-600'">
              {{ report.net_profit > 0 ? '+' : '' }}{{ report.net_profit }} zł
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="reports.length === 0" class="text-center py-6 text-gray-500">
        Brak danych finansowych. Utwórz pierwszą trasę, aby zobaczyć raport.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '../api/axios';

const reports = ref([]);
const loading = ref(true);
const error = ref(null);

const fetchReports = async () => {
  loading.value = true;
  error.value = null;
  try {
    const response = await api.get('/dispatcher/reports');
    reports.value = response.data;
  } catch (err) {
    console.error('Błąd pobierania raportów:', err);
    error.value = 'Nie udało się pobrać raportów finansowych.';
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchReports();
});
</script>