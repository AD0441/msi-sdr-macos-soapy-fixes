#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${1:-$HOME/Library/Application Support/sdrpp/config.json}"

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "error: config file not found: $CONFIG_PATH" >&2
  exit 1
fi

BACKUP_PATH="${CONFIG_PATH}.backup.$(date +%Y%m%d-%H%M%S)"
TMP_PATH="$(mktemp)"
trap 'rm -f "$TMP_PATH"' EXIT

echo "Backing up config:"
echo "  $BACKUP_PATH"
cp "$CONFIG_PATH" "$BACKUP_PATH"

python3 - "$CONFIG_PATH" "$TMP_PATH" <<'PY'
import json
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])

data = json.loads(src.read_text(encoding="utf-8"))
instances = data.get("moduleInstances")

if not isinstance(instances, dict):
    print("No moduleInstances object found. Nothing changed.")
    dst.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
    sys.exit(0)

removed = []
for name, value in list(instances.items()):
    if isinstance(value, dict) and value.get("module") == "atv_decoder":
        removed.append(name)
        del instances[name]

dst.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")

if removed:
    print("Removed ATV Decoder instance(s):")
    for name in removed:
        print(f"  - {name}")
else:
    print("No atv_decoder instances found. Nothing changed.")
PY

python3 -m json.tool "$TMP_PATH" >/dev/null
mv "$TMP_PATH" "$CONFIG_PATH"

echo "Updated config is valid JSON:"
echo "  $CONFIG_PATH"
