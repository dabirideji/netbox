<script setup lang="ts">
import { PhSpinner } from '@phosphor-icons/vue';
import { Button } from '../ui/button';
import { SectionModal } from '../ui/section-modal';
import type { MonitorTarget } from '../../types';

defineProps<{
  open: boolean;
  target: MonitorTarget | null;
  deleting: boolean;
}>();

const emit = defineEmits<{
  close: [];
  confirm: [];
}>();
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="target-taxonomy-modal">
      <SectionModal mode="modal" title="Delete source" @close="emit('close')">
        <div class="target-taxonomy-modal__form">
          <p class="target-taxonomy-modal__message">
            Delete <strong>{{ target?.label }}</strong>? This removes the monitor source and its configuration.
          </p>
          <div class="target-taxonomy-modal__actions">
            <Button type="button" variant="ghost" size="sm" :disabled="deleting" @click="emit('close')">
              Cancel
            </Button>
            <Button type="button" size="sm" :disabled="deleting" @click="emit('confirm')">
              <PhSpinner
                v-if="deleting"
                class="target-taxonomy-modal__spinner"
                weight="bold"
                aria-hidden="true"
              />
              <span>{{ deleting ? 'Deleting' : 'Delete' }}</span>
            </Button>
          </div>
        </div>
      </SectionModal>
    </div>
  </Teleport>
</template>
