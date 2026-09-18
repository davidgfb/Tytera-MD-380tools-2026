#!/usr/bin/env python3
"""Generate OpenGD77 CPS codeplug CSV files for a PMR/dPMR-style MD-380 setup.

Design:
- 2 zones: PMR Analog (UV-5R compatible) and PMR Digital (DMR)
- 16 PMR446 frequencies (446.00625 - 446.19375 MHz)
- 8 CTCSS subtone values (analogue, compatible con UV-5R/RT-5R)
- 8 Talk Groups (DMR simplex, no promiscuous, CC=1, TS=1)
- 128 channels per zone Ã— 2 zones = 256 channels total
- Channel names: just numbers (1-128) per user request
- SMS via DMR is supported by md380tools/OpenGD77 firmware natively

Files generated in docs/:
  - opengd77_channels.csv
  - opengd77_contacts.csv
  - opengd77_zones.csv

Run:  python docs\\make_pmr_codeplug.py
Import: OpenGD77 CPS â†’ Extras â†’ Import channels/contacts/zones
"""
import csv
from pathlib import Path

OUT_DIR = Path(r'D:\DL\Programacion Tytera MD380\tools\docs')

# 16 PMR446 frequencies (EU standard, 12.5 kHz spacing)
PMR_FREQS = [
    446.00625, 446.01875, 446.03125, 446.04375,
    446.05625, 446.06875, 446.08125, 446.09375,
    446.10625, 446.11875, 446.13125, 446.14375,
    446.15625, 446.16875, 446.18125, 446.19375,
]

# 8 CTCSS tones (Hz) â€” common EU PMR subtones
CTCSS_TONES = [67.0, 71.9, 74.4, 77.0, 82.5, 85.4, 88.5, 91.5]

# 8 DMR Talk Groups (private simplex TGs, no BrandMeister)
TGS = [1, 2, 3, 4, 5, 6, 7, 8]

# OpenGD77 CSV columns (combined channel list â€” superset)
ALL_CHANNEL_COLS = [
    'Channel Number', 'Channel Name', 'Mode', 'Bandwidth',
    'RX Frequency', 'TX Frequency', 'TX Power',
    'Colour Code', 'Time Slot',
    'RX CTCSS/DCS', 'TX CTCSS/DCS', 'Squelch Type',
    'Contact', 'Contact Type', 'RX Group List', 'Scan List',
    'Comment',
]

# OpenGD77 CSV columns (contact)
CONTACT_COLS = [
    'Contact Number', 'Contact Name', 'Contact Type',
    'Contact TG/DMR ID', 'Contact Timeout (seconds)',
]

# OpenGD77 CSV columns (zone)
ZONE_COLS = [
    'Zone Number', 'Zone Name', 'Channel Member',
]


def make_channels_analog():
    """128 channels: 16 freqs Ã— 8 CTCSS tones."""
    rows = []
    ch_num = 1
    for i, freq in enumerate(PMR_FREQS, 1):
        for tone in CTCSS_TONES:
            rows.append({
                'Channel Number': ch_num,
                'Channel Name': str(ch_num),
                'Mode': 'Analogue',
                'Bandwidth': '12.5kHz',
                'RX Frequency': f'{freq:.5f}',
                'TX Frequency': f'{freq:.5f}',
                'TX Power': 'High',
                'RX CTCSS/DCS': f'{tone:.1f}Hz',
                'TX CTCSS/DCS': f'{tone:.1f}Hz',
                'Squelch Type': 'CTCSS',
                'Scan List': '',
                'Comment': f'PMR Analog ch{i} tone{tone:.0f} 5W',
            })
            ch_num += 1
    return rows


def make_channels_digital():
    """128 channels: 16 freqs Ã— 8 TGs."""
    rows = []
    ch_num = 1
    for i, freq in enumerate(PMR_FREQS, 1):
        for tg in TGS:
            rows.append({
                'Channel Number': ch_num,
                'Channel Name': str(ch_num),
                'Mode': 'Digital',
                'Bandwidth': '12.5kHz',
                'RX Frequency': f'{freq:.5f}',
                'TX Frequency': f'{freq:.5f}',
                'TX Power': 'High',
                'Colour Code': 1,
                'Time Slot': 1,
                'Contact': f'TG {tg}',
                'Contact Type': 'Group',
                'RX Group List': '',
                'Scan List': '',
                'Comment': f'PMR Digital ch{i} TG{tg} 5W',
            })
            ch_num += 1
    return rows


def make_contacts():
    """8 group contacts (TG 1-8) for PMR simplex."""
    return [
        {
            'Contact Number': i,
            'Contact Name': f'TG {tg}',
            'Contact Type': 'Group',
            'Contact TG/DMR ID': tg,
            'Contact Timeout (seconds)': 30,
        }
        for i, tg in enumerate(TGS, 1)
    ]


def make_zones():
    """2 zones: PMR Analog (ch 1-128) and PMR Digital (ch 1-128).

    Channel numbers are per-channel-list (1-128 each), not global.
    OpenGD77 zones reference channels by their position in the global list.
    """
    analog_members = ','.join(str(i) for i in range(1, 129))
    digital_members = ','.join(str(i) for i in range(129, 257))
    return [
        {
            'Zone Number': 1,
            'Zone Name': 'PMR Analog',
            'Channel Member': analog_members,
        },
        {
            'Zone Number': 2,
            'Zone Name': 'PMR Digital',
            'Channel Member': digital_members,
        },
    ]


def write_csv(path, rows, cols):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows):3} rows to {path.name}")


def main():
    print(f"Output dir: {OUT_DIR}")
    OUT_DIR.mkdir(exist_ok=True)

    analog = make_channels_analog()
    digital = make_channels_digital()

    # Combine channels; analog = positions 1-128, digital = 129-256
    all_channels = analog + digital
    # Rewrite Channel Number column to be sequential across the combined list
    for idx, row in enumerate(all_channels, 1):
        row['Channel Number'] = idx

    write_csv(OUT_DIR / 'opengd77_channels.csv', all_channels,
              ALL_CHANNEL_COLS)

    write_csv(OUT_DIR / 'opengd77_contacts.csv',
              make_contacts(), CONTACT_COLS)

    write_csv(OUT_DIR / 'opengd77_zones.csv',
              make_zones(), ZONE_COLS)

    print()
    print("Import in OpenGD77 CPS: Extras -> Import -> select each CSV")
    print("Then: Extras -> Write to radio")


if __name__ == '__main__':
    main()
