"""Fetch landscape wallpapers from the Pexels API."""

from __future__ import annotations

import json
import os
import random
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from urllib.parse import parse_qs

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"
PEXELS_CURATED_URL = "https://api.pexels.com/v1/curated"
PEXELS_PER_PAGE = 15
PEXELS_MAX_PAGE = 20
PEXELS_SEARCH_ATTEMPTS = 3
# Prefer highest available resolution for full-viewport backgrounds.
IMAGE_SIZE_PRIORITY = (
    "large2x",
    "original",
    "large",
    "landscape",
    "medium",
    "small",
)

DEFAULT_WALLPAPER_CATEGORY = "nature"

WALLPAPER_CATEGORIES: dict[str, tuple[str, ...]] = {
    "nature": ("nature", "landscape", "wilderness", "scenic view"),
    "mountains": ("mountains", "alpine", "mountain peak", "snowy mountains"),
    "ocean": ("ocean", "open sea", "deep blue sea", "seascape"),
    "forest": ("forest", "trees", "woodland", "rainforest"),
    "desert": ("desert", "sand dunes", "arid landscape", "sahara"),
    "city": ("city skyline", "urban landscape", "cityscape", "downtown"),
    "night": ("night sky", "stars", "milky way", "moonlight landscape"),
    "winter": ("snow landscape", "winter forest", "frost", "icy lake"),
    "sunset": ("sunset", "golden hour", "sunrise landscape", "dusk sky"),
    "flowers": ("flower field", "wildflowers", "blooming meadow", "lavender field"),
    "lakes": ("lake", "calm lake", "mountain lake", "reflective water"),
    "waterfalls": ("waterfall", "cascade", "flowing waterfall", "forest waterfall"),
    "tropical": ("tropical beach", "palm trees", "paradise island", "turquoise water"),
    "countryside": ("countryside", "rolling hills", "farmland", "rural landscape"),
    "autumn": ("autumn forest", "fall foliage", "autumn leaves", "golden trees"),
    "spring": ("spring blossoms", "cherry blossom", "spring landscape", "green hills"),
    "fog": ("foggy landscape", "misty mountains", "morning fog", "misty forest"),
    "aerial": ("aerial landscape", "drone view", "bird eye view", "aerial mountains"),
    "fields": ("wheat field", "open field", "grassland", "green fields"),
    "islands": ("island", "tropical island", "remote island", "island coastline"),
    "cliffs": ("coastal cliffs", "rocky coast", "sea cliffs", "cliff ocean"),
    "canyon": ("canyon", "red rock canyon", "grand canyon", "rock formations"),
    "aurora": ("aurora borealis", "northern lights", "aurora sky", "polar lights"),
    "meadows": ("meadow", "green meadow", "alpine meadow", "wild meadow"),
    "coast": ("coastline", "coastal landscape", "shoreline", "rocky shoreline"),
}

WALLPAPER_CATEGORY_LABELS: dict[str, str] = {
    "nature": "Nature",
    "mountains": "Mountains",
    "ocean": "Ocean",
    "forest": "Forest",
    "desert": "Desert",
    "city": "City",
    "night": "Night",
    "winter": "Winter",
    "sunset": "Sunset",
    "flowers": "Flowers",
    "lakes": "Lakes",
    "waterfalls": "Waterfalls",
    "tropical": "Tropical",
    "countryside": "Countryside",
    "autumn": "Autumn",
    "spring": "Spring",
    "fog": "Fog",
    "aerial": "Aerial",
    "fields": "Fields",
    "islands": "Islands",
    "cliffs": "Cliffs",
    "canyon": "Canyon",
    "aurora": "Aurora",
    "meadows": "Meadows",
    "coast": "Coast",
}


def normalize_wallpaper_category(category: str | None) -> str:
    """Return a supported wallpaper category id."""

    if not category:
        return DEFAULT_WALLPAPER_CATEGORY

    normalized = category.strip().lower()
    if normalized in WALLPAPER_CATEGORIES:
        return normalized
    return DEFAULT_WALLPAPER_CATEGORY


