<script setup lang="ts">
import { PhGear } from '@phosphor-icons/vue';
import { useSettingsStore } from '../stores/settings';

const settingsStore = useSettingsStore();
const title = 'Open platform settings';
</script>

<template>
  <Teleport to="body">
    <div class="settings-button">
      <button
        type="button"
        class="settings-button__control"
        :title="title"
        :aria-label="title"
        @click="settingsStore.open()"
      >
        <PhGear class="settings-button__icon" weight="duotone" aria-hidden="true" />
      </button>
    </div>
  </Teleport>
</template>
