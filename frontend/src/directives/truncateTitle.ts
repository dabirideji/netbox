import type { Directive } from 'vue';
import { syncTruncationTitle } from '../utils/truncationTitle';

type TruncateTitleBinding = string | undefined;

const resizeObservers = new WeakMap<HTMLElement, ResizeObserver>();

export const vTruncateTitle: Directive<HTMLElement, TruncateTitleBinding> = {
  mounted(element, binding) {
    const update = () => syncTruncationTitle(element, binding.value);
    update();

    const resizeObserver = new ResizeObserver(update);
    resizeObserver.observe(element);
    resizeObservers.set(element, resizeObserver);
  },
  updated(element, binding) {
    syncTruncationTitle(element, binding.value);
  },
  unmounted(element) {
    resizeObservers.get(element)?.disconnect();
    resizeObservers.delete(element);
  },
};
