# Recuperar el proyecto / Recover the project

[Español](#español) · [English](#english)

## Español

Este documento permite continuar el trabajo sin el chat ni las carpetas del
Mac anterior. El código público y los archivos privados de recuperación se
complementan. Hay dos caminos: recuperar las aplicaciones exactas que ya
funcionaban, o reconstruir la integración desde sus entradas guardadas.

### Qué está guardado

| Lugar | Contenido |
| --- | --- |
| Este repositorio | Parches, lanzadores, perfiles iniciales sin datos personales, pruebas, recetas, revisiones y límites conocidos |
| [Respaldo privado del propietario](https://github.com/AD0441/msi-sdr-macos-recovery/releases/tag/recovery-2026.11.16.1) | Cuatro apps originales, cuatro integradas 2026.11.16.1, cuatro versiones anteriores, fuentes y SDK de construcción congelado |
| Índice privado `private-manifest.json` | Nombres, tamaños y SHA-256 de los archivos anteriores, ajustes SDR personales y notas/herramientas del trabajo local |
| Respaldo `public-project.bundle` en esa misma release | Copia del historial Git público hasta la revisión indicada en `RECOVERY-STATUS.json` |

El respaldo privado requiere iniciar sesión con AD0441 o una cuenta a la que
el propietario dé acceso. Los binarios grandes están en **Releases**; no
aparecen al descargar solamente el ZIP del código. Los ajustes personales
se conservan aparte y no se importan automáticamente. No se respaldan tokens
de GitHub, llaveros ni credenciales del sistema.

### Recuperación rápida después de formatear

Requisitos: Apple Silicon, macOS 26 o posterior y acceso al respaldo privado.

1. Abre la release privada y descarga los cuatro archivos
   `ready-…-2026.11.16.1.zip`.
2. Compara sus SHA-256 con `recovery/manifest.json` (`shasum -a 256 archivo.zip`).
   Descomprime en una carpeta nueva. Comprueba cada firma con
   `codesign --verify --deep --strict "SDR++ MSI Integrado.app"`, cambiando el
   nombre para las otras tres aplicaciones.
3. Copia las aplicaciones verificadas a Aplicaciones conservando cualquier
   versión que ya tengas. Abre una sola aplicación receptora a la vez y
   selecciona **SoapySDR → Mirics MSi2500**; comienza con 2.048 MS/s, filtro
   1.536 MHz y BULK. SDRangel usa `--soapy` desde su lanzador.

También puede hacerse con Python 3.9+, Git y GitHub CLI ya instalados:

```sh
git clone https://github.com/AD0441/msi-sdr-macos-soapy-fixes.git
cd msi-sdr-macos-soapy-fixes
gh auth login
python3 scripts/msi_recovery.py fetch --cache ../msi-cache --scope ready
python3 scripts/msi_recovery.py restore --cache ../msi-cache --output ../msi-restored
```

`restore` exige una carpeta vacía, verifica cada archivo y su firma, y deja
las cuatro `.app` listas para revisar. No modifica Aplicaciones ni perfiles.
Para volver a la versión anterior: descarga `--scope previous` y usa
`restore --previous` con otra carpeta vacía. `--variant sdrpp`, `brown`, `ce`
o `sdrangel` permite recuperar una sola aplicación.

### Reconstruir la integración

Además de Python/Git y acceso privado para descargar las entradas, instala
las herramientas de desarrollo de Apple (`xcode-select --install`) con SDK
macOS 26 o posterior. GitHub CLI solo se necesita para descargar. El SDK
congelado contiene las cabeceras y bibliotecas de terceros utilizadas; la
construcción no depende de un Homebrew existente ni de las apps MSI instaladas.

```sh
python3 scripts/msi_recovery.py doctor
python3 scripts/msi_recovery.py fetch --cache ../msi-cache --scope inputs
python3 scripts/msi_recovery.py build --cache ../msi-cache \
  --work ../msi-rebuild --output ../msi-rebuilt-apps
python3 scripts/verify-integrated.py ../msi-rebuilt-apps/*.app
```

Usa una carpeta de trabajo inicialmente vacía y una salida nueva. Se
verifican los archivos originales, se aplican los parches en orden y se
comparan las fuentes resultantes con las huellas de la versión probada.
Después se compilan libmirisdr, SoapyMiri para ABI `0.8` y `0.8-3`, los tres
plugins SDR++ y las entradas; se empaqueta y firma cada copia. Los registros,
comandos y dependencias de cabeceras quedan en `msi-rebuild/components/`;
`rebuild-results.json` identifica las salidas y sus SHA-256.

Esto reconstruye **nuestra integración**, usando los núcleos originales y
bibliotecas guardadas. No compila desde cero Qt, todos los decodificadores
ni los núcleos completos de las cuatro aplicaciones. Una nueva compilación
puede tener otro SHA-256 por firmas, rutas y versión del compilador. Para
recuperar exactamente los paquetes preservados usa `restore`.

### Estado, límites y continuidad

- Versión preservada: **2026.11.16.1**, Apple Silicon arm64, macOS mínimo 26.
- Fuentes y orden de parches: [manifest](recovery/manifest.json) y
  [bases de los parches](patches/README.md). Brown y CE utilizan snapshots
  candidatos cuyas cabeceras coinciden; el commit original de sus núcleos
  binarios no se pudo demostrar.
- Firmas locales ad hoc: no hay certificado Developer ID ni notarización.
- SDRangel original ya incluía componentes opcionales incompletos. La receta
  aparta plugins SQL/SDRplay y la utilidad `sdrangelbench` cuando faltan sus
  SDK; conserva e identifica la dependencia Orbbec ausente de OpenCV videoio.
  Esas funciones de cámara/base de datos/bench no están validadas como parte
  de la recepción MSI. No se añade el SDK propietario SDRplay.
- El workflow público comprueba integridad del manifiesto, extracción segura
  y sintaxis. No tiene acceso a los archivos privados ni a un receptor USB.
- La evidencia de recuperación descargada y reconstruida se registra en
  [docs/recovery-validation.json](docs/recovery-validation.json). Es una
  prueba en carpetas nuevas del mismo Mac, no una instalación en un Mac
  recién formateado ni certificación de todas las funciones de cada app.
- Pruebas de radio y pendientes: [validación](docs/validation-2026-11.md) y
  [errores USB](docs/usb-control-errors.md). Siguen pendientes desconexión
  física, sesiones largas de interfaz/audio y mediciones RF.
- Un futuro asistente debe comenzar por [AGENTS.md](AGENTS.md). Las notas
  históricas privadas aportan contexto; las rutas antiguas que contienen
  son evidencia, no requisitos de construcción.

Si desapareciera el repositorio público, descarga `public-project.bundle`
del respaldo privado, verifica su huella con `RECOVERY-STATUS.json`, ejecuta
`git bundle verify public-project.bundle` y recupéralo con
`git clone public-project.bundle msi-sdr-macos-soapy-fixes`.

Para preservar una mejora futura: prueba, actualiza código/manifiesto y
documentación, publica el commit, sube nuevas entradas o apps bajo **otra
release** privada, y verifica una descarga en caché vacía. Actualiza también
el bundle y su índice; los scripts no respaldan automáticamente cambios
futuros ni guardan esta conversación.

## English

This repository and its owner-only recovery release preserve the project
without requiring the old chat or local workspace. Public code includes the
patches, launchers, clean initial profiles, tests and locked recipe. The
[private release](https://github.com/AD0441/msi-sdr-macos-recovery/releases/tag/recovery-2026.11.16.1)
contains original, ready and previous applications, upstream source snapshots
and the frozen build SDK. Personal SDR settings and historical work are
indexed only in the private manifest. GitHub credentials and system keychains
are excluded. Release assets are separate from a source-code ZIP.

### Restore the exact saved applications

On an Apple Silicon Mac running macOS 26+, sign in to an authorized GitHub
account, download the four `ready-…-2026.11.16.1.zip` assets, verify their
SHA-256 against [the manifest](recovery/manifest.json), extract into a new
folder, verify each bundle with `codesign --verify --deep --strict`, then
copy the checked applications to Applications while keeping existing copies.
The command-line equivalent requires Python 3.9+, Git and GitHub CLI:

```sh
git clone https://github.com/AD0441/msi-sdr-macos-soapy-fixes.git
cd msi-sdr-macos-soapy-fixes
gh auth login
python3 scripts/msi_recovery.py fetch --cache ../msi-cache --scope ready
python3 scripts/msi_recovery.py restore --cache ../msi-cache --output ../msi-restored
```

Restore refuses a nonempty output and does not modify Applications or import
personal settings. Use `fetch --scope previous` and `restore --previous` in
another empty output folder for rollback. `--variant` selects a single app.
Close other receiving apps before selecting SoapySDR/Mirics MSi2500. Tested
starting settings: 2.048 MS/s, 1.536 MHz filter, BULK.

### Rebuild the integration from locked inputs

Install Apple Command Line Tools with a macOS 26+ SDK. GitHub CLI is only
needed for downloading. No installed MSI application or live Homebrew is a
build input:

```sh
python3 scripts/msi_recovery.py doctor
python3 scripts/msi_recovery.py fetch --cache ../msi-cache --scope inputs
python3 scripts/msi_recovery.py build --cache ../msi-cache \
  --work ../msi-rebuild --output ../msi-rebuilt-apps
python3 scripts/verify-integrated.py ../msi-rebuilt-apps/*.app
```

Use an initially empty work folder and a new output folder. The recipe checks
asset hashes, original core fingerprints and patched source hashes, then
builds libmirisdr, both SoapyMiri ABIs, each fork's source plugin and the entry
components. It packages and locally signs copies of the original apps.
Compiler commands, header dependencies and logs are retained in
`msi-rebuild/components/`; output hashes are in `rebuild-results.json`.

This rebuilds our integration against frozen original cores and dependencies;
it does not rebuild all of Qt or every decoder/core from source. Rebuilds are
not promised to be byte-identical. Use restore for the exact saved archives.
Brown/CE source revisions are matching-header candidates, not proven original
binary-core revisions. Bundles are ad hoc signed, without Developer ID or
notarization. Incomplete optional SDRangel SQL/SDRplay/bench components are
set aside; the original missing Orbbec camera dependency is recorded and that
camera path is not validated for this MSI workflow.

See [recovery evidence](docs/recovery-validation.json) for the fresh-folder,
downloaded-input checks on the same Mac. These are not a freshly formatted
machine test. Public CI runs offline guardrails, not radio tests or private
asset builds. Physical unplug/replug, extended GUI/audio sessions and RF
calibration remain pending; see the [runtime evidence](docs/validation-2026-11.md).

Future assistants should read [AGENTS.md](AGENTS.md). If the public repository
is lost, verify the private `public-project.bundle` using the private
`RECOVERY-STATUS.json`, then run `git bundle verify public-project.bundle`
and `git clone public-project.bundle msi-sdr-macos-soapy-fixes`.

Future releases need a new tested public commit, new private assets when
inputs/apps change, a fresh-download check and an updated bundle/index. This
snapshot does not automatically preserve later changes or chat messages.

Support / Apoyar: [Ko-fi](https://ko-fi.com/C0C51WQ1T0).
