<template>
  <v-container fluid class="login-background fill-height d-flex align-center justify-center py-10">
    <v-card class="login-card pa-6 pa-md-8" elevation="24">
      
      <div class="text-center mb-8">
        <v-icon icon="mdi-crown" color="#E5B338" size="48" class="mb-2"></v-icon>
        <h2 class="text-white text-h5 font-weight-black letter-spacing-1">ROYALE PACKAGE</h2>
        <span class="text-gold text-caption font-weight-bold letter-spacing-1">PREMIUM COURIER SERVICES</span>
      </div>

      <v-row class="mb-8 mx-0" dense>
        <v-col cols="6" class="pr-1">
          <v-btn block :color="isLoginMode ? '#E5B338' : '#1E293B'" :class="isLoginMode ? 'text-black font-weight-bold' : 'text-grey-lighten-1'" :variant="isLoginMode ? 'elevated' : 'flat'" rounded="lg" height="48" @click="switchMode(true)">
            Zaloguj się
          </v-btn>
        </v-col>
        <v-col cols="6" class="pl-1">
          <v-btn block :color="!isLoginMode ? '#E5B338' : '#1E293B'" :class="!isLoginMode ? 'text-black font-weight-bold' : 'text-grey-lighten-1'" :variant="!isLoginMode ? 'elevated' : 'flat'" rounded="lg" height="48" @click="switchMode(false)">
            Zarejestruj się
          </v-btn>
        </v-col>
      </v-row>

      <v-form v-model="isFormValid" @submit.prevent="handleSubmit">
        
        <template v-if="!isLoginMode">
          <v-row dense>
            <v-col cols="12" sm="6">
              <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Imię i Nazwisko</p>
              <v-text-field v-model="fullName" :rules="[rules.required]" prepend-inner-icon="mdi-account-outline" placeholder="Jan Kowalski" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="mb-2 custom-input"></v-text-field>
            </v-col>
            <v-col cols="12" sm="6">
              <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Telefon</p>
              <v-text-field v-model="phone" :rules="[rules.required, rules.phone]" prepend-inner-icon="mdi-phone-outline" placeholder="600 123 456" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="mb-2 custom-input"></v-text-field>
            </v-col>
          </v-row>

          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Adres E-mail</p>
          <v-text-field v-model="email" :rules="[rules.required, rules.email]" prepend-inner-icon="mdi-email-outline" placeholder="jan.kowalski@email.pl" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" required class="mb-2 custom-input"></v-text-field>

          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Adres Dostawy</p>
          <v-text-field v-model="address" :rules="[rules.required]" prepend-inner-icon="mdi-map-marker-outline" placeholder="ul. Marszałkowska 1/2, 00-001 Warszawa" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" class="custom-input hide-bottom-space"></v-text-field>
          <p class="text-grey-darken-1 mb-4 mt-1" style="font-size: 0.7rem;">Będzie używany jako domyślny adres dostawy</p>

          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Hasło</p>
          <v-text-field v-model="password" :rules="[rules.required, rules.passwordLength]" prepend-inner-icon="mdi-lock-outline" placeholder="Minimum 8 znaków" :type="showPassword ? 'text' : 'password'" :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'" @click:append-inner="showPassword = !showPassword" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" required class="mb-2 custom-input"></v-text-field>

          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Powtórz Hasło</p>
          <v-text-field v-model="confirmPassword" :rules="[rules.required, rules.passwordMatch]" prepend-inner-icon="mdi-shield-outline" placeholder="••••••••" :type="showConfirmPassword ? 'text' : 'password'" :append-inner-icon="showConfirmPassword ? 'mdi-eye-off' : 'mdi-eye'" @click:append-inner="showConfirmPassword = !showConfirmPassword" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" required class="mb-4 custom-input"></v-text-field>

          <div class="terms-box pa-4 mb-6 rounded-lg">
            <p class="text-grey-lighten-1 mb-0" style="font-size: 0.75rem; line-height: 1.5;">
              Rejestrując się, akceptujesz <span class="text-gold cursor-pointer">Regulamin</span> oraz <span class="text-gold cursor-pointer">Politykę Prywatności</span>. Dane przetwarzane są zgodnie z RODO.
            </p>
          </div>
        </template>

        <template v-else>
          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Adres E-mail</p>
          <v-text-field v-model="email" :rules="[rules.required, rules.email]" prepend-inner-icon="mdi-email-outline" placeholder="jan.kowalski@email.pl" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" required class="mb-4 custom-input"></v-text-field>

          <p class="text-caption text-grey-lighten-1 mb-1 font-weight-bold text-uppercase">Hasło</p>
          <v-text-field v-model="password" :rules="[rules.required]" prepend-inner-icon="mdi-lock-outline" placeholder="••••••••" :type="showPassword ? 'text' : 'password'" :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'" @click:append-inner="showPassword = !showPassword" variant="solo-filled" bg-color="#1E293B" color="#E5B338" base-color="transparent" required class="mb-2 custom-input"></v-text-field>

          <div class="d-flex justify-end mb-8">
            <a href="#" class="text-gold text-caption text-decoration-none">Zapomniałem hasła</a>
          </div>
        </template>

        <v-btn type="submit" :disabled="!isFormValid" :color="isFormValid ? '#E5B338' : 'grey-darken-3'" block height="56" :class="isFormValid ? 'text-black font-weight-bold mb-4' : 'text-grey-lighten-1 mb-4'" rounded="lg" :loading="isLoading">
          {{ isLoginMode ? 'Zaloguj się' : 'Utwórz konto' }}
        </v-btn>

        <v-alert v-if="message" :type="isError ? 'error' : 'success'" class="mb-0 text-caption rounded-lg">
          {{ message }}
        </v-alert>

      </v-form>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import axios from 'axios';

