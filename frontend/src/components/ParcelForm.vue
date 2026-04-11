<template>
  <v-card class="custom-card pa-6 pa-md-8" elevation="10">
    <v-card-title class="text-h4 font-weight-bold text-white mb-6 d-flex align-center">
      <v-icon color="#E5B338" size="40" class="mr-3">mdi-package-variant-closed</v-icon>
      Nadaj Przesyłkę
    </v-card-title>
    
    <v-form v-model="isFormValid" @submit.prevent="submitParcel">
      
      <h3 class="text-gold mb-4 text-subtitle-1 font-weight-bold text-uppercase letter-spacing-1">Dane Nadawcy</h3>
      <v-row dense>
        <v-col cols="12" md="6">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Imię i Nazwisko</p>
          <v-text-field v-model="formData.sender_name" :rules="[rules.required, rules.max200]" placeholder="Jan Kowalski" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="custom-input mb-2"></v-text-field>
        </v-col>
        <v-col cols="12" md="6">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Telefon</p>
          <v-text-field v-model="formData.sender_phone" :rules="[rules.required, rules.phone]" placeholder="np. 123456789" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="custom-input mb-2"></v-text-field>
        </v-col>
        
        <v-col cols="8" md="6">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Ulica</p>
          <v-text-field v-model="formData.sender_address.street" :rules="[rules.required, rules.max255]" placeholder="ul. Sezamkowa" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="custom-input mb-2"></v-text-field>
        </v-col>
        <v-col cols="4" md="2">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Nr lokalu</p>
          <v-text-field v-model="formData.sender_address.building_number" :rules="[rules.required, rules.max20]" placeholder="12/3" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="custom-input mb-2"></v-text-field>
        </v-col>
        <v-col cols="6" md="4">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Kod Pocztowy</p>
          <v-text-field v-model="formData.sender_address.postal_code" :rules="[rules.required, rules.max20]" placeholder="00-000" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="custom-input mb-2"></v-text-field>
        </v-col>
        <v-col cols="6" md="12">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Miasto</p>
          <v-text-field v-model="formData.sender_address.city" :rules="[rules.required, rules.max100]" placeholder="Warszawa" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="custom-input mb-2"></v-text-field>
        </v-col>
      </v-row>

      <v-divider class="my-6 border-opacity-25" color="#E5B338"></v-divider>

      <h3 class="text-gold mb-4 text-subtitle-1 font-weight-bold text-uppercase letter-spacing-1">Dane Odbiorcy</h3>
      <v-row dense>
        <v-col cols="12" md="6">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Imię i Nazwisko</p>
          <v-text-field v-model="formData.recipient_name" :rules="[rules.required, rules.max200]" placeholder="Anna Nowak" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="custom-input mb-2"></v-text-field>
        </v-col>
        <v-col cols="12" md="6">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Telefon</p>
          <v-text-field v-model="formData.recipient_phone" :rules="[rules.required, rules.phone]" placeholder="np. 987654321" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="custom-input mb-2"></v-text-field>
        </v-col>
        
        <v-col cols="8" md="6">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Ulica</p>
          <v-text-field v-model="formData.recipient_address.street" :rules="[rules.required, rules.max255]" placeholder="ul. Klonowa" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="custom-input mb-2"></v-text-field>
        </v-col>
        <v-col cols="4" md="2">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Nr lokalu</p>
          <v-text-field v-model="formData.recipient_address.building_number" :rules="[rules.required, rules.max20]" placeholder="5" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="custom-input mb-2"></v-text-field>
        </v-col>
        <v-col cols="6" md="4">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Kod Pocztowy</p>
          <v-text-field v-model="formData.recipient_address.postal_code" :rules="[rules.required, rules.max20]" placeholder="31-000" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="custom-input mb-2"></v-text-field>
        </v-col>
        <v-col cols="6" md="12">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Miasto</p>
          <v-text-field v-model="formData.recipient_address.city" :rules="[rules.required, rules.max100]" placeholder="Kraków" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="custom-input mb-2"></v-text-field>
        </v-col>
      </v-row>

      <v-divider class="my-6 border-opacity-25" color="#E5B338"></v-divider>

      <v-row dense class="align-center mb-6">
        <v-col cols="12" md="6">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Kategoria Gabarytowa</p>
          <v-select 
            v-model="formData.tariff_id" 
            :items="[{title: 'Kategoria A (do 2 kg) - 15.99 zł', value: 1}, {title: 'Kategoria B (do 10 kg) - 20.99 zł', value: 2}, {title: 'Kategoria C (do 30 kg) - 29.99 zł', value: 3}]"
            variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="custom-input"
          ></v-select>
        </v-col>
        <v-col cols="12" md="6" class="d-flex align-center justify-center pt-md-6">
          <v-checkbox v-model="formData.simulate_payment" label="Potwierdzam opłatę z góry (Symulacja)" color="#E5B338" class="text-white font-weight-bold" hide-details></v-checkbox>
        </v-col>
      </v-row>

      <v-card variant="outlined" color="#E5B338" class="mb-8 rounded-lg pa-4 bg-transparent border-opacity-25">
        <h4 class="text-white text-uppercase font-weight-bold mb-4 text-subtitle-2">Podsumowanie Kosztów</h4>
        
        <div class="d-flex justify-space-between mb-2">
          <span class="text-grey-lighten-1">Cena bazowa (Kategoria {{ formData.tariff_id === 1 ? 'A' : formData.tariff_id === 2 ? 'B' : 'C' }}):</span>
          <span class="text-white font-weight-bold">{{ basePrice.toFixed(2) }} zł</span>
        </div>
        
        <div class="d-flex justify-space-between mb-2" v-if="!formData.simulate_payment">
          <span class="text-grey-lighten-1">Opłata dodatkowa (Za pobraniem):</span>
          <span class="text-white font-weight-bold">+ {{ codFee.toFixed(2) }} zł</span>
        </div>

        <v-divider class="my-3 border-opacity-25" color="#E5B338"></v-divider>
        
        <div class="d-flex justify-space-between align-center mt-2">
          <span class="text-gold font-weight-bold text-h6">Do zapłaty:</span>
          <span class="text-gold font-weight-black text-h5">{{ totalPrice.toFixed(2) }} zł</span>
        </div>
      </v-card>

      <v-btn 
        type="submit" 
        :color="isFormValid ? '#E5B338' : 'grey-darken-3'" 
        height="64"
        :class="isFormValid ? 'text-black font-weight-black text-h6' : 'text-grey-lighten-1 text-h6'"
        block 
        rounded="lg"
        :loading="isLoading" 
        :disabled="!isFormValid">
        ZATWIERDŹ I NADAJ
      </v-btn>

      <v-alert v-if="serverMessage" class="mt-4 rounded-lg text-body-2 font-weight-bold text-center" :type="serverMessage.includes('Błąd') ? 'error' : 'success'">
        {{ serverMessage }}
      </v-alert>

    </v-form>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'; // Dodany import 'computed'
