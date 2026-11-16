#!/usr/bin/env bash
set -euo pipefail

APP_PATH="${1:-/Applications/SDR++.app}"

if [[ ! -d "$APP_PATH/Contents" ]]; then
  echo "error: not an app bundle: $APP_PATH" >&2
  exit 1
fi

echo "Inspecting: $APP_PATH"

mapfile_cmd_available=false
if command -v mapfile >/dev/null 2>&1; then
  mapfile_cmd_available=true
fi

find_libusb() {
  find "$APP_PATH" -name "libusb-1.0*.dylib" -print | head -n 1
}

BUNDLED_LIBUSB="$(find_libusb)"

if [[ -z "$BUNDLED_LIBUSB" ]]; then
  echo "error: no bundled libusb-1.0*.dylib found inside the app" >&2
  exit 1
fi

LIBUSB_NAME="$(basename "$BUNDLED_LIBUSB")"
NEW_REF="@rpath/$LIBUSB_NAME"

echo "Bundled libusb: $BUNDLED_LIBUSB"
echo "Replacement reference: $NEW_REF"

TMP_LIST="$(mktemp)"
trap 'rm -f "$TMP_LIST"' EXIT

find "$APP_PATH" -type f \( -name "*.dylib" -o -perm -111 \) -print > "$TMP_LIST"

changed=0

while IFS= read -r file; do
  if ! otool -L "$file" >/dev/null 2>&1; then
    continue
  fi

  old_refs="$(otool -L "$file" | awk '/\/opt\/homebrew.*libusb.*dylib/ {print $1}')"
  if [[ -z "$old_refs" ]]; then
    continue
  fi

  while IFS= read -r old_ref; do
    [[ -z "$old_ref" ]] && continue
    echo "Patching: $file"
    echo "  $old_ref -> $NEW_REF"
    install_name_tool -change "$old_ref" "$NEW_REF" "$file"
    changed=$((changed + 1))
  done <<< "$old_refs"
done < "$TMP_LIST"

if [[ "$changed" -eq 0 ]]; then
  echo "No Homebrew libusb references found. Nothing changed."
  exit 0
fi

echo "Re-signing app bundle..."
codesign --force --deep --sign - "$APP_PATH"

echo "Verifying signature..."
codesign --verify --deep --strict --verbose=2 "$APP_PATH"

echo "Done. Patched $changed libusb reference(s)."
