# Repository consolidation / Unificación de repositorios

## English

`AD0441/msi-sdr-macos-soapy-fixes` is the canonical repository for this work. On November 15, 2026, the contents and Git history of `AD0441/sdrpp-macos-fixes` were integrated here before retiring that repository.

Both projects address SDR compatibility on macOS. Their scope is complementary:

- **MSI integration:** receiver discovery, SoapySDR ABI compatibility, asynchronous USB lifetime fixes, fork-specific source plugins and private application bundles.
- **General SDR++ recovery:** existing bundled libusb dependency repair and recovery from saved ATV Decoder module instances.

The imported history starts at commit [`aa3d3c71c6da35510abd22e40520d7a202cb372a`](https://github.com/AD0441/msi-sdr-macos-soapy-fixes/commit/aa3d3c71c6da35510abd22e40520d7a202cb372a). The consolidation commit has both projects as parents, retaining the original commit, author, timestamp, file contents and executable modes.

| Original item | Current location |
| --- | --- |
| `fixes/01-libusb-soapysdr-macos.md` | Same path, with a note clarifying its limited scope |
| `fixes/02-atv-decoder-crash.md` | Same path, with a note about private MSI profiles |
| `scripts/repair-sdrpp-libusb.sh` | Same path, unchanged |
| `scripts/remove-atv-decoder-instance.sh` | Same path, unchanged |
| `README.md` | Original text in `docs/history/sdrpp-macos-fixes-README.txt`; current overview in the bilingual root README |
| `LICENSE` | Original copy in `docs/history/sdrpp-macos-fixes.LICENSE`; both projects use the same MIT copyright notice |
| `.gitignore` | Backup/temp exclusions combined with the canonical repository's existing rules |

A complete Git mirror, verified standalone bundle and repository metadata were saved locally before deletion. The source had one branch, no tags, no issues or pull requests, no releases and no published wiki. The backup is intentionally outside this source repository. The imported Git commit also preserves every original file as it was.

The standalone libusb script requires an existing bundled library and working `@rpath` resolution. It does not repair ABI mismatches, install missing receiver modules or fix asynchronous transfer cleanup. The ATV script is configuration recovery, not a fix for the module's destructor. See the [current integration](msi-integrated-apps.md) for the MSI solution.

## Español

`AD0441/msi-sdr-macos-soapy-fixes` es el repositorio principal. El 15 de noviembre de 2026 se incorporaron el contenido y el historial Git de `AD0441/sdrpp-macos-fixes` antes de retirar ese repositorio.

Los dos proyectos aportan a la compatibilidad SDR en macOS: uno integra el MSI en las aplicaciones existentes y corrige el controlador; el otro recupera dependencias de SDR++ y configuraciones afectadas por ATV Decoder.

El commit de unificación conserva ambos historiales como padres. El commit original `aa3d3c71c6da35510abd22e40520d7a202cb372a` mantiene todos sus archivos, autor, fecha y permisos. La tabla anterior indica dónde quedó cada archivo. Los scripts originales se incorporaron sin cambios; las guías recibieron notas para distinguir su alcance de la integración MSI actual.

Antes de eliminar el repositorio secundario se guardaron un espejo Git completo, un bundle autónomo verificado y sus metadatos. El origen tenía una rama y no tenía etiquetas, incidencias, pull requests, versiones publicadas ni wiki publicada. Ese respaldo local queda fuera del repositorio de código.

La reparación aislada de libusb requiere una biblioteca ya incluida y rutas `@rpath` que la resuelvan. No corrige ABI, módulos ausentes ni la limpieza USB asíncrona. El script de ATV recupera la configuración; su fallo de destructor sigue pendiente. La solución MSI se describe en la [integración actual](msi-integrated-apps.md).
