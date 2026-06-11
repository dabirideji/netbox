<script setup lang="ts">
import { PhFloppyDisk, PhSpinner } from '@phosphor-icons/vue';
import { computed, watch } from 'vue';
import { storeToRefs } from 'pinia';
import SmtpSettingsPanel from './settings/SmtpSettingsPanel.vue';
import { Button } from './ui/button';
import { Label } from './ui/label';
import { SectionModal } from './ui/section-modal';
import { Switch } from './ui/switch';
import { requestNotificationPermission } from '../composables/useAlertNotifications';
import { useAlertsStore } from '../stores/alerts';
import { useSettingsStore } from '../stores/settings';
import { useStorageStore } from '../stores/storage';

const settingsStore = useSettingsStore();
const alertsStore = useAlertsStore();
const storageStore = useStorageStore();

const { isOpen, platformAlerts, isLoading, isSaving, error, message } = storeToRefs(settingsStore);
const { stats: storageStats } = storeToRefs(storageStore);

const cooldownMinutes = computed({
  get: () => Math.round(platformAlerts.value.defaultCooldownMs / 60_000),
  set: (value: number) => {
    const minutes = Number.isFinite(value) ? Math.max(1, Math.min(60, value)) : 5;
    platformAlerts.value.defaultCooldownMs = minutes * 60_000;
  },
});

watch(isOpen, (open) => {
  if (!open) return;
  void alertsStore.loadSmtp();
  void storageStore.loadStats();
});

async function onSave(): Promise<void> {
  if (platformAlerts.value.defaultNotification) {
    await requestNotificationPermission();
  }
  await settingsStore.savePlatform();
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="global-settings-modal">
      <SectionModal
        mode="modal"
        eyebrow="Platform"
        title="Settings"
        @close="settingsStore.close()"
      >
        <div class="settings-panel">
          <p v-if="isLoading" class="target-test-modal__loading">
            <PhSpinner class="target-test-modal__spinner" weight="bold" aria-hidden="true" />
            <span>Loading settings</span>
          </p>

          <template v-else>
            <section class="settings-panel__section">
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

            <section class="settings-panel__section">
              <div class="settings-panel__section-head">
                <h3>Email delivery</h3>
                <p class="settings-panel__hint">Shared SMTP provider used by all email alerts.</p>
              </div>
              <SmtpSettingsPanel />
            </section>

            <section class="settings-panel__section">
              <div class="settings-panel__section-head">
                <h3>Storage</h3>
                <p class="settings-panel__hint">Local database retention for monitor history.</p>
              </div>

              <dl v-if="storageStats" class="settings-panel__stats">
                <div>
                  <dt>Auto prune</dt>
                  <dd>{{ storageStats.autoPrune ? 'Enabled' : 'Disabled' }}</dd>
                </div>
                <div>
                  <dt>Database size</dt>
                  <dd>
                    {{ formatBytes(storageStats.usage.databaseBytes) }}
                    /
                    {{ formatBytes(storageStats.limits.maxDatabaseBytes) }}
                  </dd>
                </div>
                <div>
                  <dt>Incidents</dt>
                  <dd>
                    {{ storageStats.usage.incidents.toLocaleString() }}
                    /
                    {{ storageStats.limits.maxIncidents.toLocaleString() }}
                  </dd>
                </div>
                <div>
                  <dt>Ping samples</dt>
                  <dd>
                    {{ storageStats.usage.pingSamples.toLocaleString() }}
                    /
                    {{ storageStats.limits.maxPingSamples.toLocaleString() }}
                  </dd>
                </div>
                <div>
                  <dt>Speed tests</dt>
                  <dd>
                    {{ storageStats.usage.speedTests.toLocaleString() }}
                    /
                    {{ storageStats.limits.maxSpeedTests.toLocaleString() }}
                  </dd>
                </div>
              </dl>
              <p v-else class="settings-panel__hint">Storage stats are loading…</p>
            </section>

            <p v-if="error" class="target-error">{{ error }}</p>
            <p v-if="message" class="settings-panel__success">{{ message }}</p>

            <div class="settings-panel__footer">
              <Button type="button" variant="ghost" size="sm" @click="settingsStore.close()">
                Close
              </Button>
              <Button type="button" size="sm" :disabled="isSaving" @click="onSave">
                <PhSpinner v-if="isSaving" class="target-taxonomy-modal__spinner" weight="bold" aria-hidden="true" />
                <PhFloppyDisk v-else class="settings-panel__button-icon" weight="bold" aria-hidden="true" />
                <span>{{ isSaving ? 'Saving' : 'Save settings' }}</span>
              </Button>
            </div>
          </template>
        </div>
      </SectionModal>
    </div>
  </Teleport>
</template>
