"""
Lee el codeplug del radio en DFU y lo guarda como archivo .bin + RDT-wrapped.
"""
import sys
import usb.core

# Patch PyUSB legacy compat
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

out = sys.argv[1] if len(sys.argv) > 1 else r'D:\DL\Programacion Tytera MD380\codeplug_actual.bin'
print(f'Leyendo codeplug -> {out}')
dfu = md380_dfu.init_dfu()
md380_dfu.upload_codeplug(dfu, out)
print('OK')

import os
print('Tamano:', os.path.getsize(out), 'bytes')
