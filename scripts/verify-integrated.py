#!/usr/bin/env python3
"""Read-only MSI bundle checks. Does not launch apps or access USB."""
import argparse
import json
from pathlib import Path
import plistlib
import re
import subprocess


def output(args):
    p = subprocess.run(list(map(str, args)), capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip() or str(args))
    return p.stdout


def verify(app):
    result = {"application": str(app), "ok": False, "errors": []}
    try:
        info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
        abi = info["MSISoapyABI"]
        if abi not in ("0.8", "0.8-3"):
            raise ValueError("Unknown private SoapySDR ABI: " + str(abi))
        contents = app / "Contents"
        fw = contents / "Frameworks"
        module = contents / ("Resources/msi-runtime/lib/SoapySDR/modules" + abi) / "libsoapyMiriSupport.so"
        components = [contents / "MacOS" / info["CFBundleExecutable"],
                      contents / "MacOS" / info["MSIOriginalExecutable"], module,
                      fw / "libusb-1.0.0.dylib", fw / "libmirisdr.4.dylib",
                      fw / ("libSoapySDR." + abi + ".dylib")]
        if info["MSIApplicationKind"] == "sdrpp":
            components.append(contents / "Plugins/soapy_source.dylib")
        for component in components:
            if not component.is_file():
                result["errors"].append("Missing component: " + str(component.relative_to(app)))
                continue
            if "arm64" not in output(["lipo", "-archs", component]).split():
                result["errors"].append("Missing arm64 slice: " + str(component.relative_to(app)))
            install_names = {line.strip() for line in output(["otool", "-D", component]).splitlines()
                             if line.strip() and not line.rstrip().endswith(":")}
            dependencies = re.findall(r"^\s+(.+?) \(compatibility version", output(["otool", "-L", component]), re.M)
            for dep in dependencies:
                if dep in install_names:
                    continue
                if dep.startswith(("/System/", "/usr/lib/")):
                    continue
                if dep.startswith("/"):
                    result["errors"].append("External dependency in " + component.name + ": " + dep)
                elif dep.startswith("@rpath/") and not (fw / dep[len("@rpath/"):]).exists():
                    result["errors"].append("Missing Frameworks candidate in " + component.name + ": " + dep)
        output(["codesign", "--verify", "--deep", "--strict", app])
        result.update(variant=info["MSIVariant"], soapy_abi=abi, signature="valid", components=len(components))
        result["ok"] = not result["errors"]
    except (OSError, ValueError, KeyError, RuntimeError, plistlib.InvalidFileException) as error:
        result["errors"].append(str(error))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apps", nargs="*", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    apps = args.apps or [Path("/Applications") / (name + " MSI Integrado.app")
                         for name in ("SDR++", "SDR++Brown", "SDR++CE", "SDRangel")]
    results = [verify(app) for app in apps]
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for result in results:
            print(("OK " if result["ok"] else "FAIL ") + result["application"])
            for error in result["errors"]:
                print("  " + error)
    return 0 if all(result["ok"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
