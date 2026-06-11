import {
  TRUNCATION_TITLE_SELECTOR,
  syncTruncationTitle,
} from './truncationTitle';

type WiredElement = {
  resizeObserver: ResizeObserver;
};

const wiredElements = new WeakMap<HTMLElement, WiredElement>();

function wireElement(element: HTMLElement): void {
  if (wiredElements.has(element) || !element.matches(TRUNCATION_TITLE_SELECTOR)) return;

  syncTruncationTitle(element);

  const resizeObserver = new ResizeObserver(() => {
    syncTruncationTitle(element);
  });
  resizeObserver.observe(element);
  wiredElements.set(element, { resizeObserver });
}

function unwireElement(element: HTMLElement): void {
  const wired = wiredElements.get(element);
  if (!wired) return;
  wired.resizeObserver.disconnect();
  wiredElements.delete(element);
}

function isQueryableRoot(node: Node): node is HTMLElement | DocumentFragment {
  return node instanceof HTMLElement || node instanceof DocumentFragment;
}

function wireTree(root: Node): void {
  if (!isQueryableRoot(root)) return;

  if (root instanceof HTMLElement && root.matches(TRUNCATION_TITLE_SELECTOR)) {
    wireElement(root);
  }
  root.querySelectorAll<HTMLElement>(TRUNCATION_TITLE_SELECTOR).forEach(wireElement);
}

function unwireTree(root: Node): void {
  if (!isQueryableRoot(root)) return;

  if (root instanceof HTMLElement && wiredElements.has(root)) {
    unwireElement(root);
  }
  root.querySelectorAll<HTMLElement>(TRUNCATION_TITLE_SELECTOR).forEach(unwireElement);
}

/** Observe DOM updates and keep truncation tooltips in sync for ellipsis text. */
export function startTruncationTitleObserver(root: HTMLElement): () => void {
  wireTree(root);

  const mutationObserver = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      mutation.removedNodes.forEach((node) => {
        if (node instanceof HTMLElement) unwireTree(node);
      });
      mutation.addedNodes.forEach((node) => {
        if (node instanceof HTMLElement || node instanceof DocumentFragment) wireTree(node);
      });
      if (mutation.type === 'characterData' && mutation.target.parentElement instanceof HTMLElement) {
        wireTree(mutation.target.parentElement);
      }
    }
  });

  mutationObserver.observe(root, {
    childList: true,
    subtree: true,
    characterData: true,
  });

  return () => {
    mutationObserver.disconnect();
    unwireTree(root);
  };
}
