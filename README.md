# MSI-SDR macOS Soapy fixes

Solucion reproducible para usar receptores **MSI.SDR / Mirics MSi2500 / RSP1 compatible** en macOS Apple Silicon con **SDRangel**, **SDR++**, **SDR++Brown** y **SDR++CE** mediante SoapySDR.

## Actualizacion de noviembre de 2026

Se reprodujo un cierre USB que persistia incluso con la misma libusb en la app y en el driver. La correccion completa espera las terminaciones de las transferencias antes de liberar memoria, sincroniza inicio/parada y utiliza BULK en macOS.

- [Integracion de las cuatro aplicaciones y componentes probados](docs/msi-integrated-apps.md).
- [Resultados y limites de la validacion](docs/validation-2026-11.md).
- [Parches y revisiones de origen](patches/README.md).
- [Lanzador nativo y componentes de empaquetado](packaging/README.md).

Prueba con receptor conectado: **120 segundos a 2.048 MS/s, 245,763,072 muestras y cero errores de lectura**, usando BULK. No representa una prueba prolongada de todas las funciones de cada aplicacion.

El problema no era un unico driver faltante. La solucion estable combino tres ajustes:

1. Compilar SoapyMiri contra el ABI correcto de SoapySDR cuando se usa dentro de SDRangel.
2. Agregar `soapy_source.dylib` a SDR++ para que pueda usar dispositivos SoapySDR.
3. Evitar que SDR++ y `libmirisdr` carguen versiones distintas de `libusb`.

## Equipo probado

```text
Apple Silicon arm64
macOS 27.3 (validacion inicial: 27.0)
SDRangel 7.27.1
SDR++ 1.3.0
SDR++Brown 1.2.1-brown
SDR++CE 1.2.5-CE_b
SoapySDR 0.8.1
SoapyMiri d94629b + parches de este repositorio
libmirisdr-4 fd0452e + parches de este repositorio
libusb 1.0.30 (Mach-O current version 7.0.0)
Mirics MSi2500 / RSP1 compatible
```

## Resultado final

- SoapySDR detecta el MSi2500.
- SDRangel funciona con el modulo SoapyMiri compilado contra el ABI correcto.
- SDR++ carga `soapy_source`.
- SDR++ funciona con `Sample rate = 2.048 MS/s` y `Bandwidth = 1.536 MHz`.
- SDR++ y `libmirisdr` usan la misma `libusb` 7.0.0.
- Las aplicaciones modificadas quedan firmadas nuevamente en macOS.
- Las variantes integradas cargan sus bibliotecas MSI desde el mismo bundle.
- Se verifican los ZIP descomprimidos y se comparan sus archivos con las copias instaladas.

## Diagnostico corto

### SDRangel

SDRangel trae su propia version de SoapySDR:

```text
SDRangel SoapySDR interno: ABI 0.8-3
SoapySDR Homebrew:        ABI 0.8
```

Un modulo SoapyMiri compilado contra Homebrew puede cargar parcialmente, pero queda expuesto a fallos de ABI, por ejemplo en metodos virtuales como:

```text
listGPIOBanks()
getSettingInfo()
```

La solucion fue compilar SoapyMiri contra el commit de SoapySDR usado por SDRangel:

```text
1667b4e6
SoapySDR 0.8.1-g1667b4e6
ABI 0.8-3
```

Ver: [docs/sdrangel-abi-fix.md](docs/sdrangel-abi-fix.md).

### SDR++

SDR++ tenia dos problemas separados.

Primero, cuando quedaba configurado con:

```text
Sample rate: 9 MS/s
Bandwidth: Auto
```

SDR++ seleccionaba un ancho de banda de `14 MHz`. `mirisdr_set_bandwidth()` lo rechazaba y SoapyMiri lanzaba una excepcion no capturada.

Configuracion estable:

```text
Sample rate: 2.048 MS/s
Bandwidth: 1.536 MHz
```

Segundo, SDR++ incluia una copia interna de `libusb` con version actual `6.0.0`, mientras `libmirisdr` de Homebrew usaba `7.0.0`. Era necesario unificar estas bibliotecas. Los cierres se situaban en:

```text
org.libusb.device-hotplug
darwin_async_io_callback
```

La revision posterior encontro cierres en esa misma funcion incluso despues de unificar libusb. Un error simulado en `libusb_submit_transfer` reprodujo el cierre: el driver liberaba transferencias que todavia tenian callbacks pendientes. La correccion cancela y drena esas operaciones antes de liberar memoria. La preferencia por BULK evita ademas las interrupciones observadas con la ruta isocrona en este Mac.

Ver: [docs/sdrpp-soapymiri-fix.md](docs/sdrpp-soapymiri-fix.md).

## Verificacion rapida

```bash
scripts/verify-sdrangel.sh
scripts/verify-sdrpp.sh
```

Los scripts solo inspeccionan binarios, dependencias y firma. No modifican aplicaciones. Para las nuevas variantes integradas:

```bash
python3 scripts/verify-integrated.py "/Applications/SDR++ MSI Integrado.app"
```

## Parche propuesto

El archivo [patches/soapymiri-bandwidth-safety.patch](patches/soapymiri-bandwidth-safety.patch) propone que SoapyMiri no aborte cuando una aplicacion solicita un ancho de banda no soportado exactamente. En vez de lanzar una excepcion fatal, selecciona el ancho valido mas cercano.

Ese parche minimo se conserva como antecedente. La implementacion validada esta en `patches/soapymiri-msi-macos-stability.patch`; no se deben aplicar ambos parches de bandwidth a la misma copia. Los cambios USB y de cada fork se describen en [patches/README.md](patches/README.md).

## Advertencias

- Haz respaldo de cualquier `.app` antes de modificarlo.
- Cada cambio dentro de un bundle `.app` invalida la firma y exige volver a firmar.
- Una actualizacion de SDR++ o SDRangel puede reemplazar los cambios.
- Los componentes utilizados en esta entrega requieren macOS 26 o posterior. No se afirma compatibilidad con sistemas anteriores por el minimo declarado de la app original.
- Esta guia no convierte MSI.SDR en RTL-SDR. El hardware va por Mirics/SoapyMiri, no por `rtl_test`.

## Fuentes y repositorios utiles

- SDR++: https://github.com/AlexandreRouma/SDRPlusPlus
- SDR++ nightly: https://www.sdrpp.org/nightly
- SDRangel: https://github.com/f4exb/sdrangel
- SoapySDR: https://github.com/pothosware/SoapySDR
- SoapyMiri: https://github.com/ericek111/SoapyMiri
- libmirisdr-4: https://github.com/f4exb/libmirisdr-4
