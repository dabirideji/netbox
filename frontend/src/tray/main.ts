import { createApp } from 'vue';
import { setupThemeSync } from '../theme';
import '../styles.css';
import './tray.css';
import { vTruncateTitle } from '../directives/truncateTitle';
import { startTruncationTitleObserver } from '../utils/truncationTitleObserver';
import TrayApp from './TrayApp.vue';

setupThemeSync();
const app = createApp(TrayApp);
app.directive('truncate-title', vTruncateTitle);
app.mount('#tray-app');

const mountPoint = document.getElementById('tray-app');
if (mountPoint) {
  startTruncationTitleObserver(mountPoint);
}
