// frontend/src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router';
import DashboardView from '../components/DashboardView.vue';
import LoginForm from '../components/LoginForm.vue';
import HomeView from '../components/HomeView.vue'; 

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { 
      path: '/', 
      name: 'home', 
      component: HomeView 
    },
    { 
      path: '/login', 
      name: 'login', 
      component: LoginForm 
    },
    { 
      path: '/dashboard', 
      name: 'dashboard', 
      component: DashboardView,
      meta: { requiresAuth: true } // Oznaczamy, że tu trzeba mieć bilet VIP!
    }
  ]
});

// GLOBALNY STRAŻNIK (Uruchamia się przed każdym przejściem na nową stronę)
router.beforeEach((to, from, next) => {
  const isAuthenticated = !!localStorage.getItem('access_token');

  if (to.meta.requiresAuth && !isAuthenticated) {
    // Jeśli próbuje wejść do panelu bez tokena -> wyrzuć do logowania
    next('/login');
  } else if (to.path === '/login' && isAuthenticated) {
    // Jeśli jest zalogowany i klika w logowanie -> wrzuć go prosto do panelu
    next('/dashboard');
  } else {
    // W pozostałych przypadkach pozwól mu iść tam, gdzie chce
    next();
  }
});

export default router;