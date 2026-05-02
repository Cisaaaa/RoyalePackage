<template>
  <v-container fluid class="admin-panel pa-6">
    <!-- NAGŁÓWEK -->
    <v-row>
      <v-col cols="12" class="text-center mb-4">
        <h1 class="text-h4 font-weight-bold text-white">Centrala: Panel Administratora</h1>
        <p class="text-subtitle-1 text-grey-lighten-1">Zarządzanie strukturą i pracownikami firmy Royale Package</p>
      </v-col>
    </v-row>

    <!-- NAWIGACJA (ZAKŁADKI) -->
    <v-tabs v-model="tab" color="#E5B338" align-tabs="center" class="mb-6">
      <v-tab value="staff" class="font-weight-bold">
        <v-icon start>mdi-account-tie</v-icon>
        Zarządzanie Personelem
      </v-tab>
      <v-tab value="fleet" class="font-weight-bold">
        <v-icon start>mdi-truck</v-icon>
        Zarządzanie Flotą
      </v-tab>
      <v-tab value="tariffs" class="font-weight-bold">
        <v-icon start>mdi-cash-multiple</v-icon>
        Cenniki i Taryfy
      </v-tab>
    </v-tabs>

    <!-- ZAWARTOŚĆ ZAKŁADEK -->
    <v-window v-model="tab" class="mt-4">
      
      <!-- ZAKŁADKA 1: PERSONEL -->
      <v-window-item value="staff">
        <v-card color="#0F172A" elevation="6" border style="border-color: rgba(255,255,255,0.1) !important;" class="rounded-xl pa-4">
          <v-card-title class="d-flex align-center text-white font-weight-bold mb-4">
            <v-icon color="#E5B338" class="mr-2">mdi-account-group</v-icon>
            Pracownicy Firmy
            <v-spacer></v-spacer>
            <v-btn color="#E5B338" class="text-black font-weight-bold" prepend-icon="mdi-plus" @click="dialog = true">
              Zatrudnij
            </v-btn>
          </v-card-title>
          
          <v-data-table
            :headers="headers"
            :items="employees"
            :loading="loading"
            class="bg-transparent text-white"
            no-data-text="Brak pracowników do wyświetlenia"
          >
            <!-- ZMODYFIKOWANE CHIPY RÓL: używamy variant="tonal" -->
            <template v-slot:item.role_id="{ item }">
              <v-chip :color="getRoleColor(item.role_id)" variant="tonal" size="small" class="font-weight-bold text-uppercase">
                {{ getRoleName(item.role_id) }}
              </v-chip>
            </template>
          </v-data-table>
        </v-card>
      </v-window-item>

      <v-window-item value="fleet">
        <div class="text-center py-8 text-grey text-h6">Moduł floty (W budowie)</div>
      </v-window-item>

      <v-window-item value="tariffs">
         <div class="text-center py-8 text-grey text-h6">Moduł cenników (W budowie)</div>
      </v-window-item>
    </v-window>

    <!-- ========================================== -->
    <!-- OKIENKO MODALNE (ZATRUDNIANIE PRACOWNIKA)  -->
    <!-- ========================================== -->
    <v-dialog v-model="dialog" max-width="600px" persistent>
      <v-card color="#1E293B" class="rounded-xl border border-opacity-25" style="border-color: #E5B338 !important;">
        <v-card-title class="text-h5 font-weight-bold text-white pa-6 border-b border-opacity-25">
          Zatrudnij Nowego Pracownika
        </v-card-title>
        
        <v-card-text class="pa-6">
          <v-form v-model="isFormValid" @submit.prevent="submitEmployee">
            <v-row dense>
              <v-col cols="12" md="6">
                <v-text-field v-model="formData.first_name" label="Imię" :rules="[rules.required]" variant="outlined" color="#E5B338" base-color="grey"></v-text-field>
              </v-col>
              <v-col cols="12" md="6">
                <v-text-field v-model="formData.last_name" label="Nazwisko" :rules="[rules.required]" variant="outlined" color="#E5B338" base-color="grey"></v-text-field>
              </v-col>

              <v-col cols="12">
                <v-text-field v-model="formData.email" label="E-mail (Login)" :rules="[rules.required, rules.email]" variant="outlined" color="#E5B338" base-color="grey"></v-text-field>
              </v-col>

              <v-col cols="12" md="6">
                <v-text-field v-model="formData.phone" label="Telefon" :rules="[rules.required]" variant="outlined" color="#E5B338" base-color="grey"></v-text-field>
              </v-col>
              <v-col cols="12" md="6">
                <v-text-field v-model="formData.password" label="Hasło Startowe" type="password" :rules="[rules.required]" variant="outlined" color="#E5B338" base-color="grey"></v-text-field>
              </v-col>

              <v-col cols="12" md="6">
                <v-select v-model="formData.role_id" :items="availableRoles" item-title="name" item-value="id" label="Stanowisko" variant="outlined" color="#E5B338" base-color="grey"></v-select>
              </v-col>
              <v-col cols="12" md="6">
                <!-- TODO: W przyszłości pobierzemy to z backendu, na razie hardkodujemy 2 huby tak jak w Dispatcherze -->
                <v-select v-model="formData.warehouse_id" :items="availableHubs" item-title="name" item-value="id" label="Przypisz do HUBu" variant="outlined" color="#E5B338" base-color="grey"></v-select>
              </v-col>
            </v-row>
            
            <v-alert v-if="serverError" type="error" variant="tonal" class="mt-2 text-caption">
              {{ serverError }}
            </v-alert>
          </v-form>
        </v-card-text>

        <v-card-actions class="pa-6 pt-0">
          <v-spacer></v-spacer>
          <v-btn color="grey-lighten-1" variant="text" @click="closeDialog" class="font-weight-bold">
            Anuluj
          </v-btn>
          <v-btn color="#E5B338" variant="flat" class="text-black font-weight-bold px-6" :disabled="!isFormValid" :loading="isSubmitting" @click="submitEmployee">
            Zatrudnij i Zapisz
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="4000">
      {{ snackbar.text }}
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import api from '../api/axios';

