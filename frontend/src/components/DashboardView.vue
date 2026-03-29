<template>
  <v-container fluid class="dashboard-bg fill-height align-start pa-0">
    
    <v-app-bar color="#0B172A" elevation="4" height="80">
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

    <v-container class="mt-16 text-center">
      <h1 class="text-white mt-10">Witaj w panelu głównym!</h1>
      <p class="text-grey-lighten-1">Zalogowałeś się pomyślnie. Tutaj pojawią się Twoje paczki.</p>
    </v-container>

  </v-container>
</template>

<script setup lang="ts">
// Funkcja, która pozwala nam wysłać sygnał do App.vue, że chcemy się wylogować
const emit = defineEmits(['logout-success']);

const logout = () => {
  // 1. Usuwamy przepustkę z przeglądarki
  localStorage.removeItem('access_token');
  // 2. Krzyczymy do rodzica (App.vue), żeby pokazał z powrotem logowanie
  emit('logout-success');
};
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