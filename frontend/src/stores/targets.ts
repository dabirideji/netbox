import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import {
  checkTargetNow,
  createTarget,
  deleteTarget,
  fetchTargets,
  patchTarget,
  previewTargetCheck,
  reorderTargets as reorderTargetsApi,
  setTargetFavorite as setTargetFavoriteApi,
} from '../api';
import { usePersonalisationStore } from './personalisation';
import { useMonitorStore } from './monitor';
import { sortTargetsBySortOrder } from '../targetOrder';
import { defaultTargetColor, normalizeTargetColor, targetColorForSource } from '../targetColors';
import type {
  MonitorTarget,
  TargetPayload,
  TargetPreviewCheckResponse,
  TargetProtocol,
  TargetScope,
  TargetType,
} from '../types';

export { targetColor, targetColorForSource } from '../targetColors';

export const TARGET_PROTOCOLS: TargetProtocol[] = ['icmp', 'http', 'https', 'tcp', 'dns'];
export const TARGET_TYPES: TargetType[] = ['host', 'website', 'api', 'port', 'dns'];
export const TARGET_SCOPES: TargetScope[] = ['external', 'gateway'];

export function defaultIntervalMs(protocol: TargetProtocol): number {
  if (protocol === 'icmp') return 1_000;
  return 5_000;
}

export function defaultTimeoutMs(protocol: TargetProtocol): number {
  switch (protocol) {
    case 'icmp':
      return 900;
    case 'http':
    case 'https':
      return 10_000;
    case 'tcp':
      return 5_000;
    case 'dns':
      return 3_000;
  }
}

export interface TargetFormState {
  id: string | null;
  label: string;
  type: TargetType;
  protocol: TargetProtocol;
  scope: TargetScope;
  group: string;
  environment: string;
  enabled: boolean;
  intervalMs: number;
  timeoutMs: number;
  url: string;
  method: string;
  expectedStatus: number;
  keyword: string;
  host: string;
  port: number;
  recordName: string;
  recordType: string;
  expectedValue: string;
  color: string;
}

