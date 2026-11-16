# Integracion MSI en SDR++, Brown, CE y SDRangel

Revision local `2026.11.16.1`: [manejo de errores USB, reapertura y fuente no disponible](usb-control-errors.md). Mantiene los componentes privados y los perfiles de esta guia, y agrega las protecciones descritas en esa revision.

## Resultado

Se construyeron cuatro variantes locales ARM64 con el sufijo `MSI Integrado`. Cada bundle incluye libusb, libmirisdr y SoapyMiri, y carga sus componentes MSI desde el propio paquete. Los originales se conservan.

| Aplicacion | SoapySDR | Plugin SDR++ |
|---|---|---|
| SDR++ 1.3.0 | ABI 0.8 | Compilado con headers upstream correspondientes |
| SDR++Brown 1.2.1-brown | ABI 0.8 | Compilado con headers de Brown |
| SDR++CE 1.2.5-CE_b | ABI 0.8 | Compilado con headers de CE |
| SDRangel 7.27.1 | ABI 0.8-3, commit `1667b4e6` | No utiliza el plugin de SDR++ |

El codigo de empaquetado y los parches se distribuyen aqui; las aplicaciones se construyen localmente a partir de las copias originales. No se incluyen binarios de aplicaciones de terceros en el repositorio.

## USB: dos correcciones diferentes

La primera integracion unifico libusb. Los informes posteriores mostraron que eso no bastaba: incluso la copia corregida fallaba en `darwin_async_io_callback + 80`, escribiendo en una direccion cercana a NULL.

Un fallo controlado de `libusb_submit_transfer` reprodujo ese cierre en la biblioteca original. Su ruta de error liberaba transferencias aun pendientes. La nueva ruta:

1. Registra las transferencias entregadas a libusb.
2. Detiene los reenvios y solicita cancelacion.
3. Despacha eventos hasta recibir los callbacks pendientes, serializados con los otros handlers.
4. Libera transferencias y buffers despues de su terminacion.
5. Sincroniza inicio, pausa, reanudacion y limpieza. Publica el estado inactivo como ultimo acceso al dispositivo.

La capa SoapyMiri espera ademas la salida del hilo lector antes de cerrarlo y vuelve a solicitar cancelacion si la parada llega antes de que el driver publique su arranque. El acceso directo a multiples buffers se deshabilita porque esa modalidad no implementaba reservas independientes.

En este Mac, ISOC interrumpio el flujo durante una prueba larga. BULK completo 120 segundos a 2.048 MS/s sin errores de lectura. Se usa BULK por defecto en estas variantes macOS; no se afirma que sea la mejor eleccion para todas las plataformas.

## Diferencias entre forks

Brown exporta `core::setInputSampleRate(double, double)`; CE exporta `core::setInputSampleRate(double)`. Los offsets de `SourceHandler::ctx` y el layout del stream DSP tambien difieren. Compartir el archivo `soapy_source.dylib` entre forks puede cargar codigo con interfaces incompatibles.

El plugin de cada variante se compilo contra su propio nucleo. Se corrigen el cierre de buffers mientras el worker lee, la salida del lector ante errores terminales, el cambio de AGC estando detenido y los indices antiguos de bandwidth.

En CE se elimino del perfil MSI la instancia desactivada de Meteor: el nucleo ejecutaba su constructor aunque estuviera marcada como desactivada y el inicio se quedaba alli. Sus otras funciones y el original se conservan.

Brown presenta ademas un fallo independiente en la destruccion global del waterfall sin contexto OpenGL; tambien se reproduce en el original usando `--help`. `packaging/brown-msi-entry.cpp` deja que `sdrpp_main` cierre modulos y backend y guarde configuracion, vacia stdio y termina sin ejecutar esa segunda destruccion global. No sustituye su nucleo ni su interfaz.

## Configuracion inicial

- Fuente: SoapySDR, dispositivo Mirics MSi2500.
- Muestreo: 2.048 MS/s.
- Filtro: 1.536 MHz, indice 4 en la lista con Auto en indice 0.
- USB: BULK.
- SoapyMiri expone el rango informado de este modelo: 10 kHz–1 GHz.

La interfaz puede redondear los dos primeros valores a 2.05 MHz y 1.54 MHz. El controlador ofrece filtros discretos hasta 8 MHz; el ancho comercial anunciado de 10 MHz no es una opcion implementada por esta biblioteca.

Los tres perfiles SDR++ viven separados en `~/Library/Application Support/MSI-SDR/`. SDRangel mantiene sus preferencias nativas y el lanzador activa `--soapy`. No se genera un preset universal de canales para SDRangel.

## Empaquetado

Ver [packaging/README.md](../packaging/README.md). Las rutas privadas se derivan de la ubicacion real del bundle, de modo que una copia y la instalada no dependan de una carpeta de compilacion. Las firmas se validan despues de cualquier cambio.

En una carpeta del Escritorio gestionada por un proveedor de archivos se observaron atributos Finder que impedian firmar `.app`. El montaje se hizo fuera de esa carpeta; la copia de entrega se conservo en ZIP y se verifico despues de descomprimirla. La instalacion se comparo archivo por archivo con el paquete probado.
