<template>
  <v-container fluid class="admin-panel pa-6">
    <v-row>
      <v-col cols="12" class="text-center mb-4">
        <h1 class="text-h4 font-weight-bold text-white">Centrala: Panel Administratora</h1>
        <p class="text-subtitle-1 text-grey-lighten-1">Zarządzanie strukturą i pracownikami firmy Royale Package</p>
      </v-col>
    </v-row>

    <v-tabs v-model="tab" color="#E5B338" align-tabs="center" class="mb-6">
      <v-tab value="staff" class="font-weight-bold"><v-icon start>mdi-account-tie</v-icon> Zarządzanie Personelem</v-tab>
      <v-tab value="fleet" class="font-weight-bold"><v-icon start>mdi-truck</v-icon> Zarządzanie Flotą</v-tab>
      <v-tab value="tariffs" class="font-weight-bold"><v-icon start>mdi-cash-multiple</v-icon> Cenniki i Taryfy</v-tab>
    </v-tabs>

    <v-window v-model="tab" class="mt-4">
      
      <!-- ========================================== -->
      <!-- PERSONEL -->
      <!-- ========================================== -->
      <v-window-item value="staff">
        <v-card color="#0F172A" elevation="6" border style="border-color: rgba(255,255,255,0.1) !important;" class="rounded-xl pa-4">
          <v-card-title class="d-flex align-center text-white font-weight-bold mb-4">
            <v-icon :color="showArchivedStaff ? 'error' : '#E5B338'" class="mr-2">mdi-account-group</v-icon> 
            {{ showArchivedStaff ? 'Archiwum: Zwolnieni Pracownicy' : 'Aktywni Pracownicy' }}
            <v-spacer></v-spacer>
            <v-switch v-model="showArchivedStaff" label="Pokaż Archiwum" color="error" hide-details class="mr-6 font-weight-bold"></v-switch>
            <v-btn color="#E5B338" class="text-black font-weight-bold" prepend-icon="mdi-plus" @click="openCreateStaff" v-if="!showArchivedStaff">Zatrudnij</v-btn>
          </v-card-title>
          
          <v-data-table :headers="headersStaff" :items="filteredEmployees" :loading="loadingStaff" class="bg-transparent text-white" no-data-text="Brak pracowników w tej sekcji">
            <template v-slot:item.role_id="{ item }">
              <v-chip :color="getRoleColor(item.role_id)" variant="tonal" size="small" class="font-weight-bold text-uppercase">{{ getRoleName(item.role_id) }}</v-chip>
            </template>
            <template v-slot:item.is_active="{ item }">
              <v-chip :color="item.is_active ? 'success' : 'error'" variant="outlined" size="small" class="font-weight-bold">
                {{ item.is_active ? 'Aktywny' : 'Zwolniony' }}
              </v-chip>
            </template>
            <template v-slot:item.actions="{ item }">
              <v-btn v-if="item.is_active" icon="mdi-pencil" variant="tonal" color="info" size="small" class="mr-2" @click="openEditStaff(item)" title="Edytuj"></v-btn>
              <v-btn v-if="item.is_active" icon="mdi-cancel" variant="tonal" color="error" size="small" @click="openDeleteStaff(item)" title="Zwolnij"></v-btn>
              <v-btn v-if="!item.is_active" icon="mdi-restore" variant="tonal" color="success" size="small" @click="openRestoreStaff(item)" title="Przywróć"></v-btn>
            </template>
          </v-data-table>
        </v-card>
      </v-window-item>

      <!-- ========================================== -->
      <!-- FLOTA -->
      <!-- ========================================== -->
      <v-window-item value="fleet">
        <v-card color="#0F172A" elevation="6" border style="border-color: rgba(255,255,255,0.1) !important;" class="rounded-xl pa-4">
          <v-card-title class="d-flex align-center text-white font-weight-bold mb-4">
            <v-icon :color="showArchivedFleet ? 'error' : '#E5B338'" class="mr-2">mdi-car-multiple</v-icon> 
            {{ showArchivedFleet ? 'Archiwum: Wycofane Pojazdy' : 'Aktywne Pojazdy' }}
            <v-spacer></v-spacer>
            <v-switch v-model="showArchivedFleet" label="Pokaż Archiwum" color="error" hide-details class="mr-6 font-weight-bold"></v-switch>
            <v-btn color="#E5B338" class="text-black font-weight-bold" prepend-icon="mdi-plus" @click="openCreateFleet" v-if="!showArchivedFleet">Dodaj Pojazd</v-btn>
          </v-card-title>
          
          <v-data-table :headers="headersFleet" :items="filteredVehicles" :loading="loadingFleet" class="bg-transparent text-white" no-data-text="Brak pojazdów w tej sekcji">
            <template v-slot:item.vehicle_type="{ item }">
              <v-chip :color="item.vehicle_type === 'TRUCK' ? 'deep-purple-lighten-2' : 'grey-lighten-1'" variant="tonal" size="small" class="font-weight-bold">
                <v-icon start size="small">{{ item.vehicle_type === 'TRUCK' ? 'mdi-truck-cargo-container' : 'mdi-van-utility' }}</v-icon>{{ item.vehicle_type }}
              </v-chip>
            </template>
            <template v-slot:item.capacity_kg="{ item }">{{ item.capacity_kg }} kg</template>
            <template v-slot:item.capacity_m3="{ item }">{{ item.capacity_m3 }} m³</template>
            <template v-slot:item.status="{ item }">
               <v-chip :color="item.status === 'ACTIVE' ? 'success' : 'error'" variant="outlined" size="small" class="font-weight-bold">
                 {{ item.status === 'ACTIVE' ? 'Aktywny' : 'Wycofany' }}
               </v-chip>
            </template>
            <template v-slot:item.actions="{ item }">
              <v-btn v-if="item.status === 'ACTIVE'" icon="mdi-pencil" variant="tonal" color="info" size="small" class="mr-2" @click="openEditFleet(item)" title="Edytuj"></v-btn>
              <v-btn v-if="item.status === 'ACTIVE'" icon="mdi-cancel" variant="tonal" color="error" size="small" @click="openDeleteFleet(item)" title="Wycofaj"></v-btn>
              <v-btn v-if="item.status !== 'ACTIVE'" icon="mdi-restore" variant="tonal" color="success" size="small" @click="openRestoreFleet(item)" title="Przywróć"></v-btn>
            </template>
          </v-data-table>
        </v-card>
      </v-window-item>

      <!-- ========================================== -->
      <!-- TARYFY -->
      <!-- ========================================== -->
      <v-window-item value="tariffs">
         <v-card color="#0F172A" elevation="6" border style="border-color: rgba(255,255,255,0.1) !important;" class="rounded-xl pa-4">
          <v-card-title class="d-flex align-center text-white font-weight-bold mb-4">
            <v-icon color="#E5B338" class="mr-2">mdi-currency-usd</v-icon> Cennik Detaliczny
          </v-card-title>
          <v-data-table :headers="headersTariffs" :items="tariffs" :loading="loadingTariffs" class="bg-transparent text-white" hide-default-footer>
            <template v-slot:item.size_category="{ item }">
              <v-avatar color="#E5B338" size="30" class="text-black font-weight-black mr-2">{{ item.size_category }}</v-avatar> Gabaryt {{ item.size_category }}
            </template>
            <template v-slot:item.max_weight_kg="{ item }">{{ item.max_weight_kg }} kg</template>
            <template v-slot:item.max_volume_m3="{ item }">{{ item.max_volume_m3 }} m³</template>
            <template v-slot:item.base_price="{ item }"><span class="text-gold font-weight-bold text-subtitle-1">{{ item.base_price.toFixed(2) }} zł</span></template>
            <template v-slot:item.actions="{ item }"><v-btn icon="mdi-pencil" variant="tonal" color="info" size="small" @click="openTariffDialog(item)"></v-btn></template>
          </v-data-table>
        </v-card>
      </v-window-item>
    </v-window>

    <!-- ========================================== -->
    <!-- OKIENKA MODALNE -->
    <!-- ========================================== -->

    <!-- Modal: ZATRUDNIANIE PRACOWNIKA -->
    <v-dialog v-model="dialogStaff" max-width="600px" persistent>
      <v-card color="#1E293B" class="rounded-xl border border-opacity-25" style="border-color: #E5B338 !important;">
        <v-card-title class="text-h5 font-weight-bold text-white pa-6 border-b border-opacity-25">
          {{ isEditingStaff ? 'Edytuj Pracownika' : 'Zatrudnij Nowego Pracownika' }}
        </v-card-title>
        <v-card-text class="pa-6">
          <v-form v-model="isFormValidStaff">
            <v-row dense>
              <v-col cols="12" md="6"><v-text-field v-model="formStaff.first_name" label="Imię" :rules="[rules.required]" variant="outlined" color="#E5B338" base-color="grey"></v-text-field></v-col>
              <v-col cols="12" md="6"><v-text-field v-model="formStaff.last_name" label="Nazwisko" :rules="[rules.required]" variant="outlined" color="#E5B338" base-color="grey"></v-text-field></v-col>
              <v-col cols="12"><v-text-field v-model="formStaff.email" label="E-mail (Login)" :rules="[rules.required, rules.email]" variant="outlined" color="#E5B338" base-color="grey"></v-text-field></v-col>
              <v-col cols="12" md="6"><v-text-field v-model="formStaff.phone" label="Telefon" :rules="[rules.required]" variant="outlined" color="#E5B338" base-color="grey"></v-text-field></v-col>
              <v-col cols="12" md="6">
                <v-text-field v-model="formStaff.password" :label="isEditingStaff ? 'Nowe Hasło (opcjonalne)' : 'Hasło Startowe'" type="password" :rules="isEditingStaff ? [] : [rules.required]" variant="outlined" color="#E5B338" base-color="grey"></v-text-field>
              </v-col>
              <v-col cols="12" md="6"><v-select v-model="formStaff.role_id" :items="availableRoles" item-title="name" item-value="id" label="Stanowisko" variant="outlined" color="#E5B338" base-color="grey"></v-select></v-col>
              <v-col cols="12" md="6"><v-select v-model="formStaff.warehouse_id" :items="availableHubs" item-title="name" item-value="id" label="Przypisz do HUBu" variant="outlined" color="#E5B338" base-color="grey"></v-select></v-col>
            </v-row>
            <v-alert v-if="serverError" type="error" variant="tonal" class="mt-2 text-caption">{{ serverError }}</v-alert>
          </v-form>
        </v-card-text>
        <v-card-actions class="pa-6 pt-0">
          <v-spacer></v-spacer>
          <v-btn color="grey-lighten-1" variant="text" @click="closeDialogStaff" class="font-weight-bold">Anuluj</v-btn>
          <v-btn color="#E5B338" variant="flat" class="text-black font-weight-bold px-6" :disabled="!isFormValidStaff" :loading="isSubmitting" @click="submitEmployee">Zapisz</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Modal: DODAWANIE POJAZDU -->
    <v-dialog v-model="dialogFleet" max-width="500px" persistent>
      <v-card color="#1E293B" class="rounded-xl border border-opacity-25" style="border-color: #E5B338 !important;">
        <v-card-title class="text-h5 font-weight-bold text-white pa-6 border-b border-opacity-25">
          {{ isEditingFleet ? 'Edytuj Pojazd' : 'Dodaj Pojazd do Floty' }}
        </v-card-title>
        <v-card-text class="pa-6">
          <v-form v-model="isFormValidFleet">
            <v-row dense>
              <v-col cols="12"><v-text-field v-model="formFleet.registration_number" label="Numer Rejestracyjny" :rules="[rules.required]" placeholder="np. WA 12345" variant="outlined" color="#E5B338" base-color="grey"></v-text-field></v-col>
              <v-col cols="12" md="6"><v-select v-model="formFleet.vehicle_type" :items="['VAN', 'TRUCK']" label="Typ Pojazdu" variant="outlined" color="#E5B338" base-color="grey"></v-select></v-col>
              <v-col cols="12" md="6"><v-select v-model="formFleet.warehouse_id" :items="availableHubs" item-title="name" item-value="id" label="Przypisz do HUBu" variant="outlined" color="#E5B338" base-color="grey"></v-select></v-col>
              <v-col cols="12" md="6"><v-text-field v-model.number="formFleet.capacity_kg" label="Ładowność (kg)" type="number" :rules="[rules.required]" variant="outlined" color="#E5B338" base-color="grey"></v-text-field></v-col>
              <v-col cols="12" md="6"><v-text-field v-model.number="formFleet.capacity_m3" label="Objętość (m³)" type="number" :rules="[rules.required]" variant="outlined" color="#E5B338" base-color="grey"></v-text-field></v-col>
              <v-col cols="12" v-if="isEditingFleet"><v-select v-model="formFleet.status" :items="['ACTIVE', 'INACTIVE']" label="Status Pojazdu" variant="outlined" color="#E5B338" base-color="grey"></v-select></v-col>
            </v-row>
            <v-alert v-if="serverErrorFleet" type="error" variant="tonal" class="mt-4 text-caption">{{ serverErrorFleet }}</v-alert>
          </v-form>
        </v-card-text>
        <v-card-actions class="pa-6 pt-0">
          <v-spacer></v-spacer>
          <v-btn color="grey-lighten-1" variant="text" @click="closeDialogFleet" class="font-weight-bold">Anuluj</v-btn>
          <v-btn color="#E5B338" variant="flat" class="text-black font-weight-bold px-6" :disabled="!isFormValidFleet" :loading="isSubmittingFleet" @click="submitVehicle">Zapisz</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- MODAL: ZWALNIANIE/WYCOFYWANIE -->
    <v-dialog v-model="dialogDelete" max-width="400px">
      <v-card color="#1E293B" class="rounded-xl border border-opacity-25" style="border-color: #EF4444 !important;">
        <v-card-title class="text-h6 font-weight-bold text-error pa-6 pb-2">Potwierdź Akcję</v-card-title>
        <v-card-text class="pa-6 pt-0 text-grey-lighten-1">Czy na pewno chcesz przenieść ten zasób do Archiwum?</v-card-text>
        <v-card-actions class="pa-6 pt-0">
          <v-spacer></v-spacer>
          <v-btn color="grey-lighten-1" variant="text" @click="dialogDelete = false" class="font-weight-bold">Anuluj</v-btn>
          <v-btn color="error" variant="flat" class="font-weight-bold px-6" :loading="isDeleting" @click="confirmDelete">Potwierdź</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- MODAL: PRZYWRACANIE Z ARCHIWUM -->
    <v-dialog v-model="dialogRestore" max-width="400px">
      <v-card color="#1E293B" class="rounded-xl border border-opacity-25" style="border-color: #4CAF50 !important;">
        <v-card-title class="text-h6 font-weight-bold text-success pa-6 pb-2">Przywracanie</v-card-title>
        <v-card-text class="pa-6 pt-0 text-grey-lighten-1">Czy przywrócić ten zasób z powrotem do aktywnego użytku?</v-card-text>
        <v-card-actions class="pa-6 pt-0">
          <v-spacer></v-spacer>
          <v-btn color="grey-lighten-1" variant="text" @click="dialogRestore = false" class="font-weight-bold">Anuluj</v-btn>
          <v-btn color="success" variant="flat" class="font-weight-bold px-6 text-white" :loading="isRestoring" @click="confirmRestore">Przywróć</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- MODAL: EDYCJA TARYFY -->
    <v-dialog v-model="dialogTariff" max-width="400px" persistent>
      <v-card color="#1E293B" class="rounded-xl border border-opacity-25" style="border-color: #E5B338 !important;">
        <v-card-title class="text-h5 font-weight-bold text-white pa-6 border-b border-opacity-25">Edytuj Gabaryt {{ formTariff.size_category }}</v-card-title>
        <v-card-text class="pa-6">
          <v-form v-model="isFormValidTariff">
            <v-text-field v-model.number="formTariff.base_price" label="Cena Bazowa (PLN)" type="number" step="0.01" :rules="[rules.required, rules.positiveNumber]" variant="outlined" color="#E5B338" base-color="grey" prepend-inner-icon="mdi-cash"></v-text-field>
            <v-alert v-if="serverErrorTariff" type="error" variant="tonal" class="mt-4 text-caption">{{ serverErrorTariff }}</v-alert>
          </v-form>
        </v-card-text>
        <v-card-actions class="pa-6 pt-0">
          <v-spacer></v-spacer>
          <v-btn color="grey-lighten-1" variant="text" @click="closeDialogTariff" class="font-weight-bold">Anuluj</v-btn>
          <v-btn color="#E5B338" variant="flat" class="text-black font-weight-bold px-6" :disabled="!isFormValidTariff" :loading="isSubmittingTariff" @click="submitTariff">Zapisz Cenę</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="4000">{{ snackbar.text }}</v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import api from '../api/axios';

