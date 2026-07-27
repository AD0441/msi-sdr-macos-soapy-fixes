# MSI-SDR macOS Soapy fixes

Solucion reproducible para usar receptores **MSI.SDR / Mirics MSi2500 / RSP1 compatible** en macOS Apple Silicon con **SDRangel** y **SDR++** mediante SoapySDR.

El problema no era un unico driver faltante. La solucion estable combino tres ajustes:

1. Compilar SoapyMiri contra el ABI correcto de SoapySDR cuando se usa dentro de SDRangel.
2. Agregar `soapy_source.dylib` a SDR++ para que pueda usar dispositivos SoapySDR.
3. Evitar que SDR++ y `libmirisdr` carguen versiones distintas de `libusb`.

## Equipo probado

```text
Apple Silicon arm64
macOS 27.0
SDRangel 7.27.1
SDR++ 1.3.0
SoapySDR 0.8.1
SoapyMiri d94629b
Mirics MSi2500 / RSP1 compatible
```

## Resultado final

- SoapySDR detecta el MSi2500.
- SDRangel funciona con el modulo SoapyMiri compilado contra el ABI correcto.
- SDR++ carga `soapy_source`.
- SDR++ funciona con `Sample rate = 2.048 MS/s` y `Bandwidth = 1.536 MHz`.
- SDR++ y `libmirisdr` usan la misma `libusb` 7.0.0.
- Las aplicaciones modificadas quedan firmadas nuevamente en macOS.

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

Segundo, SDR++ incluia una copia interna de `libusb` con version actual `6.0.0`, mientras `libmirisdr` de Homebrew usaba `7.0.0`. Eso provocaba caidas en:

```text
org.libusb.device-hotplug
darwin_async_io_callback
```

La solucion fue reemplazar la `libusb` dentro de SDR++ por la misma version usada por Homebrew y volver a firmar la app.

Ver: [docs/sdrpp-soapymiri-fix.md](docs/sdrpp-soapymiri-fix.md).

## Verificacion rapida

```bash
scripts/verify-sdrangel.sh
scripts/verify-sdrpp.sh
```

Los scripts solo inspeccionan binarios, dependencias y firma. No modifican aplicaciones.

## Parche propuesto

El archivo [patches/soapymiri-bandwidth-safety.patch](patches/soapymiri-bandwidth-safety.patch) propone que SoapyMiri no aborte cuando una aplicacion solicita un ancho de banda no soportado exactamente. En vez de lanzar una excepcion fatal, selecciona el ancho valido mas cercano.

Este parche es la mejora que conviene enviar a SoapyMiri como issue o pull request.

## Advertencias

- Haz respaldo de cualquier `.app` antes de modificarlo.
- Cada cambio dentro de un bundle `.app` invalida la firma y exige volver a firmar.
- Una actualizacion de SDR++ o SDRangel puede reemplazar los cambios.
- macOS 27.0 aparece como configuracion Tier 2 en Homebrew; pueden existir incompatibilidades propias de beta/pre-release.
- Esta guia no convierte MSI.SDR en RTL-SDR. El hardware va por Mirics/SoapyMiri, no por `rtl_test`.

## Fuentes y repositorios utiles

- SDR++: https://github.com/AlexandreRouma/SDRPlusPlus
- SDR++ nightly: https://www.sdrpp.org/nightly
- SDRangel: https://github.com/f4exb/sdrangel
- SoapySDR: https://github.com/pothosware/SoapySDR
- SoapyMiri: https://github.com/ericek111/SoapyMiri
- libmirisdr-4: https://github.com/f4exb/libmirisdr-4
