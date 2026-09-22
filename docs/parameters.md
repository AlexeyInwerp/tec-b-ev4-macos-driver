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
