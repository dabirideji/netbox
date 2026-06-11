import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  fetchSmtpSettings,
  fetchTargetAlert,
  testSmtpSettings,
  updateSmtpSettings,
  updateTargetAlert,
} from '../api';
import { useAlertsStore } from './alerts';

vi.mock('../api', () => ({
  fetchSmtpSettings: vi.fn(),
  fetchTargetAlert: vi.fn(),
  updateSmtpSettings: vi.fn(),
  testSmtpSettings: vi.fn(),
  updateTargetAlert: vi.fn(),
}));

describe('useAlertsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('loads alert modal state for one target', async () => {
    vi.mocked(fetchTargetAlert).mockResolvedValue({
      alert: {
        targetId: 'api-1',
        enabled: false,
        notification: true,
        sound: true,
        email: false,
        emailTo: '',
        onDegraded: true,
        onDown: true,
        cooldownMs: 300_000,
        smtpConfigured: true,
      },
    });

    const store = useAlertsStore();
    await store.openAlertModal({
      id: 'api-1',
      label: 'API',
    } as never);

    expect(store.activeTarget?.id).toBe('api-1');
    expect(store.alertForm?.smtpConfigured).toBe(true);
  });

  it('saves alert rules for the active target', async () => {
    vi.mocked(fetchTargetAlert).mockResolvedValue({
      alert: {
        targetId: 'api-1',
        enabled: true,
        notification: true,
        sound: false,
        email: false,
        emailTo: '',
        onDegraded: true,
        onDown: true,
        cooldownMs: 300_000,
        smtpConfigured: true,
      },
    });
    vi.mocked(updateTargetAlert).mockResolvedValue({
      alert: {
        targetId: 'api-1',
        enabled: true,
        notification: true,
        sound: true,
        email: false,
        emailTo: '',
        onDegraded: true,
        onDown: true,
        cooldownMs: 300_000,
        smtpConfigured: true,
      },
    });

    const store = useAlertsStore();
    await store.openAlertModal({ id: 'api-1', label: 'API' } as never);
    store.alertForm!.sound = true;

    const saved = await store.saveAlert();

    expect(saved).toBe(true);
    expect(updateTargetAlert).toHaveBeenCalledWith('api-1', expect.objectContaining({ sound: true }));
  });

  it('applies provider presets and sends SMTP tests', async () => {
    vi.mocked(fetchSmtpSettings).mockResolvedValue({
      smtp: {
        provider: 'custom',
        host: '',
        port: 587,
        username: '',
        fromEmail: '',
        fromName: 'Netbox',
        useTls: true,
        configured: false,
        hasPassword: false,
      },
    });
    vi.mocked(testSmtpSettings).mockResolvedValue({ ok: true, message: 'sent' });

    const store = useAlertsStore();
    await store.loadSmtp();
    store.applySmtpProvider('resend');
    store.smtpPassword = 're_test';
    store.smtpTestEmail = 'ops@example.com';

    const sent = await store.sendSmtpTest();

    expect(sent).toBe(true);
    expect(store.smtp?.host).toBe('smtp.resend.com');
    expect(store.smtpMessage).toBe('sent');
  });

  it('persists SMTP settings', async () => {
    vi.mocked(fetchSmtpSettings).mockResolvedValue({
      smtp: {
        provider: 'resend',
        host: 'smtp.resend.com',
        port: 587,
        username: 'resend',
        fromEmail: 'alerts@example.com',
        fromName: 'Netbox',
        useTls: true,
        configured: false,
        hasPassword: false,
      },
    });
    vi.mocked(updateSmtpSettings).mockResolvedValue({
      smtp: {
        provider: 'resend',
        host: 'smtp.resend.com',
        port: 587,
        username: 'resend',
        fromEmail: 'alerts@example.com',
        fromName: 'Netbox',
        useTls: true,
        configured: true,
        hasPassword: true,
      },
    });

    const store = useAlertsStore();
    await store.loadSmtp();
    store.smtpPassword = 're_test';

    const saved = await store.saveSmtp();

    expect(saved).toBe(true);
    expect(store.smtp?.configured).toBe(true);
  });
});
