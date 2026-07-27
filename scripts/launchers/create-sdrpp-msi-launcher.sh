#!/usr/bin/env bash
set -euo pipefail

TARGET_APP="${1:-/Applications/SDR++ Soapy.app}"
LAUNCHER="${2:-/Applications/SDR++ MSI.app}"
SOAPY_PATH="${SOAPY_SDR_PLUGIN_PATH:-/opt/homebrew/lib/SoapySDR/modules0.8}"
LOG_PATH='${HOME}/Library/Logs/SDRPP-MSI.log'

if [[ ! -x "$TARGET_APP/Contents/MacOS/sdrpp" ]]; then
  echo "Cannot find SDR++ executable at: $TARGET_APP/Contents/MacOS/sdrpp"
  exit 1
fi

sudo osacompile -o "$LAUNCHER" \
  -e "do shell script \"SOAPY_SDR_PLUGIN_PATH=\\\"$SOAPY_PATH\\\" nohup \\\"$TARGET_APP/Contents/MacOS/sdrpp\\\" >> \\\"$LOG_PATH\\\" 2>&1 &\""

echo "Created launcher: $LAUNCHER"

