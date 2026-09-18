# MD-380 Firmware Flashing on Windows â€” Working Method (2026-09-17)

## TL;DR

For TYT MD-380 (S/N 1611A02361, FCC PODMD-380), **use the OpenGD77 STM32
firmware loader** with an **unwrapped** firmware file. Two steps:

1. **Unwrap** the wrapped `.bin` using `unwrap_md380.py` (XOR with the
   MD-380's 1024-byte cyclic key).
2. **Flash** the unwrapped file using `opengd77_stm32_firmware_loader.py`
   with `-m MD-380`.

The OpenGD77 loader correctly writes to `0x0800C000` (the application
region) while preserving the TYT bootloader at `0x08000000-0x0800BFFF`.

## Hardware / Environment

- Radio: TYT MD-380, S/N 1611A02361 (manufactured 2016-11, new vocoder)
- OS: Windows 10/11
- Python: 3.14.7 (also tested on 3.11+)
- pyusb: 1.3.1
- USB driver: **libusb-win32** installed via Zadig (also works with WinUSB)
- libusb0.dll: `C:\Windows\System32\libusb0.dll` (installed by Zadig)
- DFU entry: hold **PTT + top side button** while powering on
  â†’ blank display, VID 0x0483 PID 0xDF11

## What DOES NOT Work (and why)

### 1. `FirmwareDownloadV3.04\UpgradeDownload.exe` (TYT official)

Error: `prompting usb open failed!`

Reason: this tool needs the original STMicroelectronics driver for the
application interface, not the WinUSB/libusb-win32 driver installed by
Zadig. Also incompatible with custom firmware.

### 2. `stm32_dfu.py` from md380tools

Multiple bugs in Python 3 + pyusb 1.3:

- `usb.core.find()` uses `libusb0` backend by default (not libusb1)
- `Request.ENUM` enum members not convertible to int by pyusb 1.3
- `/` integer division in Python 3 produces float
- `application_offset` shadowed by local assignment in `write` branch
- `'\xFF' * n` produces str, not bytes, in Py3 binary mode
- **MOST IMPORTANTLY**: the `download()` and `upload()` functions
  apply a hardcoded `flash_address + block_size * 2 - base_address`
  offset, which writes the firmware to `0x08001000` instead of
  `0x0800C000`. This is the application region *offset* on MD-380 â€”
  the bootloader lives at `0x08000000-0x0800BFFF` (sectors 0-2,
  48 KB) and the application starts at `0x0800C000` (sector 3).

  Result: the radio stays in DFU permanently because the application
  is written into the bootloader region, leaving the actual
  application slot empty/corrupt.

  This bug applies to:
  - `md380tools\stm32_dfu.py` (old, repo master)
  - `md380tools-2026-01-23\dist\md380tools-2026-01-23\python\stm32_dfu.py`
  - `md380_dfu.py` (same family of bugs)

### 3. `opengd77_stm32_firmware_loader.py` for wrapped firmware

The loader refuses to flash files starting with the SFUN header
`4F 75 74 53 65 63 75 72 69 74 79 42 69 6E 00 00` ("OutSecurityBin").
This matches all wrapped TYT firmware including the 2026-01-23 build
in `firmware-2026-01-23-NoGPS.bin`.

Workaround: use an **unwrapped** firmware image (e.g.
`md380tools-20241228-UNWRAPPED.bin`).

## What DOES Work

### Method: Unwrap + Flash with OpenGD77 Loader

#### Step 1: Unwrap the firmware

TYT firmware files come wrapped in an SFUN container
(`OutSecurityBin` header, 256 bytes) followed by XOR-encrypted
application data using a fixed 1024-byte cyclic key.

```powershell
python "D:\DL\Programacion Tytera MD380\tools\docs\unwrap_md380.py" ^
    "D:\DL\Programacion Tytera MD380\tools\md380tools-2026-01-23\dist\md380tools-2026-01-23\firmware-2026-01-23-NoGPS.bin" ^
    "D:\DL\Programacion Tytera MD380\tools\firmware-2026-01-23-NoGPS-UNWRAPPED.bin"
```

Expected output:
```
Magic:        OutSecurityBin
Base addr:    0x0800C000
App length:   995328 bytes (0xF3000)
Resource sz:  0 bytes (0x0)
First 16 bytes of unwrapped: 70f1012001af0908f13e0908f93e0908
  Expected STM32 SP+Reset for MD-380: 70f10120 01af0908 ...

Wrote 995328 bytes to ...\firmware-2026-01-23-NoGPS-UNWRAPPED.bin
```

#### Step 2: Patch the OpenGD77 loader for Python 3.11+

```powershell
python -c "
import re
f = r'D:\DL\Programacion Tytera MD380\tools\OpenMD380_buildtools_v2\OpenGD77\firmware\tools\opengd77_stm32_firmware_loader.py'
with open(f) as fh: src = fh.read()
src = src.replace(
    'getargspec = getattr(inspect, \"getfullargspec\", inspect.getargspec)\n\nif \"length\" in getargspec(usb.util.get_string).args:',
    'if hasattr(inspect, \"getfullargspec\"):\n    _spec = inspect.getfullargspec(usb.util.get_string)\n    _has_length = \"length\" in _spec.args\nelse:\n    _has_length = True\n\nif _has_length:'
)
with open(f, 'w') as fh: fh.write(src)
print('patched')
"
```

#### Step 3: Flash (radio in DFU mode: PTT + top button while powering on)

```powershell
python "D:\DL\Programacion Tytera MD380\tools\OpenMD380_buildtools_v2\OpenMD380\firmware\tools\opengd77_stm32_firmware_loader.py" ^
    -f "D:\DL\Programacion Tytera MD380\tools\firmware-2026-01-23-NoGPS-UNWRAPPED.bin" ^
    -m MD-380
```

Expected output:
```
OpenGD77 STM32 FW Loader v1.0.0
 *** Flashing Firmware: ...\firmware-2026-01-23-NoGPS-UNWRAPPED.bin
 *** Flashing FM Only firmware
 *** Flashing a MD-380:
 ***   > Erasing address@ 0x800c000
 ...
 *** 100% complete, now safe to disconnect and/or reboot the radio.
 *** Finished
```

After "100% complete":
1. Unplug USB cable
2. Power off radio
3. Wait 5 seconds
4. Power on radio (no buttons held) â†’ boots into md380tools

## Prerequisites Checklist

1. **Zadig** with libusb-win32 driver installed for `VID_0483&PID_DF11`
   - Options â†’ List All Devices âœ“
   - Select `Tytera` or `Digital Radio in USB mode`
   - Choose `libusb-win32` driver
   - Replace Driver (do for both interfaces if more than one appears)

2. **libusb0.dll** in `C:\Windows\System32\libusb0.dll` (installed by Zadig)

3. **pyusb 1.3+**: `pip install pyusb`

4. **Unwrapped md380tools firmware**: download from
   https://github.com/travisgoodspeed/md380tools/releases or a fork
   like PA3MET's. Use the `*-UNWRAPPED.bin` file, NOT the
   `OutSecurityBin`-wrapped version.

## Memory Layout Reference (STM32F405 in MD-380)

| Sector | Address | Size | Contents |
|--------|---------|------|----------|
| 0 | 0x08000000 | 16 KB | TYT bootloader (write-protected in DFU) |
| 1 | 0x08004000 | 16 KB | TYT bootloader (write-protected in DFU) |
| 2 | 0x08008000 | 16 KB | TYT bootloader (write-protected in DFU) |
| 3 | 0x0800C000 | 16 KB | Application start |
| 4 | 0x08010000 | 64 KB | Application |
| 5 | 0x08020000 | 128 KB | Application |
| 6 | 0x08040000 | 128 KB | Application |
| 7 | 0x08060000 | 128 KB | Application |
| 8 | 0x08080000 | 128 KB | Application |
| 9 | 0x080A0000 | 128 KB | Application |

Total: 1 MB. Application region: 976 KB.

In DFU mode, sectors 0-2 (bootloader, 48 KB) are hidden from the
memory descriptor. The DFU memory layout reported by the loader
shows only the writable application region starting at 0x0800C000.

## Patches Applied During This Work

### A. `opengd77_stm32_firmware_loader.py` Python 3.11+ compatibility

Original line 404:
```python
getargspec = getattr(inspect, "getfullargspec", inspect.getargspec)
if "length" in getargspec(usb.util.get_string).args:
```

`inspect.getargspec` was removed in Python 3.11. Fix:

```python
if hasattr(inspect, "getfullargspec"):
    _spec = inspect.getfullargspec(usb.util.get_string)
    _has_length = "length" in _spec.args
else:
    _has_length = True

if _has_length:
```

### B. `stm32_dfu.py` port to Python 3 (kept for reference, but unused)

These patches were applied but the script is NOT used in the working
flow:

```python
# Use libusb0 backend (matches Zadig-installed driver)
import usb.backend.libusb0 as _libusb0
_USB_BACKEND = _libusb0.get_backend()  # uses C:\Windows\System32\libusb0.dll

# Fix int conversion for Request enum
# Change `Request.X` to `int(Request.X)` everywhere
# (regex: \bctrl_transfer\((0xA1|0x21), (Request\.[A-Z]+), â†’ ctrl_transfer(\1, int(\2),)

# Fix integer division
# `flash_address / block_size` â†’ `flash_address // block_size`

# Fix local variable shadowing
# In `write` branch: rename `application_offset = ...` to `target_offset = ...`

# Fix str/bytes concat
# `packet += '\xFF' * n` â†’ `packet += b'\xFF' * n`
```

## Tested Versions

| Component | Version | Status |
|-----------|---------|--------|
| OpenGD77 loader | v1.0.0 | âœ… Works |
| md380tools firmware | 2024-12-28 UNWRAPPED | âœ… Boots, DMR works |
| md380tools firmware | 2026-01-23 NoGPS (unwrapped via unwrap_md380.py) | âœ… Boots, DMR works |
| TYT OFW | D14 (D35.14) | Verified via stm32_dfu write, then erased for md380tools |
| pyusb | 1.3.1 | âœ… |
| Python | 3.14.7 | âœ… |
| Zadig | 2.9 | âœ… |
| unwrap_md380.py | 2026-09-17 | âœ… Verified against md380tools 2024-12-28 and 2026-01-23 |

## Attached Files (this directory)

- `unwrap_md380.py` â€” Python script to unwrap SFUN-wrapped TYT MD-380
  firmware files. Uses the 1024-byte cyclic XOR key from
  `md380tools/md380_fw.py:118-182` and the MD380FW header format
  (`<16s7s9s16s33s47sLL120s`) from `md380_fw.py:196`. **Note:** the
  MD2017FW class uses a different header format
  (`<16s9s7s16s33s43s8sLLL112s`); using that format on MD-380 data
  will produce garbage.

## Open Questions / TODO

- [x] Unwrap `firmware-2026-01-23-NoGPS.bin` to flash the latest build
- [x] Document the unwrap process
- [ ] Verify DMR audio quality with new vocoder (S/N 1611A = new
      vocoder, should work with `NoGPS.bin` not `OLD.bin`)
- [ ] Determine if `libusb-win32` driver is preferable to `WinUSB`
      for any specific use case (md380-tool talker?)
- [ ] Test fallback: if md380tools fails to boot, can we restore TYT
      D14 firmware using the same OpenGD77 loader?

## Credits

- md380tools: https://github.com/travisgoodspeed/md380tools
- OpenGD77 project: https://www.opengd77.com
- OpenMD380-UCFW (newer fork): https://github.com/LibreDMR/OpenMD380-UCFW
- Zadig: https://zadig.akeo.ie

## License

This documentation is released under CC-BY-SA 4.0. The flashing tools
referenced are under their respective original licenses.
