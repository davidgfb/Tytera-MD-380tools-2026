# EL GRAN HALLAZGO — Programar el codeplug del TYT MD-380 con md380tools

**Fecha:** 18/09/2026 — **Estado:** CONSEGUIDO ✅
Radio TYT MD-380 S/N 1611A02361, firmware `md380tools` 2026-01-23 (NoGPS).

El radio ya muestra canales PMR programados (selector 1..16 = canal seleccionable,
subtonos CTCSS correctos). Pantalla: `radio info name hehehehehehehe...`,
`number 16777215`, `md380tools ver 2026-01-23`, `cp ver v??.??`.

---

## 1. El hallazgo en tres ideas clave

### A) El codeplug se escribe con el radio en MODO NORMAL, NO en el bootloader
- El codeplug vive en la **flash SPI** y se escribe/lee a través del **DFU de
  programación que sirve el FIRMWARE EN MARCHA** (descriptor USB:
  `0483:df11`, producto *"Digital Radio in USB mode"*).
- Ese modo es el que usa el CPS de TyT. Es el modo correcto para canales/contactos/zones.
- El **bootloader de recuperación** (LED verde+rojo parpadeando, pantalla negra)
  sirve para **flashear firmware**, NO para el codeplug. En él, el acceso DFU
  apunta a la **flash interna** del STM32: escribir ahí no persiste en el SPI,
  y las lecturas raw de SPI (`spiflashpeek`/block 1) dan `USBError Errno 5`.

### B) Mapeo archivo ↔ SPI = 1:1 (sin ningún offset)
- El contenido del fichero de codeplug se copia a la flash SPI **con el mismo
  offset**: `fichero[0x1EE00]` ⇒ SPI `0x1EE00`, etc.
- Verificado dos veces:
  - `codeplug_despues_fw.bin` (read-back) == `codeplug_v5.bin` byte a byte.
  - `codeplug_verif_v6_normal.bin` (read-back) == `codeplug_v6.bin` byte a byte (0 diffs).
  - El dump SPI completo de 16 MB (`backup_flash_v5_antes_openmduv.bin`)
    contenía el contenido de v5 en `0x1EE00`/`0x5F80` byte a byte.

### C) Un codeplug sin ZONES da "unprogrammed"
- Solo escribir canales + contactos NO es suficiente:
  - **v5** (canales + contactos, sin zones) → el radio seguía *unprogrammed*.
  - Causa: `0x149E0` (zones) y `0x2F000` (zona activa) quedaban a `0xFF` (borrados).
- Un codeplug completo necesita las cuatro regiones:

| Región SPI | Contenido |
|---|---|
| `0x1EE00` | Canales (channel_t) |
| `0x5F80`  | Contactos |
| `0x149E0` | Zonas: `zone_t` = nombre UTF-16LE (32 B) + 16 canales `uint16 LE` 1-based (64 B) |
| `0x2F000` | `zone_number_t` (5 B): `byte[3]` = índice de zona (1-based), resto `0xFF` |
| `0x200E0` | (opcional, útil) bloque de último uso: nombre zona 32 B + snapshot canal 64 B |

Durante este trabajo se perdieron horas por una hipótesis errónea (offset `+0x800`)
heredada de versiones previas; **el mapeo correcto es 1:1**.

---

## 2. Procedimiento que FUNCIONA (receta)

1. **Modo normal** del radio: encendido sin pulsar ningún botón (pantalla de
   interfaz normal). No entres en el bootloader (PTT+botón superior).
2. Conectar el cable USB.
3. Escribir el codeplug:
   ```
   python tools\escribir_codeplug.py codeplug_v6.bin
   ```
   borra 256 KB de SPI (bloques 0x0/0x10000/0x20000/0x30000) y descarga los
   bloques DFU 2..0x101 (`DFU.download`, paquetes de 1024 B).
4. Verificar (round-trip) que quedó escrito:
   ```
   python tools\leer_codeplug.py codeplug_verif.bin
   ```
   Comprobar **0 bytes distintos** contra el fichero escrito. Si difieren → el
   radio NO estaba en modo normal (probablemente estaba en bootloader).
5. Desenchufar el USB, apagar y encender (o reiniciar). La pantalla debe mostrar
   el primer canal de la zona y el selector 1..16 debe cambiar de canal.

