# MD-380 + md380tools — Codeplug y flasheo (guía practicada)

Documentación y herramientas **probadas** para un **TYT MD-380** (S/N 1611A02361)
con firmware **md380tools 2026-01-23 (NoGPS)**: cómo se flashea el firmware y
—sobre todo— cómo se programa el **codeplug PMR446** que dejaba el radio
en *"unprogrammed"*.

> El gran hallazgo: el codeplug se escribe con el radio en **MODO NORMAL**
> (firmware en marcha, "Digital Radio in USB mode"), **no** en el bootloader
> de recuperación (LED verde/rojo), que solo sirve para firmware. Mapeo
> fichero↔SPI = **1:1**. Y un codeplug necesita **zonas** (`0x149E0`),
> zona activa (`0x2F000`) y el bloque de último uso (`0x200E0`); sin ellas,
> *unprogrammed*. Ver `docs/CODEPLUG_GRAN_HALLAZGO.md`.

## Contenido

```
docs/
  CODEPLUG_GRAN_HALLAZGO.md   hallazgo + receta + formatos binarios (channel_t, contact_t, zone_t…)
  MD380_FLASH_METHOD.md       método de flasheo de firmware (unwrap + OpenGD77 loader)
  MAPA_CANALES_v5.txt         mapa canales PMR/DMR del codeplug v5/v6
  CODEPLUG_ORIGINAL.json      codeplug original de fábrica (referencia, parseado)
  CODEPLUG_ORIGINAL_INFORME.txt  informe del codeplug original
  instrucciones.txt           guía inicial (legado)
codeplugs/
  codeplug_v5.bin             canales + contactos (NUNCA escribas solo esto: sin zonas = unprogrammed)
  codeplug_v6.bin             ✓ codeplug FUNCIONAL (v5 + 4 zonas + zona activa + último uso)
  codeplug_verif_v6_normal.bin  read-back del radio == v6 (0 bytes distintos)
  generar_v5.py  generar_v6.py  make_pmr_codeplug.py   generadores
tools/
  escribir_codeplug.py        escribe un codeplug al radio (modo normal)
  leer_codeplug.py            lee el codeplug para verificar
  DFU.py  md380_dfu.py  md380_tool.py  stm32_dfu.py  dfu_suffix.py   (md380tools, necesarios)
  unwrap_md380.py             desempaqueta firmware SFUN→plano
  firmware-loader/opengd77_stm32_firmware_loader.py   flash de firmware (parcheado Py3.11+)
firmware/
  firmware-2026-01-23-NoGPS.bin            oficial envuelto (SFUN)
  firmware-2026-01-23-NoGPS-UNWRAPPED.bin  para flashear
  TYT-72310-11-MD380-D35.14-OFICIAL.bin    firmware original TYT (restauración de fábrica)
backups/
  backup_flash_20260916_220000.bin   SPI completo original de fábrica (16 MB)
  backup_flash_v5_antes_openmduv.bin SPI tras escribir v5 (16 MB)
  stm32_current_flash.bin            flash interna STM32 (1 MB)
```

## Dependencias (Windows)

- Python 3.11+, `pip install pyusb libusb-package`
- Driver USB libusb (Zadig, `libusb-win32`) para `VID_0483&PID_DF11`
  (ver `docs/MD380_FLASH_METHOD.md`).

## Flashear firmware (una vez)

1. Radio apagado → mantén **PTT + botón superior** → enciende → **LED
   parpadea rojo/verde, pantalla negra** (bootloader de recuperación).
2. USB enchufado.
3. `python tools/firmware-loader\opengd77_stm32_firmware_loader.py -f firmware/firmware-2026-01-23-NoGPS-UNWRAPPED.bin -m MD-380`
4. Desenchufa, apaga, enciende normalmente.

## Escribir el codeplug (SIEMPRE que cambies canales/zonas)

**El radio debe estar en MODO NORMAL** (encendido normalmente, pantalla
normal; entra sin pulsar botones). NO uses el bootloader para esto.

```powershell
# desde la raíz del repo
python tools\escribir_codeplug.py codeplugs\codeplug_v6.bin
python tools\leer_codeplug.py codeplugs\readback.bin
```

Verifica que el read-back coincide byte a byte con el fichero:

```powershell
python -c "a=open(r'codeplugs\codeplug_v6.bin','rb').read(); b=open(r'codeplugs\readback.bin','rb').read(); print('diffs:', sum(1 for x,y in zip(a,b) if x!=y))"
```

`0 diffs` = escrito correctamente. Desenchufa, reinicia el radio y comprueba
la pantalla.

## Generar un codeplug propio

1. Edita `codeplugs/generar_v6.py` (o reescribe desde `make_pmr_codeplug.py`).
2. `cd codeplugs && python generar_v6.py` (produce `codeplug_v6.bin`).
3. Escríbelo con el procedimiento anterior.

Los formatos binarios exactos de `channel_t`, `contact_t`, `zone_t`,
`zone_number_t` y el bloque de último uso están documentados en
`docs/CODEPLUG_GRAN_HALLAZGO.md` §6.

## Aviso

- Las herramientas solo tocan los 256 KB de codeplug del SPI; el firmware
  queda intacto. Los dumps de `backups/` permiten restaurar el SPI.
- md380tools: https://github.com/travisgoodspeed/md380tools
- OpenGD77 loader: https://www.opengd77.com
- Zadig: https://zadig.akeo.ie