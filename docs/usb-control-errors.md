# USB error recovery — 2026.11.16.1 / Recuperación de errores USB

## Español

Esta revisión implementa el primer hito del plan: comunicar fallos reales al seleccionar el modo USB, iniciar, pausar, reanudar o detener la recepción, y permitir una sesión nueva después del fallo.

### Problema reproducido

Una prueba que sustituye una respuesta USB por `LIBUSB_ERROR_TIMEOUT` (`-7`) mostró que la entrega anterior devolvía éxito. Ocurrió tanto en `mirisdr_read_async` como en las operaciones de SoapyMiri: el arranque podía indicar éxito sin entregar muestras y la parada podía ocultar un error. Las cuatro comprobaciones iniciales fallaron como se esperaba al probar ese comportamiento.

### Cambios

- `libmirisdr` devuelve la respuesta USB de inicio y parada. Si no puede seleccionar el modo BULK/ISOC, abandona el arranque.
- Una variable atómica conserva el primer error. Un fallo secundario durante la limpieza no lo reemplaza.
- Los fallos pasan por la cancelación y espera de callbacks ya incorporada en la revisión anterior. Nunca se omite esa limpieza para devolver antes el error.
- Las rutas de pausa y reanudación también comunican el fallo y dejan que el lector termine su limpieza.
- Se reclama la interfaz antes de reiniciar o configurar el receptor. Una interfaz ocupada produce un error y no se reinicia ese equipo.
- Si el reinicio invalida el handle, se cierra y se busca de nuevo solo el mismo VID/PID, bus y ruta física. La búsqueda tiene hasta 80 consultas con pausas de 25 ms; no repite el reinicio ni cambia a otro receptor igual.
- Se comprueban los comandos previos al arranque y las cinco escrituras de inicialización del ADC. El error de apertura llega al mensaje de SoapyMiri con su código.
- SoapyMiri espera la llegada de las primeras muestras o el fallo del lector antes de confirmar el arranque. Si no llega ninguna, aplica un plazo de tres segundos y solicita la parada y limpieza; ese plazo no autoriza liberar operaciones USB todavía pendientes.
- Las lecturas pendientes se despiertan al finalizar el lector, y la parada devuelve un error si falló el USB.
- El plugin de SDR++ comprueba el resultado de activación antes de crear su hilo lector. Los plugins de Brown y CE ya realizaban esa comprobación.
- Los tres plugins evitan pasar una tasa cero o no finita al núcleo si falla la apertura. Mantienen la fuente sin activar y disponible para volver a detectar, en lugar de iniciar DSP con un ajuste inválido.
- En macOS, la indicación de driver activo es informativa: la exclusividad la determina el intento real de reclamar la interfaz. No se interpreta automáticamente cualquier cliente de IORegistry como un receptor ocupado.

No se cambia el ABI público de SoapySDR ni se añade una función pública a libmirisdr. Se mantiene la separación entre módulos SoapySDR `0.8` y `0.8-3`.

### Validación

- Seis escenarios del controlador: error de inicio, parada, selección de interfaz, pausa, reanudación y dos errores consecutivos. Cada uno conservó el código esperado y volvió a recibir con el mismo handle.
- Cuatro escenarios de SoapyMiri ABI `0.8`: inicio, parada, selección y error secundario durante la limpieza. Todos devolvieron error y permitieron recibir después.
- Tres escenarios con ABI `0.8-3` de SDRangel: inicio, parada y selección. Todos pasaron.
- Tres escenarios adicionales de apertura: reinicio que requiere volver a detectar, interfaz ocupada e inicialización del ADC fallida. Se verificaron handles abiertos/cerrados equilibrados, recepción posterior y ausencia de reinicios al rechazar la interfaz ocupada.
- Una indicación simulada de driver activo no impide recibir cuando la reclamación exclusiva sí tiene éxito.
- Cien ciclos de arranque/parada con muestras, reinicio, cambios 2.048 ↔ 6 MS/s y destrucción activa completados.
- Recepción continua de 120 segundos a 2.048 MS/s: **245.772.288 muestras, cero errores de lectura**, sin interpositor ni fallos simulados.
- El interpositor comprobó que las transferencias sometidas a libusb se liberaran sin operaciones pendientes. Terminó con `pending=0` y el mismo número de transferencias registradas y liberadas.
- Siete comprobaciones de aplicación: SDR++ ante error de inicio; SDR++, Brown y CE ante interfaz ocupada; y arranque normal de las tres variantes. Los procesos permanecieron vivos durante diez segundos; las pruebas normales registraron inicio de recepción y las de error no activaron la fuente. Se usaron perfiles separados y se terminaron los procesos de prueba de forma explícita; no se afirma un cierre gráfico completo.

