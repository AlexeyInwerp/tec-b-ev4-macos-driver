#!/usr/bin/env python3
"""
rasterpreview.py - turn a CUPS raster into a PNG you can look at.

The single most useful thing when a label comes out wrong is knowing whether
the raster handed to the driver was already wrong, or whether the driver or
printer mangled a correct one. This renders the raster so you can see.

Build the companion decoder once (it uses libcupsimage to handle the
compressed raster formats):

    clang -Os -w -o rasterdump tools/rasterdump.c -lcups -lcupsimage

Then:

    ./rasterdump < job.raster | ./rasterpreview.py - preview.png

Capture a real job's raster with the debug queue - see README "Debugging".
"""
import struct, sys, zlib


def main():
    src, dst = sys.argv[1], sys.argv[2]
    data = sys.stdin.buffer.read() if src == '-' else open(src, 'rb').read()

    nl = data.index(b'\n')
    w, h = map(int, data[:nl].split())
    bits = data[nl+1:]
    bpl = (w + 7) // 8

    rows = bytearray()
    for y in range(h):
        row = bits[y*bpl:(y+1)*bpl]
        line = bytearray(b'\x00')                  # PNG filter: none
        for x in range(w):
            byte = row[x >> 3] if (x >> 3) < len(row) else 0
            ink = (byte >> (7 - (x & 7))) & 1      # 1 bit per dot, 1 = black
            line += b'\x00\x00\x00' if ink else b'\xff\xff\xff'
        rows += line

    def chunk(tag, payload):
        return (struct.pack('>I', len(payload)) + tag + payload +
                struct.pack('>I', zlib.crc32(tag + payload) & 0xffffffff))

    with open(dst, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)))
        f.write(chunk(b'IDAT', zlib.compress(bytes(rows), 6)))
        f.write(chunk(b'IEND', b''))
    print(f"{w} x {h} dots -> {dst}")


if __name__ == '__main__':
    main()
