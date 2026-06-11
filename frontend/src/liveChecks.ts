/** Shared page sizes for dashboard target lists. */

export const LIVE_CHECKS_PAGE_SIZE = 15;
export const TARGETS_PAGE_SIZE = 6;

export function sortLiveCheckTargets<T extends { isFavorite?: boolean }>(targets: T[]): T[] {
  return [...targets].sort((left, right) => {
    const leftFavorite = left.isFavorite ? 1 : 0;
    const rightFavorite = right.isFavorite ? 1 : 0;
    if (leftFavorite !== rightFavorite) {
      return rightFavorite - leftFavorite;
    }
    return 0;
  });
}
