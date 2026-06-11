/** Helpers for persisted monitor target display order. */

export function compareTargetsBySortOrder<T extends { id: string; sortOrder?: number }>(
  left: T,
  right: T,
): number {
  const leftOrder = left.sortOrder ?? Number.MAX_SAFE_INTEGER;
  const rightOrder = right.sortOrder ?? Number.MAX_SAFE_INTEGER;
  if (leftOrder !== rightOrder) return leftOrder - rightOrder;
  return left.id.localeCompare(right.id);
}

export function sortTargetsBySortOrder<T extends { id: string; sortOrder?: number }>(targets: T[]): T[] {
  return [...targets].sort(compareTargetsBySortOrder);
}

export function reorderTargetIds(order: string[], draggedId: string, overId: string): string[] | null {
  const fromIndex = order.indexOf(draggedId);
  const toIndex = order.indexOf(overId);
  if (fromIndex < 0 || toIndex < 0 || fromIndex === toIndex) return null;

  const next = [...order];
  next.splice(fromIndex, 1);
  next.splice(toIndex, 0, draggedId);
  return next;
}

export function sameTargetIdOrder(left: string[], right: string[]): boolean {
  return left.length === right.length && left.every((id, index) => id === right[index]);
}

export function reorderTargetsByIds<T extends { id: string }>(targets: T[], order: string[]): T[] {
  const byId = new Map(targets.map((target) => [target.id, target]));
  return order.flatMap((id) => {
    const target = byId.get(id);
    return target ? [target] : [];
  });
}
