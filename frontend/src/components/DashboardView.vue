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
            <ParcelForm :key="formKey" />
          </v-col>
          
          <v-col cols="12" md="4">
            
            <v-btn 
              block 
              color="#1E293B" 
              class="mb-4 text-white font-weight-bold rounded-xl border border-opacity-25" 
              style="border-color: #E5B338 !important;" 
              height="56"
              @click="openContactsModal"
            >
              <v-icon start color="#E5B338">mdi-notebook-outline</v-icon> Książka Adresowa
            </v-btn>

            <v-card class="pa-4 rounded-xl" color="#0B172A" elevation="6">
              <v-card-title class="text-gold font-weight-bold d-flex align-center">
                <v-icon start color="#E5B338" class="mr-2">mdi-package-variant</v-icon> Moje Paczki
                <v-spacer></v-spacer>
                <v-btn icon="mdi-refresh" variant="text" size="small" @click="refreshClientData" :loading="isLoading"></v-btn>
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
                      <div class="mt-2 d-flex flex-wrap align-center ga-2">
                        <v-chip
                          v-if="complaintStatusByParcel[p.parcel_id]"
                          size="x-small"
                          :color="getComplaintChipColor(complaintStatusByParcel[p.parcel_id])"
                          variant="flat"
                          class="font-weight-bold"
                        >
                          Reklamacja: {{ getComplaintLabel(complaintStatusByParcel[p.parcel_id]) }}
                        </v-chip>

                        <v-btn
                          v-if="canSubmitComplaint(p)"
                          size="x-small"
                          color="error"
                          variant="outlined"
                          @click="openComplaintDialog(p)"
                        >
                          Zgłoś reklamację
                        </v-btn>
                      </div>
                      <template v-slot:append>
                        <div class="d-flex align-center">
                          <v-btn icon="mdi-printer" size="small" variant="text" color="#E5B338" title="Pobierz Etykietę PDF" @click="downloadLabel(p.parcel_id, p.tracking_number)"></v-btn>
                        </div>
                      </template>
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

      <div v-else-if="userRole === 2 || userRole === 5">
        <v-row class="mb-4 text-center">
          <v-col>
            <h1 class="text-white">Panel Kierowcy</h1>
            <p class="text-grey-lighten-1">Zarządzaj swoją dzisiejszą trasą i doręczeniami.</p>
          </v-col>
        </v-row>
        <v-row justify="center">
          <v-col cols="12" lg="10"><CourierMap /></v-col>
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

    <v-dialog v-model="dialogContacts" max-width="600px">
      <v-card color="#0F172A" class="rounded-xl border border-opacity-25" style="border-color: #E5B338 !important;">
        <v-card-title class="text-h5 font-weight-bold text-white pa-6 border-b border-opacity-25 d-flex align-center">
          <v-icon color="#E5B338" class="mr-3">mdi-notebook-outline</v-icon> Twoja Książka Adresowa
          <v-spacer></v-spacer>
          <v-btn icon="mdi-close" variant="text" color="white" @click="closeContactsModal"></v-btn>
        </v-card-title>
        
        <v-card-text class="pa-6">
          <div v-if="isLoadingContacts" class="d-flex justify-center py-4">
            <v-progress-circular indeterminate color="#E5B338"></v-progress-circular>
          </div>
          
          <v-list v-else-if="myContacts.length > 0" bg-color="transparent" class="pa-0">
            <v-list-item
              v-for="c in myContacts"
              :key="c.contact_id"
              class="mb-3 rounded-lg border border-opacity-10 pa-3"
              style="background-color: #1E293B;"
            >
              <template v-slot:prepend>
                <v-avatar color="#E5B338" size="40" class="mr-3">
                  <span class="text-black font-weight-bold">{{ c.first_name.charAt(0) }}{{ c.last_name.charAt(0) }}</span>
                </v-avatar>
              </template>
              
              <v-list-item-title class="text-white font-weight-bold">{{ c.first_name }} {{ c.last_name }}</v-list-item-title>
              <v-list-item-subtitle class="text-grey-lighten-1 text-caption mt-1">
                {{ c.address.street }} {{ c.address.building_number }}, {{ c.address.city }}
              </v-list-item-subtitle>
              <v-list-item-subtitle class="text-gold text-caption">Tel: {{ c.phone }}</v-list-item-subtitle>
              
              <template v-slot:append>
                <v-btn icon="mdi-delete" variant="tonal" color="error" size="small" @click="deleteContact(c.contact_id)" title="Usuń z książki"></v-btn>
              </template>
            </v-list-item>
          </v-list>
          
          <div v-else class="text-center py-8">
            <v-icon size="48" color="grey-darken-1" class="mb-2">mdi-account-off-outline</v-icon>
            <p class="text-grey-lighten-1">Nie masz jeszcze żadnych zapisanych kontaktów.</p>
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>

    <v-dialog v-model="complaintDialog" max-width="500px">
      <v-card color="#0F172A" class="rounded-xl border border-opacity-25" style="border-color: #E5B338 !important;">
        <v-card-title class="text-h5 font-weight-bold text-white pa-6 border-b border-opacity-25 d-flex align-center">
          <v-icon color="#E5B338" class="mr-3">mdi-alert-circle-outline</v-icon>
          Zgłoś reklamację
          <v-spacer></v-spacer>
          <v-btn icon="mdi-close" variant="text" color="white" @click="closeComplaintDialog"></v-btn>
        </v-card-title>

        <v-card-text class="pa-6">
          <p class="text-grey-lighten-1 mb-4" v-if="selectedParcel">
            Reklamujesz paczkę nr: <strong class="text-white">{{ selectedParcel.tracking_number }}</strong>
          </p>

          <v-select
            v-model="complaintForm.reason"
            :items="['Uszkodzenie zawartości', 'Zaginięcie paczki', 'Opóźnienie doręczenia', 'Inne']"
            label="Powód reklamacji"
            variant="outlined"
            color="#E5B338"
            class="mb-3"
            required
          ></v-select>

          <v-textarea
            v-model="complaintForm.description"
            label="Opis sytuacji (opcjonalnie)"
            rows="3"
            variant="outlined"
            color="#E5B338"
          ></v-textarea>
        </v-card-text>

        <v-card-actions class="pa-6 pt-0">
          <v-spacer></v-spacer>
          <v-btn color="blue-grey-lighten-1" variant="text" @click="closeComplaintDialog">Anuluj</v-btn>
          <v-btn color="error" variant="text" @click="submitComplaintForm" :loading="isSubmitting">
            Wyślij reklamację
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import ParcelForm from './ParcelForm.vue';
import CourierMap from './CourierMap.vue';
import { useRouter } from 'vue-router';
import api, { submitComplaint, getMyComplaints } from '../api/axios';
import DispatcherPanel from '../components/DispatcherPanel.vue';
import AdminPanel from '../components/AdminPanel.vue';