export const useTargetsStore = defineStore('targets', () => {
  const targets = ref<MonitorTarget[]>([]);
  const form = ref<TargetFormState>(defaultTargetForm());
  const isLoading = ref(false);
  const isSaving = ref(false);
  const checkingId = ref<string | null>(null);
  const isTestingForm = ref(false);
  const isReordering = ref(false);
  const favoritingId = ref<string | null>(null);
  const error = ref<string | null>(null);

  const isEditing = computed(() => form.value.id !== null);
  const sortedTargets = computed(() => sortTargetsBySortOrder(targets.value));

  async function loadTargets(): Promise<void> {
    isLoading.value = true;
    error.value = null;
    try {
      targets.value = (await fetchTargets()).targets;
      usePersonalisationStore().syncTargetTaxonomyFromTargets(targets.value);
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : 'Unable to load targets';
    } finally {
      isLoading.value = false;
    }
  }

  function applyTargets(nextTargets: MonitorTarget[]): void {
    targets.value = nextTargets;
    usePersonalisationStore().syncTargetTaxonomyFromTargets(nextTargets);
  }

  function resetForm(): void {
    form.value = defaultTargetForm(targets.value.length);
    error.value = null;
  }

  function editTarget(target: MonitorTarget): void {
    const config = target.config;
    form.value = {
      id: target.id,
      label: target.label,
      type: target.type,
      protocol: target.protocol,
      scope: target.scope,
      group: target.group,
      environment: target.environment,
      enabled: target.enabled,
      intervalMs: target.intervalMs,
      timeoutMs: target.timeoutMs,
      url: stringValue(config.url, target.protocol === 'http' || target.protocol === 'https' ? target.host : ''),
      method: stringValue(config.method, 'GET'),
      expectedStatus: numberValue(config.expectedStatus, 200),
      keyword: stringValue(config.keyword, ''),
      host: stringValue(config.host, target.host),
      port: numberValue(config.port, 443),
      recordName: stringValue(config.name, target.host),
      recordType: stringValue(config.recordType, 'A'),
      expectedValue: stringValue(config.expectedValue, ''),
      color: targetColorForSource(config, target.id),
    };
  }

  async function saveForm(): Promise<void> {
    isSaving.value = true;
    error.value = null;
    try {
      const payload = formToPayload(form.value);
      const saved = form.value.id
        ? (await patchTarget(form.value.id, payload)).target
        : (await createTarget(payload)).target;
      upsertTarget(saved);
      usePersonalisationStore().registerTargetTaxonomy(saved.group, saved.environment);
      resetForm();
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : 'Unable to save target';
    } finally {
      isSaving.value = false;
    }
  }

  async function removeTarget(targetId: string): Promise<void> {
    isSaving.value = true;
    error.value = null;
    try {
      await deleteTarget(targetId);
      targets.value = targets.value.filter((target) => target.id !== targetId);
      usePersonalisationStore().syncTargetTaxonomyFromTargets(targets.value);
      if (form.value.id === targetId) resetForm();
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : 'Unable to delete target';
    } finally {
      isSaving.value = false;
    }
  }

  async function testForm(): Promise<TargetPreviewCheckResponse> {
    isTestingForm.value = true;
    error.value = null;
    try {
      return await previewTargetCheck(formToPayload(form.value));
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : 'Unable to test target';
      error.value = message;
      throw caught;
    } finally {
      isTestingForm.value = false;
    }
  }

  async function runCheckNow(targetId: string): Promise<void> {
    checkingId.value = targetId;
    error.value = null;
    try {
      await checkTargetNow(targetId);
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : 'Unable to run target check';
    } finally {
      checkingId.value = null;
    }
  }

  function upsertTarget(target: MonitorTarget): void {
    const index = targets.value.findIndex((candidate) => candidate.id === target.id);
    if (index === -1) {
      targets.value = [...targets.value, target];
      return;
    }
    targets.value = targets.value.map((candidate) => (candidate.id === target.id ? target : candidate));
  }

  async function setTargetFavorite(targetId: string, favorite: boolean): Promise<boolean> {
    favoritingId.value = targetId;
    error.value = null;

    const previous = targets.value.find((target) => target.id === targetId);
    if (previous) {
      upsertTarget({ ...previous, isFavorite: favorite });
      useMonitorStore().setTargetFavorite(targetId, favorite);
    }

    try {
      const response = await setTargetFavoriteApi(targetId, favorite);
      upsertTarget(response.target);
      useMonitorStore().setTargetFavorite(targetId, response.target.isFavorite ?? favorite);
      return true;
    } catch (caught) {
      if (previous) {
        upsertTarget(previous);
        useMonitorStore().setTargetFavorite(targetId, previous.isFavorite ?? false);
      }
      error.value = caught instanceof Error ? caught.message : 'Unable to update favorite';
      return false;
    } finally {
      favoritingId.value = null;
    }
  }

  async function reorderTargets(order: string[]): Promise<void> {
    const previous = [...targets.value];
    error.value = null;
    isReordering.value = true;

    const byId = new Map(targets.value.map((target) => [target.id, target]));
    targets.value = order.flatMap((id, index) => {
      const target = byId.get(id);
      return target ? [{ ...target, sortOrder: index }] : [];
    });
    useMonitorStore().reorderSummaryTargets(order);

    try {
      const response = await reorderTargetsApi(order);
      applyTargets(response.targets);
      useMonitorStore().reorderSummaryTargets(response.targets.map((target) => target.id));
    } catch (caught) {
      targets.value = previous;
      useMonitorStore().reorderSummaryTargets(previous.map((target) => target.id));
      error.value = caught instanceof Error ? caught.message : 'Unable to reorder targets';
      throw caught;
    } finally {
      isReordering.value = false;
    }
  }

  return {
    targets,
    sortedTargets,
    form,
    isEditing,
    isLoading,
    isSaving,
    checkingId,
    isTestingForm,
    isReordering,
    favoritingId,
    error,
    loadTargets,
    applyTargets,
    resetForm,
    editTarget,
    saveForm,
    testForm,
    removeTarget,
    reorderTargets,
    setTargetFavorite,
    runCheckNow,
  };
});

function defaultTargetForm(existingCount = 0): TargetFormState {
  const protocol: TargetProtocol = 'icmp';
  return {
    id: null,
    label: '',
    type: 'host',
    protocol,
    scope: 'external',
    group: 'Default',
    environment: 'local',
    enabled: true,
    intervalMs: defaultIntervalMs(protocol),
    timeoutMs: defaultTimeoutMs(protocol),
    url: 'https://example.com',
    method: 'GET',
    expectedStatus: 200,
    keyword: '',
    host: '1.1.1.1',
    port: 443,
    recordName: 'example.com',
    recordType: 'A',
    expectedValue: '',
    color: defaultTargetColor(existingCount),
  };
}

export function formToPayload(value: TargetFormState): TargetPayload {
  const config = {
    ...protocolConfig(value),
    color: normalizeTargetColor(value.color, 0),
  };
  return {
    label: value.label,
    type: value.type,
    protocol: value.protocol,
    scope: value.scope,
    group: value.group,
    environment: value.environment,
    enabled: value.enabled,
    intervalMs: value.intervalMs,
    timeoutMs: value.timeoutMs,
    config,
  };
}

function protocolConfig(value: TargetFormState): Record<string, unknown> {
  if (value.protocol === 'http' || value.protocol === 'https') {
    return {
      url: value.url,
      method: value.method,
      expectedStatus: value.expectedStatus,
      keyword: value.keyword || undefined,
      headers: {},
    };
  }

  if (value.protocol === 'tcp') {
    return {
      host: value.host,
      port: value.port,
    };
  }

  if (value.protocol === 'dns') {
    return {
      name: value.recordName,
      recordType: value.recordType,
      expectedValue: value.expectedValue || undefined,
    };
  }

  return { host: value.host };
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === 'string' ? value : fallback;
}

function numberValue(value: unknown, fallback: number): number {
  return typeof value === 'number' ? value : fallback;
}
