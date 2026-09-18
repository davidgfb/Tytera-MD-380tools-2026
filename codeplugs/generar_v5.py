"""
Codeplug v5: nombres simples + variedad de TGs.
- Analog: 'PMR-1' a 'PMR-32' (sin sufijos raros)
- Digital: 'DMR-1' a 'DMR-32' (numeracion limpia)
- TGs variados (1-32 con sentido) pero nombres planos
"""
import struct

DST = 'codeplug_v5.bin'
SIZE = 262144

MEM_OFFSET = 0x1EE00
MEM_SIZE = 64
CONT_OFFSET = 0x5F80
CONT_SIZE = 36

# Distribucion de TGs: 16 grupos principales + extras
# Cada TG aparece 1-2 veces en distintos canales (freq + timeslot)
TG_DISTRIBUTION = [
    9,    # 1  - TG 9 Local (uso general)
    9,    # 2  - TG 9 (otro timeslot)
    1,    # 3  - TG 1 Grupo 1
    1,    # 4  - TG 1 (otro timeslot)
    2,    # 5  - TG 2 Grupo 2
    2,    # 6  - TG 2 (otro timeslot)
    3,    # 7  - TG 3 Grupo 3
    3,    # 8  - TG 3 (otro timeslot)
    4,    # 9  - TG 4 Grupo 4
    4,    # 10 - TG 4 (otro timeslot)
    5,    # 11 - TG 5 Grupo 5
    5,    # 12 - TG 5 (otro timeslot)
    6,    # 13 - TG 6 Grupo 6
    6,    # 14 - TG 6 (otro timeslot)
    7,    # 15 - TG 7 Grupo 7
    7,    # 16 - TG 7 (otro timeslot)
    8,    # 17 - TG 8 Grupo 8
    8,    # 18 - TG 8 (otro timeslot)
    16,   # 19 - TG 16 Direct (private call)
    16,   # 20 - TG 16 (otro timeslot)
    9990, # 21 - TG 9990 Echo/Parrot (test)
    9990, # 22 - TG 9990 (otro timeslot)
    9999, # 23 - TG 9999 Private
    9999, # 24 - TG 9999 (otro timeslot)
    91,   # 25 - TG 91 Worldwide
    91,   # 26 - TG 91 (otro timeslot)
    92,   # 27 - TG 92 Europe
    92,   # 28 - TG 92 (otro timeslot)
    214,  # 29 - TG 214 Spain (si tienes indicativo)
    214,  # 30 - TG 214 (otro timeslot)
    10,   # 31 - TG 10 extra
    11,   # 32 - TG 11 extra
]

# 16 freqs PMR446
PMR_FREQS = [
    446.00625, 446.01875, 446.03125, 446.04375,
    446.05625, 446.06875, 446.08125, 446.09375,
    446.10625, 446.11875, 446.13125, 446.14375,
    446.15625, 446.16875, 446.18125, 446.19375,
]

# Subtonos analog: ch7=85.4 EMRG, resto variados
CTCSS_TONES = [
    0, 0, 0, 0, 0, 0, 85.4, 0,           # 1-8: solo 7 con tono emergencia
    67.0, 77.0, 88.5, 100.0,             # 9-12
    107.2, 114.8, 127.3, 136.5,          # 13-16
    146.2, 156.7, 167.9, 179.9,          # 17-20 (sub-grupo B en freqs 1-4)
    192.8, 203.5, 218.1, 233.6,          # 21-24 (sub-grupo B en freqs 5-8)
    241.8, 250.3, 71.9, 79.7,            # 25-28 (sub-grupo C en freqs 9-12)
    82.5, 91.5, 94.8, 97.4,              # 29-32 (sub-grupo C en freqs 13-16)
]

PMR_FREQ_IDX = [
    0, 1, 2, 3, 4, 5, 6, 7,
    8, 9, 10, 11, 12, 13, 14, 15,
    0, 1, 2, 3, 4, 5, 6, 7,
    8, 9, 10, 11, 12, 13, 14, 15,
]

def encode_freq_hz(freq_mhz):
    hz = int(round(freq_mhz * 100000))
    val = hz // 10
    digits = []
    for _ in range(8):
        digits.append(val % 10)
        val //= 10
    r = bytearray(4)
    for i in range(4):
        r[i] = (digits[i*2+1] << 4) | digits[i*2]
    return bytes(r)

def encode_ctcss_hz(hz):
    if hz == 0:
        return b'\xff\xff'
    val = int(hz * 10)
    digits = []
    for _ in range(4):
        digits.append(val % 10)
        val //= 10
    r = bytearray(2)
    for i in range(2):
        r[i] = (digits[i*2+1] << 4) | digits[i*2]
    return bytes(r)

def encode_name(s):
    b = s.encode('utf-16-le')[:32]
    return b + b'\x00' * (32 - len(b))

data = bytearray(b'\xff' * SIZE)

