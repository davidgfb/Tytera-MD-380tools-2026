"""Codeplug v6 = v5 + zones + zone-index + current-channel restore block.

Fixes the 'unprogrammed' issue: v5 only wrote channels (0x1EE00) and
contacts (0x5F80); the zone list (0x149E0), zone number (0x2F000) and the
last-used-channel block (0x200E0) were left erased (0xFF), so the firmware
could not select any channel at boot.

Layout (SPI flash, file mapping is 1:1 through DFU programming mode):
  Channels   @ 0x0001EE00  64 B/entry  (from v5, unchanged)
  Contacts   @ 0x00005F80  36 B/entry  (from v5, unchanged)
  Zones      @ 0x000149E0  64 B/entry  (name[16] utf16 + 16x uint16 ch, 1-based)
  Zone num   @ 0x0002F000  5 B: unknown_ff[3] + zone_index(1-based) + ff
  Last-used  @ 0x000200E0  32 B zone name + 64 B channel snapshot
"""
import struct

SRC = 'codeplug_v5.bin'
DST = 'codeplug_v6.bin'

ADDR_ZONE     = 0x000149E0
ADDR_ZONE_SEL = 0x0002F000
ADDR_LAST     = 0x000200E0
ZONE_SIZE = 64

flash = bytearray(open(SRC, 'rb').read())
assert len(flash) == 262144

def encode_name16(s):
    b = s.encode('utf-16-le')
    assert len(b) <= 32
    return b + b'\x00' * (32 - len(b))

def make_zone(name, channels_1based):
    z = bytearray(ZONE_SIZE)
    z[0:32] = encode_name16(name)
    for i, ch in enumerate(channels_1based[:16]):
        struct.pack_into('<H', z, 32 + i * 2, ch)
    return bytes(z)

# Zones (16 channels max each; 32 analog + 32 digital)
chans_analog   = list(range(1, 33))
chans_digital  = list(range(33, 65))
zones = [
    make_zone('PMR A',   chans_analog[0:16]),
    make_zone('PMR B',   chans_analog[16:32]),
    make_zone('DMR A',   chans_digital[0:16]),
    make_zone('DMR B',   chans_digital[16:32]),
]
for i, z in enumerate(zones):
    off = ADDR_ZONE + i * ZONE_SIZE
    flash[off:off + ZONE_SIZE] = z
    chs = [struct.unpack_from('<H', z, 32 + j * 2)[0] for j in range(16) if
           struct.unpack_from('<H', z, 32 + j * 2)[0] != 0]
    print(f'Zone {i+1} @ 0x{off:06X}: {chs[:16]}')

# Zone number struct @ 0x2F000: [0-2]=FF, [3]=zone_index(1), [4]=FF
print(f'Setting zone index = 1 @ 0x{ADDR_ZONE_SEL:06X}')
flash[ADDR_ZONE_SEL + 3] = 1

# Last-used block @ 0x200E0: zone name + PMR-1 channel snapshot
pmr1 = bytes(flash[0x1EE00:0x1EE00 + 64])
print(f'Last-used block @ 0x{ADDR_LAST:06X} (zone name + PMR-1 channel)')
flash[ADDR_LAST:ADDR_LAST + 32] = encode_name16('PMR A')
flash[ADDR_LAST + 32:ADDR_LAST + 32 + 64] = pmr1

with open(DST, 'wb') as f:
    f.write(bytes(flash))
print(f'\nSaved {DST} ({len(flash)} bytes)')