def parse_wallpaper_category_query(query: str) -> str:
    """Parse the `category` query parameter from `/api/wallpaper`."""

    params = parse_qs(query)
    raw_values = params.get("category")
    if not raw_values:
        return DEFAULT_WALLPAPER_CATEGORY

    raw = raw_values[0]
    if not isinstance(raw, str):
        return DEFAULT_WALLPAPER_CATEGORY

    return normalize_wallpaper_category(raw)


def wallpaper_categories() -> list[dict[str, str]]:
    """Return supported wallpaper categories for the settings UI."""

    return [
        {"id": category_id, "label": WALLPAPER_CATEGORY_LABELS[category_id]}
        for category_id in WALLPAPER_CATEGORIES
    ]


def _pexels_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": api_key,
        "User-Agent": "Netbox/1.0",
        "Accept": "application/json",
    }


def _request_pexels_json(url: str, api_key: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=_pexels_headers(api_key))

    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        raise ValueError(f"Pexels request failed: {error.code}") from error
    except urllib.error.URLError as error:
        reason = getattr(error, "reason", error)
        raise ValueError(f"Pexels request failed: {reason}") from error

    if not isinstance(payload, dict):
        raise ValueError("Pexels response is invalid")

    return payload


def _image_url_from_photo(photo: dict[str, Any]) -> str | None:
    src = photo.get("src")
    if not isinstance(src, dict):
        return None

    return next(
        (url for size in IMAGE_SIZE_PRIORITY if isinstance(url := src.get(size), str) and url),
        None,
    )


def _pick_random_photo(payload: dict[str, Any]) -> dict[str, Any] | None:
    photos = payload.get("photos")
    if not isinstance(photos, list) or not photos:
        return None

    candidates = [photo for photo in photos if isinstance(photo, dict) and _image_url_from_photo(photo)]
    if not candidates:
        return None

    return random.choice(candidates)


def _wallpaper_payload(photo: dict[str, Any], category_id: str) -> dict[str, Any]:
    image_url = _image_url_from_photo(photo)
    if not image_url:
        raise ValueError("Pexels photo has no usable image URL")

    photographer = photo.get("photographer")
    photo_url = photo.get("url")

    return {
        "url": image_url,
        "photographer": photographer if isinstance(photographer, str) else "",
        "photoUrl": photo_url if isinstance(photo_url, str) else "",
        "category": category_id,
    }


def _search_wallpaper(api_key: str, query: str, page: int) -> dict[str, Any]:
    search_params = urllib.parse.urlencode(
        {
            "query": query,
            "orientation": "landscape",
            "per_page": str(PEXELS_PER_PAGE),
            "page": str(page),
        }
    )
    return _request_pexels_json(f"{PEXELS_SEARCH_URL}?{search_params}", api_key)


def _curated_wallpaper(api_key: str, page: int) -> dict[str, Any]:
    search_params = urllib.parse.urlencode(
        {
            "per_page": str(PEXELS_PER_PAGE),
            "page": str(page),
        }
    )
    return _request_pexels_json(f"{PEXELS_CURATED_URL}?{search_params}", api_key)


def fetch_wallpaper(category: str | None = None) -> dict[str, Any]:
    """Return one landscape wallpaper payload for the dashboard."""

    api_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not api_key:
        raise ValueError("PEXELS_API_KEY is not configured")

    category_id = normalize_wallpaper_category(category)
    queries = list(WALLPAPER_CATEGORIES[category_id])
    random.shuffle(queries)
    last_error: ValueError | None = None

    for query in queries[:PEXELS_SEARCH_ATTEMPTS]:
        try:
            payload = _search_wallpaper(api_key, query, random.randint(1, PEXELS_MAX_PAGE))
            photo = _pick_random_photo(payload)
            if photo is None:
                raise ValueError("Pexels returned no photos")
            return _wallpaper_payload(photo, category_id)
        except ValueError as error:
            last_error = error

    try:
        payload = _curated_wallpaper(api_key, random.randint(1, PEXELS_MAX_PAGE))
        photo = _pick_random_photo(payload)
        if photo is None:
            raise ValueError("Pexels returned no photos")
        return _wallpaper_payload(photo, category_id)
    except ValueError as error:
        last_error = error

    if last_error is not None:
        raise last_error

    raise ValueError("Pexels request failed")
