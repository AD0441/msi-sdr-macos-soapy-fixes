# SDR++ crash report notes

## Falla 1: `SoapyMiri::setBandwidth()`

Sintoma:

```text
SDR++ detecta SoapySDR y el MSi2500, pero se cierra al iniciar.
```

Causa:

```text
Sample rate: 9 MS/s
Bandwidth: Auto
Auto bandwidth seleccionado: 14 MHz
mirisdr_set_bandwidth(): error
SoapyMiri::setBandwidth(): excepcion no capturada
```

Solucion operativa:

```text
Sample rate: 2.048 MS/s
Bandwidth: 1.536 MHz
```

Archivo de configuracion:

```text
~/Library/Application Support/sdrpp/soapy_source_config.json
```

## Falla 2: `org.libusb.device-hotplug`

Sintoma:

```text
SDR++ ya no cae en setBandwidth, pero se cierra en un hilo USB.
```

Indicadores:

```text
org.libusb.device-hotplug
darwin_async_io_callback
libusb-1.0.0.dylib
```

Causa probable confirmada:

```text
libmirisdr usa libusb 7.0.0
SDR++ bundle trae libusb 6.0.0
```

Solucion:

1. Respaldar la copia interna de `libusb`.
2. Copiar la version de Homebrew dentro del bundle.
3. Volver a firmar SDR++.
4. Verificar con `otool -L` y `codesign`.

