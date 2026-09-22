# Porting notes

Assessment of what it would take to run this on older macOS, and on Windows.

Everything in the macOS section was verified by compiling and inspecting
binaries on macOS 26 / Apple Silicon. **None of it has been run on an actual
Catalina machine** — there wasn't one available — so treat it as a well-founded
static analysis rather than a tested port.

## Older macOS, down to Catalina (10.15)

**Verdict: should work with no source changes.** The build system now produces a
universal binary targeting 10.15 by default.

### Why it looks safe

The filter needs only twelve CUPS symbols, all of them long-stable API that
predates Catalina by years:

```
cupsFreeOptions   cupsMarkOptions      cupsParseOptions
cupsRasterClose   cupsRasterOpen       cupsRasterReadHeader2  cupsRasterReadPixels
ppdClose          ppdFindMarkedChoice  ppdIsMarked            ppdMarkDefaults
ppdOpenFile
```

`cupsRasterReadHeader2` is the newest of them and dates from CUPS 1.2 (2006).
Catalina ships CUPS 2.3 with both `libcups.2.dylib` and `libcupsimage.2.dylib`,
so every symbol resolves.

Compiling against the macOS 26 SDK with `-mmacosx-version-min=10.15` produces a
binary stamped `minos 10.15` linked only against `libcups.2.dylib`,
`libcupsimage.2.dylib` and `libSystem.B.dylib`.

### Architecture

Catalina is Intel-only, and Apple Silicon did not exist before Big Sur, so the
two slices get different floors:

| Slice | Minimum | Covers |
| --- | --- | --- |
| `x86_64` | 10.15 Catalina | Intel Macs, Catalina onwards |
| `arm64` | 11.0 Big Sur | Apple Silicon |

`build.sh` produces both and `lipo`s them together. Override with
`UNIVERSAL=0`, `MACOS_MIN_X86` or `MACOS_MIN_ARM`.

### Things that need no change

* **The absolute `cupsFilter` path.** Catalina introduced the read-only system
  volume, so `/usr/libexec/cups/filter` is already unwritable there. The
  `/Library/Printers/TEC/filter` approach is required on every version from
  10.15 up, not just current ones.
* **LPD networking.** A printer-side limitation, identical everywhere.
* **The Python tools.** Standard library only. `bytes.hex(sep)` needs Python
  3.8, which Catalina provides via the Command Line Tools.

### One real risk

`ppdc` compiles the `.drv` into PPDs. It is present on macOS 26, but Apple has
been steadily removing CUPS utilities, and it may be missing on some systems in
either direction. `build.sh` now falls back to the checked-in `ppd-prebuilt/`
directory when `ppdc` is unavailable, so a missing `ppdc` is no longer fatal.

Note the deprecation pressure runs **forwards**, not backwards: `lpadmin`
already warns that "printer drivers are deprecated and will stop working in a
future version of CUPS". Old macOS is the safe direction; new macOS is where
this will eventually break.

## Windows

**Verdict: do not port the driver. Port the tooling.**

### Why not the driver

Toshiba ships an official Windows TPCL driver, so there is a supported,
maintained option already. Rewriting a CUPS raster filter as a Windows V4 or
XPS print driver is a substantial project — a different rendering pipeline, a
different installation model, and driver signing — to arrive at something that
already exists.

### What is worth having on Windows

The Python tools are pure standard library and run unchanged:

| Tool | Windows | Notes |
| --- | --- | --- |
| `tpcl.py` | yes | no I/O of its own |
| `tpcldecode.py` | yes | |
| `bev4ctl.py` | yes | sockets and HTTP only |
| `netconfig.py` | yes | writes to stdout |
| `lpdsend.py` | yes | plain sockets |
| `lan-setup.sh` | no | needs `ifconfig`/`route`; PowerShell rewrite |
| `lan-find.sh` | no | needs `tcpdump`; PowerShell rewrite |

### The one thing that matters most on Windows

When adding the printer, Windows offers a **Standard TCP/IP Port** which
defaults to **RAW on port 9100**. Do not use raw mode. This printer's
raw-socket implementation silently discards jobs above a few kilobytes — see
the main README — and that is a printer-side fault, so it will behave exactly
the same way from Windows.

Configure the port as **LPR**, queue name `lp`, and enable **LPR Byte Counting**.
