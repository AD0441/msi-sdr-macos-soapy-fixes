# Parches probados

Aplicar cada parche desde una copia limpia del repositorio indicado, usando `git apply --check` antes de `git apply`. Mantener los avisos y licencias de los proyectos de origen.

| Parche | Repositorio y revision de base | Alcance |
|---|---|---|
| `libmirisdr-async-lifetime.patch` | `f4exb/libmirisdr-4`, `fd0452e31264f065bb315e74313384ca4a121ef1` | Cancelacion, callbacks pendientes, exclusion entre reanudacion y limpieza, estado atomico. Requiere C11. |
| `soapymiri-msi-macos-stability.patch` | `ericek111/SoapyMiri`, `d94629b58f70ae36a1b4e1f58277918cec600740` | BULK en macOS, filtros soportados, cierre con join, cancelacion temprana, escala CS16 y rango del receptor MSI probado. |
| `sdrpp-soapy-stability.patch` | `AlexandreRouma/SDRPlusPlus`, `8c9f5ee8fe405775bfcd62c8c8f8c0fc928a64af` | Parar el lector antes de cerrar buffers, errores de stream, AGC y seleccion guardada de bandwidth. |
| `sdrpp-brown-soapy-stability.patch` | `sannysanoff/SDRPlusPlusBrown`, `af32c3a547a71d29be38c847beaad3d245987499` | Lifecycle y validaciones adaptados al ABI de Brown. |
| `sdrpp-ce-soapy-stability.patch` | `LunaeMons/SDRPlusPlus_CommunityEdition`, `722635ead9d1b0d4ec794453384d3524d376739d` | Lifecycle y validaciones adaptados al ABI de CE. |

Los parches de Brown y CE necesitan ademas copiar `packaging/rx_lifecycle.h` a `source_modules/soapy_source/src/rx_lifecycle.h` de su respectivo arbol antes de compilar el plugin. Este archivo contiene la limpieza compartida y el bucle de lectura con timeout finito.

Los commits candidatos de Brown y CE coinciden con los simbolos y layouts examinados de los bundles probados. Los binarios originales no contienen un SHA que certifique su origen exacto. No se deben generalizar esos encabezados a cualquier release del fork.

`soapymiri-bandwidth-safety.patch` es el prototipo anterior. La nueva implementacion acepta Auto, descarta valores no finitos, selecciona un filtro soportado sin exceder la solicitud y elimina 14 MHz de la lista. Aplicar solo una version de la correccion de bandwidth.

El parche SoapyMiri configura un perfil para el MSI2500/MSI001 probado, informado como 10 kHz–1 GHz. Para otros modelos deben revisarse sus limites; no se generaliza ese rango a todos los dispositivos Mirics o SDRplay.

## Orden recomendado

1. Aplicar y compilar `libmirisdr-async-lifetime.patch` como C11.
2. Aplicar el parche de SoapyMiri y compilar una variante por ABI SoapySDR: 0.8 y 0.8-3.
3. Compilar el plugin correspondiente de cada SDR++, con los headers y el nucleo del mismo fork.
4. Construir bundles privados, firmarlos y verificar sus dependencias.

Las pruebas funcionales y de fallos estan documentadas en [validation-2026-11.md](../docs/validation-2026-11.md). No se han publicado estos parches como cambios ya aceptados por upstream.