const tab = ref('staff');
const snackbar = ref({ show: false, text: '', color: 'success' });
const serverError = ref('');
const serverErrorFleet = ref('');
const serverErrorTariff = ref('');

// --- TABELE I ŁADOWANIE ---
const employees = ref<any[]>([]);
const vehicles = ref<any[]>([]);
const tariffs = ref([]);
const loadingStaff = ref(false);
const loadingFleet = ref(false);
const loadingTariffs = ref(false);

const showArchivedStaff = ref(false);
const showArchivedFleet = ref(false);

const filteredEmployees = computed(() => {
  return employees.value.filter(e => e.is_active === !showArchivedStaff.value);
});

const filteredVehicles = computed(() => {
  return vehicles.value.filter(v => v.status === (showArchivedFleet.value ? 'INACTIVE' : 'ACTIVE'));
});

const headersStaff = [
  { title: 'Status', key: 'is_active', align: 'start' },
  { title: 'Imię', key: 'first_name' },
  { title: 'Nazwisko', key: 'last_name' },
  { title: 'E-mail', key: 'email' },
  { title: 'Stanowisko', key: 'role_id' },
  { title: 'Przypisany HUB', key: 'warehouse_name' },
  { title: 'Akcje', key: 'actions', align: 'end', sortable: false },
];