const emit = defineEmits(['login-success']);

const isLoginMode = ref(false);
const isFormValid = ref(false); // Zmienna śledząca czy formularz jest bezbłędny

const email = ref('');
const password = ref('');
const confirmPassword = ref('');
const fullName = ref('');
const phone = ref('');
const address = ref('');
const showPassword = ref(false);
const showConfirmPassword = ref(false);
const message = ref('');
const isError = ref(false);
const isLoading = ref(false);

// ==========================================
// MOZG WALIDACJI (REGUŁY)
// ==========================================
const rules = {
  required: (v: string) => !!v || 'To pole jest wymagane',
  email: (v: string) => /.+@.+\..+/.test(v) || 'Wpisz poprawny adres e-mail (np. jan@test.pl)',
  passwordLength: (v: string) => (v && v.length >= 8) || 'Hasło musi mieć minimum 8 znaków',
  passwordMatch: (v: string) => v === password.value || 'Hasła nie są identyczne',
  phone: (v: string) => /^[0-9\s\-\+]{9,15}$/.test(v) || 'Wpisz poprawny numer telefonu'
};

// Funkcja do czyszczenia formularza przy zmianie trybu Logowanie/Rejestracja
const switchMode = (toLogin: boolean) => {
  isLoginMode.value = toLogin;
  message.value = '';
  isError.value = false;
  // Czyścimy hasła przy przełączaniu zakładek ze względów bezpieczeństwa
  password.value = '';
  confirmPassword.value = '';
};

const handleSubmit = async () => {
  if (!isFormValid.value) return; // Podwójne zabezpieczenie przed kliknięciem

  isLoading.value = true;
  message.value = '';
  isError.value = false;

  try {
    if (isLoginMode.value) {
      // --- LOGOWANIE ---
      const formData = new URLSearchParams();
      formData.append('username', email.value);
      formData.append('password', password.value);

      const response = await axios.post('http://localhost:8000/api/v1/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });

      localStorage.setItem('access_token', response.data.access_token);
      emit('login-success'); 

    } else {
      // --- REJESTRACJA ---
      const nameParts = fullName.value.trim().split(' ');
      const firstName = nameParts[0] || 'Nieznane';
      const lastName = nameParts.length > 1 ? nameParts.slice(1).join(' ') : 'Nieznane';

      await axios.post('http://localhost:8000/api/v1/register', {
        email: email.value,
        password: password.value,
        first_name: firstName,
        last_name: lastName,
        phone: phone.value, 
        role_id: 1 
      });

      message.value = 'Konto utworzone! Przełączam na logowanie...';
      isError.value = false;
      
      setTimeout(() => {
        switchMode(true);
      }, 1500);
    }

  } catch (error: any) {
    isError.value = true;
    message.value = isLoginMode.value ? 'Błędny email lub hasło.' : 'Błąd rejestracji. Sprawdź dane lub użytkownik już istnieje.';
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
.login-background {
  background: radial-gradient(circle at center, #0B172A 0%, #020617 100%);
  min-height: 100vh;
}

.login-card {
  background-color: #0F172A !important;
  border-radius: 20px !important;
  width: 100%;
  max-width: 520px;
  border: 1px solid rgba(229, 179, 56, 0.1);
  box-shadow: 0 20px 50px rgba(0,0,0,0.5), 0 0 20px rgba(229, 179, 56, 0.05) !important;
}

.text-gold { color: #E5B338 !important; }
.cursor-pointer { cursor: pointer; }

.custom-input :deep(.v-field) {
  border-radius: 12px;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.3) !important;
}

/* Dostosowanie odstępu na błędy pod inputem */
.custom-input :deep(.v-messages) {
  padding-left: 4px;
  opacity: 1 !important;
}

.hide-bottom-space :deep(.v-input__details) {
  display: none !important;
}

.terms-box {
  background-color: #1E293B;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.letter-spacing-1 { letter-spacing: 1px; }
</style>