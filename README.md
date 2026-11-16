<div align="center">
  <h1>MSI-SDR · macOS Fixes</h1>
  <p><strong>Tu receptor, en las aplicaciones que ya usas.<br>Your receiver, in the applications you already use.</strong></p>
  <p>Compatibilidad, integración y estabilidad para MSI2500/MSI001 en macOS.<br>Compatibility, integration and stability for MSI2500/MSI001 on macOS.</p>
  <p>
    <img alt="macOS 26 or later for the tested components" src="https://img.shields.io/badge/macOS-26%2B-183B4A?style=flat-square&amp;logo=apple&amp;logoColor=white">
    <img alt="Apple Silicon arm64" src="https://img.shields.io/badge/Apple_Silicon-arm64-365D72?style=flat-square">
    <img alt="MIT license for this project's original code" src="https://img.shields.io/badge/license-MIT-58616B?style=flat-square">
  </p>
  <p><a href="#es">Español</a> · <a href="#en">English</a> · <a href="#empezar">Empezar</a> · <a href="#getting-started">Get started</a> · <a href="docs/validation-2026-11.md">Validación / Validation</a> · <a href="https://ko-fi.com/C0C51WQ1T0">Apoyar / Support</a></p>
</div>

**Creado por Sebastián Pastén F. / Created by Sebastián Pastén F.**

