# B-EV4 parameter reference

Every setting on `/admin/cgi-bin/parameter.cgi`, what it actually does, and
what it should be for 100 × 150 mm gapped direct-thermal labels over USB/LAN.

These map to the positional fields of the Parameter Set Command `[ESC]Z2;1`.
Several fields in that command are documented as **"Ignore"** on the B-EV4 —
the parameter block is shared across Toshiba's B-series and this model simply
does not implement them (ribbon saving, head-broken-dot check, Centronics
timing, Kanji codes, strip status, web printer function).

Changes take effect **only after the printer is re-initialised** — power-cycle,
or send the Batch Reset Command `[ESC]Z0`.

| Web UI | Field | Meaning | For gapped DT labels |
| --- | --- | --- | --- |
| FONT CODE | `code_page` | Code page for the printer's **built-in bitmap fonts**. PC-850 covers Western European incl. umlauts. No effect on raster printing. | `PC-850` |
| Zero Code | `zero_code` | Whether `0` renders slashed, in native fonts only. Cosmetic. | either |
| Comm. Speed | `rate` | RS-232C baud rate. | irrelevant over USB/LAN |
| Data Leng. | `data` | RS-232C word length. | irrelevant |
| Stop Bit(s) | `stop` | RS-232C stop bits. | irrelevant |
| Parity | `parity` | RS-232C parity. | irrelevant |
| CONTROL | `control` | RS-232C flow control, and whether XON/XOFF is emitted at power on/off. | irrelevant |
| DESTINATION | `destination` | Regional firmware variant. `JA`/`CSG` remap `5CH` from `\` to `¥` and enable Japanese bitmap fonts. | `QM` |
| Forward Wait | `forward` | **Forward feed standby after an issue.** Advances ~16.3 mm after printing so the label clears the tear bar, then reverse-feeds before the next one. Costs media and adds a feed cycle per job. | `OFF` unless you tear off every label by hand |
| Code | `code` | Control-code family: automatic, fixed `[ESC]…[LF][NUL]`, or fixed `{…|}`. **Automatic accepts both and decides per command.** | `Automatic Selection` — see warning below |
| Feed Key | `feedkey` | What the front key does: `FEED` advances one blank label, `PRINT` re-issues the image buffer. | `FEED` |
| Euro Code | `euro` | Code point that renders `€`, as two ASCII hex digits. | `B0` |
| Auto Home | `autohome` | **Automatic home position detection — black-mark media with a cutter only.** At power-on or cover-close the printer *reverse*-feeds hunting for the 2nd black mark, then backs up a further 35 mm. If it is not found within half the media length it raises a **paper jam error**. | **`OFF`** — on gapped labels this errors |
| AUTO CALIB. | `autocalib` | **Automatic sensor calibration at power-on.** Feeds media to sample gap-vs-label sensor levels every time the printer starts. Factory default OFF. | `OFF` — this is the startup label feed |
| Model Select | `model` | `DT` direct thermal / `TT` thermal transfer. `TT` makes the printer expect a ribbon and raise ribbon errors without one. | `DT` |
| X Coordinate | `x_coordinate` | Horizontal print offset, `000`–`995` in **0.5 mm** units, signed. Shifts the whole image left/right. Part of `[ESC]Z2;2`, not `Z2;1`. | `0`, unless output sits off-centre |

## Warning: do not set `Code` to a fixed mode

The CUPS filter (`rastertotpcl`) emits `{…|}` control codes, while the Python
tooling in `tools/` emits `[ESC]…[LF][NUL]`. Both work at once **only because
`Code` is `Automatic Selection`**, which re-detects the family on every command.

Pinning it to one mode silently breaks the other half of this project.

## Calibration

If gap detection becomes unreliable after turning `AUTO CALIB.` off — typically
after changing to different label stock — run a **manual** calibration once from
`/cgi-bin/calibrate.cgi` rather than turning the automatic one back on. The
result is stored, so it survives power cycles without feeding labels every time.

## Media sensors

The B-EV4 has **both sensors built in**, plus a no-sensor mode. You choose which
one is active; it is not a hardware variant.

| Sensor | How it works | Media it is for |
| --- | --- | --- |
| **Transmissive** (gap) | Emitter and receiver sit on **opposite sides** of the paper path. Light shines *through* the media; the label-to-label gap is just liner, so more light gets through and the printer sees a spike. | Die-cut labels on a liner — **the normal case**, incl. 100 × 150 mm |
| **Reflective** (black mark) | Emitter and receiver sit on the **same side**, below the media. Light bounces off; a black mark printed on the **back** absorbs it and the reflection dips. | Tag stock with black marks |
| **No sensor** | No detection at all — the printer just feeds the length given by `[ESC]D`. | Continuous receipt-style roll |

Either way the printer prints the length set by the Label Size Set Command, but
with a sensor active it re-finds the true edge **on every label**, correcting
drift. With no sensor, small errors accumulate down the roll.

### Selecting it

Three places, in increasing precedence:

1. **On the printer**, which sets the stored default. Power on to online mode,
   open the cover (the LED goes out), hold **FEED for over 5 seconds** and
   release — the printer enters sensor selection mode. Then press FEED when the
   LED shows the one you want:

   | LED | Selects |
   | --- | --- |
   | green | reflective |
   | orange | no sensor |
   | red | transmissive |

2. **Per queue**, via the PPD's *Media Detection* option (`teMediaTracking`).
3. **Per job**, via parameter `c` of the Issue Command `[ESC]XS;I,…`.

The driver passes the PPD choice straight through to `c`, so the queue setting
wins for anything printed through CUPS.

### A mislabelling in the upstream PPD

Toshiba's specification defines parameter `c` as:

```
0: No sensor          1: Reflective         2: Transmissive
3: Transmissive       4: Reflective
```

— i.e. `3` is a second *transmissive* code and `4` a second *reflective* one.
The upstream `tectpcl2.drv` labelled them the other way round, as "Reflective
Pre-Print" and "Transmissive Pre-Print", so picking either would have engaged
the **opposite** sensor. The choices are relabelled here to match the spec.

## Changing settings when the printer is on USB

The parameter page lives on the printer's **web server**, which only exists on
the LAN interface. On USB there is no web UI, and TPCL offers no command to
*read* parameters back — only `[ESC]Z2;1`, which rewrites all of them
positionally in one shot. Writing that blind, without knowing the current
values, risks changing the destination or control-code mode and losing
communication with the printer.

So `bev4ctl params` requires `--host`. Over USB (`--queue`) only the commands
that write are available: `feed`, `reset`, `print`.

Three ways to configure a USB-attached printer:

### 1. Read the settings from a self-test print

The printer prints its own parameters. Power it on **holding FEED**, and
release at the right point in the LED sequence — each step lasts 1.5 s:

| Step | LED | Release here for |
| --- | --- | --- |
| 1 | flashing red | — |
| 2 | flashing red | firmware download |
| 3 | flashing orange | cancel auto-call |
| 4 | solid orange | **parameter clearance** (factory reset) |
| 5 | solid red | **sensor calibration** (also measures label length) |
| 6 | solid green | **self-test print, then dump mode** |

Step 6 prints the program version, checksum and every parameter with its
current value. Step 5 is the manual sensor calibration to run after turning
`AUTO CALIB.` off.

Note step 6 leaves the printer in **dump mode**, where it prints received data
instead of interpreting it. That is genuinely useful for debugging a job, but
power-cycle to get out of it.

### 2. Put it on the LAN temporarily

Even a direct cable to a laptop works. Configure it with `tools/netconfig.py`
over USB, use the web UI, then move it back. See the LAN section of the README.

### 3. Write the whole parameter block deliberately

If you know every current value — from a self-test print — you can send
`[ESC]Z2;1` followed by `[ESC]Z0` to re-initialise. This project does not wrap
that command, on purpose: a partially-correct parameter block is worse than no
change at all, and the two safe routes above already exist.

## Calibration

The printer measures the gap between labels with its media sensor. If it
mis-positions, feeds continuously, or reports a paper jam on media that is
loaded correctly, the sensor needs calibrating for that stock.

### Automatic calibration — the normal route

Do this once whenever you change to different label stock.

**On the printer**, with the media loaded: power on **holding FEED**, release at
the **fifth** LED step (solid red). The printer feeds a few labels, sets the
sensor threshold for that media, and measures the label pitch. The result is
stored and survives power cycles — which is the point: you calibrate once
deliberately, rather than leaving `AUTO CALIB.` on and paying for it with wasted
labels at every power-on.

**Over the network**, the web UI has the same function at
`/cgi-bin/calibrate.cgi`.

Calibration works with media up to 254 mm pitch.

### Reading the current sensor setting

The self-test print (power on holding FEED, release at the **sixth** step,
solid green) lists it as, for example:

```
SENSOR TRANSMISSIVE [17]
```

— transmissive sensor, sensitivity level 17.

### Manual sensitivity, when automatic calibration fails

On difficult media — very thin liner, heavily pre-printed labels — automatic
calibration may fail to find the gap. Sensitivity can then be set by hand
through the Fine Adjustment Value Set Command `[ESC]Z2;2`, which carries a
sensitivity value for each sensor, `00` (lowest) to `63` (highest), followed by
`[ESC]Z0` to re-initialise.

This project does **not** wrap that command, for the same reason it does not
wrap `[ESC]Z2;1`: it rewrites every fine-adjustment value positionally, there is
no command to read the current ones back, and a partially-correct block is worse
than no change. Read the current values from a self-test print first, and send
the command deliberately if you need it.

Note these are *system* settings, stored in the printer. They are not per-job,
so they do not belong in the print dialog and are not in the PPD. The per-job
adjustments — feed, cut and back-feed position, in 0.5 mm steps — are in the
queue's **Options**, and those map to `[ESC]AX`.
