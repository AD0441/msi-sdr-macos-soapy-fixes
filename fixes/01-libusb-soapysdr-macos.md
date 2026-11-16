# SDR++ macOS SoapySDR/libusb bundle repair

> Imported from `sdrpp-macos-fixes`. This is a targeted dependency repair for an existing SDR++ bundle. For the current MSI2500/MSI001 solution, follow the [integrated application guide](../docs/msi-integrated-apps.md). Unifying libusb alone did not resolve the later USB crashes.

The helper requires a bundled libusb and an existing `@rpath` that resolves it from every modified component. It neither adds missing rpaths nor builds or installs SoapyMiri. Make a separate copy of the application before running it; the script does not create an application backup. Keep the original if dependency resolution or signing fails.

## Problem

On Apple Silicon macOS, SDR++ may load successfully while some bundled SoapySDR
or device support libraries still reference a Homebrew `libusb` path:

```text
/opt/homebrew/opt/libusb/lib/libusb-1.0.0.dylib
```

That can break SDR++ on machines where the exact Homebrew path is missing or
where the application is expected to be self-contained.

Typical symptoms include:

- SDR++ starts but a device source fails to load.
- SoapySDR input cannot see hardware that works outside the app.
- Terminal output mentions `Library not loaded`, `image not found`, or
  a missing `libusb-1.0.0.dylib`.

## Diagnosis

Close SDR++ and inspect the application bundle:

```bash
find "/Applications/SDR++.app" -type f \( -name "*.dylib" -o -perm +111 \) -print
```

Then inspect likely libraries:

```bash
otool -L "/Applications/SDR++.app/Contents/MacOS/SDR++"
find "/Applications/SDR++.app" -name "*.dylib" -print -exec otool -L {} \;
```

Search for Homebrew references:

```bash
find "/Applications/SDR++.app" -name "*.dylib" -print0 |
while IFS= read -r -d '' file; do
  if otool -L "$file" | grep -q "/opt/homebrew.*libusb"; then
    echo "$file"
    otool -L "$file" | grep "/opt/homebrew.*libusb"
  fi
done
```

## Repair approach

The preferred repair is to make libraries inside the SDR++ bundle refer to the
bundled copy of `libusb`, when that bundled copy exists.

The helper script automates the cautious path:

```bash
scripts/repair-sdrpp-libusb.sh "/Applications/SDR++.app"
```

It performs these steps:

1. Confirms the target is an SDR++ `.app` bundle.
2. Locates a bundled `libusb-1.0.0.dylib`.
3. Finds bundled `.dylib` files that reference `/opt/homebrew/...libusb...`.
4. Rewrites those install names with `install_name_tool`.
5. Re-signs the modified app with ad-hoc signing.
6. Verifies the signature.

## Manual commands

If the script reports the exact file and old dependency path, the manual repair
usually looks like this:

```bash
install_name_tool \
  -change "/opt/homebrew/opt/libusb/lib/libusb-1.0.0.dylib" \
  "@rpath/libusb-1.0.0.dylib" \
  "/path/to/library-that-references-libusb.dylib"
```

After changing a signed macOS app bundle, re-sign it:

```bash
codesign --force --deep --sign - "/Applications/SDR++.app"
codesign --verify --deep --strict --verbose=2 "/Applications/SDR++.app"
```

## Upstream issue summary

This is a packaging problem, not a user configuration problem. A distributed
macOS `.app` bundle should not require a local Homebrew dependency path unless
that requirement is intentionally documented.
