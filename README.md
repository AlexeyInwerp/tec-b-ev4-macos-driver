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
| TOPIX graphics compression | working (~12:1 on a typical 100 × 150 mm label) |
| 100 × 150 mm direct thermal | working, default media |
| Verbose debug filter + TPCL decoder | working |
| LAN printing | working via **LPD** (`lpd://<ip>/lp`); raw socket is broken |
| Web UI + CLI administration | working |
| Media sensor (transmissive / gap) | working |

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

## Updating

```sh
git pull
sudo driver/update.sh
```

`update.sh` rebuilds and swaps the filter binaries in place — safe at any time,
since CUPS exec's the filter per job — and refreshes the installed PPDs. It
deliberately **leaves your queues alone**, so a tuned darkness or print speed
survives the update.

If the PPD itself changed (new media sizes, new options), `update.sh` says so
but does not force it on you, because re-applying a PPD resets queue options
back to defaults. Note your current settings first, then opt in:

```sh
lpoptions -p TEC_B_EV4          # what you have now
sudo APPLY_PPD=1 driver/update.sh
```

Re-running `sudo driver/install.sh` also works as a blunt update, but it always
recreates the queue and so always resets those options.

## Uninstalling

```sh
sudo driver/uninstall.sh                    # filter, PPDs and queues
KEEP_QUEUES=1 sudo -E driver/uninstall.sh   # leave queues in place
```

## Printer administration

The B-EV4 has **two independent management surfaces**, and they expose
different things:

| Surface | Port | Gives you |
| --- | --- | --- |
| TPCL raw socket | 8000 | live status, model, serial, feed, printing |
| Embedded web server (`Ethernut`) | 80 | the **stored configuration** — parameters, calibration, network, password |

TPCL has no command to read parameters back — only `[ESC]Z2;1`, which writes
all of them positionally at once. The web UI is therefore the only safe way to
see the current configuration.

`tools/bev4ctl.py` talks to both:

```sh
bev4ctl.py --host 192.168.1.50 status   # live state + remaining count
bev4ctl.py --host 192.168.1.50 info     # model, serial, firmware, mileage
bev4ctl.py --host 192.168.1.50 params   # stored configuration
bev4ctl.py --host 192.168.1.50 feed
bev4ctl.py --host 192.168.1.50 print label.tpcl
```

The web UI lives at `http://<printer-ip>/` and its pages are:

| Page | Path |
| --- | --- |
| Status | `/cgi-bin/status.cgi` |
| Parameter | `/admin/cgi-bin/parameter.cgi` |
| Calibration | `/cgi-bin/calibrate.cgi` |
| Network | `/cgi-bin/network.cgi` |
| Function | `/cgi-bin/function.cgi` |
| Password | `/admin/cgi-bin/password.cgi` |

Note the server answers some `/admin/` paths in bare **HTTP/0.9** with no status
line, which makes `curl` refuse them unless you pass `--http0.9`. `bev4ctl.py`
parses both forms.

### Stopping the label feed at every power-on

