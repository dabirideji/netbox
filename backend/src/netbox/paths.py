"""Resolve project and runtime paths for development and packaged builds."""

from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    """Return the repository root in dev or the backend bundle directory when frozen."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]
