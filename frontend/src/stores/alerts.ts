import { defineStore } from 'pinia';
import { ref } from 'vue';
import {
  fetchSmtpSettings,
  fetchTargetAlert,
  testSmtpSettings,
  updateSmtpSettings,
  updateTargetAlert,
} from '../api';
import type { SmtpSettings, TargetAlertRules, TargetSummary } from '../types';

function defaultSmtpSettings(): SmtpSettings {
  return {
    provider: 'resend',
    host: 'smtp.resend.com',
    port: 587,
    username: 'resend',
    fromEmail: '',
    fromName: 'Netbox',
    useTls: true,
    configured: false,
    hasPassword: false,
  };
}

function defaultAlertRules(targetId: string, smtpConfigured = false): TargetAlertRules {
  return {
    targetId,
    enabled: false,
    notification: true,
    sound: true,
    email: false,
    emailTo: '',
    onDegraded: true,
    onDown: true,
    cooldownMs: 300_000,
    smtpConfigured,
  };
}

function loadErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

const SMTP_PRESETS: Record<SmtpSettings['provider'], Partial<SmtpSettings>> = {
  resend: {
    host: 'smtp.resend.com',
    port: 587,
    username: 'resend',
    useTls: true,
  },
  custom: {
    host: '',
    port: 587,
    username: '',
    useTls: true,
  },
};

export const useAlertsStore = defineStore('alerts', () => {
  const smtp = ref<SmtpSettings | null>(null);
  const smtpPassword = ref('');
  const smtpTestEmail = ref('');
  const isSavingSmtp = ref(false);
  const isTestingSmtp = ref(false);
  const smtpError = ref<string | null>(null);
  const smtpMessage = ref<string | null>(null);

  const activeTarget = ref<TargetSummary | null>(null);
  const alertForm = ref<TargetAlertRules | null>(null);
  const isLoadingAlert = ref(false);
  const isSavingAlert = ref(false);
  const alertError = ref<string | null>(null);

  async function loadSmtp(): Promise<void> {
    smtpError.value = null;
    try {
      const response = await fetchSmtpSettings();
      smtp.value = response.smtp;
      if (!smtpTestEmail.value) {
        smtpTestEmail.value = response.smtp.fromEmail;
      }
    } catch (error) {
      smtpError.value = error instanceof Error ? error.message : 'Unable to load SMTP settings';
    }
  }

  function applySmtpProvider(provider: SmtpSettings['provider']): void {
    if (!smtp.value) return;
    const preset = SMTP_PRESETS[provider];
    smtp.value = {
      ...smtp.value,
      provider,
      host: preset.host ?? smtp.value.host,
      port: preset.port ?? smtp.value.port,
      username: preset.username ?? smtp.value.username,
      useTls: preset.useTls ?? smtp.value.useTls,
    };
  }

  async function saveSmtp(): Promise<boolean> {
    if (!smtp.value) return false;
    isSavingSmtp.value = true;
    smtpError.value = null;
    smtpMessage.value = null;

    try {
      const response = await updateSmtpSettings({
        provider: smtp.value.provider,
        host: smtp.value.host,
        port: smtp.value.port,
        username: smtp.value.username,
        fromEmail: smtp.value.fromEmail,
        fromName: smtp.value.fromName,
        useTls: smtp.value.useTls,
        ...(smtpPassword.value ? { password: smtpPassword.value } : {}),
      });
      smtp.value = response.smtp;
      smtpPassword.value = '';
      smtpMessage.value = 'SMTP provider saved.';
      return true;
    } catch (error) {
      smtpError.value = error instanceof Error ? error.message : 'Unable to save SMTP settings';
      return false;
    } finally {
      isSavingSmtp.value = false;
    }
  }

  async function sendSmtpTest(): Promise<boolean> {
    if (!smtp.value) return false;
    isTestingSmtp.value = true;
    smtpError.value = null;
    smtpMessage.value = null;

    try {
      const response = await testSmtpSettings({
        provider: smtp.value.provider,
        host: smtp.value.host,
        port: smtp.value.port,
        username: smtp.value.username,
        fromEmail: smtp.value.fromEmail,
        fromName: smtp.value.fromName,
        useTls: smtp.value.useTls,
        testEmail: smtpTestEmail.value,
        ...(smtpPassword.value ? { password: smtpPassword.value } : {}),
      });
      smtpMessage.value = response.message;
      return true;
    } catch (error) {
      smtpError.value = error instanceof Error ? error.message : 'SMTP test failed';
      return false;
    } finally {
      isTestingSmtp.value = false;
    }
  }

  async function openAlertModal(target: TargetSummary): Promise<void> {
    activeTarget.value = target;
    alertError.value = null;
    isLoadingAlert.value = true;
    alertForm.value = null;

    try {
      const response = await fetchTargetAlert(target.id);
      alertForm.value = { ...response.alert };
    } catch (error) {
      alertForm.value = defaultAlertRules(target.id);
      alertError.value = loadErrorMessage(error, 'Unable to load saved alert settings');
    } finally {
      isLoadingAlert.value = false;
    }
  }

  function closeAlertModal(): void {
    activeTarget.value = null;
    alertForm.value = null;
    alertError.value = null;
  }

  async function saveAlert(): Promise<boolean> {
    if (!activeTarget.value || !alertForm.value) return false;
    isSavingAlert.value = true;
    alertError.value = null;

    try {
      const response = await updateTargetAlert(activeTarget.value.id, alertForm.value);
      alertForm.value = { ...response.alert };
      return true;
    } catch (error) {
      alertError.value = error instanceof Error ? error.message : 'Unable to save alert settings';
      return false;
    } finally {
      isSavingAlert.value = false;
    }
  }

  return {
    smtp,
    smtpPassword,
    smtpTestEmail,
    isSavingSmtp,
    isTestingSmtp,
    smtpError,
    smtpMessage,
    activeTarget,
    alertForm,
    isLoadingAlert,
    isSavingAlert,
    alertError,
    loadSmtp,
    applySmtpProvider,
    saveSmtp,
    sendSmtpTest,
    openAlertModal,
    closeAlertModal,
    saveAlert,
  };
});
