#!/usr/bin/env bash
set -euo pipefail

APP="${1:-/Applications/SDRangel.app}"

echo "== SDRangel app =="
if [[ ! -d "$APP" ]]; then
  echo "Not found: $APP"
  exit 1
fi
echo "$APP"

echo
echo "== binary =="
file "$APP/Contents/MacOS/sdrangel" || file "$APP/Contents/MacOS/SDRangel"

echo
echo "== Soapy/Miri files inside bundle =="
find "$APP" -iname '*Soapy*' -o -iname '*miri*' | sort || true

echo
echo "== Soapy links =="
if [[ -f "$APP/Contents/MacOS/sdrangel" ]]; then
  otool -L "$APP/Contents/MacOS/sdrangel" | grep -i Soapy || true
elif [[ -f "$APP/Contents/MacOS/SDRangel" ]]; then
  otool -L "$APP/Contents/MacOS/SDRangel" | grep -i Soapy || true
fi

echo
echo "== signature =="
codesign --verify --deep --strict --verbose=2 "$APP"

