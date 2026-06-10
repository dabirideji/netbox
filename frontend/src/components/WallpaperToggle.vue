<script setup lang="ts">
import { computed } from 'vue';
import { useWallpaper } from '../composables/useWallpaper';
import { Switch } from './ui/switch';

const { enabled, loading, error, setEnabled } = useWallpaper();

const title = computed(() => {
  if (loading.value) return 'Loading wallpaper…';
  if (error.value) return error.value;
  return enabled.value ? 'Turn off Pexels wallpaper' : 'Turn on Pexels wallpaper';
});
</script>

<template>
  <Teleport to="body">
    <div class="wallpaper-toggle" :title="title">
      <Switch
        id="wallpaper-switch"
        :model-value="enabled"
        :disabled="loading"
        :aria-label="title"
        @update:model-value="setEnabled"
      />
      <label class="wallpaper-toggle__label" for="wallpaper-switch">Wallpaper</label>
    </div>
  </Teleport>
</template>
