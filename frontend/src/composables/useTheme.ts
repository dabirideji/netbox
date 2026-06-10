import { computed, onMounted, onUnmounted, ref } from 'vue';
import {
  applyThemePreference,
  cycleThemePreference,
  getStoredThemePreference,
  resolveTheme,
  setThemePreference,
  type ThemePreference,
} from '../theme';

export function useTheme() {
  const preference = ref<ThemePreference>(getStoredThemePreference());
  const resolvedTheme = computed(() => resolveTheme(preference.value));

  function syncTheme(): void {
    applyThemePreference(preference.value);
  }

  function cycleTheme(): void {
    preference.value = cycleThemePreference(preference.value);
    setThemePreference(preference.value);
  }

  let mediaQuery: MediaQueryList | undefined;
  let onSystemThemeChange: ((event: MediaQueryListEvent) => void) | undefined;

  onMounted(() => {
    syncTheme();

    mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    onSystemThemeChange = () => {
      if (preference.value === 'system') {
        syncTheme();
      }
    };
    mediaQuery.addEventListener('change', onSystemThemeChange);
  });

  onUnmounted(() => {
    if (mediaQuery && onSystemThemeChange) {
      mediaQuery.removeEventListener('change', onSystemThemeChange);
    }
  });

  return {
    preference,
    resolvedTheme,
    cycleTheme,
  };
}
