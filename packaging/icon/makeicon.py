#!/usr/bin/env python3
"""
Render the printer icon at every size macOS wants, then `iconutil` builds the
.icns from the result.

PNG is written directly with zlib rather than through an imaging library, so
this has no dependencies beyond the standard library. Shapes are drawn 4x
oversampled and box-filtered down, which is enough anti-aliasing at icon sizes.

    makeicon.py <output.iconset>
"""
import os, struct, sys, zlib

SS = 4  # supersampling factor


class Canvas:
    def __init__(self, n):
        self.n = n
        self.px = bytearray(n * n * 4)          # RGBA, transparent

    def _blend(self, x, y, rgba):
        if not (0 <= x < self.n and 0 <= y < self.n):
            return
        i = (y * self.n + x) * 4
        r, g, b, a = rgba
        if a == 255:
            self.px[i:i+4] = bytes((r, g, b, 255))
        elif a:
            dr, dg, db, da = self.px[i:i+4]
            k = a / 255.0
            self.px[i:i+4] = bytes((
                int(r*k + dr*(1-k)), int(g*k + dg*(1-k)),
                int(b*k + db*(1-k)), max(da, a)))

    def rect(self, x, y, w, h, c):
        for yy in range(int(y), int(y+h)):
            for xx in range(int(x), int(x+w)):
                self._blend(xx, yy, c)

    def rrect(self, x, y, w, h, rad, c):
        rad = min(rad, w/2, h/2)
        for yy in range(int(y), int(y+h)):
            for xx in range(int(x), int(x+w)):
                dx = min(xx - (x+rad), 0) or max(xx - (x+w-1-rad), 0)
                dy = min(yy - (y+rad), 0) or max(yy - (y+h-1-rad), 0)
                if dx*dx + dy*dy <= rad*rad:
                    self._blend(xx, yy, c)

    def ellipse(self, cx, cy, rx, ry, c):
        for yy in range(int(cy-ry), int(cy+ry)+1):
            for xx in range(int(cx-rx), int(cx+rx)+1):
                if ((xx-cx)/rx)**2 + ((yy-cy)/ry)**2 <= 1.0:
                    self._blend(xx, yy, c)

    def downsample(self, factor):
        m = self.n // factor
        out = bytearray(m * m * 4)
        f2 = factor * factor
        for y in range(m):
            for x in range(m):
                r = g = b = a = 0
                for dy in range(factor):
                    row = (y*factor + dy) * self.n
                    for dx in range(factor):
                        i = (row + x*factor + dx) * 4
                        r += self.px[i]; g += self.px[i+1]
                        b += self.px[i+2]; a += self.px[i+3]
                j = (y*m + x) * 4
                out[j:j+4] = bytes((r//f2, g//f2, b//f2, a//f2))
        c = Canvas(m); c.px = out
        return c

    def png(self, path):
        raw = b''.join(b'\x00' + bytes(self.px[y*self.n*4:(y+1)*self.n*4])
                       for y in range(self.n))
        def chunk(tag, data):
            return (struct.pack('>I', len(data)) + tag + data +
                    struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))
        with open(path, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n')
            f.write(chunk(b'IHDR', struct.pack('>IIBBBBB', self.n, self.n, 8, 6, 0, 0, 0)))
            f.write(chunk(b'IDAT', zlib.compress(raw, 9)))
            f.write(chunk(b'IEND', b''))


BODY   = (51, 56, 66, 255)
SLOT   = (20, 23, 28, 255)
PAPER  = (255, 255, 255, 255)
EDGE   = (184, 189, 199, 255)
INK    = (28, 31, 36, 255)
FAINT  = (115, 120, 133, 255)
GREEN  = (64, 204, 107, 255)
BUTTON = (97, 105, 120, 255)
VENT   = (77, 84, 97, 255)


def render(px):
    """Draw at px*SS then filter down. Coordinates are fractions of the icon."""
    n = px * SS
    c = Canvas(n)
    U = lambda v: v * n            # unit -> pixels

    # Label emerging from the top
    c.rrect(U(.26), U(.10), U(.48), U(.34), U(.02), PAPER)
    c.rrect(U(.26), U(.10), U(.48), U(.005), U(.002), EDGE)

    # Barcode: varied bar widths so it reads as one
    x, unit = .305, .0125
    for w in (1, 2, 1, 3, 1, 1, 2, 1, 3, 2, 1, 1):
        if x + w*unit > .695:
            break
        c.rect(U(x), U(.145), U(w*unit), U(.145), INK)
        x += w*unit + unit
    # Text lines beneath
    c.rect(U(.305), U(.322), U(.30), U(.022), FAINT)
    c.rect(U(.305), U(.360), U(.20), U(.022), FAINT)

    # Printer body
    c.rrect(U(.13), U(.41), U(.74), U(.42), U(.06), BODY)
    # Exit slot
    c.rrect(U(.22), U(.43), U(.56), U(.045), U(.02), SLOT)
    # Status light, feed button
    c.ellipse(U(.246), U(.695), U(.031), U(.031), GREEN)
    c.ellipse(U(.350), U(.695), U(.025), U(.025), BUTTON)
    # Vents
    for i in range(4):
        c.rect(U(.60), U(.60 + i*.038), U(.19), U(.018), VENT)

    return c.downsample(SS)


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    sizes = [("icon_16x16", 16), ("icon_16x16@2x", 32),
             ("icon_32x32", 32), ("icon_32x32@2x", 64),
             ("icon_128x128", 128), ("icon_128x128@2x", 256),
             ("icon_256x256", 256), ("icon_256x256@2x", 512),
             ("icon_512x512", 512), ("icon_512x512@2x", 1024)]
    cache = {}
    for name, px in sizes:
        if px not in cache:
            cache[px] = render(px)
        cache[px].png(os.path.join(out, name + ".png"))
        print(f"  {name}.png")
    print(f"wrote {len(sizes)} sizes to {out}")


if __name__ == "__main__":
    main()
