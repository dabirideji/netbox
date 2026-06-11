<script setup lang="ts">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { useStorageStore } from '../../stores/storage';

const storageStore = useStorageStore();
const { settings, stats } = storeToRefs(storageStore);

const maxDatabaseGb = computed({
  get: () => {
    const bytes = settings.value?.limits.maxDatabaseBytes ?? 0;
    return Math.round((bytes / (1024 * 1024 * 1024)) * 100) / 100;
  },
  set: (value: number) => {
    if (!settings.value || !Number.isFinite(value)) return;
    const gb = Math.max(0.001, value);
    settings.value.limits.maxDatabaseBytes = Math.round(gb * 1024 * 1024 * 1024);
  },
});

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}
</script>

<template>
  <div v-if="settings" class="settings-panel__storage">
    <div class="settings-panel__row">
      <div>
        <strong>Auto prune</strong>
        <p class="settings-panel__hint">Delete oldest records when a limit is reached.</p>
      </div>
      <Switch v-model="settings.autoPrune" />
    </div>

    <label class="settings-panel__field">
      <Label>Max database size (GB)</Label>
      <input v-model.number="maxDatabaseGb" type="number" min="0.001" max="100" step="0.1" />
    </label>

    <label class="settings-panel__field">
      <Label>Max incidents</Label>
      <input v-model.number="settings.limits.maxIncidents" type="number" min="1" max="10000000" step="1000" />
    </label>

    <label class="settings-panel__field">
      <Label>Max ping samples</Label>
      <input v-model.number="settings.limits.maxPingSamples" type="number" min="1000" max="10000000" step="1000" />
    </label>

    <label class="settings-panel__field">
      <Label>Max speed tests</Label>
      <input v-model.number="settings.limits.maxSpeedTests" type="number" min="1" max="100000" step="10" />
    </label>

    <dl v-if="stats" class="settings-panel__stats">
      <div>
        <dt>Database used</dt>
        <dd>
          {{ formatBytes(stats.usage.databaseBytes) }}
          /
          {{ formatBytes(stats.limits.maxDatabaseBytes) }}
        </dd>
      </div>
      <div>
        <dt>Incidents stored</dt>
        <dd>
          {{ stats.usage.incidents.toLocaleString() }}
          /
          {{ stats.limits.maxIncidents.toLocaleString() }}
        </dd>
      </div>
      <div>
        <dt>Ping samples</dt>
        <dd>
          {{ stats.usage.pingSamples.toLocaleString() }}
          /
          {{ stats.limits.maxPingSamples.toLocaleString() }}
        </dd>
      </div>
      <div>
        <dt>Speed tests</dt>
        <dd>
          {{ stats.usage.speedTests.toLocaleString() }}
          /
          {{ stats.limits.maxSpeedTests.toLocaleString() }}
        </dd>
      </div>
    </dl>
  </div>
  <p v-else class="settings-panel__hint">Storage settings are loading…</p>
</template>
