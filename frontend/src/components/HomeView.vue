<template>
  <v-container fluid class="home-bg pa-0">
    <v-app-bar color="transparent" flat height="80" class="px-md-10">
      <div class="d-flex align-center">
        <v-icon icon="mdi-crown" color="#E5B338" size="36" class="mr-2"></v-icon>
        <div class="d-flex flex-column">
          <span class="text-white font-weight-bold text-h6 lh-1">ROYALE PACKAGE</span>
          <span class="text-gold text-caption" style="font-size: 0.7rem !important;">TWÓJ KURIER PREMIUM</span>
        </div>
      </div>
      <v-spacer></v-spacer>
      <v-btn variant="text" class="text-white text-capitalize mx-1" to="/login">Zaloguj się</v-btn>
      <v-btn color="#E5B338" class="text-black font-weight-bold rounded-lg px-6" to="/login">Zarejestruj się</v-btn>
    </v-app-bar>

    <v-row class="fill-height align-center justify-center text-center mt-16 pt-16 mx-0">
      <v-col cols="12" md="8" lg="6">
        <v-chip color="#E5B338" variant="outlined" class="mb-6 font-weight-bold">👑 ROYALE PACKAGE — KURIER PREMIUM</v-chip>
        <h1 class="text-white text-h2 text-md-h1 font-weight-black mb-4">Twoja paczka.<br><span class="text-gold">Zawsze na czas.</span></h1>
        <p class="text-grey-lighten-1 text-h6 mb-10 px-6">Śledzenie przesyłek w czasie rzeczywistym, trzy kategorie wagowe i dostawa do całej Polski — niezawodnie i bez kompromisów.</p>
        
        <v-card max-width="600" class="mx-auto rounded-xl pa-2 mb-16" color="#1E293B" elevation="12">
          <v-row no-gutters align="center">
            <v-col cols="8" sm="9">
              <v-text-field v-model="trackingNumber" placeholder="RP1234567PL" variant="plain" class="px-4 text-white" hide-details prepend-inner-icon="mdi-magnify" @keyup.enter="goToTracking"></v-text-field>
            </v-col>
            <v-col cols="4" sm="3">
              <v-btn block color="#E5B338" height="52" class="rounded-lg text-black font-weight-bold" @click="goToTracking">ŚLEDŹ</v-btn>
            </v-col>
          </v-row>
        </v-card>

        <v-btn size="x-large" color="#E5B338" class="text-black font-weight-black rounded-lg px-12 py-4" @click="$router.push('/dashboard')">
          NADAJ PRZESYŁKĘ TERAZ
        </v-btn>
      </v-col>
    </v-row>
  </v-container>
</template>

<style scoped>
.home-bg {
  background: radial-gradient(circle at 50% 30%, #0B172A 0%, #020617 100%);
  min-height: 100vh;
}
.text-gold { color: #E5B338 !important; }
.lh-1 { line-height: 1; }
</style>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();
const trackingNumber = ref('');

const goToTracking = () => {
  if (trackingNumber.value.trim()) {
    router.push(`/tracking/${trackingNumber.value.trim()}`);
  } else {
    router.push('/tracking');
  }
};
</script>