const router = useRouter();

// Stan dla roli i paczek
const userRole = ref<number>(1);
const parcels = ref<any[]>([]);
const isLoading = ref(false);

// --- STAN DLA KSIĄŻKI ADRESOWEJ ---
const formKey = ref(0); // Zmienna wymuszająca odświeżenie formularza po zamknięciu modala
const dialogContacts = ref(false);
const myContacts = ref<any[]>([]);
const isLoadingContacts = ref(false);

// --- STAN REKLAMACJI ---
const complaintDialog = ref(false);
const selectedParcel = ref<any | null>(null);
const isSubmitting = ref(false);
const complaintForm = ref({
  reason: '',
  description: ''
});
const complaintStatusByParcel = ref<Record<number, string>>({});

const fetchMyParcels = async () => {
  try {
    isLoading.value = true;
    const response = await api.get('/parcels'); 
    parcels.value = response.data;
  } catch (error) {
    console.error("Błąd podczas pobierania paczek z bazy:", error);
  } finally {
    isLoading.value = false;
  }
};

const fetchMyComplaints = async () => {
  try {
    const complaints = await getMyComplaints();
    const byParcel: Record<number, string> = {};
    complaints.forEach((c: any) => {
      byParcel[c.parcel_id] = c.status;
    });
    complaintStatusByParcel.value = byParcel;
  } catch (error) {
    console.error('Błąd podczas pobierania reklamacji klienta:', error);
  }
};