import api from '../api/axios';

const isFormValid = ref(false);
const isLoading = ref(false);
const serverMessage = ref('');

const formData = ref({
  sender_name: '',
  sender_phone: '',
  sender_address: { street: '', building_number: '', city: '', postal_code: '' },
  recipient_name: '',
  recipient_phone: '',
  recipient_address: { street: '', building_number: '', city: '', postal_code: '' },
  tariff_id: 1, 
  simulate_payment: false
});

// --- LOGIKA OBLICZANIA KOSZTÓW (REAKTYWNA) ---
const basePrice = computed(() => {
  if (formData.value.tariff_id === 1) return 15.99;
  if (formData.value.tariff_id === 2) return 20.99;
  if (formData.value.tariff_id === 3) return 29.99;
  return 15.99;
});

const codFee = computed(() => {
  // Jeśli klient opłaci z góry (checkbox true), dopłata wynosi 0 zł. W przeciwnym razie 5 zł.
  return formData.value.simulate_payment ? 0 : 5.00;
});

const totalPrice = computed(() => {
  return basePrice.value + codFee.value;
});
// ----------------------------------------------

const rules = {
  required: (v: string) => !!v || 'To pole jest wymagane, nie możesz go pominąć',
  phone: (v: string) => {
    if (!v) return true;
    const digitsOnly = v.replace(/\D/g, '');
    return (digitsOnly.length >= 9 && digitsOnly.length <= 15) || 'Wpisz poprawny numer telefonu (od 9 do 15 cyfr)';
  },
  max200: (v: string) => (v && v.length <= 200) || 'Przekroczono limit znaków (max 200)',
  max255: (v: string) => (v && v.length <= 255) || 'Przekroczono limit znaków (max 255)',
  max100: (v: string) => (v && v.length <= 100) || 'Przekroczono limit znaków (max 100)',
  max20: (v: string) => (v && v.length <= 20) || 'Przekroczono limit znaków (max 20)'
};

const submitParcel = async () => {
  if (!isFormValid.value) return;
  
  isLoading.value = true;
  serverMessage.value = '';

  try {
    const response = await api.post('/parcels', formData.value);
    
    serverMessage.value = `Sukces! Nadano paczkę. Twój numer śledzenia: ${response.data.tracking_number}`;
  } catch (error: any) {
    if (error.response && error.response.status === 422) {
      serverMessage.value = 'Błąd Walidacji Serwera: Upewnij się, że wszystkie pola są poprawne.';
    } else {
      serverMessage.value = 'Wystąpił problem z połączeniem lub sesja wygasła. Spróbuj ponownie.';
    }
  } finally {
    isLoading.value = false;
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
.letter-spacing-1 { letter-spacing: 1px; }

.custom-input :deep(.v-field) {
  border-radius: 12px;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.3) !important;
}

.custom-input :deep(.v-field__input) {
  color: white !important;
}

.custom-input :deep(.v-label) {
  color: #94A3B8 !important;
}
</style>