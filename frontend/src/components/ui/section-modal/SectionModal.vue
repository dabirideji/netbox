<script setup lang="ts">
import { onMounted, onUnmounted, useId, watch } from 'vue';
import { PhX } from '@phosphor-icons/vue';

const props = withDefaults(
  defineProps<{
    mode?: 'inline' | 'modal';
    eyebrow?: string;
    title?: string;
  }>(),
  {
    mode: 'modal',
  },
);

const emit = defineEmits<{
  close: [];
}>();

const titleId = useId();

function onKeydown(event: KeyboardEvent): void {
  if (props.mode !== 'modal' || event.key !== 'Escape') return;
  emit('close');
}

watch(
  () => props.mode,
  (mode) => {
    if (mode === 'modal') {
      document.addEventListener('keydown', onKeydown);
      return;
    }
    document.removeEventListener('keydown', onKeydown);
  },
  { immediate: true },
);

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown);
});
</script>

<template>
  <div class="section-modal-shell" :class="{ 'section-modal': mode === 'modal' }">
    <button
      v-if="mode === 'modal'"
      type="button"
      class="section-modal__backdrop"
      aria-label="Close dialog"
      @click="emit('close')"
    />
    <div
      class="section-modal__frame"
      :class="mode === 'modal' ? 'section-modal__dialog' : 'dashboard-card__body'"
      :role="mode === 'modal' ? 'dialog' : undefined"
      :aria-modal="mode === 'modal' ? 'true' : undefined"
      :aria-labelledby="mode === 'modal' ? titleId : undefined"
      :aria-label="mode === 'modal' && !title ? 'Section details' : undefined"
      @click.stop
    >
      <header v-if="mode === 'modal'" class="section-modal__header">
        <div class="section-modal__titles">
          <p v-if="eyebrow" class="eyebrow">{{ eyebrow }}</p>
          <h2 :id="titleId">{{ title }}</h2>
        </div>
        <button type="button" class="section-modal__close" aria-label="Close" @click="emit('close')">
          <PhX class="section-modal__close-icon" weight="bold" aria-hidden="true" />
        </button>
      </header>
      <div :class="{ 'section-modal__body': mode === 'modal' }">
        <slot />
      </div>
    </div>
  </div>
</template>
