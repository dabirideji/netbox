<script setup lang="ts">
import { PhArrowsClockwise } from '@phosphor-icons/vue';
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useWallpaperStore } from '../stores/wallpaper';

const wallpaperStore = useWallpaperStore();
const { loading, error } = storeToRefs(wallpaperStore);

const title = computed(() => {
  if (loading.value) return 'Refreshing wallpaper…';
  if (error.value) return error.value;
  return 'Refresh wallpaper';
});
</script>

<template>
  <Teleport to="body">
    <div class="wallpaper-refresh">
      <button
        type="button"
        class="wallpaper-refresh__button"
        :title="title"
        :aria-label="title"
        :disabled="loading"
        @click="wallpaperStore.refreshWallpaper()"
      >
        <PhArrowsClockwise
          class="wallpaper-refresh__icon"
          :class="{ 'is-spinning': loading }"
          weight="bold"
          aria-hidden="true"
        />
      </button>
    </div>
  </Teleport>
</template>
