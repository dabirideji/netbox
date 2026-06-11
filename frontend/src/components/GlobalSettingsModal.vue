<script setup lang="ts">
import { PhBell, PhEnvelopeSimple, PhFloppyDisk, PhHardDrives, PhSpinner } from '@phosphor-icons/vue';
import { computed, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import SmtpSettingsPanel from './settings/SmtpSettingsPanel.vue';
import StorageSettingsPanel from './settings/StorageSettingsPanel.vue';
import { Button } from './ui/button';
import { Label } from './ui/label';
import { SectionModal } from './ui/section-modal';
import { Switch } from './ui/switch';
import { requestNotificationPermission } from '../composables/useAlertNotifications';
import { useAlertsStore } from '../stores/alerts';
import { useSettingsStore } from '../stores/settings';
import { useStorageStore } from '../stores/storage';

type SettingsTab = 'alerts' | 'email' | 'storage';

const settingsStore = useSettingsStore();
const alertsStore = useAlertsStore();
const storageStore = useStorageStore();

const activeTab = ref<SettingsTab>('alerts');

const { isOpen, platformAlerts, isLoading, isSaving, error, message } = storeToRefs(settingsStore);
const { isSaving: isSavingStorage, error: storageError } = storeToRefs(storageStore);

const cooldownMinutes = computed({
  get: () => Math.round(platformAlerts.value.defaultCooldownMs / 60_000),
  set: (value: number) => {
    const minutes = Number.isFinite(value) ? Math.max(1, Math.min(60, value)) : 5;
    platformAlerts.value.defaultCooldownMs = minutes * 60_000;
  },
});

watch(isOpen, (open) => {
  if (!open) return;
  activeTab.value = 'alerts';
  void alertsStore.loadSmtp();
  void storageStore.loadAll();
});

async function onSave(): Promise<void> {
  if (activeTab.value === 'alerts') {
    if (platformAlerts.value.defaultNotification) {
      await requestNotificationPermission();
    }
    await settingsStore.savePlatform();
    return;
  }

  if (activeTab.value === 'storage') {
    const saved = await storageStore.saveSettings();
    if (saved) {
      settingsStore.message = 'Storage settings saved.';
      settingsStore.error = null;
    } else if (storageError.value) {
      settingsStore.error = storageError.value;
      settingsStore.message = null;
    }
  }
}

const isFooterSaving = computed(() =>
  activeTab.value === 'storage' ? isSavingStorage.value : isSaving.value,
);
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="global-settings-modal">
      <SectionModal
        mode="modal"
        eyebrow="Platform"
        title="Settings"
        :close-on-backdrop="false"
        :close-on-escape="false"
        @close="settingsStore.close()"
      >
        <div class="settings-panel">
          <p v-if="isLoading" class="target-test-modal__loading">
            <PhSpinner class="target-test-modal__spinner" weight="bold" aria-hidden="true" />
            <span>Loading settings</span>
          </p>

          <template v-else>
            <div class="settings-panel__tabs" role="tablist" aria-label="Settings sections">
              <button
                type="button"
                class="settings-panel__tab"
                :class="{ 'is-active': activeTab === 'alerts' }"
                role="tab"
                :aria-selected="activeTab === 'alerts'"
                @click="activeTab = 'alerts'"
              >
                <PhBell
                  class="settings-panel__tab-icon"
                  :weight="activeTab === 'alerts' ? 'fill' : 'bold'"
                  aria-hidden="true"
                />
                <span>Alerts</span>
              </button>
              <button
                type="button"
                class="settings-panel__tab"
                :class="{ 'is-active': activeTab === 'email' }"
                role="tab"
                :aria-selected="activeTab === 'email'"
                @click="activeTab = 'email'"
              >
                <PhEnvelopeSimple
                  class="settings-panel__tab-icon"
                  :weight="activeTab === 'email' ? 'fill' : 'bold'"
                  aria-hidden="true"
                />
                <span>Email</span>
              </button>
              <button
                type="button"
                class="settings-panel__tab"
                :class="{ 'is-active': activeTab === 'storage' }"
                role="tab"
                :aria-selected="activeTab === 'storage'"
                @click="activeTab = 'storage'"
              >
                <PhHardDrives
                  class="settings-panel__tab-icon"
                  :weight="activeTab === 'storage' ? 'fill' : 'bold'"
                  aria-hidden="true"
                />
                <span>Storage</span>
              </button>
            </div>

            <div class="settings-panel__body">
              <section v-show="activeTab === 'alerts'" class="settings-panel__section">
                <div class="settings-panel__section-head">
                  <h3>Default alert behavior</h3>
                  <p class="settings-panel__hint">
                    New targets inherit these defaults until you customize alerts per target.
                  </p>
                </div>

                <div class="settings-panel__row">
                  <div>
                    <strong>Desktop notifications</strong>
                    <p class="settings-panel__hint">Default on for new target alerts.</p>
                  </div>
                  <Switch v-model="platformAlerts.defaultNotification" />
                </div>

                <div class="settings-panel__row">
                  <div>
                    <strong>Alert sound</strong>
                    <p class="settings-panel__hint">Repeats every minute while a target stays down.</p>
                  </div>
                  <Switch v-model="platformAlerts.defaultSound" />
                </div>

                <div class="settings-panel__row">
                  <div>
                    <strong>Email alerts</strong>
                    <p class="settings-panel__hint">
                      Sends immediately, then every 15 minutes while a target stays down.
                    </p>
                  </div>
                  <Switch v-model="platformAlerts.defaultEmail" />
                </div>

                <label v-if="platformAlerts.defaultEmail" class="settings-panel__field">
                  <Label>Default alert email</Label>
                  <input v-model="platformAlerts.defaultEmailTo" type="email" placeholder="you@example.com" />
                </label>

                <label class="settings-panel__field">
                  <Label>Notification repeat interval (minutes)</Label>
                  <input v-model.number="cooldownMinutes" type="number" min="1" max="60" />
                </label>

                <div class="settings-panel__checks">
                  <label class="settings-panel__check">
                    <input v-model="platformAlerts.defaultOnDegraded" type="checkbox" />
                    <span>Alert on degraded by default</span>
                  </label>
                  <label class="settings-panel__check">
                    <input v-model="platformAlerts.defaultOnDown" type="checkbox" />
                    <span>Alert on down by default</span>
                  </label>
                </div>
              </section>

              <section v-show="activeTab === 'email'" class="settings-panel__section">
                <div class="settings-panel__section-head">
                  <h3>Email delivery</h3>
                  <p class="settings-panel__hint">Shared SMTP provider used by all email alerts.</p>
                </div>
                <SmtpSettingsPanel />
              </section>

              <section v-show="activeTab === 'storage'" class="settings-panel__section">
                <div class="settings-panel__section-head">
                  <h3>Retention limits</h3>
                  <p class="settings-panel__hint">
                    Local database limits. Oldest records are removed automatically when a cap is reached.
                  </p>
                </div>
                <StorageSettingsPanel />
              </section>

              <p v-if="error" class="target-error settings-panel__message">{{ error }}</p>
              <p v-if="message" class="settings-panel__success settings-panel__message">{{ message }}</p>
            </div>

            <div v-if="activeTab !== 'email'" class="settings-panel__footer">
              <Button type="button" size="sm" :disabled="isFooterSaving" @click="onSave">
                <PhSpinner
                  v-if="isFooterSaving"
                  class="target-taxonomy-modal__spinner"
                  weight="bold"
                  aria-hidden="true"
                />
                <PhFloppyDisk v-else class="settings-panel__button-icon" weight="bold" aria-hidden="true" />
                <span>{{ isFooterSaving ? 'Saving' : 'Save settings' }}</span>
              </Button>
            </div>
          </template>
        </div>
      </SectionModal>
    </div>
  </Teleport>
</template>
