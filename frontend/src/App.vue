<template>
  <v-app>
    <DashboardView v-if="isAuthenticated" @logout-success="handleLogout" />
    
    <LoginForm v-else @login-success="handleLogin" />
  </v-app>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import LoginForm from './components/LoginForm.vue';
import DashboardView from './components/DashboardView.vue';

// Zmienna trzymająca informację, czy jesteśmy zalogowani
const isAuthenticated = ref(false);

// Przy ładowaniu strony sprawdzamy, czy token przypadkiem już nie siedzi w przeglądarce
onMounted(() => {
  const token = localStorage.getItem('access_token');
  if (token) {
    isAuthenticated.value = true;
  }
});

// Funkcja uruchamiana, gdy LoginForm krzyknie "Udało się zalogować!"
const handleLogin = () => {
  isAuthenticated.value = true;
};

// Funkcja uruchamiana, gdy Dashboard krzyknie "Użytkownik kliknął Wyloguj"
const handleLogout = () => {
  isAuthenticated.value = false;
};
</script>

<style>
/* Globalne style, żeby zlikwidować białe marginesy */
body, html {
  margin: 0;
  padding: 0;
  background-color: #020617;
}
</style>