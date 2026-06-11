<script setup lang="ts">
import { PhFloppyDisk, PhPaperPlaneTilt, PhSpinner } from '@phosphor-icons/vue';
import { storeToRefs } from 'pinia';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { useAlertsStore } from '../../stores/alerts';

const alertsStore = useAlertsStore();
const {
  smtp,
  smtpPassword,
  smtpTestEmail,
  isSavingSmtp,
  isTestingSmtp,
  smtpError,
  smtpMessage,
} = storeToRefs(alertsStore);
</script>

<template>
  <div v-if="smtp" class="settings-panel__smtp">
    <p class="settings-panel__hint">
      Credentials are encrypted before they are stored in the local database. Resend works with host
      <code>smtp.resend.com</code>, username <code>resend</code>, and your API key as the password.
    </p>

    <label class="settings-panel__field">
      <Label>Provider</Label>
      <select
        :value="smtp.provider"
        @change="alertsStore.applySmtpProvider(($event.target as HTMLSelectElement).value as 'resend' | 'custom')"
      >
        <option value="resend">Resend</option>
        <option value="custom">Custom SMTP</option>
      </select>
    </label>

    <label class="settings-panel__field">
      <Label>SMTP host</Label>
      <input v-model="smtp.host" type="text" />
    </label>

    <div class="settings-panel__grid">
      <label class="settings-panel__field">
        <Label>Port</Label>
        <input v-model.number="smtp.port" type="number" min="1" max="65535" />
      </label>
      <label class="settings-panel__field">
        <Label>Username</Label>
        <input v-model="smtp.username" type="text" />
      </label>
    </div>

    <label class="settings-panel__field">
      <Label>{{ smtp.hasPassword ? 'SMTP password or API key' : 'SMTP password or API key (required)' }}</Label>
      <input
        v-model="smtpPassword"
        type="password"
        autocomplete="new-password"
        :placeholder="smtp.hasPassword ? 'Leave blank to keep saved password' : 'Enter API key or password'"
      />
    </label>

    <div class="settings-panel__grid">
      <label class="settings-panel__field">
        <Label>From email</Label>
        <input v-model="smtp.fromEmail" type="email" />
      </label>
      <label class="settings-panel__field">
        <Label>From name</Label>
        <input v-model="smtp.fromName" type="text" />
      </label>
    </div>

    <div class="settings-panel__row">
      <div>
        <strong>Use TLS</strong>
      </div>
      <Switch v-model="smtp.useTls" />
    </div>

    <label class="settings-panel__field">
      <Label>Test recipient</Label>
      <input v-model="smtpTestEmail" type="email" placeholder="you@example.com" />
    </label>

    <p v-if="smtpError" class="target-error">{{ smtpError }}</p>
    <p v-if="smtpMessage" class="settings-panel__success">{{ smtpMessage }}</p>

    <div class="settings-panel__actions">
      <Button type="button" variant="ghost" size="sm" :disabled="isTestingSmtp" @click="alertsStore.sendSmtpTest()">
        <PhSpinner v-if="isTestingSmtp" class="target-taxonomy-modal__spinner" weight="bold" aria-hidden="true" />
        <PhPaperPlaneTilt v-else class="settings-panel__button-icon" weight="bold" aria-hidden="true" />
        <span>{{ isTestingSmtp ? 'Sending test' : 'Send test email' }}</span>
      </Button>
      <Button type="button" variant="ghost" size="sm" :disabled="isSavingSmtp" @click="alertsStore.saveSmtp()">
        <PhSpinner v-if="isSavingSmtp" class="target-taxonomy-modal__spinner" weight="bold" aria-hidden="true" />
        <PhFloppyDisk v-else class="settings-panel__button-icon" weight="bold" aria-hidden="true" />
        <span>{{ isSavingSmtp ? 'Saving SMTP' : 'Save SMTP provider' }}</span>
      </Button>
    </div>
  </div>
</template>
