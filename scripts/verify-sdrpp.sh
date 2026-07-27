#!/usr/bin/env bash
set -euo pipefail

APP="${1:-/Applications/SDR++ Soapy.app}"

echo "== SDR++ app =="
if [[ ! -d "$APP" ]]; then
  echo "Not found: $APP"
  exit 1
fi
echo "$APP"

echo
echo "== soapy_source plugin =="
PLUGIN="$APP/Contents/Plugins/soapy_source.dylib"
if [[ -f "$PLUGIN" ]]; then
  ls -l "$PLUGIN"
  otool -L "$PLUGIN" | grep -i Soapy || true
else
  echo "Missing: $PLUGIN"
fi

echo
echo "== bundled libusb =="
USB="$APP/Contents/Frameworks/libusb-1.0.0.dylib"
if [[ -f "$USB" ]]; then
  otool -L "$USB" | head -5
else
  echo "Missing: $USB"
fi

echo
echo "== Homebrew libmirisdr libusb link =="
if [[ -f /opt/homebrew/lib/libmirisdr.4.dylib ]]; then
  otool -L /opt/homebrew/lib/libmirisdr.4.dylib | grep -i usb || true
else
  echo "Missing: /opt/homebrew/lib/libmirisdr.4.dylib"
fi

echo
echo "== signature =="
codesign --verify --deep --strict --verbose=2 "$APP"

