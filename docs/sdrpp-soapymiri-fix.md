# SDR++: SoapyMiri, bandwidth y libusb

> Esta es la receta inicial. La [actualizacion de noviembre de 2026](msi-integrated-apps.md) corrige tambien la limpieza asincrona del driver: unificar libusb por si solo no evito todos los cierres. Brown y CE requieren sus propios plugins.

## Objetivo

Hacer funcionar un MSI.SDR / MSi2500 en SDR++ 1.3.0 para macOS Apple Silicon usando SoapySDR.

## Parte 1: compilar `soapy_source`

Configurar SDR++ para compilar el modulo SoapySDR y desactivar fuentes que no sean necesarias:

```bash
cd ~/SDRPlusPlus-soapy/build-soapy

cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DCMAKE_PREFIX_PATH=/opt/homebrew \
  -DOPT_BUILD_SOAPY_SOURCE=ON \
  -DOPT_BUILD_AIRSPYHF_SOURCE=OFF \
  -DOPT_BUILD_PLUTOSDR_SOURCE=OFF \
  -DOPT_BUILD_SDRPLAY_SOURCE=OFF \
  -DOPT_BUILD_PERSEUS_SOURCE=OFF \
  -DOPT_BUILD_USRP_SOURCE=OFF
```

Compilar:

```bash
make -j1
```

Verificar el modulo:

```bash
ls -l ~/SDRPlusPlus-soapy/build-soapy/source_modules/soapy_source/soapy_source.dylib
otool -L ~/SDRPlusPlus-soapy/build-soapy/source_modules/soapy_source/soapy_source.dylib | grep -i Soapy
```

Salida esperada de enlace:

```text
/opt/homebrew/opt/soapysdr/lib/libSoapySDR.0.8.dylib
```

Copiar el plugin al bundle:

```bash
cp -f \
~/SDRPlusPlus-soapy/build-soapy/source_modules/soapy_source/soapy_source.dylib \
"/Applications/SDR++ Soapy.app/Contents/Plugins/soapy_source.dylib"
```

Limpiar atributos extendidos si macOS rechaza la firma:

```bash
xattr -cr "/Applications/SDR++ Soapy.app"
```

Firmar:

```bash
sudo codesign --force --deep --sign - "/Applications/SDR++ Soapy.app"
codesign --verify --deep --strict --verbose=2 "/Applications/SDR++ Soapy.app"
```

## Parte 2: fijar configuracion estable

Si SDR++ queda en `9 MS/s` con `Bandwidth = Auto`, puede elegir `14 MHz`. En MSi2500/libmirisdr ese ancho falla.

Configurar manualmente:

```bash
python3 - <<'PY'
import json
from pathlib import Path

path = Path.home() / "Library/Application Support/sdrpp/soapy_source_config.json"
data = json.loads(path.read_text())

device = "Mirics MSi2500 default (e.g. VTX3D card) :: 00000001"
cfg = data["devices"][device]

cfg["sampleRate"] = 2048000.0
cfg["bandwidth"] = 4

data["device"] = device
path.write_text(json.dumps(data, indent=4) + "\n")

print("Configurado: 2.048 MS/s y 1.536 MHz de ancho de banda.")
PY
```

En esta configuracion, `bandwidth = 4` selecciona el valor discreto de `1.536 MHz` en la lista del plugin.

## Parte 3: corregir mezcla de libusb

Diagnostico:

```bash
echo "=== libmirisdr ==="
otool -L /opt/homebrew/lib/libmirisdr.4.dylib | grep -i usb

echo "=== SoapyMiri ==="
otool -L /opt/homebrew/lib/SoapySDR/modules0.8/libsoapyMiriSupport.so | grep -i usb

echo "=== libusb del bundle ==="
otool -L "/Applications/SDR++ Soapy.app/Contents/Frameworks/libusb-1.0.0.dylib" | head -5
```

Problema confirmado:

```text
libmirisdr: libusb current version 7.0.0
SDR++ app:  libusb current version 6.0.0
```

Crear respaldo:

```bash
sudo cp -p \
"/Applications/SDR++ Soapy.app/Contents/Frameworks/libusb-1.0.0.dylib" \
"/Applications/SDR++ Soapy.app/Contents/Frameworks/libusb-1.0.0.dylib.backup-v6"
```

Reemplazar por la version de Homebrew:

```bash
sudo cp -f \
"/opt/homebrew/opt/libusb/lib/libusb-1.0.0.dylib" \
"/Applications/SDR++ Soapy.app/Contents/Frameworks/libusb-1.0.0.dylib"
```

Firmar:

```bash
sudo codesign --force --deep --sign - "/Applications/SDR++ Soapy.app"
codesign --verify --deep --strict --verbose=2 "/Applications/SDR++ Soapy.app"
```

Verificar:

```bash
otool -L "/Applications/SDR++ Soapy.app/Contents/Frameworks/libusb-1.0.0.dylib" | head -2
```

Salida esperada:

```text
current version 7.0.0
```

## Lanzador recomendado

Para asegurar que SDR++ vea los modulos Soapy de Homebrew:

```bash
sudo osacompile -o "/Applications/SDR++ MSI.app" \
-e 'do shell script "SOAPY_SDR_PLUGIN_PATH=\"/opt/homebrew/lib/SoapySDR/modules0.8\" nohup \"/Applications/SDR++ Soapy.app/Contents/MacOS/sdrpp\" >> \"$HOME/Library/Logs/SDRPP-MSI.log\" 2>&1 &"'
```

Luego abrir `SDR++ MSI.app`, seleccionar `SoapySDR`, usar `2.048 MS/s` y `1.536 MHz`, y probar durante varios minutos con el MSi2500 conectado.

