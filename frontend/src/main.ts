import { createApp } from 'vue'
import App from './App.vue'

// --- KONFIGURACJA VUETIFY ---
import 'vuetify/styles' // Importujemy główne style CSS od Vuetify
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

// --- IKONKI ---
//import '@mdi/font/css/materialdesignicons.css' 

// Odpalamy silnik Vuetify
const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'dark' // Od razu mówimy mu, że robimy mroczny, premium design!
  }
})

// Tworzymy aplikację, wstrzykujemy Vuetify i montujemy na ekranie
createApp(App).use(vuetify).mount('#app')