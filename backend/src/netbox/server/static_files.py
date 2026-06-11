"""Static asset path safety checks."""

from __future__ import annotations

from pathlib import Path


def is_within(path: Path, parent: Path) -> bool:
    """Return whether `path` resolves inside `parent`."""

    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
