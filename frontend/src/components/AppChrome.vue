<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { useWallpaperStore } from '../stores/wallpaper';
import ApiLoadingSpinner from './ApiLoadingSpinner.vue';
import GlobalSettingsModal from './GlobalSettingsModal.vue';
import SettingsButton from './SettingsButton.vue';
import ThemeSwitcher from './ThemeSwitcher.vue';
import WallpaperRefreshButton from './WallpaperRefreshButton.vue';

const wallpaperStore = useWallpaperStore();
const { enabled: wallpaperEnabled } = storeToRefs(wallpaperStore);
</script>

<template>
  <ApiLoadingSpinner />
  <WallpaperRefreshButton v-if="wallpaperEnabled" />
  <ThemeSwitcher />
  <SettingsButton />
  <GlobalSettingsModal />
</template>
