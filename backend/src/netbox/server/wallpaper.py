"""Fetch nature wallpapers from the Pexels API."""

from __future__ import annotations

import json
import os
import random
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"
# Prefer highest available resolution for full-viewport backgrounds.
IMAGE_SIZE_PRIORITY = (
    "large2x",
    "original",
    "large",
    "landscape",
    "medium",
    "small",
)
NATURE_QUERIES = (
    "nature",
    "forest",
    "mountains",
    "landscape",
    "wilderness",
    "waterfall",
    "meadow",
    "ocean",
)


def fetch_wallpaper() -> dict[str, Any]:
    """Return one nature landscape wallpaper payload for the dashboard."""

    api_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not api_key:
        raise ValueError("PEXELS_API_KEY is not configured")

    query = random.choice(NATURE_QUERIES)
    page = random.randint(1, 100)
    search_params = urllib.parse.urlencode(
        {
            "query": query,
            "orientation": "landscape",
            "per_page": "1",
            "page": str(page),
        }
    )
    request = urllib.request.Request(
        f"{PEXELS_SEARCH_URL}?{search_params}",
        headers={
            "Authorization": api_key,
            "User-Agent": "Netbox/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        raise ValueError(f"Pexels request failed: {error.code}") from error
    except urllib.error.URLError as error:
        raise ValueError("Pexels request failed") from error

    photos = payload.get("photos")
    if not isinstance(photos, list) or not photos:
        raise ValueError("Pexels returned no photos")

    photo = photos[0]
    if not isinstance(photo, dict):
        raise ValueError("Pexels photo payload is invalid")

    src = photo.get("src")
    if not isinstance(src, dict):
        raise ValueError("Pexels photo payload is invalid")

    image_url = next(
        (url for size in IMAGE_SIZE_PRIORITY if isinstance(url := src.get(size), str) and url),
        None,
    )
    if not image_url:
        raise ValueError("Pexels photo has no usable image URL")

    photographer = photo.get("photographer")
    photo_url = photo.get("url")

    return {
        "url": image_url,
        "photographer": photographer if isinstance(photographer, str) else "",
        "photoUrl": photo_url if isinstance(photo_url, str) else "",
    }
