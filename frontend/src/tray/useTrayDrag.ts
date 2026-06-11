import { onUnmounted, ref } from 'vue';

function isTrayDesktop(): boolean {
  return typeof window !== 'undefined' && Boolean(window.netboxDesktop?.desktop);
}

/** Drag the frameless Electron tray popup by its header handle. */
export function useTrayDrag() {
  const dragging = ref(false);
  let activeTarget: HTMLElement | null = null;

  function endDrag(event?: PointerEvent): void {
    if (!dragging.value) {
      return;
    }

    dragging.value = false;
    window.netboxDesktop?.endTrayDrag?.();

    if (activeTarget && event?.pointerId !== undefined) {
      try {
        activeTarget.releasePointerCapture(event.pointerId);
      } catch {
        // Pointer capture may already be released.
      }
    }

    activeTarget = null;
  }

  function onPointerDown(event: PointerEvent): void {
    if (!isTrayDesktop() || event.button !== 0) {
      return;
    }

    dragging.value = true;
    activeTarget = event.currentTarget as HTMLElement;
    activeTarget.setPointerCapture(event.pointerId);
    window.netboxDesktop?.startTrayDrag?.(event.screenX, event.screenY);
  }

  function onPointerMove(event: PointerEvent): void {
    if (!dragging.value || !isTrayDesktop()) {
      return;
    }

    window.netboxDesktop?.moveTrayDrag?.(event.screenX, event.screenY);
  }

  function onPointerUp(event: PointerEvent): void {
    endDrag(event);
  }

  function onPointerCancel(event: PointerEvent): void {
    endDrag(event);
  }

  onUnmounted(() => {
    endDrag();
  });

  return {
    dragging,
    onPointerDown,
    onPointerMove,
    onPointerUp,
    onPointerCancel,
  };
}