[![Apoyar / Support on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/C0C51WQ1T0)

<a id="es"></a>

## Español

### Por qué existe

**El problema principal era que las aplicaciones de macOS no reconocían el MSI-SDR.** El receptor podía aparecer en USB o funcionar con herramientas externas, pero no estar disponible como fuente dentro de SDR++, sus variantes o SDRangel. Después de resolver la detección también aparecieron cierres al recibir, cambiar ajustes o detener el equipo.

Este proyecto reúne parches, componentes de integración y pruebas para usar el receptor **MSI2500 + MSI001** en aplicaciones existentes. La propuesta mejora el controlador y su conexión con cada programa. Se construyeron y probaron variantes locales de **SDR++, SDR++Brown, SDR++CE y SDRangel** con el sufijo `MSI Integrado`.

También se conserva el contenido y el historial del antiguo proyecto `sdrpp-macos-fixes`: las reparaciones generales de dependencias y la recuperación del ATV Decoder forman ahora parte de este repositorio. [Detalle de la unificación](docs/repository-consolidation.md).

**Revisión 2026.11.16.1:** se corrigió el falso éxito al fallar comandos USB de inicio/parada o la selección del modo. El controlador conserva el primer error, limpia las transferencias pendientes y vuelve a detectar el receptor en su puerto si un reinicio USB invalida su referencia. [Cambios, pruebas y límites](docs/usb-control-errors.md).

### Qué resuelve

| Problema observado | Solución incorporada | Alcance |
| --- | --- | --- |
| El MSI no aparece como fuente | SoapyMiri, fuente SoapySDR y rutas de carga adaptadas a cada aplicación | Integración MSI2500/MSI001 en las cuatro variantes probadas |
| SDRangel carga un módulo incompatible | SoapyMiri compilado contra su SoapySDR ABI `0.8-3` | El módulo para Homebrew ABI `0.8` requiere una compilación distinta |
| Dependencias USB mezcladas o ausentes | Componentes MSI privados dentro de cada `.app` | La reparación aislada de libusb se conserva para diagnosticar otros bundles |
| Cierres durante recepción o parada | Cancelar y esperar transferencias USB, sincronizar el lector y usar BULK por defecto en macOS | Fallo USB reproducido y corregido en las pruebas documentadas |
| Filtros inválidos o diferencias entre forks | Filtros soportados y un plugin compilado para cada variante de SDR++ | Los plugins de Brown, CE y upstream no son intercambiables |
| Configuración afectada por ATV Decoder | Respaldo y eliminación selectiva de sus instancias guardadas | Recuperación de configuración; el fallo del destructor de ATV sigue pendiente |

### Aplicaciones y receptor

| Aplicación probada | Versión | SoapySDR |
| --- | --- | --- |
| SDR++ | 1.3.0 | ABI `0.8` |
| SDR++Brown | 1.2.1-brown | ABI `0.8`, plugin propio de Brown |
| SDR++CE | 1.2.5-CE_b | ABI `0.8`, plugin propio de CE |
| SDRangel | 7.27.1 | ABI `0.8-3`, revisión `1667b4e6` |

Receptor: ADC **MSI2500 de 12 bits** y sintonizador **MSI001**. Las especificaciones suministradas indican **10 kHz–1 GHz**, ancho de banda comercial de **500 kHz–10 MHz** y TCXO de **24 MHz / 1 ppm**. El controlador se ajustó al rango informado de ese modelo y ofrece filtros discretos hasta **8 MHz**. El ancho comercial de 10 MHz no está implementado en esta biblioteca. No se midieron ENOB, precisión del TCXO, sensibilidad ni rendimiento en todo el rango RF.

Entorno de validación: Apple Silicon arm64, macOS 27.3, SoapySDR 0.8.1 y libusb 1.0.30. Los componentes construidos requieren **macOS 26 o posterior**; la validación funcional corresponde al Mac y las versiones indicadas.

<a id="empezar"></a>

### Empezar

Este repositorio distribuye **código, parches y documentación**. Las cuatro aplicaciones se construyeron localmente a partir de copias originales; aquí no se publican bundles completos ni un instalador automático.

**Recuperación después de formatear:** [guía en español e inglés](RECOVERY.md). Incluye una receta automatizada para reconstruir la integración y restaurar las aplicaciones preservadas. Las apps, sus entradas exactas y los ajustes personales están en un respaldo privado del propietario; el código público funciona como registro duradero del proyecto.

```sh
git clone https://github.com/AD0441/msi-sdr-macos-soapy-fixes.git
cd msi-sdr-macos-soapy-fixes
```

1. Revisa la [integración de las cuatro aplicaciones](docs/msi-integrated-apps.md) y las [revisiones de origen de los parches](patches/README.md).
2. Compila los componentes con el ABI de la aplicación elegida y prepara una copia siguiendo la [estructura de empaquetado](packaging/README.md). Conserva el original antes de modificar una `.app`.
3. Verifica la copia integrada sin abrirla ni acceder al receptor:

   ```sh
   python3 scripts/verify-integrated.py "/Applications/SDR++ MSI Integrado.app"
   ```

4. Con las otras aplicaciones de recepción cerradas, selecciona **SoapySDR → Mirics MSi2500**. Ajuste inicial probado: **2.048 MS/s**, filtro **1.536 MHz**, USB **BULK**. La tasa de muestreo y el ancho del filtro son ajustes distintos.

Cada variante de SDR++ utiliza un perfil separado en `~/Library/Application Support/MSI-SDR/`. SDRangel mantiene sus preferencias nativas y el lanzador activa `--soapy`.

### Pruebas y límites

| Comprobación | Resultado observado |
| --- | --- |
| BULK a 2.048 MS/s durante 120 segundos | **245,763,072 muestras y cero errores de lectura** |
| 30 ciclos de arranque y parada inmediata | Sin bloqueo |
| Error USB simulado que cerraba el driver original | El driver corregido devuelve un error y finaliza sin SIGSEGV |
| SDR++ integrado | Espectro y waterfall observados con el receptor |
| Brown y CE integrados | Arranque de recepción y componentes MSI cargados desde su bundle |
| SDRangel | Enumeración y recepción directa con su ABI `0.8-3` |
| Cuatro copias instaladas | Pruebas breves de muestras reales y firmas verificadas |

Estos resultados no certifican todos los decodificadores, audio ni sesiones prolongadas en cada aplicación. [Evidencia, pruebas reproducibles y límites completos](docs/validation-2026-11.md).

### Herramientas de recuperación

- [Dependencias SoapySDR/libusb de SDR++](fixes/01-libusb-soapysdr-macos.md): `scripts/repair-sdrpp-libusb.sh`. Requiere una libusb ya incluida y rutas `@rpath` resolubles; cambia enlaces y vuelve a firmar la aplicación. No sustituye los parches del controlador ni la integración completa.
- [Recuperación del ATV Decoder](fixes/02-atv-decoder-crash.md): `scripts/remove-atv-decoder-instance.sh`. Crea un respaldo y elimina solamente instancias `atv_decoder` de `config.json`. Para los perfiles MSI separados, indica explícitamente el archivo correspondiente.
- `scripts/verify-sdrpp.sh` y `scripts/verify-sdrangel.sh`: inspección de las instalaciones iniciales. `scripts/verify-integrated.py`: comprobación de las variantes privadas actuales.

Cierra SDR++ antes de utilizar los scripts de recuperación. Cada modificación del bundle exige volver a firmarlo; una actualización de la aplicación puede reemplazar los cambios. MSI-SDR utiliza Mirics/SoapyMiri; `rtl_test` corresponde a otro controlador.

### Contribuir y apoyar

Para [informar un problema](https://github.com/AD0441/msi-sdr-macos-soapy-fixes/issues), incluye modelo del receptor, versión de macOS, aplicación y versión, registro o informe de cierre, y pasos para reproducirlo. Las mejoras del controlador USB pueden compartirse entre proyectos; la integración de cada aplicación debe respetar su ABI y licencia.

Se publicó una [propuesta de colaboración con `olexii4/msi-sdr-radio`](https://github.com/olexii4/msi-sdr-radio/issues/1) sobre estos hallazgos. Es una propuesta de contribución; no implica que ese proyecto haya aceptado los parches.

Puedes apoyar el trabajo en [Ko-fi](https://ko-fi.com/C0C51WQ1T0).

<a id="en"></a>

## English

### Why this project exists

**The main problem was that macOS SDR applications did not recognize the MSI-SDR receiver.** The device could appear on USB or work with external tools while remaining unavailable as an input in SDR++, its variants or SDRangel. After detection was restored, further crashes appeared during reception, setting changes and device shutdown.

This project brings together patches, integration components and tests for using the **MSI2500 + MSI001** receiver in existing applications. The approach improves the driver and its connection to each program. Local **SDR++, SDR++Brown, SDR++CE and SDRangel** variants were built and tested with the suffix `MSI Integrado`.

It also preserves the content and history of the former `sdrpp-macos-fixes` project: general dependency repair and ATV Decoder recovery now live in this repository. [Consolidation details](docs/repository-consolidation.md).

**Revision 2026.11.16.1:** corrected false success after USB start/stop or alternate-setting failures. The driver preserves the first error, drains pending transfers and rediscovers the receiver at its physical port when a USB reset invalidates the handle. [Changes, tests and limitations](docs/usb-control-errors.md).

### What it addresses

| Observed problem | Included solution | Scope |
| --- | --- | --- |
| The MSI is missing from the input list | SoapyMiri, a SoapySDR source and application-specific loading paths | MSI2500/MSI001 integration in the four tested variants |
| SDRangel loads an incompatible module | SoapyMiri built against its SoapySDR ABI `0.8-3` | Homebrew ABI `0.8` needs a separate module build |
| Mixed or missing USB dependencies | Private MSI components inside each `.app` | The standalone libusb repair remains available for diagnosing other bundles |
| Crashes during reception or shutdown | Cancel and drain USB transfers, synchronize the reader and default to BULK on macOS | USB failure reproduced and corrected in the documented tests |
| Invalid filters or fork differences | Supported filters and a separate plugin build for each SDR++ variant | Brown, CE and upstream plugins are not interchangeable |
| Configuration affected by ATV Decoder | Backup and selective removal of saved instances | Configuration recovery; the ATV destructor defect remains unresolved |

### Applications and hardware

| Tested application | Version | SoapySDR |
| --- | --- | --- |
| SDR++ | 1.3.0 | ABI `0.8` |
| SDR++Brown | 1.2.1-brown | ABI `0.8`, Brown-specific plugin |
| SDR++CE | 1.2.5-CE_b | ABI `0.8`, CE-specific plugin |
| SDRangel | 7.27.1 | ABI `0.8-3`, revision `1667b4e6` |

Receiver: **12-bit MSI2500 ADC** and **MSI001 tuner**. The supplied specifications state **10 kHz–1 GHz**, advertised bandwidth of **500 kHz–10 MHz** and a **24 MHz / 1 ppm TCXO**. The driver profile follows that model's reported frequency range and offers discrete filters up to **8 MHz**. The advertised 10 MHz bandwidth is not implemented by this library. ENOB, TCXO accuracy, sensitivity and performance across the full RF range were not measured.

Validation environment: Apple Silicon arm64, macOS 27.3, SoapySDR 0.8.1 and libusb 1.0.30. The built components require **macOS 26 or later**; functional validation applies to the tested Mac and application versions.

<a id="getting-started"></a>

### Getting started

This repository distributes **source code, patches and documentation**. The four applications were built locally from original copies; complete application bundles and an automatic installer are not published here.

**Recovery after reinstalling macOS:** [Spanish and English guide](RECOVERY.md). It includes an automated integration rebuild and restoration of the preserved applications. Exact apps, inputs and personal settings are stored in the owner's private backup; this public repository preserves the durable project context.

```sh
git clone https://github.com/AD0441/msi-sdr-macos-soapy-fixes.git
cd msi-sdr-macos-soapy-fixes
```

1. Read the [four-application integration notes](docs/msi-integrated-apps.md) and [patch base revisions](patches/README.md).
2. Build components against the chosen application's ABI and prepare a copy using the [packaging layout](packaging/README.md). Keep the original before changing a `.app` bundle.
3. Check the integrated copy without launching it or accessing the receiver:

   ```sh
   python3 scripts/verify-integrated.py "/Applications/SDR++ MSI Integrado.app"
   ```

4. Close other receiving applications, then select **SoapySDR → Mirics MSi2500**. Tested starting settings: **2.048 MS/s**, **1.536 MHz** filter, USB **BULK**. Sample rate and filter bandwidth are separate settings.

Each SDR++ variant uses a separate profile under `~/Library/Application Support/MSI-SDR/`. SDRangel retains its native preferences, with `--soapy` enabled by the launcher. Detailed technical notes currently use Spanish; commands, paths and revision identifiers are shared.

### Validation and limits

| Check | Observed result |
| --- | --- |
| BULK at 2.048 MS/s for 120 seconds | **245,763,072 samples and zero read errors** |
| 30 immediate start/stop cycles | No hang |
| Injected USB error that crashed the original driver | Patched driver reports an error and exits without SIGSEGV |
| Integrated SDR++ | Live spectrum and waterfall observed with the receiver |
| Integrated Brown and CE | Reception started and MSI components loaded from their bundles |
| SDRangel | Enumeration and direct reception with its ABI `0.8-3` |
| Four installed copies | Brief real-sample checks and signature verification |

These results do not certify every decoder, audio path or extended session in each application. [Evidence, reproducible tests and full limitations](docs/validation-2026-11.md).

### Recovery tools

- [SDR++ SoapySDR/libusb dependency repair](fixes/01-libusb-soapysdr-macos.md): `scripts/repair-sdrpp-libusb.sh`. Requires an existing bundled libusb and resolvable `@rpath` paths; changes dependency references and re-signs the application. It does not replace driver patches or the full integration.
- [ATV Decoder recovery](fixes/02-atv-decoder-crash.md): `scripts/remove-atv-decoder-instance.sh`. Backs up `config.json` and removes only `atv_decoder` instances. Pass the appropriate configuration file explicitly for the separate MSI profiles.
- `scripts/verify-sdrpp.sh` and `scripts/verify-sdrangel.sh`: inspect the initial installations. `scripts/verify-integrated.py`: inspect the current private variants.

Close SDR++ before using recovery scripts. Bundle changes require re-signing, and application updates may replace them. MSI-SDR uses Mirics/SoapyMiri; `rtl_test` belongs to a different driver.

### Contributing and support

When [reporting an issue](https://github.com/AD0441/msi-sdr-macos-soapy-fixes/issues), include the receiver model, macOS version, application and version, log or crash report, and reproduction steps. USB driver improvements can be shared across projects; each application's integration must respect its ABI and license.

A [collaboration proposal for `olexii4/msi-sdr-radio`](https://github.com/olexii4/msi-sdr-radio/issues/1) describes these findings. It is a contribution proposal; it does not mean that project has accepted the patches.

You can support this work on [Ko-fi](https://ko-fi.com/C0C51WQ1T0).

## Sources and license / Fuentes y licencia

- [SDR++](https://github.com/AlexandreRouma/SDRPlusPlus)
- [SDR++Brown](https://github.com/sannysanoff/SDRPlusPlusBrown)
- [SDR++CE](https://github.com/LunaeMons/SDRPlusPlus_CommunityEdition)
- [SDRangel](https://github.com/f4exb/sdrangel)
- [SoapySDR](https://github.com/pothosware/SoapySDR)
- [SoapyMiri](https://github.com/ericek111/SoapyMiri)
- [libmirisdr-4](https://github.com/f4exb/libmirisdr-4)

Código original de este proyecto: [MIT](LICENSE). Los parches y componentes de terceros conservan las licencias y avisos de sus proyectos de origen.

This project's original code: [MIT](LICENSE). Third-party patches and components retain their upstream licenses and notices.

<div align="center">
  <p><strong>Simplicidad con impacto.</strong><br>Concéntrate en lo que vale la pena.</p>
  <p><a href="https://github.com/AD0441/NABERIUS">NABERIUS</a> · <a href="https://github.com/AD0441/RAZIEL">RAZIEL</a> · <a href="https://github.com/AD0441/METATRON">METATRON</a> · <a href="https://github.com/AD0441/PAIMON">PAIMON</a> · <a href="https://github.com/AD0441/VAPULA">VAPULA</a></p>
  <p><strong>Creado por Sebastián Pastén F. / Created by Sebastián Pastén F.</strong></p>
  <p><a href="https://www.sebastianpasten.com/desarrollos-aplicaciones-para-mac-software-sdr">Más aplicaciones para Mac / More Mac applications</a> · <a href="https://ko-fi.com/C0C51WQ1T0">Apoyar / Support on Ko-fi</a></p>
</div>