If the printer feeds several labels each time it starts, the cause is the
**`AUTO CALIB.`** parameter (`v` in `[ESC]Z2;1`, "automatic sensor calibration
— ON with current sensor when power on"). Its factory default is OFF; when it
is ON the printer feeds media at power-up to sample the gap sensor.

Set **AUTO CALIB.** to **OFF** at `/admin/cgi-bin/parameter.cgi`, press *Set*,
and power-cycle. `bev4ctl.py params` reports the current value.

A related setting, **`Forward Wait`** (`i`, "forward feed standby after an
issue"), makes the printer advance 16.3 mm after issuing; turn that off too if
you see a feed *after* printing rather than at startup.

Porting notes for older macOS and Windows: **[docs/porting.md](docs/porting.md)**.

Every parameter is documented in **[docs/parameters.md](docs/parameters.md)**,
including which ones the B-EV4 ignores entirely and one that will silently
break this project if changed.

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

## Network (LAN) printing

The B-EV4's LAN interface offers **LPD on port 515**, a **raw socket on port
8000**, and a **web UI on port 80**.

> **Use LPD. Do not use the raw socket port.**
>
> The raw socket silently discards anything much over a few kilobytes — see
> below. LPD works correctly, including full-page TOPIX-compressed graphics.

```sh
lpadmin -p TEC_B_EV4_NET -E -v lpd://192.168.1.50/lp \
        -P driver/ppd/tecbev4d.ppd \
        -o PageSize=w283h425 -o teMediaTracking=2 -o MediaType=Direct \
        -o Resolution=203dpi -o Gap=2 -o teGraphicsMode=1
```

### Why not `socket://`

`socket://<ip>:8000` is the obvious choice and it is a trap. Small jobs print,
so it looks like it works — then real jobs vanish. Measured on a B-EV4-G
running firmware V1.1G:

| Job | Size | Result over `socket://8000` |
| --- | --- | --- |
| Text and lines only | 1.2 KB | prints |
| One small graphic | 0.4 KB | prints |
| 12 banded graphics | 7.7 KB | prints |
| 100 banded graphics | 63 KB | **syntax error, nothing printed** |
| Full page, TOPIX | 9.7 KB | **no error, nothing printed** |
| Full page, banded nibble | 251 KB | **no error, nothing printed** |

The failure is silent in the worst way: CUPS reports the job completed, the
printer reports status `00` (normal), and no label appears. The printer accepts
the whole job into its TCP buffers in milliseconds without ever applying
backpressure — far faster than a device with a 1 KB receive buffer could
actually consume it — so the data is being taken in and dropped.

Things that did **not** fix it, in case you are tempted:

* **Pacing the send.** Chunking with delays makes it *worse* — a pause inside a
  graphic payload produces a syntax error where a straight burst does not.
* **Avoiding binary data.** Nibble mode (every byte `30H`-`3FH`, pure printable
  ASCII) fails exactly like TOPIX, so this is not byte-level corruption.
* **Splitting into small commands.** 400 self-contained `SG` commands, none
  larger than 626 bytes, fail just as a single large one does. The limit is on
  the job, not the command.
* **Either control-code family.** `[ESC]…[LF][NUL]` and `{…|}` behave the same.

The identical byte streams print correctly over USB, and over LPD. It is the
raw-socket implementation in the print server that is at fault, nothing else.

### Reserve the address

The printer has no mDNS, so nothing rediscovers it if its address changes — and
a DHCP lease *will* eventually move. When it does, the CUPS queue keeps pointing
at the old address and every job fails; during development the lease jumped from
`…135` to `…163` mid-session and broke the queue exactly this way.

Give it a **DHCP reservation** on your router, or a static address via
`tools/lan-setup.sh --ip <address>`. If it does go missing:

```sh
nmap -p 80,515,8000 192.168.1.0/24 --open    # B-EV4 answers on all three
lpadmin -p TEC_B_EV4_NET -v lpd://<new-ip>/lp
```

### Sending to LPD directly

`tools/lpdsend.py` is a minimal RFC 1179 client, useful for testing without
CUPS in the way:

```sh
tools/lpdsend.py label.tpcl lp
```

Every stage is acknowledged by the printer, which is exactly what the raw
socket fails to do.

### The problem: a factory-fresh unit is invisible on your network

This is the part that costs an afternoon, so it is worth stating plainly.

The printer ships with a **static IP of `192.168.10.20`**. Almost nobody runs
that subnet, so when you plug it into a typical LAN:

* it does **not** appear in a ping sweep or an ARP scan of your subnet;
* it does **not** appear in Bonjour — the B-EV4 has no mDNS at all, so
  "Add Printer" will never find it;
* the **link LED is green and blinking**, which makes the cabling look fine —
  and it *is* fine. The printer is on the wire, just on a different subnet;
* its web UI is unreachable, so you cannot use the web UI to fix the web UI.

That last point is the trap: every on-printer configuration surface is behind
an IP address the printer does not yet have on your network.

### Three ways out, in order of preference

**1. Over USB** — the reliable one. `netconfig.py` emits the configuration
commands; send them with `lp -o raw`, then power-cycle:

```sh
tools/netconfig.py --dhcp > net.tpcl
lp -d <usb-queue> -o raw net.tpcl
```

It writes only to stdout, so nothing reaches the printer unless you pipe it
there. The 53 bytes it produces are `[ESC]IH;1,FF…` (enable DHCP, use the MAC
as the client ID) and `[ESC]IS;1,08000` (keep socket printing enabled).

**2. Over the LAN, without touching any cable** — `lan-setup.sh` reaches the
printer *on its own subnet* by giving your Mac a temporary second address
there:

```sh
sudo tools/lan-setup.sh --dhcp          # or: --ip 192.168.1.60
```

It adds `192.168.10.99/24` to your default interface, sends `[ESC]WS` first and
**refuses to continue unless a TPCL printer answers** — an HTTP reply is
rejected explicitly, because a NAS on port 8000 looked like a candidate during
development — then removes the alias from an `EXIT` trap, so a failure cannot
leave your interface modified.

**3. When you do not know where it is at all** — `lan-find.sh` listens
passively instead of probing:

```sh
sudo tools/lan-find.sh 30      # power-cycle the printer while it listens
```

A ping sweep cannot see a host on a foreign subnet, but that host still
chatters. This captures ARP/DHCP/ICMP and reports any MAC that is not a known
neighbour, flagging Toshiba TEC OUIs and off-subnet addresses. It separates the
three failure modes that otherwise look identical:

| Observation | Meaning |
| --- | --- |
| Toshiba MAC sending DHCP DISCOVER, no reply | DHCP works; your server is not leasing to it |
| Toshiba MAC using `192.168.10.x` | Still on the factory static |
| No Toshiba MAC at all | Not on your segment, despite the link LED |

After any of these, **power-cycle the printer** — network settings only take
effect at initialisation.

### Finding it afterwards

Scan for the port signature rather than by name; there is no mDNS to find:

```sh
# the B-EV4 answers on 515 (LPD), 8000 (socket) and 80 (web UI)
nmap -p 80,515,8000 192.168.1.0/24 --open
```

Confirm identity without printing anything — `[ESC]IR` returns model and
serial:

```sh
tools/bev4ctl.py --host <ip> info
```

> A port scan limited to the usual printer ports (515/631/9100) will miss the
> **web UI on port 80** entirely. Include 80, or you will conclude the printer
> has no management interface when it has a full one.

## A note on USB stability

During development this printer repeatedly dropped off the USB bus when
connected through a chained hub, re-enumerating at a different location ID each
time (`?location=1130000` -> `130000` -> `1100000`). A queue pinned to
`usb://TEC/B-EV4-G?location=...` goes "offline" the moment that happens, and
queued jobs stall until the URI is corrected.

Two mitigations:

* Connect the printer **directly to the machine**, not through a hub chain.
* Or use the LAN interface, which has no such problem.

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
