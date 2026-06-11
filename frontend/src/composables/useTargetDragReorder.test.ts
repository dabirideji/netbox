import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { defineComponent, nextTick } from 'vue';
import { TARGET_REORDER_ID_ATTR, useTargetDragReorder } from './useTargetDragReorder';

function mountComposable<T>(composable: () => T): T {
  let result!: T;
  const Comp = defineComponent({
    setup() {
      result = composable();
      return () => null;
    },
  });
  mount(Comp);
  return result;
}

function createHandle(): HTMLButtonElement {
  const handle = document.createElement('button');
  handle.setPointerCapture = vi.fn();
  document.body.appendChild(handle);
  return handle;
}

describe('useTargetDragReorder', () => {
  it('previews order while dragging before drop commits', async () => {
    const onReorder = vi.fn();
    const orderedIds = vi.fn(() => ['a', 'b', 'c']);
    const { draggingId, dragOverId, previewOrder, onPointerDown } = mountComposable(() =>
      useTargetDragReorder({
        orderedIds,
        onReorder,
      }),
    );

    const handle = createHandle();

    onPointerDown('c', {
      button: 0,
      pointerId: 1,
      currentTarget: handle,
      preventDefault: vi.fn(),
    } as unknown as PointerEvent);

    expect(draggingId.value).toBe('c');
    expect(previewOrder.value).toEqual(['a', 'b', 'c']);

    dragOverId.value = 'a';
    await nextTick();

    expect(previewOrder.value).toEqual(['c', 'a', 'b']);
    expect(onReorder).not.toHaveBeenCalled();

    document.body.removeChild(handle);
    document.body.classList.remove('is-target-reordering');
  });

  it('keeps committed order after release until the store matches', async () => {
    const orderedIds = vi.fn(() => ['a', 'b', 'c']);
    let resolveReorder: (() => void) | undefined;
    const onReorder = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolveReorder = resolve;
        }),
    );

    const { previewOrder, isSettling, onPointerDown, dragOverId } = mountComposable(() =>
      useTargetDragReorder({ orderedIds, onReorder }),
    );

    const handle = createHandle();
    onPointerDown('c', {
      button: 0,
      pointerId: 3,
      currentTarget: handle,
      preventDefault: vi.fn(),
    } as unknown as PointerEvent);

    dragOverId.value = 'a';
    await nextTick();
    expect(previewOrder.value).toEqual(['c', 'a', 'b']);

    document.dispatchEvent(
      new PointerEvent('pointerup', { pointerId: 3, bubbles: true }),
    );
    await nextTick();

    expect(isSettling.value).toBe(true);
    expect(previewOrder.value).toEqual(['c', 'a', 'b']);
    expect(orderedIds()).toEqual(['a', 'b', 'c']);

    orderedIds.mockReturnValue(['c', 'a', 'b']);
    resolveReorder?.();
    await nextTick();

    expect(onReorder).toHaveBeenCalledWith(['c', 'a', 'b']);
    expect(isSettling.value).toBe(false);
    expect(previewOrder.value).toEqual(['c', 'a', 'b']);

    document.body.removeChild(handle);
    document.body.classList.remove('is-target-reordering');
  });

  it('updates hover target while the pointer moves', () => {
    const row = document.createElement('article');
    row.setAttribute(TARGET_REORDER_ID_ATTR, 'target-2');
    document.body.appendChild(row);

    const orderedIds = vi.fn(() => ['target-1', 'target-2']);
    const { onPointerDown, dragOverId } = mountComposable(() =>
      useTargetDragReorder({
        orderedIds,
        onReorder: vi.fn(),
      }),
    );

    const handle = createHandle();

    onPointerDown('target-1', {
      button: 0,
      pointerId: 2,
      currentTarget: handle,
      preventDefault: vi.fn(),
    } as unknown as PointerEvent);

    const elementsFromPoint = vi.fn(() => [row]);
    Object.defineProperty(document, 'elementsFromPoint', {
      configurable: true,
      value: elementsFromPoint,
    });

    document.dispatchEvent(
      new PointerEvent('pointermove', {
        pointerId: 2,
        clientX: 10,
        clientY: 10,
        bubbles: true,
      }),
    );

    expect(dragOverId.value).toBe('target-2');

    document.body.removeChild(row);
    document.body.removeChild(handle);
    document.body.classList.remove('is-target-reordering');
  });
});