# === CONTACTOS (32 contactos, uno por TG unico) ===
unique_tgs = sorted(set(TG_DISTRIBUTION))
TG_INFO = {
    9: ('TG 9 Local', 'Llamadas locales generales'),
    1: ('TG 1 Grupo 1', 'Grupo privado 1'),
    2: ('TG 2 Grupo 2', 'Grupo privado 2'),
    3: ('TG 3 Grupo 3', 'Grupo privado 3'),
    4: ('TG 4 Grupo 4', 'Grupo privado 4'),
    5: ('TG 5 Grupo 5', 'Grupo privado 5'),
    6: ('TG 6 Grupo 6', 'Grupo privado 6'),
    7: ('TG 7 Grupo 7', 'Grupo privado 7'),
    8: ('TG 8 Grupo 8', 'Grupo privado 8'),
    16: ('TG 16 Direct', 'Llamadas directas (private)'),
    9990: ('TG 9990 Echo', 'Test: te oyes a ti mismo'),
    9999: ('TG 9999 Private', 'Private call test'),
    91: ('TG 91 Worldwide', 'Mundial (ingles)'),
    92: ('TG 92 Europe', 'Europa continental'),
    214: ('TG 214 Espana', 'EspaÃ±a (requiere indicativo EA)'),
    10: ('TG 10 Grupo 10', 'Grupo privado 10'),
    11: ('TG 11 Grupo 11', 'Grupo privado 11'),
}

for idx, tg in enumerate(unique_tgs):
    off = CONT_OFFSET + idx * CONT_SIZE
    name, _ = TG_INFO.get(tg, (f'TG {tg}', ''))
    entry = bytearray(CONT_SIZE)
    entry[0] = tg & 0xFF
    entry[1] = (tg >> 8) & 0xFF
    entry[2] = (tg >> 16) & 0xFF
    entry[3] = 0xc1  # group call
    nb = name.encode('utf-16-le')[:32]
    entry[4:4+len(nb)] = nb
    data[off:off+CONT_SIZE] = entry

# === 32 CANALES ANALOG (ch 1-32) ===
for i in range(32):
    off = MEM_OFFSET + i * MEM_SIZE
    mem = bytearray(MEM_SIZE)
    freq = PMR_FREQS[PMR_FREQ_IDX[i]]
    ctcss = CTCSS_TONES[i]
    mem[0] = 0x61  # NBFM analog
    mem[1] = 0x00
    mem[2] = 0x00
    mem[3] = 0xe1
    mem[4] = 0x24  # HIGH
    mem[5] = 0xc3
    mem[6:8] = b'\x00\x00'
    mem[8:11] = b'\x0c\x00\x00'
    mem[11] = 0x00
    mem[12] = 0x00
    mem[13:16] = b'\x01\x06\x01'
    mem[16:20] = encode_freq_hz(freq)
    mem[20:24] = encode_freq_hz(freq)
    mem[24:26] = encode_ctcss_hz(ctcss)
    mem[26:28] = encode_ctcss_hz(ctcss)
    mem[28:32] = b'\x00\x00\xff\xff'
    if i == 6:
        name = 'PMR-7 7-7 EMRG'
    else:
        name = f'PMR-{i+1}'
    mem[32:64] = encode_name(name)
    data[off:off+MEM_SIZE] = mem

# === 32 CANALES DIGITALES (ch 33-64) ===
# Mapeo: tg -> indice en contactos
tg_to_idx = {tg: i+1 for i, tg in enumerate(unique_tgs)}

for i in range(32):
    ch_num = 33 + i
    tg = TG_DISTRIBUTION[i]
    freq = PMR_FREQS[i // 2]
    ts = (i % 2) + 1
    contact_idx = tg_to_idx[tg]
    off = MEM_OFFSET + (ch_num - 1) * MEM_SIZE
    mem = bytearray(MEM_SIZE)
    mem[0] = 0x62  # DMR
    if ts == 1:
        mem[1] = (1 << 4) | 0x04  # CC=1, TS1
    else:
        mem[1] = (1 << 4) | 0x08  # CC=1, TS2
    mem[2] = 0x00
    mem[3] = 0xe1
    mem[4] = 0x24  # HIGH
    mem[5] = 0xc3
    struct.pack_into('<H', mem, 6, contact_idx)
    mem[8:11] = b'\x0c\x00\x00'
    mem[11] = 0x00
    mem[12] = 0x00
    mem[13:16] = b'\x01\x06\x01'
    mem[16:20] = encode_freq_hz(freq)
    mem[20:24] = encode_freq_hz(freq)
    mem[24:26] = b'\xff\xff'
    mem[26:28] = b'\xff\xff'
    mem[28:32] = b'\x00\x00\xff\xff'
    name = f'DMR-{i+1}'  # nombre plano, sin sufijo
    mem[32:64] = encode_name(name)
    data[off:off+MEM_SIZE] = mem

with open(DST, 'wb') as f:
    f.write(bytes(data))

print(f'Codeplug v5 guardado: {DST}')
print()
print('Analog (ch 1-32, ruleta 1-16): nombres PMR-1 a PMR-32')
print('Digital (ch 33-64, flechas):    nombres DMR-1 a DMR-32')
print()
print('TGs asignados (variedad):')
for tg in unique_tgs:
    name, desc = TG_INFO[tg]
    n_canales = TG_DISTRIBUTION.count(tg)
    print(f'  TG {tg:>5} = {name:<25} ({n_canales} canales) - {desc}')
