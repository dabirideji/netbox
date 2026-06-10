#!/usr/bin/env python3
"""Run the Netbox monitor backend."""

from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_ROOT / "src"))

from netbox.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
