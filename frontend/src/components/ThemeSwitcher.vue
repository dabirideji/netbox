<script setup lang="ts">
import { computed } from 'vue';
import { PhDesktop, PhMoon, PhSun } from '@phosphor-icons/vue';
import { useTheme } from '../composables/useTheme';
import { cycleThemePreference, themePreferenceLabel } from '../theme';

const { preference, cycleTheme } = useTheme();

const nextPreference = computed(() => cycleThemePreference(preference.value));

const label = computed(() => themePreferenceLabel(preference.value));
const nextLabel = computed(() => themePreferenceLabel(nextPreference.value));

const title = computed(() => `${label.value} theme. Switch to ${nextLabel.value}.`);
</script>

<template>
  <Teleport to="body">
    <div class="theme-switcher">
      <button
        type="button"
        class="theme-switcher__button"
        :title="title"
        :aria-label="title"
        @click="cycleTheme"
      >
        <PhSun v-if="preference === 'light'" class="theme-switcher__icon" weight="duotone" aria-hidden="true" />
        <PhMoon v-else-if="preference === 'dark'" class="theme-switcher__icon" weight="duotone" aria-hidden="true" />
        <PhDesktop v-else class="theme-switcher__icon" weight="duotone" aria-hidden="true" />
      </button>
    </div>
  </Teleport>
</template>
