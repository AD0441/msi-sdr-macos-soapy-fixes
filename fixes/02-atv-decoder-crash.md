# SDR++ ATV Decoder crash recovery

> Imported from `sdrpp-macos-fixes`. This is configuration recovery, separate from MSI receiver discovery and USB stability. It does not patch the ATV Decoder destructor.

The default path below belongs to a standard SDR++ profile. The integrated MSI variants use separate profiles under `~/Library/Application Support/MSI-SDR/`; pass the desired profile's `config.json` explicitly. Close the relevant application before editing its configuration.

## Problem

SDR++ can crash on Apple Silicon macOS when removing an `atv_decoder` instance
from Module Manager.

The crash report points to the ATV Decoder destructor:

```text
ATVDecoderModule::~ATVDecoderModule()
ModuleManager::deleteInstance(...)
module_manager_menu::draw(...)
std::terminate()
abort()
SIGABRT
```

At the time of the crash, ATV-related DSP worker threads may still appear active,
including:

```text
dsp::loop::FastAGC<dsp::complex_t>::run()
dsp::demod::Amplitude::run()
LineSync::run()
dsp::sink::Handler<float>::run()
```

That suggests a lifecycle bug: the module may be destroying DSP objects or UI
resources before all worker threads have fully stopped and joined.

## Observed configuration

The SDR++ configuration contained two saved module instances pointing to
`atv_decoder`:

```json
"Soapy": {
    "enabled": false,
    "module": "atv_decoder"
},

"dasd": {
    "enabled": true,
    "module": "atv_decoder"
}
```

Removing these saved instances from `config.json` prevents SDR++ from recreating
them at startup.

This does not fix the destructor crash itself. It is a recovery workaround that
lets SDR++ start cleanly after a bad ATV Decoder instance was saved.

## Recovery script

Close SDR++ first.

Then run:

```bash
scripts/remove-atv-decoder-instance.sh
```

The default config path is:

```text
$HOME/Library/Application Support/sdrpp/config.json
```

You can also pass a path explicitly:

```bash
scripts/remove-atv-decoder-instance.sh \
  "$HOME/Library/Application Support/sdrpp/config.json"
```

The script:

1. Creates a timestamped backup next to `config.json`.
2. Parses the file as JSON.
3. Removes only entries in `moduleInstances` whose `module` is `atv_decoder`.
4. Writes the cleaned config.
5. Validates that the result is still valid JSON.

## Manual recovery

Create a backup:

```bash
cp "$HOME/Library/Application Support/sdrpp/config.json" \
   "$HOME/Library/Application Support/sdrpp/config.json.backup"
```

Find ATV references:

```bash
grep -n -i -C 6 'atv_decoder' \
  "$HOME/Library/Application Support/sdrpp/config.json"
```

Edit the file:

```bash
nano "$HOME/Library/Application Support/sdrpp/config.json"
```

Remove only the full instance blocks that point to:

```json
"module": "atv_decoder"
```

Validate before reopening SDR++:

```bash
python3 -m json.tool \
  "$HOME/Library/Application Support/sdrpp/config.json" >/dev/null
```

## Upstream issue summary

This should be reported separately from packaging issues.

Suggested upstream title:

```text
Crash when removing ATV Decoder instance from Module Manager on Apple Silicon
```

Expected behavior:

```text
Deleting an ATV Decoder instance should stop its DSP chain, join all worker
threads, and destroy the module cleanly without terminating SDR++.
```

Actual behavior:

```text
The application aborts inside ATVDecoderModule::~ATVDecoderModule(), causing
SIGABRT.
```
