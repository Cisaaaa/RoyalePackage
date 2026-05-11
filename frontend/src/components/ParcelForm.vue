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
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Imię</p>
          <v-text-field v-model="formData.sender_first_name" :rules="[rules.required]" placeholder="Jan" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="custom-input mb-2"></v-text-field>
        </v-col>
        <v-col cols="12" md="6">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Nazwisko</p>
          <v-text-field v-model="formData.sender_last_name" :rules="[rules.required]" placeholder="Kowalski" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="custom-input mb-2"></v-text-field>
        </v-col>

        <v-col cols="4" md="3">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Kraj</p>
          <v-select v-model="senderPhonePrefix" :items="['+48', '+44', '+49']" variant="solo-filled" bg-color="#1E293B" color="#E5B338" class="custom-input mb-2"></v-select>
        </v-col>
        <v-col cols="8" md="9">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Telefon (9 cyfr)</p>
          <v-text-field v-model="formData.sender_phone" :rules="[rules.required, rules.phoneStrict]" placeholder="123456789" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="custom-input mb-2"></v-text-field>
        </v-col>
        
        <v-col cols="12">
          <p class="text-caption text-gold mb-1 font-weight-bold text-uppercase">Wyszukaj Adres Nadawcy (Google)</p>
          <v-text-field id="sender-autocomplete" placeholder="Zacznij wpisywać adres (np. Fiołkowa 12, Warszawa)..." variant="solo-filled" bg-color="#2D3748" color="#E5B338" prepend-inner-icon="mdi-magnify" class="custom-input mb-2"></v-text-field>
        </v-col>

        <v-col cols="8" md="5">
          <v-text-field v-model="formData.sender_address.street" label="Ulica (Z automatu)" readonly variant="outlined" color="#94A3B8"></v-text-field>
        </v-col>
        <v-col cols="4" md="3">
          <v-text-field v-model="formData.sender_address.building_number" :rules="[rules.required]" label="Nr lokalu / dom" placeholder="np. 12/3" variant="outlined" color="#E5B338" hint="Wpisz ręcznie" persistent-hint></v-text-field>
        </v-col>
        <v-col cols="4" md="4">
          <v-text-field v-model="formData.sender_address.postal_code" label="Kod" readonly variant="outlined" color="#94A3B8"></v-text-field>
        </v-col>
        <v-col cols="8" md="12">
          <v-text-field v-model="formData.sender_address.city" label="Miasto (Z automatu)" readonly variant="outlined" color="#94A3B8"></v-text-field>
        </v-col>
      </v-row>

      <v-divider class="my-6 border-opacity-25" color="#E5B338"></v-divider>

      <h3 class="text-gold mb-4 text-subtitle-1 font-weight-bold text-uppercase letter-spacing-1">Dane Odbiorcy</h3>

      <v-select
        v-if="contacts.length > 0"
        v-model="selectedContact"
        :items="contacts"
        item-title="label"
        item-value="contact_id"
        label="Wybierz zapisanego odbiorcę (Opcjonalnie)"
        variant="outlined"
        color="#E5B338"
        base-color="grey"
        class="mb-4"
        clearable
        @update:modelValue="fillContactData"
      ></v-select>
      <v-row dense>
        <v-col cols="12" md="6">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Imię</p>
          <v-text-field v-model="formData.recipient_first_name" :rules="[rules.required]" placeholder="Anna" variant="solo-filled" bg-color="#1E293B" color="#E5B338" class="custom-input mb-2"></v-text-field>
        </v-col>
        <v-col cols="12" md="6">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Nazwisko</p>
          <v-text-field v-model="formData.recipient_last_name" :rules="[rules.required]" placeholder="Nowak" variant="solo-filled" bg-color="#1E293B" color="#E5B338" class="custom-input mb-2"></v-text-field>
        </v-col>

        <v-col cols="4" md="3">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Kraj</p>
          <v-select v-model="recipientPhonePrefix" :items="['+48', '+44', '+49']" variant="solo-filled" bg-color="#1E293B" color="#E5B338" class="custom-input mb-2"></v-select>
        </v-col>
        <v-col cols="8" md="9">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Telefon (9 cyfr)</p>
          <v-text-field v-model="formData.recipient_phone" :rules="[rules.required, rules.phoneStrict]" placeholder="987654321" variant="solo-filled" bg-color="#1E293B" color="#E5B338" class="custom-input mb-2"></v-text-field>
        </v-col>
        
        <v-col cols="12">
          <p class="text-caption text-gold mb-1 font-weight-bold text-uppercase">Wyszukaj Adres Odbiorcy (Google)</p>
          <v-text-field id="recipient-autocomplete" placeholder="Zacznij wpisywać adres..." variant="solo-filled" bg-color="#2D3748" color="#E5B338" prepend-inner-icon="mdi-magnify" class="custom-input mb-2"></v-text-field>
        </v-col>

        <v-col cols="8" md="5">
          <v-text-field v-model="formData.recipient_address.street" label="Ulica" readonly variant="outlined" color="#94A3B8"></v-text-field>
        </v-col>
        <v-col cols="4" md="3">
          <v-text-field v-model="formData.recipient_address.building_number" :rules="[rules.required]" label="Nr lokalu / dom" variant="outlined" color="#E5B338"></v-text-field>
        </v-col>
        <v-col cols="4" md="4">
          <v-text-field v-model="formData.recipient_address.postal_code" label="Kod" readonly variant="outlined" color="#94A3B8"></v-text-field>
        </v-col>
        <v-col cols="8" md="12">
          <v-text-field v-model="formData.recipient_address.city" label="Miasto" readonly variant="outlined" color="#94A3B8"></v-text-field>
        </v-col>
      </v-row>

      <v-divider class="my-6 border-opacity-25" color="#E5B338"></v-divider>

      <v-row dense class="align-center mb-6">
        <v-col cols="12" md="6" class="d-flex align-center">
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Kategoria Gabarytowa</p>
          <v-select 
            v-model="formData.tariff_id" 
            :items="[{title: 'Kategoria A (do 2 kg) - 15.99 zł', value: 1}, {title: 'Kategoria B (do 10 kg) - 20.99 zł', value: 2}, {title: 'Kategoria C (do 30 kg) - 29.99 zł', value: 3}]"
            variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="custom-input"
          ></v-select>
        </v-col>
        <v-col cols="12" md="6" class="d-flex align-center">
          <v-text-field
            v-model.number="formData.declared_value"
            label="Zadeklarowana wartość przedmiotu (PLN)"
            type="number"
            min="0"
            prepend-inner-icon="mdi-cash"
            hint="Podaj wartość paczki w razie zgłoszenia reklamacji"
            persistent-hint
            variant="solo-filled"
            bg-color="#1E293B"
            color="#E5B338"
            class="custom-input"
          ></v-text-field>
        </v-col>
        <v-col cols="12" md="6" class="d-flex align-center justify-center pt-md-6">
          <v-checkbox v-model="formData.simulate_payment" label="Potwierdzam opłatę z góry (Symulacja)" color="#E5B338" class="text-white font-weight-bold" hide-details></v-checkbox>
          <v-checkbox v-model="formData.save_recipient_to_contacts" label="Zapisz tego odbiorcę w Książce Adresowej" color="#E5B338" class="text-white font-weight-bold w-100" hide-details></v-checkbox>
        </v-col>
      </v-row>

      <v-card variant="outlined" color="#E5B338" class="mb-8 rounded-lg pa-4 bg-transparent border-opacity-25">
        <h4 class="text-white text-uppercase font-weight-bold mb-4 text-subtitle-2">Podsumowanie Kosztów</h4>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-grey-lighten-1">Cena bazowa:</span>
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
import { ref, computed, onMounted } from 'vue';
import api from '../api/axios';

