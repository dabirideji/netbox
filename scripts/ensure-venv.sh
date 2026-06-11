#!/usr/bin/env bash
# Create the local Python virtualenv and install backend dependencies.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

base_python() {
  if [ -f .dev/python-bin ]; then
    cat .dev/python-bin
  elif command -v python3 >/dev/null 2>&1; then
    command -v python3
  else
    printf 'python3\n'
  fi
}

BASE="$(base_python)"
"$BASE" -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 11) else 1)" || {
  printf 'Python 3.11+ is required. Run make run first.\n' >&2
  exit 1
}

if [ ! -x .venv/bin/python ]; then
  printf 'Creating local Python virtualenv at .venv\n'
  "$BASE" -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/python -m pip install -e "./backend[dev]"