const tab = ref('staff');
const snackbar = ref({ show: false, text: '', color: 'success' });

// --- STAN DLA TABELI PRACOWNIKÓW ---
const employees = ref([]);
const loading = ref(false);

const headers = [
  { title: 'ID', key: 'user_id', align: 'start' },
  { title: 'Imię', key: 'first_name' },
  { title: 'Nazwisko', key: 'last_name' },
  { title: 'E-mail', key: 'email' },
  { title: 'Stanowisko', key: 'role_id' },
  { title: 'Przypisany Magazyn / HUB', key: 'warehouse_name' },
];

// --- STAN DLA MODALA ZATRUDNIANIA ---
const dialog = ref(false);
const isFormValid = ref(false);
const isSubmitting = ref(false);
const serverError = ref('');

const formData = ref({
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  password: '',
  role_id: 2, // Domyślnie Kurier
  warehouse_id: 1 // Domyślnie Warszawa
});

const rules = {
  required: (v: any) => !!v || 'To pole jest wymagane',
  email: (v: string) => /.+@.+\..+/.test(v) || 'Niepoprawny e-mail'
};

const availableRoles = [
  { id: 2, name: 'Kurier Lokalny / Kierowca TIR' },
  { id: 5, name: 'Kierowca TIR (Line-Haul)' },
  { id: 3, name: 'Dyspozytor HUBu' }
];

const availableHubs = [
  { id: 1, name: 'HUB Warszawa (Mazowieckie)' },
  { id: 2, name: 'HUB Kraków (Małopolskie)' }
];

// --- FUNKCJE POBIERAJĄCE I WYSYŁAJĄCE ---
const fetchEmployees = async () => {
  loading.value = true;
  try {
    const response = await api.get('/admin/users');
    employees.value = response.data;
  } catch (error) {
    showSnackbar("Błąd pobierania pracowników", "error");
  } finally {
    loading.value = false;
  }
};

const submitEmployee = async () => {
  if (!isFormValid.value) return;
  isSubmitting.value = true;
  serverError.value = '';

  try {
    // Zgodnie z naszym backendem, user_data idzie w body, a warehouse_id w query params
    await api.post(`/admin/users?warehouse_id=${formData.value.warehouse_id}`, {
      email: formData.value.email,
      password: formData.value.password,
      first_name: formData.value.first_name,
      last_name: formData.value.last_name,
      phone: formData.value.phone,
      role_id: formData.value.role_id
    });
    
    showSnackbar('Sukces! Nowy pracownik został dodany do systemu.', 'success');
    closeDialog();
    fetchEmployees(); // Odświeżamy tabelę, żeby od razu zobaczyć nowego pracownika!
  } catch (error: any) {
    serverError.value = error.response?.data?.detail || "Wystąpił błąd po stronie serwera.";
  } finally {
    isSubmitting.value = false;
  }
};

const closeDialog = () => {
  dialog.value = false;
  serverError.value = '';
  // Reset formularza
  formData.value = {
    first_name: '', last_name: '', email: '', phone: '', password: '', role_id: 2, warehouse_id: 1
  };
};

const showSnackbar = (text: string, color: string) => {
  snackbar.value = { show: true, text, color };
};

// --- FUNKCJE POMOCNICZE WIZUALNE (CHIPY) ---
const getRoleName = (roleId: number) => {
  if (roleId === 2) return 'Kurier';
  if (roleId === 3) return 'Dyspozytor';
  if (roleId === 4) return 'Administrator';
  if (roleId === 5) return 'Kierowca TIR'; 
  return 'Klient';
};

const getRoleColor = (roleId: number) => {
  if (roleId === 2) return 'grey-lighten-1'; 
  if (roleId === 3) return 'blue-lighten-2'; 
  if (roleId === 4) return '#E5B338'; 
  if (roleId === 5) return 'deep-purple-lighten-2'; 
  return 'white';
};

onMounted(() => {
  fetchEmployees();
});
</script>

<style scoped>
.admin-panel {
  background-color: transparent;
}
:deep(.v-data-table) { 
  background-color: transparent !important; 
}
:deep(.v-data-table-header th) {
  color: #94A3B8 !important; 
  font-weight: bold !important;
  text-transform: uppercase;
  border-bottom: 1px solid rgba(255,255,255,0.1) !important;
}
</style>