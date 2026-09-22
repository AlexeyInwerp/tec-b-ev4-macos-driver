#!/usr/bin/env python3
"""
tpcldecode.py - decode a TPCL byte stream into a readable command listing.

Handles both control-code families the B-EV4 accepts:
  [ESC] ... [LF][NUL]      and      { ... |}
Binary graphic payloads ([ESC]SG / {SG) are summarised, not dumped.

Usage:  tpcldecode.py file.tpcl        (or stdin)
"""
import sys, re

NAMES = {
    'D':  'Label size set',          'AX': 'Position fine adjust',
    'AY': 'Print density fine adjust','C': 'Image buffer clear',
    'LC': 'Line/box format',         'PC': 'Bit map font format',
    'PV': 'Outline font format',     'XB': 'Bar code format',
    'RC': 'Bit map font data',       'RV': 'Outline font data',
    'RB': 'Bar code data',           'XS': 'ISSUE (print)',
    'SG': 'Graphic',                 'T':  'Feed',
    'IB': 'Eject/cut',               'XR': 'Clear area',
    'XJ': 'Comment/annotation',      'U1': 'Forward feed',
    'U2': 'Reverse feed',            'WX': 'Status request',
    'IP': 'IP address set',          'IS': 'Socket comms port set',
    'IH': 'DHCP function set',       'IG': 'Printer info store',
    'WS': 'Status//mode select',     'RM': 'Ribbon motor adjust',
}


def commands(data: bytes):
    """Yield (control_style, body) for each command in the stream."""
    i, n = 0, len(data)
    while i < n:
        if data[i] == 0x1B:                      # [ESC] .. [LF][NUL]
            end = data.find(b'\x0a\x00', i + 1)
            if end < 0:
                yield ('ESC', data[i + 1:]); return
            yield ('ESC', data[i + 1:end]); i = end + 2
        elif data[i] == 0x7B:                    # { .. |}
            end = data.find(b'|}', i + 1)
            if end < 0:
                yield ('{}', data[i + 1:]); return
            yield ('{}', data[i + 1:end]); i = end + 2
        else:
            i += 1


def opcode(body: bytes) -> str:
    m = re.match(rb'([A-Z]{1,2}[0-9]?)', body)
    return m.group(1).decode() if m else '?'


def main():
    raw = open(sys.argv[1], 'rb').read() if len(sys.argv) > 1 else sys.stdin.buffer.read()
    total = 0
    stats = {}
    for idx, (style, body) in enumerate(commands(raw), 1):
        total += 1
        op = opcode(body)
        base = re.sub(r'\d+$', '', op) or op
        stats[base] = stats.get(base, 0) + 1
        label = NAMES.get(base, NAMES.get(op, ''))
        if base == 'SG':
            head, _, payload = body.partition(b',')
            # summarise the binary graphic payload rather than dumping it
            parts = body.split(b',')
            meta = b','.join(parts[:6])[:70].decode('latin-1', 'replace')
            print(f"{idx:5}  {style:4} SG   {label:28} {meta}... "
                  f"[+{len(body)} bytes binary]")
        else:
            txt = body.decode('latin-1', 'replace')
            if len(txt) > 96:
                txt = txt[:93] + '...'
            print(f"{idx:5}  {style:4} {base:4} {label:28} {txt}")
    print(f"\n{total} commands, {len(raw)} bytes")
    print("opcode histogram: " + ", ".join(f"{k}={v}" for k, v in
                                           sorted(stats.items(), key=lambda kv: -kv[1])))


if __name__ == '__main__':
    main()
