# Toshiba TEC B-EV4 — macOS / CUPS driver

A working CUPS driver for the **Toshiba TEC B-EV4** thermal label printer on
modern macOS (tested on macOS 26 "Tahoe", Apple Silicon), plus a small Python
toolkit for talking native **TPCL** to the printer directly.

I bought this printer and it turned out to be the only genuinely nice, stable
workhorse label printer I've owned — so I decided to spend some tokens and make
a proper open-source driver for it, because Toshiba never shipped one for the
Mac.

## Status

| Thing | State |
| --- | --- |
| Native TPCL text / lines / boxes | working |
| Native TPCL barcodes (CODE128 etc.) | working |
| CUPS raster driver (print any app / PDF) | working |
| TOPIX graphics compression | working (~12:1 on a real shipping label) |
| 100 × 150 mm direct thermal | working, default media |
| Verbose debug filter + TPCL decoder | working |

## Hardware

* Toshiba TEC **B-EV4-G** (203 dpi, 8 dots/mm). The 300 dpi `-T` variants are
  covered by the same PPD set.
* USB. The printer reports itself as `usb://TEC/B-EV4-G`.
* Media used for development: 100 × 150 mm direct thermal labels, 2 mm gap.

## Install

```sh
sudo driver/install.sh
```

This builds the filter, generates the PPDs, installs them, and creates a
`TEC_B_EV4` queue. Then:

```sh
lp -d TEC_B_EV4 some-100x150-label.pdf
```

`sudo` is required because CUPS refuses to execute a filter that is not owned
by root.

### Why the filter does not live in `/usr/libexec/cups/filter`

On current macOS the system volume is a **sealed, read-only snapshot**, so
nothing can be added to `/usr/libexec`. CUPS accepts an *absolute path* in the
PPD's `*cupsFilter` line, which is what vendor drivers under `/Library/Printers`
already do, so the filter is installed to `/Library/Printers/TEC/filter` and
the PPDs are rewritten to point at it.

## Native TPCL toolkit

`tools/tpcl.py` generates TPCL directly — much sharper and far smaller than
rasterising, and it uses the printer's own fonts and barcode engine:

```python
from tpcl import Label
L = Label(width_mm=100, length_mm=150, gap_mm=2)
L.size(); L.clear()
L.rect(20, 20, 980, 1480, width_dots=3)
L.text(1, 60, 80, "HELLO", font=b'K')
L.barcode(1, 55, 880, "BEV4-MACOS", btype=b'9', module=3, height_mm=20)
L.issue(copies=1, sensor='2', mode='C', speed='3', ribbon='0')
open("label.tpcl","wb").write(L.bytes())
```

```sh
lp -d TEC_B_EV4 -o raw label.tpcl
```

`tools/tpcldecode.py` turns a TPCL stream back into a readable command listing
(handling both the `[ESC]…[LF][NUL]` and `{…|}` control-code families, and
summarising binary graphic payloads instead of dumping them).

## Debugging

Install with `DEBUG_QUEUE=1 sudo -E driver/install.sh` to also get a
`TEC_B_EV4_DEBUG` queue wired to `rastertotpcl-debug`. That wrapper logs the
full filter invocation and tees both the incoming CUPS raster and the outgoing
TPCL into `/tmp/tpcl-debug/`, so any job can be replayed without a printer:

```sh
cupsctl LogLevel=debug
lp -d TEC_B_EV4_DEBUG label.pdf
tools/tpcldecode.py /tmp/tpcl-debug/<stamp>.tpcl
lp -d TEC_B_EV4 -o raw /tmp/tpcl-debug/<stamp>.tpcl   # replay
```

## Changes made to the upstream driver

`rastertotpcl` needed several fixes to work on current macOS:

1. **`#include <cups/ppd.h>`** — CUPS 2.3 no longer pulls `ppd.h` in via
   `cups.h`, so every `ppd_file_t` failed to compile.
2. **Absolute `cupsFilter` path** — required by the sealed system volume.
3. **Metric label sizes** — added 100×150, 100×100, 100×75, 100×50, 60×40,
   58×40, 57×32, 50×30 and 40×30 mm; 100×150 mm is now the default.
4. **Fixed malformed PostScript** in the `Darkness` option (choice `2` emitted
   `<</cupsCompression 2>setpagedevice` — a missing `>`).
5. **Location-independent USB URI** — `usb://TEC/B-EV4-G` rather than pinning
   `?location=…`, which breaks whenever the printer is replugged into a
   different port or hub.
6. **Verbose debug filter** and a **TPCL decoder** for offline diagnosis.

## Credits and licensing

This project is **GPLv3**, inherited from `rastertotpcl`.

* **`rastertotpcl`** — Copyright 2010 [Sam Lown](https://github.com/samlown/rastertotpcl), GPLv3.
* **`rastertotec`** — Copyright 2009 Patrick Kong (SKE s.a.r.l), which
  `rastertotpcl` is based on.
* **`rastertolabel`** — Copyright 2001–2007 Easy Software Products, part of the
  CUPS printing system, which `rastertotec` is based on.
* macOS port, metric media, debug tooling and the TPCL toolkit — this repo,
  GPLv3.

Command syntax follows Toshiba TEC's *B-EV4 Series External Equipment Interface
Specification*, which documents TPCL. Toshiba TEC and TPCL are trademarks of
Toshiba TEC Corporation; this project is not affiliated with or endorsed by
Toshiba TEC.

See [LICENSE](LICENSE) for the full GPLv3 text.
