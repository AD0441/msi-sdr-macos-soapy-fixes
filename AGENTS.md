# Continuing MSI-SDR work

This repository is the durable project context. Read `RECOVERY.md`,
`recovery/manifest.json`, `docs/usb-control-errors.md` and
`docs/validation-2026-11.md` before changing the integration.

- Canonical repository: AD0441/msi-sdr-macos-soapy-fixes. The former
  sdrpp-macos-fixes repository was merged with its history and removed.
- Owner-only binary inputs, original/ready/previous apps, source snapshots,
  frozen SDK, personal SDR settings and historical local notes are in the
  **private** AD0441/msi-sdr-macos-recovery release `recovery-2026.11.16.1`.
  Never publish settings, raw personal logs, credentials or third-party app
  archives in the public repository. Do not change the vault's visibility.
- Recovery must work from a fresh clone plus locked downloaded inputs.
  Do not use installed MSI bundles, a developer's home directory or live
  Homebrew as implicit build inputs. Use `scripts/msi_recovery.py`.
- Rebuilds compile our patched driver, both SoapyMiri ABIs, three distinct
  SDR++ plugins and the two entry components. Original app cores, Qt and
  dependency binaries are frozen inputs, not rebuilt from their full source.
- Preserve the tested source hashes when refactoring recovery tooling. If
  changing driver/plugin logic, deliberately update the manifest and its
  evidence only after the appropriate hardware and failure-injection tests.
- Brown/CE snapshot revisions are header-matching candidates; they do not
  establish the exact commit used to produce the original binary cores.
- Only the receiver MSI2500/MSI001 and documented versions were tested.
  Soapy ABI 0.8 and SDRangel ABI 0.8-3 require separate builds. Do not swap
  plugin binaries across SDR++ forks.
- Keep originals. Build/restore into an empty directory. Do not overwrite
  /Applications or personal profiles without the user's instruction.
- Maintain Spanish and English entry documentation and Ko-fi attribution.
- Run offline recovery tests for tooling changes. For runtime changes use
  the documented USB probes and error-injection checks. A passing GitHub
  workflow does not certify radio reception, RF performance or audio.
- Remaining runtime work: physical unplug/replug, extended GUI/audio use,
  per-block stream counters and RF calibration. The initial legacy sample
  counter can wrap at -1; do not report it as measured billions of lost samples.
- Collaboration issue: https://github.com/olexii4/msi-sdr-radio/issues/1.
  Do not contact maintainers or publish PRs without user authorization.