Resultados estructurados: [evidencia de validación](../tests/results/usb-control-errors-2026-11-16.json).

Las cuatro variantes locales quedaron instaladas como `MSI Integrado`, revisión `2026.11.16.1`. Cada instalación recibió 2.064.384 muestras en una prueba breve sin errores; se confirmaron sus bibliotecas privadas, firmas y huellas de componentes. Los ZIP nuevos y anteriores se descomprimieron y compararon con sus respectivos bundles. SDRangel completó además `--help` con salida cero. Los bundles son entregas locales; no se publican binarios de terceros en este repositorio.

Los errores se inyectan únicamente en procesos de prueba; el interpositor no se instala en las aplicaciones. La reconexión física, una hora de recepción y la validación visual completa de las cuatro aplicaciones siguen siendo etapas posteriores. Esta revisión no corrige todavía todas las escrituras de registros de inicialización ni implementa los nuevos contadores de pérdidas.

Durante la prueba entre paquetes se observó un fallo real `LIBUSB_ERROR_NOT_FOUND` al reiniciar, seguido de `LIBUSB_ERROR_NO_DEVICE` al intentar reclamar la referencia antigua. La consulta posterior encontró el MSI en el mismo puerto, con dirección USB distinta. La [documentación de libusb](https://libusb.sourceforge.io/api-1.0/group__libusb__dev.html) especifica que un reinicio puede invalidar el handle y requerir cerrar y redescubrir el dispositivo. La prueba controlada de esa ruta confirmó dos aperturas y dos cierres, un solo reinicio y muestras reales después. La ocupación y el fallo del ADC se simularon; no equivalen a probar otra aplicación activa o una desconexión física.

## English

This revision implements the first milestone: report USB failures when selecting the transport, starting, pausing, resuming or stopping reception, clean up pending transfers safely, and allow a new session after failure.

Replacing one USB response with `LIBUSB_ERROR_TIMEOUT` (`-7`) reproduced false success in the previous driver and SoapyMiri delivery. All four initial regression checks failed as expected: start could report success without delivering samples, and stop could hide a USB error.

The driver now returns start/stop errors, aborts on alternate-setting failure, and preserves the first failure in an atomic field. Cleanup still cancels and drains all pending callbacks before freeing transfers. Pause/resume errors also reach the reader's cleanup path.

The interface is claimed before reset or configuration, so a busy receiver is rejected without resetting it. If reset invalidates the handle, the driver closes it and rediscovers only the same VID/PID, bus and physical port path. Discovery is limited to 80 polls separated by 25 ms; it does not issue another reset or select another same-model receiver. Pre-start commands and all five ADC initialization writes are checked, and SoapyMiri includes the USB code in an open-failure message.

SoapyMiri waits for the first samples or worker failure before confirming activation. A three-second no-data deadline requests cancellation and cleanup; it does not allow pending USB transfers to be freed early. Readers wake when the worker finishes, and deactivation reports a USB failure. The upstream SDR++ plugin now checks activation status; Brown and CE already did so.

All three plugins avoid passing zero or non-finite sample rates to the core after open failure. The source remains inactive and available for rediscovery. On macOS, a reported driver-active flag is advisory: actual interface claiming determines exclusivity, rather than treating every IORegistry child as a busy receiver.

No public SoapySDR ABI changes or new public libmirisdr functions are introduced. ABI `0.8` and SDRangel ABI `0.8-3` remain separate builds.

Validation covered six driver fault scenarios, four SoapyMiri ABI `0.8` scenarios and three SDRangel ABI `0.8-3` scenarios. Each reported failure and recovered real samples. One hundred start/stop cycles with samples, restart, 2.048 ↔ 6 MS/s transitions and active destruction also completed. The test interposer confirmed no pending transfer was freed and recorded balanced transfer lifetimes.

A normal 120-second reception at 2.048 MS/s delivered **245,772,288 samples with zero read errors**, without the interposer or injected faults.

Three additional open-path scenarios passed: reset requiring rediscovery, busy interface and ADC initialization failure. The reset test recorded two opens, two closes, one reset and subsequent real samples. The busy test confirmed zero resets before rejecting ownership. These are controlled error scenarios, not physical-disconnection or concurrent-application validation. A real reset/old-handle failure was also observed while switching test bundles; a subsequent descriptor read found the receiver at a new USB address on the same physical port.

An additional advisory-driver flag scenario confirmed successful reception when actual interface claiming succeeds. Seven application smoke cases also passed: SDR++ start failure, a busy interface in SDR++/Brown/CE, and normal startup in all three. Each process remained alive for ten seconds; normal cases logged reception startup and error cases kept the source inactive. Tests used separate profiles and intentional process termination, not a complete graphical shutdown check. [Structured evidence](../tests/results/usb-control-errors-2026-11-16.json).

All four local `MSI Integrado` variants were installed as revision `2026.11.16.1`. Each installed runtime delivered 2,064,384 samples without read errors in a brief check; private libraries, signatures and component hashes were verified. New and previous ZIP archives were extracted and compared to their respective bundles. Native SDRangel also completed `--help` with exit zero. Application bundles remain local deliveries; third-party binaries are not published in this repository.

Physical reconnects, hour-long reception and complete GUI validation remain later stages. This milestone does not yet check every initialization register write or implement the new loss counters.

The legacy sample-counter diagnostic can show a large unsigned value at the first block when the initial expected counter differs by one. That isolated startup message is not evidence of billions of missing samples. The planned per-block counter work remains separate; zero read errors here does not certify full end-to-end sample continuity.

## Apply order / Orden de aplicación

These are **follow-up patches**, applied after the previously documented stability patches:

| Component | Previous patch | Follow-up |
| --- | --- | --- |
| libmirisdr-4 | `libmirisdr-async-lifetime.patch` | `libmirisdr-usb-control-errors.patch` |
| SoapyMiri | `soapymiri-msi-macos-stability.patch` | `soapymiri-usb-control-errors.patch` |
| Upstream SDR++ source plugin | `sdrpp-soapy-stability.patch` | `sdrpp-activation-errors.patch` |
| Brown source plugin | `sdrpp-brown-soapy-stability.patch` | `sdrpp-brown-open-errors.patch` |
| CE source plugin | `sdrpp-ce-soapy-stability.patch` | `sdrpp-ce-open-errors.patch` |

Use the base revisions in [patches/README.md](../patches/README.md), apply the previous patch, then run `git apply --check` and apply the follow-up. Build the driver as C11. Rebuild all three SoapyMiri translation units using the matching SoapySDR headers/library; a module build cannot be shared across ABI `0.8` and `0.8-3`.

## Reproduce / Reproducir

Use one connected MSI and close other receiving applications. The runtime must contain the patched driver, matching SoapySDR and module, and libusb. Build probes with the same headers and libraries as that runtime. The following example uses ABI `0.8`; change both the headers and library filename for `0.8-3`.

```sh
MSI_RUNTIME="/absolute/path/to/private-runtime"
MSI_SOAPY_HEADERS="/absolute/path/to/SoapySDR/include"
MSI_MIRI_HEADERS="/absolute/path/to/libmirisdr-4/include"

c++ -std=c++11 -O2 -I"$MSI_MIRI_HEADERS" tests/msi-driver-error.cpp \
  "$MSI_RUNTIME/lib/libmirisdr.4.dylib" \
  -Wl,-rpath,"$MSI_RUNTIME/lib" -o /tmp/msi-driver-error

c++ -std=c++11 -O2 -I"$MSI_MIRI_HEADERS" tests/msi-open-recovery.cpp \
  "$MSI_RUNTIME/lib/libmirisdr.4.dylib" \
  -Wl,-rpath,"$MSI_RUNTIME/lib" -o /tmp/msi-open-recovery

c++ -std=c++11 -O2 -I"$MSI_SOAPY_HEADERS" tests/msi-control-recovery.cpp \
  "$MSI_RUNTIME/lib/libSoapySDR.0.8.dylib" \
  -Wl,-rpath,"$MSI_RUNTIME/lib" -o /tmp/msi-control-recovery

cc -std=c11 -dynamiclib tests/inject-control-failure.c \
  $(pkg-config --cflags libusb-1.0) \
  "$MSI_RUNTIME/lib/libusb-1.0.0.dylib" \
  -Wl,-rpath,"$MSI_RUNTIME/lib" -o /tmp/msi-control-failure.dylib

python3 tests/run-control-recovery.py --runtime "$MSI_RUNTIME" \
  --driver-probe /tmp/msi-driver-error --soapy-probe /tmp/msi-control-recovery \
  --open-probe /tmp/msi-open-recovery \
  --injector /tmp/msi-control-failure.dylib --output /tmp/msi-control-results.json
```

`DYLD_INSERT_LIBRARIES` is set only for each child test process. Do not add it to shell startup files or application launchers. The injector deliberately suppresses selected USB commands, so results describe controlled fault recovery, not a physical cable-disconnect test.
