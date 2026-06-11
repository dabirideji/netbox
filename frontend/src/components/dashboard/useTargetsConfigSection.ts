import { computed, nextTick, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { useTargetDragReorder } from '../../composables/useTargetDragReorder';
import { reorderTargetsByIds } from '../../targetOrder';
import { canDeleteTaxonomyValue } from '../../targetTaxonomy';
import { TARGETS_PAGE_SIZE } from '../../liveChecks';
import {
  defaultIntervalMs,
  defaultTimeoutMs,
  usePersonalisationStore,
  useTargetsStore,
} from '../../stores';
import type { MonitorTarget, TargetPreviewCheckResponse, TargetScope } from '../../types';

export function useTargetsConfigSection() {
  const targetsStore = useTargetsStore();
  const personalisation = usePersonalisationStore();
  const { targetsPage, targetGroups, targetEnvironments } = storeToRefs(personalisation);
  const {
    sortedTargets,
    form,
    isEditing,
    isLoading,
    isSaving,
    checkingId,
    isTestingForm,
    isReordering,
    error,
  } = storeToRefs(targetsStore);

  const expandedTargetIds = ref<Set<string>>(new Set());
  const targetListScrollRef = ref<HTMLElement | null>(null);
  const deleteSourceModalOpen = ref(false);
  const pendingDeleteSource = ref<MonitorTarget | null>(null);
  const deletingSource = ref(false);
  const testModalOpen = ref(false);
  const testResult = ref<TargetPreviewCheckResponse | null>(null);
  const testError = ref<string | null>(null);

  const {
    draggingId,
    previewOrder,
    isSettling,
    onPointerDown,
  } = useTargetDragReorder({
    orderedIds: () => sortedTargets.value.map((target) => target.id),
    onReorder: (order) => targetsStore.reorderTargets(order),
    disabled: () => isLoading.value || isSaving.value || isReordering.value,
  });

  const displayTargets = computed(() => {
    const targets = sortedTargets.value;
    const reordered = reorderTargetsByIds(targets, previewOrder.value);
    const start = targetsPage.value * TARGETS_PAGE_SIZE;
    return reordered.slice(start, start + TARGETS_PAGE_SIZE);
  });

  const protocolLabel = computed(() => form.value.protocol.toUpperCase());

  const scopeCounts = computed(() => {
    const counts = { gateway: 0, external: 0 };
    for (const target of sortedTargets.value) {
      counts[target.scope] += 1;
    }
    return counts;
  });

  function scopeMetaLabel(scope: TargetScope): string {
    const count = scopeCounts.value[scope];
    if (!count) return '';
    const noun = count === 1 ? 'source' : 'sources';
    return `${count} ${noun}`;
  }

  function targetSubtitle(target: MonitorTarget): string {
    return `${target.protocol.toUpperCase()} · ${target.group} · ${target.environment}`;
  }

  const useGroupDropdown = computed(() => targetGroups.value.length > 0);
  const useEnvironmentDropdown = computed(() => targetEnvironments.value.length > 0);

  function canDeleteGroup(value: string): boolean {
    return canDeleteTaxonomyValue(sortedTargets.value, 'group', value);
  }

  function canDeleteEnvironment(value: string): boolean {
    return canDeleteTaxonomyValue(sortedTargets.value, 'environment', value);
  }

  async function createGroupValue(value: string): Promise<void> {
    personalisation.addTargetGroup(value);
    form.value.group = value;
    await personalisation.syncPreferencesNow();
  }

  async function createEnvironmentValue(value: string): Promise<void> {
    personalisation.addTargetEnvironment(value);
    form.value.environment = value;
    await personalisation.syncPreferencesNow();
  }

  async function removeGroupValue(value: string): Promise<void> {
    if (!canDeleteGroup(value)) return;
    personalisation.removeTargetGroup(value);
    if (form.value.group === value) {
      form.value.group = targetGroups.value[0] ?? 'Default';
    }
    await personalisation.syncPreferencesNow();
  }

  async function removeEnvironmentValue(value: string): Promise<void> {
    if (!canDeleteEnvironment(value)) return;
    personalisation.removeTargetEnvironment(value);
    if (form.value.environment === value) {
      form.value.environment = targetEnvironments.value[0] ?? 'local';
    }
    await personalisation.syncPreferencesNow();
  }

  function openDeleteSourceModal(target: MonitorTarget): void {
    if (deletingSource.value) return;
    pendingDeleteSource.value = target;
    deleteSourceModalOpen.value = true;
  }

  function closeDeleteSourceModal(): void {
    if (deletingSource.value) return;
    deleteSourceModalOpen.value = false;
    pendingDeleteSource.value = null;
  }

  async function confirmDeleteSource(): Promise<void> {
    const target = pendingDeleteSource.value;
    if (!target || deletingSource.value) return;

    deletingSource.value = true;
    try {
      await targetsStore.removeTarget(target.id);
      deleteSourceModalOpen.value = false;
      pendingDeleteSource.value = null;
    } finally {
      deletingSource.value = false;
    }
  }

  function isTargetExpanded(targetId: string): boolean {
    return expandedTargetIds.value.has(targetId);
  }

  function targetToggleLabel(target: MonitorTarget): string {
    return isTargetExpanded(target.id)
      ? `Collapse ${target.label}`
      : `Expand ${target.label}`;
  }

  async function toggleTarget(targetId: string): Promise<void> {
    const wasExpanded = expandedTargetIds.value.has(targetId);
    const next = new Set(expandedTargetIds.value);
    if (next.has(targetId)) {
      next.delete(targetId);
    } else {
      next.add(targetId);
    }
    expandedTargetIds.value = next;

    if (!wasExpanded && next.has(targetId)) {
      await nextTick();
      targetListScrollRef.value
        ?.querySelector<HTMLElement>(`[data-target-id="${targetId}"]`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  async function expandTarget(targetId: string): Promise<void> {
    if (expandedTargetIds.value.has(targetId)) return;
    expandedTargetIds.value = new Set([...expandedTargetIds.value, targetId]);
    await nextTick();
    targetListScrollRef.value
      ?.querySelector<HTMLElement>(`[data-target-id="${targetId}"]`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  watch(
    () => form.value.id,
    (targetId) => {
      if (targetId) expandTarget(targetId);
    },
  );

  watch(
    sortedTargets,
    (targets) => {
      personalisation.syncTargetTaxonomyFromTargets(targets);
    },
    { immediate: true },
  );

  watch(
    () => sortedTargets.value.length,
    (total) => {
      const maxPage = Math.max(0, Math.ceil(total / TARGETS_PAGE_SIZE) - 1);
      if (targetsPage.value > maxPage) {
        personalisation.setTargetsPage(maxPage);
      }
    },
  );

  watch(
    () => form.value.protocol,
    (protocol) => {
      if (isEditing.value) return;
      form.value.intervalMs = defaultIntervalMs(protocol);
      form.value.timeoutMs = defaultTimeoutMs(protocol);
    },
  );

  watch(
    () => form.value.type,
    (type) => {
      if (isEditing.value || type !== 'api') return;
      if (form.value.protocol !== 'http' && form.value.protocol !== 'https') return;

      try {
        const parsed = new URL(form.value.url);
        if (parsed.pathname && parsed.pathname !== '/') return;
        parsed.pathname = '/health';
        form.value.url = parsed.toString();
      } catch {
        // Ignore invalid URLs while the field is being edited.
      }
    },
  );

  function closeTestModal(): void {
    testModalOpen.value = false;
    testResult.value = null;
    testError.value = null;
  }

  async function runFormTest(): Promise<void> {
    testModalOpen.value = true;
    testResult.value = null;
    testError.value = null;
    try {
      testResult.value = await targetsStore.testForm();
    } catch (caught) {
      testError.value = caught instanceof Error ? caught.message : 'Unable to test target';
    }
  }

  async function addTargetFromTest(): Promise<void> {
    closeTestModal();
    await targetsStore.saveForm();
  }

  return {
    targetsStore,
    personalisation,
    targetsPage,
    targetGroups,
    targetEnvironments,
    sortedTargets,
    form,
    isEditing,
    isLoading,
    isSaving,
    checkingId,
    isTestingForm,
    isReordering,
    error,
    draggingId,
    isSettling,
    onPointerDown,
    testModalOpen,
    testResult,
    testError,
    targetListScrollRef,
    deleteSourceModalOpen,
    pendingDeleteSource,
    deletingSource,
    displayTargets,
    protocolLabel,
    scopeCounts,
    scopeMetaLabel,
    targetSubtitle,
    useGroupDropdown,
    useEnvironmentDropdown,
    canDeleteGroup,
    canDeleteEnvironment,
    createGroupValue,
    createEnvironmentValue,
    removeGroupValue,
    removeEnvironmentValue,
    openDeleteSourceModal,
    closeDeleteSourceModal,
    confirmDeleteSource,
    closeTestModal,
    runFormTest,
    addTargetFromTest,
    isTargetExpanded,
    targetToggleLabel,
    toggleTarget,
    TARGETS_PAGE_SIZE,
  };
}
