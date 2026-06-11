#!/usr/bin/env bash
# Generate web and Electron icon assets from icons/black.png and icons/white.png.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/icons"
BUILD="$ROOT/electron/build"
PUBLIC="$ROOT/frontend/public/icons"
RESOURCES="$ROOT/electron/resources"
RUNTIME_ICONS="$RESOURCES/icons"

if [ ! -f "$SRC/black.png" ] || [ ! -f "$SRC/white.png" ]; then
  printf 'Expected icons/black.png and icons/white.png\n' >&2
  exit 1
fi

if command -v magick >/dev/null 2>&1; then
  MAGICK=(magick)
elif command -v convert >/dev/null 2>&1; then
  MAGICK=(convert)
else
  printf 'ImageMagick is required to generate icons. Install it with: brew install imagemagick\n' >&2
  exit 1
fi

pad_square() {
  local input="$1"
  local size="$2"
  local output="$3"
  "${MAGICK[@]}" "$input" -resize "${size}x${size}" -background none -gravity center -extent "${size}x${size}" "$output"
}

resize_height() {
  local input="$1"
  local height="$2"
  local output="$3"
  "${MAGICK[@]}" "$input" -resize "x${height}" "$output"
}

mkdir -p "$PUBLIC" "$BUILD" "$RESOURCES" "$RUNTIME_ICONS"

cp "$SRC/black.png" "$PUBLIC/black.png"
cp "$SRC/white.png" "$PUBLIC/white.png"
pad_square "$SRC/black.png" 32 "$PUBLIC/black-32.png"
pad_square "$SRC/white.png" 32 "$PUBLIC/white-32.png"

pad_square "$SRC/black.png" 1024 "$BUILD/icon.png"
resize_height "$SRC/black.png" 22 "$BUILD/iconTemplate.png"
pad_square "$SRC/black.png" 256 "$BUILD/icon-tray.png"
"${MAGICK[@]}" "$SRC/black.png" -define icon:auto-resize=16,24,32,48,64,128,256 "$BUILD/icon.ico"
resize_height "$SRC/white.png" 72 "$RESOURCES/logo.png"

cp "$BUILD/icon.png" "$RUNTIME_ICONS/icon.png"
cp "$BUILD/iconTemplate.png" "$RUNTIME_ICONS/iconTemplate.png"
cp "$BUILD/icon-tray.png" "$RUNTIME_ICONS/icon-tray.png"
cp "$BUILD/icon.ico" "$RUNTIME_ICONS/icon.ico"

if [ "$(uname -s)" = "Darwin" ] && command -v iconutil >/dev/null 2>&1; then
  iconset="$(mktemp -d)/icon.iconset"
  mkdir -p "$iconset"
  for size in 16 32 64 128 256 512 1024; do
    pad_square "$SRC/black.png" "$size" "$iconset/icon_${size}x${size}.png"
    if [ "$size" -lt 1024 ]; then
      pad_square "$SRC/black.png" "$((size * 2))" "$iconset/icon_${size}x${size}@2x.png"
    fi
  done
  iconutil -c icns "$iconset" -o "$BUILD/icon.icns"
  cp "$BUILD/icon.icns" "$RUNTIME_ICONS/icon.icns"
fi

printf 'Generated web icons in frontend/public/icons/\n'
printf 'Generated Electron build icons in electron/build/\n'
printf 'Generated packaged runtime icons in electron/resources/icons/\n'
printf 'Generated splash logo in electron/resources/logo.png\n'
