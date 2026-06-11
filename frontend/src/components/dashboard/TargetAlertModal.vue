<script setup lang="ts">
import { PhSpinner } from '@phosphor-icons/vue';
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { SectionModal } from '../ui/section-modal';
import { Switch } from '../ui/switch';
import { requestNotificationPermission } from '../../composables/useAlertNotifications';
import { useAlertsStore } from '../../stores/alerts';
import { useSettingsStore } from '../../stores/settings';

const alertsStore = useAlertsStore();
const settingsStore = useSettingsStore();
const {
  activeTarget,
  alertForm,
  isLoadingAlert,
  isSavingAlert,
  alertError,
} = storeToRefs(alertsStore);

const open = computed(() => Boolean(activeTarget.value));
const title = computed(() => (activeTarget.value ? `Alerts · ${activeTarget.value.label}` : 'Alerts'));
const emailDisabled = computed(() => !alertForm.value?.smtpConfigured);

async function onSave(): Promise<void> {
  if (alertForm.value?.notification) {
    await requestNotificationPermission();
  }
  const saved = await alertsStore.saveAlert();
  if (saved) {
    alertsStore.closeAlertModal();
  }
}

function openGlobalSettings(): void {
  alertsStore.closeAlertModal();
  void settingsStore.open();
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="target-taxonomy-modal">
      <SectionModal mode="modal" :title="title" @close="alertsStore.closeAlertModal()">
        <div class="target-alert-modal">
          <p v-if="isLoadingAlert" class="target-test-modal__loading">
            <PhSpinner class="target-test-modal__spinner" weight="bold" aria-hidden="true" />
            <span>Loading alert settings</span>
          </p>

          <template v-else-if="alertForm">
            <div class="target-alert-modal__body">
              <p v-if="alertError" class="target-error">{{ alertError }}</p>
              <div class="target-alert-modal__section">
                <div class="target-alert-modal__row">
                  <div>
                    <strong>Enable alerts</strong>
                    <p class="target-alert-modal__hint">Notify when this target changes status.</p>
                  </div>
                  <Switch v-model="alertForm.enabled" />
                </div>

                <div class="target-alert-modal__row">
                  <div>
                    <strong>Desktop notification</strong>
                    <p class="target-alert-modal__hint">Show a system or browser notification.</p>
                  </div>
                  <Switch v-model="alertForm.notification" :disabled="!alertForm.enabled" />
                </div>

                <div class="target-alert-modal__row">
                  <div>
                    <strong>Alert sound</strong>
                    <p class="target-alert-modal__hint">Repeats every minute while the target stays down.</p>
                  </div>
                  <Switch v-model="alertForm.sound" :disabled="!alertForm.enabled" />
                </div>

                <div class="target-alert-modal__row">
                  <div>
                    <strong>Email alert</strong>
                    <p class="target-alert-modal__hint">
                      {{
                        emailDisabled
                          ? 'Configure the shared SMTP provider in Settings before enabling email alerts.'
                          : 'Sends immediately, then every 15 minutes while the target stays down.'
                      }}
                    </p>
                  </div>
                  <Switch
                    v-model="alertForm.email"
                    :disabled="!alertForm.enabled || emailDisabled"
                  />
                </div>

                <label v-if="alertForm.email" class="target-alert-modal__field">
                  <Label>Alert email</Label>
                  <input v-model="alertForm.emailTo" type="email" placeholder="you@example.com" />
                </label>

                <div class="target-alert-modal__checks">
                  <label class="target-alert-modal__check">
                    <input v-model="alertForm.onDegraded" type="checkbox" :disabled="!alertForm.enabled" />
                    <span>Alert on degraded</span>
                  </label>
                  <label class="target-alert-modal__check">
                    <input v-model="alertForm.onDown" type="checkbox" :disabled="!alertForm.enabled" />
                    <span>Alert on down</span>
                  </label>
                </div>

                <p v-if="emailDisabled" class="target-alert-modal__hint">
                  <button type="button" class="settings-panel__inline-link" @click="openGlobalSettings">
                    Open Settings
                  </button>
                  to configure SMTP and platform defaults.
                </p>
              </div>
            </div>

            <div class="target-alert-modal__footer target-taxonomy-modal__actions">
              <Button type="button" variant="ghost" size="sm" @click="alertsStore.closeAlertModal()">
                Cancel
              </Button>
              <Button type="button" size="sm" :disabled="isSavingAlert" @click="onSave">
                <PhSpinner v-if="isSavingAlert" class="target-taxonomy-modal__spinner" weight="bold" aria-hidden="true" />
                <span>{{ isSavingAlert ? 'Saving' : 'Save alerts' }}</span>
              </Button>
            </div>
          </template>
        </div>
      </SectionModal>
    </div>
  </Teleport>
</template>
