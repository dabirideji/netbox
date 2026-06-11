/** CSS selectors for single-line ellipsis text that should expose full values on hover. */

export const TRUNCATION_TITLE_SELECTOR = [
  '.components-scope-head__hint',
  '.component-cell.stat',
  '.component-name strong',
  '.component-name small',
  '.target-taxonomy-field__value',
  '.target-taxonomy-field__option-button',
  '.target-scope-head__hint',
  '.target-item__label',
  '.target-item small',
  '.target-item__badge',
  '.event-copy strong',
  '.event-copy small',
  '.tray-row__ip',
  '.tray-row__text strong',
  '.tray-row__text small',
  '.tray-row__latency',
].join(', ');

export function truncationTitleText(element: HTMLElement, explicitText?: string): string {
  return (explicitText ?? element.dataset.truncateTitle ?? element.textContent ?? '').trim();
}

export function isTextTruncated(element: HTMLElement): boolean {
  return element.scrollWidth > element.clientWidth + 1 || element.scrollHeight > element.clientHeight + 1;
}

export function shouldManageTruncationTitle(element: HTMLElement): boolean {
  return element.dataset.fixedTitle === undefined && element.dataset.truncateTitleOff === undefined;
}

/** Sync native `title` so truncated copy shows the full text on hover. */
export function syncTruncationTitle(element: HTMLElement, explicitText?: string): void {
  if (!shouldManageTruncationTitle(element)) return;

  const fullText = truncationTitleText(element, explicitText);
  if (!fullText) {
    element.removeAttribute('title');
    return;
  }

  if (isTextTruncated(element)) {
    element.title = fullText;
    return;
  }

  element.removeAttribute('title');
}
