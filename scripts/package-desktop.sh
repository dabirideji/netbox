#!/usr/bin/env bash
# Build frontend, backend bundle, and Electron installers.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

make build
bash "$ROOT/scripts/build-backend.sh"

if [ ! -d frontend/dist ]; then
  printf 'frontend/dist is missing after build.\n' >&2
  exit 1
fi

cd "$ROOT/electron"
if [ ! -d node_modules ]; then
  npm install
fi

npm run dist
printf '\nDesktop artifacts are in electron/release/\n'
