import { computed, nextTick, onUnmounted, ref, watch } from 'vue';
import { reorderTargetIds, sameTargetIdOrder } from '../targetOrder';

export const TARGET_REORDER_ID_ATTR = 'data-reorder-id';

export function useTargetDragReorder(options: {
  orderedIds: () => string[];
  onReorder: (order: string[]) => void | Promise<void>;
  disabled?: () => boolean;
}) {
  const draggingId = ref<string | null>(null);
  const dragOverId = ref<string | null>(null);
  const committedOrder = ref<string[] | null>(null);
  const isReordering = ref(false);
  let activePointerId: number | null = null;

  const previewOrder = computed(() => {
    const order = options.orderedIds();
    if (committedOrder.value) return committedOrder.value;
    if (!draggingId.value || !dragOverId.value || draggingId.value === dragOverId.value) {
      return order;
    }
    return reorderTargetIds(order, draggingId.value, dragOverId.value) ?? order;
  });

  const isDragging = computed(() => draggingId.value !== null);
  const isSettling = computed(() => committedOrder.value !== null);

  watch(
    () => options.orderedIds(),
    (order) => {
      if (!committedOrder.value) return;
      if (sameTargetIdOrder(order, committedOrder.value)) {
        committedOrder.value = null;
      }
    },
  );

  function resolveOverId(clientX: number, clientY: number): string | null {
    const elements = document.elementsFromPoint(clientX, clientY);
    for (const element of elements) {
      const row = element.closest(`[${TARGET_REORDER_ID_ATTR}]`);
      if (!row) continue;
      const id = row.getAttribute(TARGET_REORDER_ID_ATTR);
      if (id) return id;
    }
    return null;
  }

  function onPointerDown(targetId: string, event: PointerEvent): void {
    if (options.disabled?.() || event.button !== 0) return;

    event.preventDefault();
    draggingId.value = targetId;
    dragOverId.value = targetId;
    activePointerId = event.pointerId;

    const handle = event.currentTarget as HTMLElement;
    try {
      handle.setPointerCapture(event.pointerId);
    } catch {
      // Pointer capture may be unavailable in some environments.
    }

    document.body.classList.add('is-target-reordering');
    document.addEventListener('pointermove', onDocumentPointerMove);
    document.addEventListener('pointerup', onDocumentPointerUp);
    document.addEventListener('pointercancel', onDocumentPointerCancel);
  }

  function onDocumentPointerMove(event: PointerEvent): void {
    if (!draggingId.value || activePointerId !== event.pointerId) return;

    const overId = resolveOverId(event.clientX, event.clientY);
    if (overId && overId !== dragOverId.value) {
      dragOverId.value = overId;
    }
  }

  async function finishDrag(commit: boolean): Promise<void> {
    if (!draggingId.value) return;

    const draggedId = draggingId.value;
    const overId = dragOverId.value ?? draggedId;
    const nextOrder = commit ? reorderTargetIds(options.orderedIds(), draggedId, overId) : null;

    teardownListeners();
    resetDrag();

    if (!nextOrder) return;

    committedOrder.value = nextOrder;
    isReordering.value = true;

    try {
      await nextTick();
      await options.onReorder(nextOrder);
      if (committedOrder.value && sameTargetIdOrder(options.orderedIds(), committedOrder.value)) {
        committedOrder.value = null;
      }
    } catch (caught) {
      committedOrder.value = null;
      throw caught;
    } finally {
      isReordering.value = false;
    }
  }

  function onDocumentPointerUp(event: PointerEvent): void {
    if (activePointerId !== event.pointerId) return;
    void finishDrag(true);
  }

  function onDocumentPointerCancel(event: PointerEvent): void {
    if (activePointerId !== event.pointerId) return;
    void finishDrag(false);
  }

  function teardownListeners(): void {
    document.body.classList.remove('is-target-reordering');
    document.removeEventListener('pointermove', onDocumentPointerMove);
    document.removeEventListener('pointerup', onDocumentPointerUp);
    document.removeEventListener('pointercancel', onDocumentPointerCancel);
    activePointerId = null;
  }

  function resetDrag(): void {
    draggingId.value = null;
    dragOverId.value = null;
  }

  onUnmounted(() => {
    teardownListeners();
    resetDrag();
    committedOrder.value = null;
  });

  return {
    draggingId,
    dragOverId,
    previewOrder,
    isDragging,
    isSettling,
    isReordering,
    onPointerDown,
  };
}
