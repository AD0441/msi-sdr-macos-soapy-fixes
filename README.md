# SDR++ macOS fixes

Practical recovery notes and helper scripts for two SDR++ issues observed on
Apple Silicon macOS:

1. A bundled dependency problem where SDR++/SoapySDR can still point to a
   Homebrew `libusb` path such as `/opt/homebrew/...`.
2. A crash when removing an `atv_decoder` instance from Module Manager,
   ending in `ATVDecoderModule::~ATVDecoderModule()` and `SIGABRT`.

These notes are written for users who installed SDR++ as a `.app` bundle and
want a reproducible way to inspect, repair, and recover without mixing the work
into unrelated repositories.

## Contents

```text
sdrpp-macos-fixes/
├── README.md
├── LICENSE
├── .gitignore
├── fixes/
│   ├── 01-libusb-soapysdr-macos.md
│   └── 02-atv-decoder-crash.md
└── scripts/
    ├── repair-sdrpp-libusb.sh
    └── remove-atv-decoder-instance.sh
```

## Fix 1: bundled `libusb` reference

See [fixes/01-libusb-soapysdr-macos.md](fixes/01-libusb-soapysdr-macos.md).

The helper script checks the SDR++ application bundle for libraries that still
refer to Homebrew's `libusb`, attempts to rewrite those references to bundled
libraries when possible, then re-signs the app locally:

```bash
scripts/repair-sdrpp-libusb.sh "/Applications/SDR++.app"
```

If your SDR++ app is on the Desktop, pass that path instead:

```bash
scripts/repair-sdrpp-libusb.sh "$HOME/Desktop/SDR++.app"
```

## Fix 2: ATV Decoder crash recovery

See [fixes/02-atv-decoder-crash.md](fixes/02-atv-decoder-crash.md).

The recovery script backs up SDR++'s `config.json`, removes only module
instances that point to `atv_decoder`, and validates the resulting JSON:

```bash
scripts/remove-atv-decoder-instance.sh
```

You can also pass an explicit config path:

```bash
scripts/remove-atv-decoder-instance.sh \
  "$HOME/Library/Application Support/sdrpp/config.json"
```

## Safety notes

- Close SDR++ before running either script.
- Keep the generated backups until SDR++ has restarted cleanly.
- The ATV Decoder script removes saved ATV module instances from the SDR++
  configuration. It does not patch the underlying SDR++ crash.
- The `libusb` script modifies the `.app` bundle and performs an ad-hoc
  `codesign`; macOS may still require you to approve the application again.

## Upstream reports

The two issues should be reported upstream separately:

- Packaging/dependency issue: bundled libraries should not depend on a local
  Homebrew path that may not exist on the user's machine.
- ATV Decoder lifecycle issue: deleting an ATV Decoder instance from Module
  Manager appears to abort inside `ATVDecoderModule::~ATVDecoderModule()` while
  DSP worker threads are still active.

## License

MIT. See [LICENSE](LICENSE).
