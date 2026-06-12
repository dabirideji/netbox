export const WALLPAPER_CATEGORIES = [
  { id: 'nature', label: 'Nature' },
  { id: 'mountains', label: 'Mountains' },
  { id: 'ocean', label: 'Ocean' },
  { id: 'forest', label: 'Forest' },
  { id: 'desert', label: 'Desert' },
  { id: 'city', label: 'City' },
  { id: 'night', label: 'Night' },
  { id: 'winter', label: 'Winter' },
  { id: 'sunset', label: 'Sunset' },
  { id: 'flowers', label: 'Flowers' },
  { id: 'lakes', label: 'Lakes' },
  { id: 'waterfalls', label: 'Waterfalls' },
  { id: 'tropical', label: 'Tropical' },
  { id: 'countryside', label: 'Countryside' },
  { id: 'autumn', label: 'Autumn' },
  { id: 'spring', label: 'Spring' },
  { id: 'fog', label: 'Fog' },
  { id: 'aerial', label: 'Aerial' },
  { id: 'fields', label: 'Fields' },
  { id: 'islands', label: 'Islands' },
  { id: 'cliffs', label: 'Cliffs' },
  { id: 'canyon', label: 'Canyon' },
  { id: 'aurora', label: 'Aurora' },
  { id: 'meadows', label: 'Meadows' },
  { id: 'coast', label: 'Coast' },
] as const;

export type WallpaperCategoryId = (typeof WALLPAPER_CATEGORIES)[number]['id'];

export const DEFAULT_WALLPAPER_CATEGORY: WallpaperCategoryId = 'nature';

const CATEGORY_IDS = new Set<string>(WALLPAPER_CATEGORIES.map((category) => category.id));

export function isWallpaperCategoryId(value: string): value is WallpaperCategoryId {
  return CATEGORY_IDS.has(value);
}

export function normalizeWallpaperCategoryId(value: string | null | undefined): WallpaperCategoryId {
  if (!value) {
    return DEFAULT_WALLPAPER_CATEGORY;
  }

  const normalized = value.trim().toLowerCase();
  return isWallpaperCategoryId(normalized) ? normalized : DEFAULT_WALLPAPER_CATEGORY;
}

export function wallpaperCategoryLabel(categoryId: WallpaperCategoryId): string {
  return WALLPAPER_CATEGORIES.find((category) => category.id === categoryId)?.label ?? 'Nature';
}
