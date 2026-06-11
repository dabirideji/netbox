<script setup lang="ts">
import { PhSpinner } from '@phosphor-icons/vue';
import { computed } from 'vue';
import { Button } from '../ui/button';
import { SectionModal } from '../ui/section-modal';
import { formatClock, formatMs } from '../../format';
import type { TargetPreviewCheckResponse } from '../../types';

const props = defineProps<{
  open: boolean;
  loading: boolean;
  result: TargetPreviewCheckResponse | null;
  error: string | null;
  canAdd: boolean;
}>();

const emit = defineEmits<{
  close: [];
  add: [];
}>();

const headline = computed(() => {
  if (props.loading) return 'Running test check';
  if (props.error) return 'Test failed';
  if (!props.result) return 'Test result';
  return props.result.result.ok ? 'Check passed' : 'Check failed';
});

const outcomeClass = computed(() => {
  if (props.error) return 'down';
  return props.result?.status ?? 'unknown';
});
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="target-taxonomy-modal">
      <SectionModal mode="modal" title="Test source" @close="emit('close')">
        <div class="target-taxonomy-modal__form target-test-modal">
          <p class="target-taxonomy-modal__message">
            {{ loading ? 'Running one live check with the current form settings.' : headline }}
          </p>

          <div v-if="loading" class="target-test-modal__loading">
            <PhSpinner class="target-test-modal__spinner" weight="bold" aria-hidden="true" />
            <span>Checking<span class="pill__dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span></span>
          </div>

          <p v-else-if="error" class="target-error">{{ error }}</p>

          <dl v-else-if="result" class="target-test-modal__details">
            <div class="target-test-modal__row">
              <dt>Outcome</dt>
              <dd>
                <span class="status" :class="outcomeClass">
                  <span class="dot" />
                  {{ result.status }}
                </span>
              </dd>
            </div>
            <div class="target-test-modal__row">
              <dt>Target</dt>
              <dd>{{ result.result.label }}</dd>
            </div>
            <div class="target-test-modal__row">
              <dt>Host</dt>
              <dd>{{ result.result.host }}</dd>
            </div>
            <div class="target-test-modal__row">
              <dt>Protocol</dt>
              <dd>{{ result.result.protocol.toUpperCase() }}</dd>
            </div>
            <div class="target-test-modal__row">
              <dt>Latency</dt>
              <dd>
                {{
                  result.result.latencyMs == null
                    ? result.result.error ?? 'fail'
                    : formatMs(result.result.latencyMs)
                }}
              </dd>
            </div>
            <div class="target-test-modal__row">
              <dt>Checked</dt>
              <dd>{{ formatClock(result.result.checkedAt) }}</dd>
            </div>
            <div v-if="result.result.error" class="target-test-modal__row target-test-modal__row--wide">
              <dt>Error</dt>
              <dd>{{ result.result.error }}</dd>
            </div>
          </dl>

          <div class="target-taxonomy-modal__actions">
            <Button type="button" variant="ghost" size="sm" :disabled="loading" @click="emit('close')">
              Close
            </Button>
            <Button v-if="canAdd && result && !error" type="button" size="sm" :disabled="loading" @click="emit('add')">
              Add target
            </Button>
          </div>
        </div>
      </SectionModal>
    </div>
  </Teleport>
</template>
