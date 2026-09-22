#!/usr/bin/env python3
import sys, datetime
from tpcl import Label

L = Label(width_mm=100.0, length_mm=150.0, gap_mm=2.0)
L.size(); L.clear()

L.rect(20, 20, 980, 1480, width_dots=3)
L.line(20, 210, 980, 210, width_dots=3)

L.text(1, 55, 70,  "TOSHIBA TEC B-EV4",             font=b'K')
L.text(2, 55, 150, "macOS native driver - PAGE 2",  font=b'I')

L.text(10, 55, 270, "Native TPCL vector text + printer barcode engine", font=b'G')

# Font sample ladder - each line is a different ROM font
samples = [
    (b'A', "A  Times Roman 12pt"),
    (b'E', "E  Times Bold 21pt"),
    (b'H', "H  Helvetica 15pt"),
    (b'K', "K  Helvetica Bold 21pt"),
    (b'M', "M  Presentation 27pt"),
    (b'Q', "Q  Courier 15pt"),
]
y = 340
for font, caption in samples:
    L.text(20 + samples.index((font, caption)), 55, y, caption, font=font)
    y += 75

# CODE128 with auto code-set selection, 3-dot module, 20 mm tall
L.barcode(1, 55, 880, "BEV4-MACOS-2026", btype=b'9', checkdigit=b'1',
          module=3, height_mm=20.0)
L.text(30, 55, 1100, "BEV4-MACOS-2026", font=b'Q')
L.text(31, 55, 1160, "CODE128 (auto code set), 3 dot module", font=b'G')

L.line(20, 1240, 980, 1240, width_dots=2)
L.text(40, 55, 1270, "203 dpi | 100 x 150 mm | direct thermal", font=b'H')
L.text(41, 55, 1330, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), font=b'Q')
L.text(42, 55, 1400, "Driver: rastertotpcl (GPLv3) + TPCL toolkit", font=b'G')

L.issue(copies=1, sensor='2', mode='C', speed='3', ribbon='0')

sys.stdout.buffer.write(L.bytes())
sys.stderr.write("generated %d bytes\n" % len(L.bytes()))