const headersFleet = [
  { title: 'Status', key: 'status', align: 'start' },
  { title: 'Typ', key: 'vehicle_type' },
  { title: 'Rejestracja', key: 'registration_number' },
  { title: 'Masa Max', key: 'capacity_kg' },
  { title: 'Objętość Max', key: 'capacity_m3' },
  { title: 'Stacjonuje w', key: 'warehouse_name' },
  { title: 'Akcje', key: 'actions', align: 'end', sortable: false },
];

const headersTariffs = [
  { title: 'Gabaryt', key: 'size_category', align: 'start' },
  { title: 'Maks. Waga', key: 'max_weight_kg' },
  { title: 'Maks. Objętość', key: 'max_volume_m3' },
  { title: 'Cena Bazowa', key: 'base_price' },
  { title: 'Akcje', key: 'actions', align: 'end', sortable: false },
];

// --- MODALE I STAN FORMULARZY ---
const dialogStaff = ref(false);
const dialogFleet = ref(false);
const dialogTariff = ref(false);
const dialogDelete = ref(false);
const dialogRestore = ref(false);

const isEditingStaff = ref(false);
const isEditingFleet = ref(false);
const deleteTarget = ref<{ type: 'staff' | 'fleet', id: number } | null>(null);
const restoreTarget = ref<{ type: 'staff' | 'fleet', id: number } | null>(null);