> Nota: `escribir_codeplug.py` también corta la puesta en DFU antes de borrar.
> El firmware NO se toca; si algo falla, se restaura con los `backup_flash_*.bin`.

---

## 3. Herramientas

- `tools\escribir_codeplug.py <codeplug.bin>` — escribe el codeplug.
- `tools\leer_codeplug.py <salida.bin>` — lee los 256 KB del codeplug.
- `tools\generar_v6.py` — genera `codeplug_v6.bin` (v5 + 4 zonas PMR/DMR + zona activa + bloque de último uso).
- `tools\generar_v5.py` — v5: solo canales + contactos (NO es suficiente, sin zones).
- `tools\md380tools\md380_dfu.py` — `init_dfu()`, `download_codeplug`, `upload_codeplug`.
- `tools\md380tools\md380_tool.py` — `spiflashdump/spiflashpeek` (SPI raw; solo funcionó en sesiones concretas, ver §4).
- `tools\OpenMD380_buildtools_v2\...\opengd77_stm32_firmware_loader.py` — flasheo de FIRMWARE (usa el bootloader real, correcto para firmware, NO para codeplug).

---

## 4. Cómo llegamos hasta aquí (resumen de la odisea)

1. El radio mostraba *unprogrammed* pese a flashear md380tools 2026-01-23.
2. v3 (herramienta `_gen_md380tools_v3.py`) fallaba porque **restaba 0x800** a
   todos los offsets → todo el content aterrizaba 0x800 más abajo. ⚠️ Muerto.
3. v4/v5: canales y contactos bien ubicados y verificados en SPI (16 MB dump)… pero
   sin zonas → seguía *unprogrammed*.
4. Descubrimiento de la estructura de zonas (a partir de `backup_flash_20260916_220000.bin`).
5. v6: + 4 zonas, zona activa y bloque de último uso. **PERO** los primeros intentos
   de escribir v6 se hicieron con el radio en el **bootloader de recuperación**
   (LED verde/rojo) → los writes no se reflejaban (iban a flash interna) → read-back
   distinto y SPI raw con I/O error. Parecía que nada funcionaba.
6. **El giro:** recordamos que v5 (el único que verificó y que SÍ quedó en SPI)
   se había escrito con el radio en **modo normal**. Repetimos la escritura de v6 en
   modo normal → **round-trip 0 diffs** → reinicio → ¡canales visibles y operativos!

Lecciones:
- *"Digital Radio in USB mode"* ≠ bootloader: es el modo de programación del firmware.
- LED rojo/verde + pantalla negra = bootloader de recuperación = **solo firmware**.
- No confundir; el indicador definitivo es el round-trip byte a byte tras escribir.

---

## 5. Estado actual y tareas pendientes (opcionales)

- ✅ Canales PMR analógicos operativos (selector 1..16), CTCSS correctos.
- ⏳ `cp ver v??.??` — se puede poner un número de versión de codeplug si se desea.
- ⏳ `radio info number 16777215` (0xFFFFFF) — asignar radio ID / DMR ID si se usará DMR.
- ⏳ Verificar el lado DMR (zonas DMR A/B, talkgroups) en el aire.
- 💾 Copias de seguridad disponibles: `backup_flash_20260916_220000.bin`
  (original), `backup_flash_v5_antes_openmduv.bin`, `spi_check2.bin`.

---

## 6. Formato binario (para generar codeplugs desde cero)

Referencia de código: `tools\md380tools\applet\src\codeplug.h`
(estructuras `channel_info_t`, `contact_t`, `zone_t`, `zone_number_t`)
y `tools\generar_v5.py` / `tools\generar_v6.py` (codificadores verificados).

> ⚠️ Los offsets del fichero `.rdt` del CPS TyT difieren del SPI (~549 bytes
> más altos). Aquí todo es **offset SPI == offset de fichero, mapeo 1:1**.

### Constantes de región (todas en SPI / fichero)

