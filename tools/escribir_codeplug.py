"""
Escribe el codeplug nuevo al radio. SOLO toca 256 KB del SPI flash (codeplug region).
El firmware (en flash interno del STM32, separado del SPI) queda intacto.
"""
import sys
import usb.core
import usb.backend.libusb1
import libusb_package

# PyUSB legacy patch
_orig_ctrl = usb.core.Device.ctrl_transfer
def _patched_ctrl(self, bmRequestType, bRequest, wValue=0, wIndex=0,
                  data_or_wLength=None, timeout=None):
    if hasattr(bRequest, 'value'):
        bRequest = bRequest.value
    elif not isinstance(bRequest, int):
        try: bRequest = int(bRequest)
        except: pass
    if isinstance(data_or_wLength, str):
        data_or_wLength = data_or_wLength.encode('latin-1')
    return _orig_ctrl(self, bmRequestType, bRequest, wValue, wIndex,
                      data_or_wLength, timeout)
usb.core.Device.ctrl_transfer = _patched_ctrl

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import md380_dfu

binfile = sys.argv[1] if len(sys.argv) > 1 else 'codeplug.bin'
with open(binfile, 'rb') as f:
    data = f.read()

print(f'Codeplug a escribir: {binfile} ({len(data)} bytes)')
assert len(data) == 262144, f'Tamano incorrecto: {len(data)}'
print('Conectando al radio en DFU...')
dfu = md380_dfu.init_dfu()
print('OK conectado')
print()
print('!!! ATENCION: borrando 256 KB del SPI flash (codeplug) y escribiendo...')
print('Si algo va mal, el firmware NO se toca. Restaurable con backup_flash_*.bin')
print()
md380_dfu.download_codeplug(dfu, data)
print()
print('=== Codeplug escrito. Apaga y enciende el walkie para reiniciar. ===')
