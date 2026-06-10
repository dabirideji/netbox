import { createApp } from 'vue';
import { createPinia } from 'pinia';
import { createPersistedState } from 'pinia-plugin-persistedstate';
import { PhSpinner } from '@phosphor-icons/vue';
import App from './App.vue';
import { applyThemePreference, getStoredThemePreference } from './theme';
import { initWallpaperFromStorage } from './wallpaper';
import './styles.css';

applyThemePreference(getStoredThemePreference());
initWallpaperFromStorage();

const pinia = createPinia();
pinia.use(
  createPersistedState({
    storage: localStorage,
    auto: false,
  }),
);

const app = createApp(App);
app.component('PhSpinner', PhSpinner);
app.use(pinia).mount('#app');
