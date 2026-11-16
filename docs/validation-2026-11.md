# Validacion de noviembre de 2026

La primera entrega se describe a continuacion. Para la revision posterior `2026.11.16.1`, ver [errores USB y recuperacion](usb-control-errors.md) y su [evidencia estructurada](../tests/results/usb-control-errors-2026-11-16.json).

Entorno: MacBookPro17,1, ARM64, macOS 27.3. Receptor conectado MSI2500/MSI001. SoapySDR 0.8.1 y variante ABI 0.8-3 de SDRangel; libusb 1.0.30. Las dependencias utilizadas fijan un minimo efectivo de macOS 26, aunque algunos originales declaren versiones anteriores.

## Evidencia funcional

| Comprobacion | Resultado observado |
|---|---|
| Original: fallo simulado en envio USB 8 | SIGSEGV en `darwin_async_io_callback + 80` |
| Original: fallo simulado en envio USB 30 | SIGSEGV en la misma funcion |
| Driver corregido: mismos tipos de fallo | Termina el stream con un error, sin SIGSEGV |
| Arranque y parada inmediata, 30 ciclos | Finaliza sin bloqueo |
| Reinicio, cambios 2.048 ↔ 6 MS/s y destruccion activa | Prueba funcional breve completada |
| ISOC durante 120 s | Flujo interrumpido por error de reenvio USB; el proceso corregido sobrevive |
| BULK durante 120 s, 2.048 MS/s | 245,763,072 muestras, cero errores de lectura |
| SDR++ integrado | Espectro y waterfall observados con el receptor |
| Brown y CE integrados | Arranque automatico de recepcion, proceso vivo y componentes MSI cargados desde el bundle |
| SDRangel ABI 0.8-3 | Dispositivo Soapy/Mirics enumerado y muestras reales en prueba directa |
| Cuatro copias instaladas | Cada controlador recibio 2,045,952 muestras en una prueba breve, sin errores de lectura |
| ZIP e instalacion | Firmas validas; contenido descomprimido e instalado identico al paquete de entrega |
| Brown `--help` | Original: SIGSEGV en limpieza OpenGL. Nueva entrada: salida 0 |

Los informes de cierre iniciales procedian de una copia del Escritorio con libusb antigua. Los de noviembre mostraron el mismo fallo USB en la copia que ya usaba libusb unificada. El nombre del hilo `device-hotplug` no demuestra por si solo que se haya desconectado fisicamente el cable.

La prueba a 6 MS/s verifica transiciones cortas, no una sesion prolongada a esa tasa. Se mantuvo 2.048 MS/s como ajuste inicial. No se midieron ENOB, precision del TCXO, sensibilidad RF ni todos los modos de cada aplicacion.

Se utilizo analisis de enlaces de REA y herramientas Mach-O, contrastados con firmas y ejecucion. El control visual remoto fallo durante las revisiones posteriores; no se afirma una inspeccion visual exhaustiva de Brown, CE o SDRangel. Las comprobaciones de recepcion directa no prueban todos sus decodificadores o audio.

## Reproducir pruebas del driver

Estas pruebas acceden al receptor conectado. Ejecutar una a la vez, con las otras aplicaciones de recepcion cerradas. No reproducen audio ni guardan I/Q.

```sh
c++ -std=c++11 tests/msi-stream-probe.cpp \
  $(pkg-config --cflags --libs SoapySDR) -o /tmp/msi-stream-probe
/tmp/msi-stream-probe 2048000 1 120

c++ -std=c++11 tests/msi-lifecycle-probe.cpp \
  $(pkg-config --cflags --libs SoapySDR) -o /tmp/msi-lifecycle-probe
/tmp/msi-lifecycle-probe
```

Fijar `SOAPY_SDR_ROOT` a la instalacion privada que se desea probar y comprobar antes su ABI y rutas. Para SDRangel, compilar la prueba y el modulo con los mismos encabezados de ABI 0.8-3 que usa su biblioteca; no enlazar por accidente contra Homebrew 0.8.

`tests/inject-submit-failure.c` es un interpositor de prueba para macOS. Puede provocar deliberadamente un cierre al probar la biblioteca antigua. Solo se carga en el proceso de prueba mediante `DYLD_INSERT_LIBRARIES`; no forma parte de las aplicaciones entregadas.

```sh
cc -dynamiclib tests/inject-submit-failure.c \
  $(pkg-config --cflags --libs libusb-1.0) -o /tmp/msi-submit-failure.dylib
MSI_FAIL_SUBMIT=8 DYLD_INSERT_LIBRARIES=/tmp/msi-submit-failure.dylib \
  /tmp/msi-stream-probe 2048000 1 2
```

Una prueba cuyo fallo inicial no entrega muestras puede terminar con codigo 2, sin que eso sea una caida del proceso. Comprobar el resultado y el registro, no solamente que un proceso permanezca vivo.
