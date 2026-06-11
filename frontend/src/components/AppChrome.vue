<script setup lang="ts">
import ApiLoadingSpinner from './ApiLoadingSpinner.vue';
import GlobalSettingsModal from './GlobalSettingsModal.vue';
import SettingsButton from './SettingsButton.vue';
import ThemeSwitcher from './ThemeSwitcher.vue';
import WallpaperToggle from './WallpaperToggle.vue';
</script>

<template>
  <ApiLoadingSpinner />
  <WallpaperToggle />
  <ThemeSwitcher />
  <SettingsButton />
  <GlobalSettingsModal />
</template>
