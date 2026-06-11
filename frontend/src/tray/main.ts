import { createApp } from 'vue';
import { setupThemeSync } from '../theme';
import '../styles.css';
import './tray.css';
import TrayApp from './TrayApp.vue';

setupThemeSync();
createApp(TrayApp).mount('#tray-app');