const isFormValidStaff = ref(false);
const isSubmitting = ref(false);
const isFormValidFleet = ref(false);
const isSubmittingFleet = ref(false);
const isFormValidTariff = ref(false);
const isSubmittingTariff = ref(false);
const isDeleting = ref(false);
const isRestoring = ref(false);

const formStaff = ref({ user_id: 0, first_name: '', last_name: '', email: '', phone: '', password: '', role_id: 2, warehouse_id: 1 });
const formFleet = ref({ vehicle_id: 0, registration_number: '', capacity_kg: 1000, capacity_m3: 10, vehicle_type: 'VAN', warehouse_id: 1, status: 'ACTIVE' });
const formTariff = ref({ tariff_id: 0, size_category: '', base_price: 0 });

const rules = {
  required: (v: any) => !!v || 'Wymagane',
  email: (v: string) => /.+@.+\..+/.test(v) || 'Niepoprawny e-mail',
  positiveNumber: (v: number) => v > 0 || 'Musi być > 0'
};

const availableRoles = [
  { id: 2, name: 'Kurier Lokalny (VAN)' },
  { id: 5, name: 'Kierowca TIR (Line-Haul)' },
  { id: 3, name: 'Dyspozytor HUBu' }
];

const availableHubs = [
  { id: 1, name: 'HUB Warszawa (Mazowieckie)' },
  { id: 2, name: 'HUB Kraków (Małopolskie)' }
];

