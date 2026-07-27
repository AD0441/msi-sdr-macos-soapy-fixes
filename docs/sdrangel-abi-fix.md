# SDRangel: correccion de ABI SoapySDR

## Sintoma

SDRangel puede detectar o intentar cargar modulos SoapySDR, pero un modulo SoapyMiri compilado contra Homebrew no queda plenamente compatible con la copia interna de SoapySDR usada por SDRangel.

El riesgo aparece como incompatibilidad de ABI:

```text
SDRangel SoapySDR interno: ABI 0.8-3
SoapySDR Homebrew:        ABI 0.8
```

En esa condicion, el modulo puede fallar al invocar metodos virtuales agregados o reordenados, por ejemplo:

```text
listGPIOBanks()
getSettingInfo()
```

## Causa

SDRangel fue construido con un commit especifico de SoapySDR:

```text
1667b4e6
SoapySDR 0.8.1-g1667b4e6
ABI 0.8-3
```

SoapyMiri compilado contra Homebrew enlaza contra:

```text
libSoapySDR.0.8.dylib
```

pero SDRangel espera modulos compatibles con:

```text
@rpath/libSoapySDR.0.8-3.dylib
```

## Solucion

1. Identificar el commit de SoapySDR empaquetado por SDRangel.
2. Compilar SoapyMiri contra esos headers y esa biblioteca.
3. Instalar el modulo en el bundle de SDRangel o en una ruta que SDRangel cargue.
4. Verificar dependencias con `otool`.
5. Volver a firmar SDRangel.

## Verificaciones utiles

```bash
otool -L /Applications/SDRangel.app/Contents/MacOS/sdrangel | grep -i Soapy
find /Applications/SDRangel.app -iname '*Soapy*' -o -iname '*miri*'
codesign --verify --deep --strict --verbose=2 /Applications/SDRangel.app
```

Resultado esperado de firma:

```text
/Applications/SDRangel.app: valid on disk
/Applications/SDRangel.app: satisfies its Designated Requirement
```

## Nota

No mezcles modulos SoapySDR compilados contra Homebrew con aplicaciones que traen su propia ABI interna, salvo que hayas confirmado que ambas coinciden.

