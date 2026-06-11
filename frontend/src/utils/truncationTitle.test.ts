import { afterEach, describe, expect, it } from 'vitest';
import { isTextTruncated, syncTruncationTitle } from './truncationTitle';

describe('truncationTitle', () => {
  let element: HTMLSpanElement;

  afterEach(() => {
    element?.remove();
  });

  it('sets title only when text overflows', () => {
    element = document.createElement('span');
    element.textContent = 'A very long monitor source label that should truncate';
    element.style.width = '40px';
    element.style.display = 'inline-block';
    element.style.overflow = 'hidden';
    element.style.whiteSpace = 'nowrap';
    element.style.textOverflow = 'ellipsis';
    document.body.append(element);

    syncTruncationTitle(element);

    if (isTextTruncated(element)) {
      expect(element.title).toBe(element.textContent);
    } else {
      expect(element.title).toBe('');
    }
  });

  it('skips elements with a fixed title', () => {
    element = document.createElement('span');
    element.dataset.fixedTitle = 'true';
    element.textContent = 'Pinned tooltip';
    element.title = 'Pinned tooltip';
    element.style.width = '20px';
    element.style.display = 'inline-block';
    element.style.overflow = 'hidden';
    document.body.append(element);

    syncTruncationTitle(element);

    expect(element.title).toBe('Pinned tooltip');
  });
});
