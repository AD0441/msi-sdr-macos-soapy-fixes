# SDRangel crash report notes

## Falla por biblioteca faltante

Ejemplo de terminacion:

```text
namespace: DYLD
indicator: Library missing
Library not loaded: @rpath/liblibsigmf.dylib
```

Esto apunta a un bundle incompleto o a rutas `@rpath` rotas dentro de SDRangel.

## Falla por ABI SoapySDR

Cuando SDRangel usa una copia interna de SoapySDR y el modulo SoapyMiri se compila contra Homebrew, puede aparecer una incompatibilidad sutil:

```text
SDRangel ABI: 0.8-3
Homebrew ABI: 0.8
```

Aunque el modulo cargue, el proceso puede fallar al invocar metodos agregados en la interfaz de SoapySDR.

## Verificaciones

```bash
otool -L /Applications/SDRangel.app/Contents/MacOS/sdrangel
find /Applications/SDRangel.app -iname '*Soapy*' -o -iname '*miri*'
codesign --verify --deep --strict --verbose=2 /Applications/SDRangel.app
```

## Recomendacion

Para SDRangel, priorizar compatibilidad exacta de ABI antes de instalar modulos Soapy externos. Si se recompila SoapyMiri para SDRangel, debe apuntar a la misma SoapySDR que usa el bundle.

