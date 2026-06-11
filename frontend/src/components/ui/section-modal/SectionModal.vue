<script setup lang="ts">
import { onMounted, onUnmounted, useId, watch } from 'vue';
import { PhX } from '@phosphor-icons/vue';
import { AnimatePresence, motion } from 'motion-v';
import {
  modalBackdropAnimate,
  modalBackdropExit,
  modalBackdropInitial,
  modalDialogAnimate,
  modalDialogExit,
  modalDialogInitial,
} from '../../../motion/sectionAnimations';

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
  <div v-if="mode === 'inline'" class="section-modal-shell">
    <div class="section-modal__frame dashboard-card__body">
      <slot />
    </div>
  </div>

  <AnimatePresence mode="sync">
    <motion.div
      v-if="mode === 'modal'"
      key="section-modal"
      class="section-modal-shell section-modal"
      :initial="modalBackdropInitial"
      :animate="modalBackdropAnimate"
      :exit="modalBackdropExit"
    >
      <button
        type="button"
        class="section-modal__backdrop"
        aria-label="Close dialog"
        @click="emit('close')"
      />
      <motion.div
        class="section-modal__frame section-modal__dialog"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        :aria-label="!title ? 'Section details' : undefined"
        :initial="modalDialogInitial"
        :animate="modalDialogAnimate"
        :exit="modalDialogExit"
        @click.stop
      >
        <header class="section-modal__header">
          <div class="section-modal__titles">
            <p v-if="eyebrow" class="eyebrow">{{ eyebrow }}</p>
            <h2 :id="titleId">{{ title }}</h2>
          </div>
          <button type="button" class="section-modal__close" aria-label="Close" @click="emit('close')">
            <PhX class="section-modal__close-icon" weight="bold" aria-hidden="true" />
          </button>
        </header>
        <div class="section-modal__body">
          <slot />
        </div>
      </motion.div>
    </motion.div>
  </AnimatePresence>
</template>