const isFormValid = ref(false);
const isLoading = ref(false);
const serverMessage = ref('');

// Dodatkowe zmienne dla selectów z prefiksami
const senderPhonePrefix = ref('+48');
const recipientPhonePrefix = ref('+48');

// Zaktualizowany formData (osobne imiona, dodane lat/lon)
const formData = ref({
  sender_first_name: '',
  sender_last_name: '',
  sender_phone: '',
  sender_address: { street: '', building_number: '', city: '', postal_code: '', lat: null as number | null, lon: null as number | null },
  
  recipient_first_name: '',
  recipient_last_name: '',
  recipient_phone: '',
  recipient_address: { street: '', building_number: '', city: '', postal_code: '', lat: null as number | null, lon: null as number | null },
  
  tariff_id: 1, 
  simulate_payment: false,
  save_recipient_to_contacts: false
  ,
  declared_value: 0.0
});

// --- STAN KSIĄŻKI ADRESOWEJ ---
const contacts = ref<any[]>([]);
const selectedContact = ref(null);

const fetchContacts = async () => {
  try {
    const response = await api.get('/contacts');
    // Generujemy ładną etykietę dla dropdowna (Imię Nazwisko - Miasto, Ulica)
    contacts.value = response.data.map((c: any) => ({
      ...c,
      label: `${c.first_name} ${c.last_name} - ${c.address.city}, ${c.address.street}`
    }));
  } catch (error) {
    console.error("Błąd pobierania kontaktów", error);
  }
};

