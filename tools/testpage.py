#!/usr/bin/env python3
import sys, datetime
from tpcl import Label

L = Label(width_mm=100.0, length_mm=150.0, gap_mm=2.0)
L.size()
L.clear()

# Outer frame - shows the real printable area on the label
L.rect(20, 20, 980, 1480, width_dots=3)
# Inner header rule
L.line(20, 200, 980, 200, width_dots=2)

L.text(1, 60,  80,  "TOSHIBA TEC B-EV4",  font=b'K', hmag=1, vmag=1)
L.text(2, 60,  150, "macOS CUPS driver - TEST PAGE", font=b'H')

L.text(10, 60, 260, "Model      : B-EV4-G  (203 dpi / 8 dots-mm)", font=b'Q')
L.text(11, 60, 320, "Media      : 100 x 150 mm direct thermal",   font=b'Q')
L.text(12, 60, 380, "Label size : D%04d,%04d,%04d" % (L.pitch, L.width, L.length), font=b'Q')
L.text(13, 60, 440, "Date       : " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), font=b'Q')
L.text(14, 60, 500, "Control    : [ESC] .. [LF][NUL]", font=b'Q')

# Corner registration marks - verify margins / skew
for (x, y) in ((40, 40), (940, 40), (40, 1440), (940, 1440)):
    L.rect(x - 20, y - 20, x + 20, y + 20, width_dots=2)

# Vertical ruler down the left edge: a tick every 10 mm
for mm in range(0, 151, 10):
    y = mm * 10
    if y < 60 or y > 1460:
        continue
    L.line(20, y, 90 if mm % 50 else 140, y, width_dots=1)

L.text(20, 60, 1380, "If you can read this, the driver works.", font=b'H')

L.issue(copies=1, sensor='2', mode='C', speed='3', ribbon='0')

out = L.bytes()
sys.stdout.buffer.write(out)
sys.stderr.write("generated %d bytes\n" % len(out))
