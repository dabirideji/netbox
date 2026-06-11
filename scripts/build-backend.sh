#!/usr/bin/env bash
# Bundle the Python monitor backend with PyInstaller for desktop packaging.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -x "$ROOT/.venv/bin/python" ]; then
  PYTHON="$ROOT/.venv/bin/python"
elif [ -f .dev/python-bin ]; then
  PYTHON="$(cat .dev/python-bin)"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
else
  printf 'python3 is required to build the desktop backend.\n' >&2
  exit 1
fi

"$PYTHON" -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 11) else 1)" || {
  printf 'Python 3.11+ is required to build the desktop backend.\n' >&2
  exit 1
}

if [ ! -x "$ROOT/.venv/bin/python" ]; then
  printf 'Creating local build virtualenv at .venv\n'
  "$PYTHON" -m venv "$ROOT/.venv"
  PYTHON="$ROOT/.venv/bin/python"
fi

"$PYTHON" -m pip install --upgrade pip >/dev/null
"$PYTHON" -m pip install -e "./backend[dev]" pyinstaller >/dev/null

rm -rf dist-backend .dev/pyinstaller
mkdir -p dist-backend

"$PYTHON" -m PyInstaller \
  --noconfirm \
  --clean \
  --distpath "$ROOT/dist-backend" \
  --workpath "$ROOT/.dev/pyinstaller" \
  "$ROOT/scripts/netbox-backend.spec"

if [ ! -f "$ROOT/dist-backend/netbox-backend" ] && [ ! -f "$ROOT/dist-backend/netbox-backend.exe" ]; then
  printf 'PyInstaller did not produce dist-backend/netbox-backend\n' >&2
  exit 1
fi

printf 'Backend bundle ready in dist-backend/\n'