const getComplaintLabel = (status: string) => {
  if (status === 'PENDING') return 'Oczekująca';
  if (status === 'ACCEPTED') return 'Uznana';
  if (status === 'REJECTED') return 'Odrzucona';
  return status;
};

const getComplaintChipColor = (status: string) => {
  if (status === 'PENDING') return 'warning';
  if (status === 'ACCEPTED') return 'success';
  if (status === 'REJECTED') return 'error';
  return 'grey';
};

const canSubmitComplaint = (parcel: any) => {
  const isDelivered = parcel.status_name === 'Dostarczona' || parcel.status_id === 6;
  const hasComplaint = !!complaintStatusByParcel.value[parcel.parcel_id];
  return isDelivered && !hasComplaint;
};

const refreshClientData = async () => {
  await Promise.all([fetchMyParcels(), fetchMyComplaints()]);
};

const downloadLabel = async (parcelId: number, trackingNumber: string) => {
  try {
    const response = await api.get(`/parcels/${parcelId}/label`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `Etykieta_${trackingNumber}.pdf`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } catch (error) {
    console.error("Błąd pobierania etykiety:", error);
  }
};

// --- FUNKCJE KSIĄŻKI ADRESOWEJ ---
const openContactsModal = async () => {
  dialogContacts.value = true;
  await fetchContacts();
};

const closeContactsModal = () => {
  dialogContacts.value = false;
  formKey.value += 1; // Ta linijka odświeża komponent ParcelForm, aktualizując jego dropdown!
};

const fetchContacts = async () => {
  isLoadingContacts.value = true;
  try {
    const response = await api.get('/contacts');
    myContacts.value = response.data;
  } catch (e) {
    console.error("Błąd pobierania kontaktów", e);
  } finally {
    isLoadingContacts.value = false;
  }
};

const deleteContact = async (contactId: number) => {
  try {
    await api.delete(`/contacts/${contactId}`);
    await fetchContacts(); // Odświeżamy listę widoczną w modalu
  } catch (e) {
    console.error("Błąd usuwania kontaktu", e);
    alert("Wystąpił błąd podczas usuwania kontaktu.");
  }
};

const openComplaintDialog = (parcel: any) => {
  selectedParcel.value = parcel;
  complaintForm.value.reason = '';
  complaintForm.value.description = '';
  complaintDialog.value = true;
};

const closeComplaintDialog = () => {
  complaintDialog.value = false;
  selectedParcel.value = null;
};

const submitComplaintForm = async () => {
  if (!complaintForm.value.reason) {
    alert('Proszę wybrać powód reklamacji.');
    return;
  }

  if (!selectedParcel.value) {
    alert('Nie wybrano paczki do reklamacji.');
    return;
  }

  isSubmitting.value = true;
  try {
    await submitComplaint({
      parcel_id: selectedParcel.value.parcel_id,
      reason: complaintForm.value.reason,
      description: complaintForm.value.description
    });

    alert('Reklamacja została przyjęta.');
    closeComplaintDialog();
    await refreshClientData();
  } catch (error) {
    console.error('Błąd podczas wysyłania reklamacji:', error);
    const detail = (error as any)?.response?.data?.detail;
    alert(detail || 'Wystąpił błąd podczas zgłaszania reklamacji.');
  } finally {
    isSubmitting.value = false;
  }
};

const logout = () => {
  localStorage.clear();
  router.push('/login'); 
};

onMounted(() => {
  const roleFromStorage = localStorage.getItem('user_role');
  if (roleFromStorage) {
    userRole.value = parseInt(roleFromStorage);
  }
  if (userRole.value === 1) {
    refreshClientData();
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