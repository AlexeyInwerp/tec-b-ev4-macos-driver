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

SS = 2  # supersampling factor


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

    def vgrad_rrect(self, x, y, w, h, rad, top, bot):
        """Rounded rect with a vertical gradient - gives the body some form."""
        rad = min(rad, w/2, h/2)
        for yy in range(int(y), int(y+h)):
            t = (yy - y) / max(h - 1, 1)
            c = tuple(int(top[i] + (bot[i]-top[i])*t) for i in range(3)) + (255,)
            for xx in range(int(x), int(x+w)):
                dx = min(xx - (x+rad), 0) or max(xx - (x+w-1-rad), 0)
                dy = min(yy - (y+rad), 0) or max(yy - (y+h-1-rad), 0)
                if dx*dx + dy*dy <= rad*rad:
                    self._blend(xx, yy, c)

    def shadow(self, x, y, w, h, rad, spread, alpha, steps=5):
        """Soft shadow from a few offset rounded rects.

        Deliberately only a handful of passes: each one is a full per-pixel
        fill in Python, so a true blur here costs minutes at 1024px.
        """
        for i in range(steps, 0, -1):
            off = spread * i / steps
            a = int(alpha / steps)
            if a < 1:
                continue
            self.rrect(x - off, y - off + spread*0.35,
                       w + 2*off, h + 2*off, rad + off, (0, 0, 0, a))

    def downsample(self, factor):
        m = self.n // factor
        out = bytearray(m * m * 4)
        f2 = factor * factor
        px = self.px
        for y in range(m):
            for x in range(m):
                r = g = b = a = 0
                for dy in range(factor):
                    row = (y*factor + dy) * self.n
                    for dx in range(factor):
                        i = (row + x*factor + dx) * 4
                        av = px[i+3]
                        r += px[i]*av; g += px[i+1]*av; b += px[i+2]*av
                        a += av
                j = (y*m + x) * 4
                if a:
                    out[j:j+4] = bytes((r//a, g//a, b//a, a//f2))
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


BODY_TOP = (74, 82, 98)          # gradient, lighter at the top
BODY_BOT = (38, 43, 54)
HILITE   = (104, 113, 132, 255)
SLOT     = (18, 21, 26, 255)
SLOT_LIP = (9, 11, 14, 255)
PAPER    = (255, 255, 255, 255)
EDGE     = (170, 176, 189, 255)
INK      = (26, 29, 34, 255)
FAINT    = (132, 138, 152, 255)
GREEN    = (56, 190, 100, 255)
BUTTON   = (112, 121, 138, 255)
VENT     = (92, 100, 116, 255)


def render(px):
    """Draw at px*SS then filter down. Coordinates are fractions of the icon."""
    n = px * SS
    c = Canvas(n)
    U = lambda v: v * n            # unit -> pixels

    # --- label, emerging from the top -----------------------------------
    lx, ly, lw, lh = .275, .055, .45, .40
    c.rrect(U(lx), U(ly), U(lw), U(lh), U(.012), PAPER)
    # full border, not just a top edge
    c.rrect(U(lx), U(ly), U(lw), U(lh), U(.012), EDGE)
    c.rrect(U(lx) + U(.006), U(ly) + U(.006), U(lw) - U(.012), U(lh) - U(.012),
            U(.008), PAPER)

    # barcode, with quiet zones either side
    x, unit = lx + .055, .0115
    for w in (2, 1, 1, 3, 1, 2, 1, 1, 3, 1, 2, 1, 1, 2):
        if x + w*unit > lx + lw - .055:
            break
        c.rect(U(x), U(ly + .055), U(w*unit), U(.155), INK)
        x += w*unit + unit
    # human-readable lines beneath
    c.rect(U(lx + .055), U(ly + .235), U(.24), U(.020), FAINT)
    c.rect(U(lx + .055), U(ly + .275), U(.16), U(.020), FAINT)

    # --- printer body ----------------------------------------------------
    bx, by, bw, bh = .105, .40, .79, .455
    c.vgrad_rrect(U(bx), U(by), U(bw), U(bh), U(.075), BODY_TOP, BODY_BOT)
    # exit slot, recessed
    c.rrect(U(.185), U(.425), U(.63), U(.052), U(.024), SLOT)
    c.rrect(U(.185), U(.425), U(.63), U(.014), U(.007), SLOT_LIP)

    # --- controls --------------------------------------------------------
    c.ellipse(U(.205), U(.705), U(.028), U(.028), GREEN)
    c.ellipse(U(.300), U(.705), U(.026), U(.026), BUTTON)

    # vents
    for i in range(4):
        c.rect(U(.60), U(.615 + i*.042), U(.205), U(.020), VENT)

    return c.downsample(SS)


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    sizes = [("icon_16x16", 16), ("icon_16x16@2x", 32),
             ("icon_32x32", 32), ("icon_32x32@2x", 64),
             ("icon_128x128", 128), ("icon_128x128@2x", 256),
             ("icon_256x256", 256), ("icon_256x256@2x", 512),
             ("icon_512x512", 512), ("icon_512x512@2x", 1024)]
    # Render once at the largest size, then halve repeatedly. Far cheaper than
    # rendering each size, and keeps them visually identical.
    master = render(1024)
    cache = {1024: master}
    for px in (512, 256, 128, 64, 32, 16):
        cache[px] = cache[px*2].downsample(2)
    for name, px in sizes:
        cache[px].png(os.path.join(out, name + ".png"))
        print(f"  {name}.png")
    print(f"wrote {len(sizes)} sizes to {out}")


if __name__ == "__main__":
    main()
