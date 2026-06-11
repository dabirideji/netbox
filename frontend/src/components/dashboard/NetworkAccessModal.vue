<script setup lang="ts">
import { ref, watch } from 'vue';
import { PhCheck, PhSpinner } from '@phosphor-icons/vue';
import { Button } from '../ui/button';
import { SectionModal } from '../ui/section-modal';
import type { NetworkInterfaceOption } from '../../types';

const props = defineProps<{
  open: boolean;
  busy: boolean;
  statusMessage: string | null;
  interfaces: NetworkInterfaceOption[];
  interfacesLoading: boolean;
  activeInterface: string | null;
}>();

const emit = defineEmits<{
  close: [];
  refresh: [];
  selectInterface: [option: NetworkInterfaceOption];
  saveManual: [ssid: string];
}>();

const manualSsid = ref('');
const pendingInterface = ref<string | null>(null);

watch(
  () => props.open,
  (open) => {
    if (!open) {
      manualSsid.value = '';
      pendingInterface.value = null;
    }
  },
);

function interfaceDetail(option: NetworkInterfaceOption): string {
  if (option.ssid) return option.ssid;
  if (option.hidden) return 'Hidden';
  return option.label;
}

function isSelected(option: NetworkInterfaceOption): boolean {
  return props.activeInterface === option.interface;
}

function isPending(option: NetworkInterfaceOption): boolean {
  return pendingInterface.value === option.interface;
}

function selectOption(option: NetworkInterfaceOption): void {
  if (props.busy) return;
  pendingInterface.value = option.interface;
  emit('selectInterface', option);
}

function submitManual(): void {
  const ssid = manualSsid.value.trim();
  if (!ssid) return;
  emit('saveManual', ssid);
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="target-taxonomy-modal network-access-modal">
      <SectionModal mode="modal" title="Network" @close="emit('close')">
        <div class="target-taxonomy-modal__form network-access-modal__form">
          <div v-if="interfacesLoading" class="network-access-modal__loading">
            <PhSpinner class="target-taxonomy-modal__spinner" weight="bold" aria-hidden="true" />
          </div>

          <div
            v-else-if="interfaces.length"
            class="network-access-modal__list"
            role="listbox"
            aria-label="Network interfaces"
          >
            <button
              v-for="option in interfaces"
              :key="option.interface"
              type="button"
              class="network-access-modal__option"
              :class="{
                'network-access-modal__option--selected': isSelected(option),
                'network-access-modal__option--pending': isPending(option),
              }"
              role="option"
              :aria-selected="isSelected(option)"
              :disabled="busy"
              @click="selectOption(option)"
            >
              <span class="network-access-modal__option-main">
                <span class="network-access-modal__option-title">
                  {{ option.service || 'Network' }}
                  <small>{{ option.interface }}</small>
                </span>
                <span class="network-access-modal__option-detail">{{ interfaceDetail(option) }}</span>
              </span>
              <span class="network-access-modal__option-meta">
                <PhSpinner
                  v-if="isPending(option) && busy"
                  class="network-access-modal__option-icon"
                  weight="bold"
                  aria-hidden="true"
                />
                <PhCheck
                  v-else-if="isSelected(option)"
                  class="network-access-modal__option-icon network-access-modal__option-icon--check"
                  weight="bold"
                  aria-hidden="true"
                />
                <span v-else-if="option.active" class="network-access-modal__badge">Active</span>
              </span>
            </button>
          </div>

          <p v-else class="network-access-modal__empty">None found</p>

          <p v-if="statusMessage" class="network-access-modal__status">{{ statusMessage }}</p>

          <div class="network-access-modal__footer">
            <div class="network-access-modal__actions">
              <Button type="button" variant="ghost" size="sm" :disabled="busy" @click="emit('refresh')">
                Refresh
              </Button>
              <Button type="button" variant="ghost" size="sm" :disabled="busy" @click="emit('close')">
                Close
              </Button>
            </div>
          </div>

          <details class="network-access-modal__manual">
            <summary>Manual</summary>
            <div class="network-access-modal__manual-row">
              <input
                v-model.trim="manualSsid"
                type="text"
                maxlength="64"
                placeholder="Name"
                :disabled="busy"
                @keydown.enter.prevent="submitManual"
              />
              <Button type="button" size="sm" :disabled="busy || !manualSsid.trim()" @click="submitManual">
                Save
              </Button>
            </div>
          </details>
        </div>
      </SectionModal>
    </div>
  </Teleport>
</template>