// --- FUNKCJE API: POBIERANIE ---
const fetchEmployees = async () => { loadingStaff.value = true; try { const res = await api.get('/admin/users'); employees.value = res.data; } catch (e) { console.error(e); } finally { loadingStaff.value = false; } };
const fetchVehicles = async () => { loadingFleet.value = true; try { const res = await api.get('/admin/vehicles'); vehicles.value = res.data; } catch (e) { console.error(e); } finally { loadingFleet.value = false; } };
const fetchTariffs = async () => { loadingTariffs.value = true; try { const res = await api.get('/admin/tariffs'); tariffs.value = res.data; } catch (e) { console.error(e); } finally { loadingTariffs.value = false; } };

// --- FUNKCJE API: ZAPIS (DODAJ / EDYTUJ) ---
const submitEmployee = async () => {
  if (!isFormValidStaff.value) return;
  isSubmitting.value = true; serverError.value = '';
  try {
    if (isEditingStaff.value) {
      await api.put(`/admin/users/${formStaff.value.user_id}`, formStaff.value);
    } else {
      await api.post(`/admin/users?warehouse_id=${formStaff.value.warehouse_id}`, formStaff.value);
    }
    showSnackbar(isEditingStaff.value ? 'Zapisano zmiany.' : 'Dodano pracownika.', 'success');
    closeDialogStaff();
    await fetchEmployees().catch(e => e);
  } catch (error: any) {
    if(error.response && error.response.status !== 200) {
      serverError.value = error.response?.data?.detail || "Błąd serwera.";
    } else {
       closeDialogStaff();
       await fetchEmployees();
       showSnackbar('Zapisano z drobnymi ostrzeżeniami.', 'success');
    }
  } finally { isSubmitting.value = false; }
};

