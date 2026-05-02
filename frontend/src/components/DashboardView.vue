<template>
  <v-container fluid class="dashboard-bg fill-height align-start pa-0">
    
    <v-app-bar app color="#0B172A" elevation="4" height="80">
      <v-container class="d-flex align-center max-width-1200">
        
        <v-icon icon="mdi-crown" color="#E5B338" size="32" class="mr-2"></v-icon>
        <div class="d-flex flex-column">
          <span class="text-white font-weight-bold text-subtitle-1 lh-1">ROYALE PACKAGE</span>
          <span class="text-gold text-caption" style="font-size: 0.6rem !important;">TWÓJ KURIER PREMIUM</span>
        </div>

        <v-spacer></v-spacer>

        <div class="d-none d-md-flex align-center">
          <v-btn variant="text" class="text-white text-capitalize mr-2">Śledzenie</v-btn>
          <v-btn variant="text" class="text-white text-capitalize mr-2">Cennik</v-btn>
          <v-btn variant="text" class="text-white text-capitalize mr-4">Pomoc</v-btn>
        </div>

        <v-btn color="#E5B338" variant="outlined" @click="logout" class="text-capitalize font-weight-bold rounded-lg">
          Wyloguj się
        </v-btn>
      </v-container>
    </v-app-bar>

    <v-container class="mt-16 pt-5 max-width-1200">
      
      <div v-if="userRole === 1">
        <v-row class="mb-4">
          <v-col>
            <h1 class="text-white">Panel Klienta</h1>
            <p class="text-grey-lighten-1">Zarządzaj swoimi przesyłkami i nadawaj nowe.</p>
          </v-col>
        </v-row>
        
        <v-row>
          <v-col cols="12" md="8">
            <ParcelForm />
          </v-col>
          
          <v-col cols="12" md="4">
            <v-card class="pa-4 rounded-xl" color="#0B172A" elevation="6">
              <v-card-title class="text-gold font-weight-bold d-flex align-center">
                <v-icon start color="#E5B338" class="mr-2">mdi-package-variant</v-icon>
                Moje Paczki
                <v-spacer></v-spacer>
                <v-btn icon="mdi-refresh" variant="text" size="small" @click="fetchMyParcels" :loading="isLoading"></v-btn>
              </v-card-title>

              <v-card-text class="mt-2">
                <div v-if="isLoading" class="d-flex justify-center py-4">
                  <v-progress-circular indeterminate color="#E5B338"></v-progress-circular>
                </div>

                <div v-else-if="parcels.length > 0">
                  <v-list bg-color="transparent" class="pa-0">
                    <v-list-item 
                      v-for="p in parcels" 
                      :key="p.parcel_id" 
                      class="mb-3 rounded-lg border border-opacity-10" 
                      style="background-color: #1E293B;"
                    >
                      <template v-slot:prepend>
                        <v-icon color="#E5B338">mdi-numeric-1-box-outline</v-icon>
                      </template>
                      
                      <v-list-item-title class="text-gold font-weight-bold text-caption">
                        {{ p.tracking_number }}
                      </v-list-item-title>
                      
                      <v-list-item-subtitle class="text-white text-caption">
                        Status: <span class="text-grey-lighten-1">{{ p.status_name || 'Wysłano' }}</span>
                      </v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </div>

                <p v-else class="text-grey-lighten-1 mt-2 text-caption">
                  Brak nadanych przesyłek. Twoja pierwsza paczka pojawi się tutaj po zatwierdzeniu formularza.
                </p>
              </v-card-text>
            </v-card>
          </v-col>
          </v-row>
      </div>

      <!-- WIDOK KURIERA ORAZ KIEROWCY TIR -->
      <div v-else-if="userRole === 2 || userRole === 5">
        <v-row class="mb-4 text-center">
          <v-col>
            <h1 class="text-white">Panel Kierowcy</h1>
            <p class="text-grey-lighten-1">Zarządzaj swoją dzisiejszą trasą i doręczeniami.</p>
          </v-col>
        </v-row>
        
        <v-row justify="center">
          <v-col cols="12" lg="10">
            <CourierMap />
          </v-col>
        </v-row>
      </div>

      <div v-else-if="userRole === 3">
        <v-row class="mb-4 text-center">
          <v-col>
            <h1 class="text-white">Panel Dyspozytora HUBu</h1>
            <p class="text-grey-lighten-1">Zarządzaj magazynem i twórz trasy dla kurierów.</p>
          </v-col>
        </v-row>
        
        <DispatcherPanel />
      </div>

      <div v-else-if="userRole === 4" class="w-100">
        <AdminPanel />
      </div>

    </v-container>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import ParcelForm from './ParcelForm.vue';
import CourierMap from './CourierMap.vue';
import { useRouter } from 'vue-router';
import api from '../api/axios'; // KLUCZOWY DODATEK: nasz komunikator z backendem
import DispatcherPanel from '../components/DispatcherPanel.vue';
import AdminPanel from '../components/AdminPanel.vue';

const router = useRouter();

// Stan dla roli i paczek
const userRole = ref<number>(1);
const parcels = ref<any[]>([]); // Tu będą przechowywane paczki pobrane z bazy danych
const isLoading = ref(false); // Flaga ładowania dla ikonki odświeżania

// FUNKCJA POBIERAJĄCA DANE: łączy się z bazą i pobiera listę paczek użytkownika
const fetchMyParcels = async () => {
  try {
    isLoading.value = true;
    // Wysyłamy prośbę do backendu o paczki przypisane do zalogowanego konta
    const response = await api.get('/parcels'); 
    parcels.value = response.data;
  } catch (error) {
    console.error("Błąd podczas pobierania paczek z bazy:", error);
  } finally {
    isLoading.value = false;
  }
};

// Funkcja wylogowania - teraz jedna, czysta wersja korzystająca z routera
const logout = () => {
  localStorage.clear();
  router.push('/login'); 
};

onMounted(() => {
  // 1. Sprawdzamy rolę, żeby wiedzieć co wyświetlić (Klient/Kurier/Dyspozytor)
  const roleFromStorage = localStorage.getItem('user_role');
  if (roleFromStorage) {
    userRole.value = parseInt(roleFromStorage);
  }

  // 2. Jeśli zalogowany to Klient (rola 1), od razu pobieramy jego paczki
  if (userRole.value === 1) {
    fetchMyParcels();
  }
});
</script>

<style scoped>
.dashboard-bg {
  background-color: #020617;
  min-height: 100vh;
}
.text-gold {
  color: #E5B338 !important;
}
.lh-1 {
  line-height: 1.2;
}
.max-width-1200 {
  max-width: 1200px;
  margin: 0 auto;
}
</style>