const fillContactData = (contactId: any) => {
  if (!contactId) return; // Jeśli użytkownik "wyczyści" pole
  const contact = contacts.value.find(c => c.contact_id === contactId);
  if (contact) {
    formData.value.recipient_first_name = contact.first_name;
    formData.value.recipient_last_name = contact.last_name;
    formData.value.recipient_phone = contact.phone;
    // Kopiujemy wszystkie dane adresowe wraz z GPS (dzięki temu VROOM działa idealnie bez ponownego wpisywania!)
    formData.value.recipient_address = { ...contact.address };
  }
};

const basePrice = computed(() => {
  if (formData.value.tariff_id === 1) return 15.99;
  if (formData.value.tariff_id === 2) return 20.99;
  if (formData.value.tariff_id === 3) return 29.99;
  return 15.99;
});

const codFee = computed(() => { return formData.value.simulate_payment ? 0 : 5.00; });
const totalPrice = computed(() => { return basePrice.value + codFee.value; });

const rules = {
  required: (v: string) => !!v || 'Wymagane',
  // Prostsza walidacja telefonu, bo usunęliśmy prefiks do selecta
  phoneStrict: (v: string) => {
    if (!v) return true;
    const digitsOnly = v.replace(/\D/g, '');
    return digitsOnly.length === 9 || 'Wpisz dokładnie 9 cyfr';
  }
};

// --- MAGIA GOOGLE PLACES API ---
onMounted(() => {
  fetchContacts(); // Pobieramy kontakty przy montowaniu komponentu
  // Funkcja pomocnicza do "rozpakowywania" danych od Google
  const extractAddressData = (place: any, targetObject: any) => {
    targetObject.street = '';
    targetObject.city = '';
    targetObject.postal_code = '';
    targetObject.lat = place.geometry?.location?.lat() || null;
    targetObject.lon = place.geometry?.location?.lng() || null;

    for (const component of place.address_components) {
      const type = component.types[0];
      if (type === 'route') targetObject.street = component.long_name;
      if (type === 'street_number') {
        // Jeśli Google ma numer w bazie, doklejamy do ulicy lub wpisujemy w nr budynku
        targetObject.building_number = component.long_name;
      }
      if (type === 'locality') targetObject.city = component.long_name;
      if (type === 'postal_code') targetObject.postal_code = component.long_name;
    }
  };

  // Uruchomienie Google Autocomplete dla Nadawcy
  const senderInput = document.getElementById('sender-autocomplete') as HTMLInputElement;
  if (senderInput && window.google) {
    const senderAutocomplete = new google.maps.places.Autocomplete(senderInput, {
      types: ['address'], componentRestrictions: { country: 'pl' }
    });
    senderAutocomplete.addListener('place_changed', () => {
      extractAddressData(senderAutocomplete.getPlace(), formData.value.sender_address);
    });
  }

  // Uruchomienie Google Autocomplete dla Odbiorcy
  const recipientInput = document.getElementById('recipient-autocomplete') as HTMLInputElement;
  if (recipientInput && window.google) {
    const recipientAutocomplete = new google.maps.places.Autocomplete(recipientInput, {
      types: ['address'], componentRestrictions: { country: 'pl' }
    });
    recipientAutocomplete.addListener('place_changed', () => {
      extractAddressData(recipientAutocomplete.getPlace(), formData.value.recipient_address);
    });
  }
});

const submitParcel = async () => {
  if (!isFormValid.value) return;
  isLoading.value = true;
  serverMessage.value = '';

  // Przed wysłaniem do backendu, łączymy imiona, żeby backendowy `sender_name` (jeśli w backendzie jeszcze nie zmieniłeś na first i last name) zadziałał
  // UWAGA: Jeśli w schemas.py już rozdzieliłeś to na `sender_first_name` i `sender_last_name`, wyślij obiekt tak jak jest!
  
  try {
    // Wysyłamy dane (bez prefixu, bo zakładamy polskie numery na potrzeby MVP)
    const payload = {
      ...formData.value,
      sender_phone: formData.value.sender_phone, // backend zweryfikuje 9 cyfr
      recipient_phone: formData.value.recipient_phone,
    };

    const response = await api.post('/parcels', payload);
    serverMessage.value = `Sukces! Nadano paczkę. Numer: ${response.data.tracking_number}`;
  } catch (error: any) {
    serverMessage.value = 'Błąd Walidacji Serwera: Upewnij się, że wszystkie pola są poprawne i wpisałeś 9 cyfr telefonu.';
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
.custom-input :deep(.v-field__input) { color: white !important; }
.custom-input :deep(.v-label) { color: #94A3B8 !important; }

/* Opcjonalne: Stylizacja inputa Google Places, żeby pasował do reszty */
.pac-container {
  background-color: #1E293B !important;
  color: white !important;
  border: 1px solid #E5B338 !important;
}
.pac-item { color: #94A3B8 !important; }
.pac-item-query { color: white !important; }
</style>