const submitVehicle = async () => {
  if (!isFormValidFleet.value) return;
  isSubmittingFleet.value = true; serverErrorFleet.value = '';
  try {
    if (isEditingFleet.value) {
      await api.put(`/admin/vehicles/${formFleet.value.vehicle_id}`, formFleet.value);
    } else {
      await api.post(`/admin/vehicles?registration_number=${formFleet.value.registration_number}&capacity_kg=${formFleet.value.capacity_kg}&capacity_m3=${formFleet.value.capacity_m3}&vehicle_type=${formFleet.value.vehicle_type}&warehouse_id=${formFleet.value.warehouse_id}`);
    }
    showSnackbar(isEditingFleet.value ? 'Zapisano zmiany.' : 'Dodano pojazd.', 'success');
    closeDialogFleet();
    await fetchVehicles().catch(e => e);
  } catch (error: any) {
     if(error.response && error.response.status !== 200) {
        serverErrorFleet.value = error.response?.data?.detail || "Błąd serwera.";
     } else {
        closeDialogFleet();
        await fetchVehicles();
     }
  } finally { isSubmittingFleet.value = false; }
};

const submitTariff = async () => {
  if (!isFormValidTariff.value) return;
  isSubmittingTariff.value = true; serverErrorTariff.value = '';
  try {
    await api.put(`/admin/tariffs/${formTariff.value.tariff_id}?new_price=${formTariff.value.base_price}`);
    showSnackbar(`Zaktualizowano cenę.`, 'success');
    closeDialogTariff();
    await fetchTariffs();
  } catch (error: any) { 
     serverErrorTariff.value = error.response?.data?.detail || "Błąd podczas zmiany ceny."; 
  } finally { isSubmittingTariff.value = false; }
};

// --- FUNKCJE API: USUWANIE (SOFT DELETE) ---
const confirmDelete = async () => {
  if (!deleteTarget.value) return;
  isDeleting.value = true;
  try {
    if (deleteTarget.value.type === 'staff') {
      await api.delete(`/admin/users/${deleteTarget.value.id}`);
      showSnackbar('Pracownik przeniesiony do archiwum', 'success');
      await fetchEmployees().catch(e=>e);
    } else {
      await api.delete(`/admin/vehicles/${deleteTarget.value.id}`);
      showSnackbar('Pojazd przeniesiony do archiwum', 'success');
      await fetchVehicles().catch(e=>e);
    }
    dialogDelete.value = false;
  } catch (error: any) {
    if(error.response && error.response.status !== 200) {
      alert(error.response?.data?.detail || "Wystąpił błąd podczas operacji.");
    } else {
       dialogDelete.value = false;
       if(deleteTarget.value.type === 'staff') fetchEmployees();
       else fetchVehicles();
    }
  } finally {
    isDeleting.value = false;
    deleteTarget.value = null;
  }
};

