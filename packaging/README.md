# Componentes para bundles MSI privados

Estos son los componentes usados en las variantes locales. Los bundles originales completos y las dependencias deben estar disponibles localmente. No hay un instalador que reemplace aplicaciones del usuario desde este repositorio.

La [receta de recuperación](../RECOVERY.md) automatiza este proceso usando entradas archivadas y verificadas. No necesita las copias MSI previamente instaladas ni rutas del Mac original.

## Estructura

```text
Example MSI Integrado.app/Contents/
  Info.plist
  MacOS/
    msi-launcher
    sdrpp-original             # o sdrpp_ce-original / SDRangel-original
  Frameworks/
    libsdrpp_core.dylib        # nucleo del fork, donde corresponda
    libusb-1.0.0.dylib
    libmirisdr.4.dylib
    libSoapySDR.0.8.dylib      # 0.8-3 en SDRangel
  Plugins/soapy_source.dylib   # solamente SDR++ y sus forks
  Resources/
    msi-defaults/config.json
    msi-defaults/soapy_source_config.json
    msi-runtime/lib/SoapySDR/modules0.8/libsoapyMiriSupport.so
```

En SDRangel se utiliza `modules0.8-3`. El modulo y libmirisdr deben resolver sus dependencias dentro de `Contents/Frameworks`. El resto de las dependencias del bundle original tambien deben verificarse; copiar solo las cuatro bibliotecas MSI no demuestra que toda la aplicacion sea portable.

## Lanzador

Compilar `msi-launcher.m` con Foundation:

```sh
clang -fobjc-arc -O2 -arch arm64 msi-launcher.m \
  -framework Foundation -o msi-launcher
```

El lanzador deriva las rutas de su bundle, fija el prefijo y modulo Soapy privados y pasa un perfil separado a SDR++. No escribe estado dentro del bundle firmado. Antes de copiar una app se conserva su ejecutable original con otro nombre y se configura el nuevo ejecutable en Info.plist.

Campos adicionales de Info.plist:

| Campo | Ejemplo |
|---|---|
| `CFBundleExecutable` | `msi-launcher` |
| `CFBundleIdentifier` | Un identificador propio, distinto del original |
| `MSIVariant` | `sdrpp`, `brown`, `ce` o `sdrangel` |
| `MSIOriginalExecutable` | `sdrpp-original` |
| `MSISoapyABI` | `0.8` o `0.8-3` |
| `MSIApplicationKind` | `sdrpp` o `sdrangel` |

Los seeds JSON de SDR++ deben seleccionar SoapySDR y el dispositivo real, usar 2.048 MS/s y bandwidth 4, y conservar solo las instancias necesarias al inicio. Algunos nucleos construyen incluso las instancias marcadas como desactivadas. Se guardan los perfiles fuera de la app; las rutas de Plugins/Resources se actualizan al abrir la copia.

Para el componente SoapyMiri en esa estructura, un rpath hacia Frameworks es `@loader_path/../../../../../Frameworks`. Para las bibliotecas dentro de Frameworks basta `@loader_path`; para el plugin de SDR++ se usa `@loader_path/../Frameworks`.

## Entrada de Brown

`brown-msi-entry.cpp` se enlaza con el nucleo original de Brown y conserva su export `sdrpp_main`. Se utiliza en lugar de la entrada minima original para evitar la destruccion OpenGL duplicada al finalizar:

```sh
c++ -std=c++17 -arch arm64 -O2 -Wl,-headerpad_max_install_names \
  brown-msi-entry.cpp /ruta/Brown.app/Contents/Frameworks/libsdrpp_core.dylib \
  -Wl,-rpath,@executable_path/../Frameworks -o sdrpp-original
```

No es una entrada intercambiable con cualquier otro fork. El nucleo probado hace su limpieza y guardado antes de devolver el control.

## Cierre de la entrega

Firmar primero los componentes modificados y despues el bundle. Validar con `codesign --verify --deep --strict`. Comprimir, descomprimir en una carpeta nueva y volver a verificar. Comparar archivos y enlaces simbolicos entre el paquete probado y la instalacion. Conservar los originales y evitar modificar Homebrew global para introducir el perfil privado.

El verificador `scripts/verify-integrated.py` comprueba los componentes principales, rutas MSI, arquitectura y firma, sin abrir la app ni acceder al USB. Su alcance no incluye todas las dependencias de todos los plugins opcionales.