| Región | Addr SPI | Tamaño/entrada | Máx | Notas |
|---|---|---|---|---|
| Canales | `0x1EE00` | 64 B | 1000 | — |
| Contactos digitales | `0x5F80` | 36 B | 1000 | entrada 0 = índice 1 |
| Listas RX group | `0xEC20` | 96 B | 250 | termina justo en `0x149E0` |
| Zonas | `0x149E0` | 64 B | <250 | el siguiente array no empezó en `0x189E0` |
| Zone number | `0x2F000` | 5 B | 1 | zona activa (1-based) |
| Bloque último uso | `0x200E0` | 32+64 B | 1 | nombre zona + snapshot canal |

### channel_t (64 B) — formato verificado

| Offset | Tamaño | Campo | Codificación |
|---|---|---|---|
| 0 | 1 | `mode` | bajo-bits `MM`: 0x61 = FM analógico, 0x62 = DMR |
| 1 | 1 | `cc_slot` | DMR: nibble alto = color code (`0x10`=CC1), bajo = timeslot (`0x04`=TS1, `0x08`=TS2); analógico = `0x00` |
| 2 | 1 | `priv` | `0x00` |
| 3 | 1 | const | `0xE1` |
| 4 | 1 | `power` | `0x24` = alta (verificado); otras potencias sin verificar |
| 5 | 1 | const | `0xC3` |
| 6..7 | 2 | `contact` | `uint16 LE`, índice de contacto 1-based (tabla `0x5F80`); `0` en analógico |
| 8..10 | 3 | const | `0C 00 00` |
| 11 | 1 | const | `0x00` |
| 12 | 1 | const | `0x00` |
| 13..15 | 3 | const | `01 06 01` |
| 16..19 | 4 | `rxFreq` | 8 dígitos BCD del valor **`freq_mhz × 10000`** (unidad = 0.1 kHz, exacto a 100 Hz), empaquetados 2 dígitos por byte, dígito **menos** significativo primero ⇒ `446.00625 MHz` (4 460 062) → `62 00 46 04` |
| 20..23 | 4 | `txFreq` | ídem |
| 24..25 | 2 | `rxTone` | `0xFFFF` = sin tono; si no, `Hz×10` en 4 dígitos BCD (2/byte) ⇒ `85.4 Hz` → `54 08` |
| 26..27 | 2 | `txTone` | ídem |
| 28..31 | 4 | const | `00 00 FF FF` |
| 32..63 | 32 | `name` | UTF-16LE + relleno `0x00` hasta 32 B |

Decodificador de frecuencia (inverso del usado): `dígitos = nibble bajo + alto de cada byte, empezando por el menos significativo`; `freq_MHz = valor/10000` (verificado: `62 00 46 04` → 446.0062 MHz, `12 08 46 04` → 446.0812 MHz).

### contact_t (36 B) — formato verificado

| Offset | Tamaño | Campo | Codificación |
|---|---|---|---|
| 0..2 | 3 | `id_l/m/h` | TG en `uint24 LE` (byte bajo primero) |
| 3 | 1 | `type` | `0xC1` grupo, `0xC2` usuario, `0xE1` grupo/2 (constantes `CONTACT_*` en codeplug.h) |
| 4..35 | 32 | `name` | UTF-16LE + relleno hasta 32 B |

### zone_t (64 B) — formato verificado

| Offset | Tamaño | Campo | Codificación |
|---|---|---|---|
| 0..31 | 32 | `name` | UTF-16LE + relleno `0x00` hasta 32 B |
| 32..63 | 32 | `channels[16]` | 16× `uint16 LE`, índice de canal 1-based; `0` = vacío |

### zone_number_t (5 B) @ `0x2F000` — formato verificado

| Offset | Valor |
|---|---|
| 0..2 | `0xFF` |
| 3 | `zone_index` — **1-based** (zona 1 = primera de la lista) |
| 4 | `0xFF` |

### Bloque de último uso @ `0x200E0` (96 B)

- `[0..31]`  nombre de zona UTF-16LE
- `[32..95]` copia del `channel_t` (64 B) del canal activo (snapshot)

### Contactos usados en v5/v6

17 TG únicos → contactos 1..17 en `0x5F80` (TG 9 Local, 1..8, 16 Direct,
9990 Echo, 9999 Private, 91 Worldwide, 92 Europe, 214 España, 10, 11);
los canales DMR referencian su índice 1-based en bytes 6..7.