// --- FUNKCJE API: PRZYWRACANIE Z ARCHIWUM ---
const confirmRestore = async () => {
  if (!restoreTarget.value) return;
  isRestoring.value = true;
  try {
    if (restoreTarget.value.type === 'staff') {
      await api.patch(`/admin/users/${restoreTarget.value.id}/restore`);
      showSnackbar('Pracownik wrócił do gry!', 'success');
      await fetchEmployees().catch(e=>e);
    } else {
      await api.patch(`/admin/vehicles/${restoreTarget.value.id}/restore`);
      showSnackbar('Pojazd wrócił do służby!', 'success');
      await fetchVehicles().catch(e=>e);
    }
    dialogRestore.value = false;
  } catch (error: any) {
    if(error.response && error.response.status !== 200) {
      alert(error.response?.data?.detail || "Wystąpił błąd podczas przywracania.");
    } else {
       dialogRestore.value = false;
       if(restoreTarget.value.type === 'staff') fetchEmployees();
       else fetchVehicles();
    }
  } finally {
    isRestoring.value = false;
    restoreTarget.value = null;
  }
};

// --- OTWIERANIE MODALI ---
const openCreateStaff = () => { isEditingStaff.value = false; formStaff.value = { user_id: 0, first_name: '', last_name: '', email: '', phone: '', password: '', role_id: 2, warehouse_id: 1 }; dialogStaff.value = true; };
const openEditStaff = (item: any) => { 
  isEditingStaff.value = true; 
  const warehouseId = item.warehouse_name.includes('Warszawa') ? 1 : (item.warehouse_name.includes('Kraków') ? 2 : 1);
  formStaff.value = { ...item, password: '', warehouse_id: warehouseId }; 
  dialogStaff.value = true; 
};
const openDeleteStaff = (item: any) => { deleteTarget.value = { type: 'staff', id: item.user_id }; dialogDelete.value = true; };
const openRestoreStaff = (item: any) => { restoreTarget.value = { type: 'staff', id: item.user_id }; dialogRestore.value = true; };

const openCreateFleet = () => { isEditingFleet.value = false; formFleet.value = { vehicle_id: 0, registration_number: '', capacity_kg: 1000, capacity_m3: 10, vehicle_type: 'VAN', warehouse_id: 1, status: 'ACTIVE' }; dialogFleet.value = true; };
const openEditFleet = (item: any) => { 
  isEditingFleet.value = true; 
  const warehouseId = item.warehouse_name.includes('Warszawa') ? 1 : (item.warehouse_name.includes('Kraków') ? 2 : 1);
  formFleet.value = { ...item, warehouse_id: warehouseId }; 
  dialogFleet.value = true; 
};
const openDeleteFleet = (item: any) => { deleteTarget.value = { type: 'fleet', id: item.vehicle_id }; dialogDelete.value = true; };
const openRestoreFleet = (item: any) => { restoreTarget.value = { type: 'fleet', id: item.vehicle_id }; dialogRestore.value = true; };

const openTariffDialog = (item: any) => { formTariff.value = { ...item }; dialogTariff.value = true; };

const closeDialogStaff = () => { dialogStaff.value = false; serverError.value = ''; };
const closeDialogFleet = () => { dialogFleet.value = false; serverErrorFleet.value = ''; };
const closeDialogTariff = () => { dialogTariff.value = false; serverErrorTariff.value = ''; };

const getRoleName = (id: number) => availableRoles.find(r => r.id === id)?.name || (id === 4 ? 'Administrator' : 'Inne');
const getRoleColor = (id: number) => id === 2 ? 'grey-lighten-1' : id === 3 ? 'blue-lighten-2' : id === 4 ? '#E5B338' : id === 5 ? 'deep-purple-lighten-2' : 'white';

onMounted(() => { fetchEmployees(); fetchVehicles(); fetchTariffs(); });
</script>

<style scoped>
.admin-panel { background-color: transparent; }
.text-gold { color: #E5B338 !important; }
:deep(.v-data-table) { background-color: transparent !important; }
:deep(.v-data-table-header th) { color: #94A3B8 !important; font-weight: bold !important; text-transform: uppercase; border-bottom: 1px solid rgba(255,255,255,0.1) !important; }
</style>