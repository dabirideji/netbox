import { createApp } from 'vue';
import { createPinia } from 'pinia';
import { createPersistedState } from 'pinia-plugin-persistedstate';
import { PhSpinner } from '@phosphor-icons/vue';
import App from './App.vue';
import { applyThemePreference, getStoredThemePreference } from './theme';
import { initWallpaperFromStorage } from './wallpaper';
import { vTruncateTitle } from './directives/truncateTitle';
import { startTruncationTitleObserver } from './utils/truncationTitleObserver';
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
app.directive('truncate-title', vTruncateTitle);
app.use(pinia).mount('#app');

const mountPoint = document.getElementById('app');
if (mountPoint) {
  startTruncationTitleObserver(mountPoint);
}
