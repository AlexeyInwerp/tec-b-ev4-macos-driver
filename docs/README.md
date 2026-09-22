# Reference documentation

The command syntax used by this driver comes from Toshiba TEC's

> **B-EV4 Series — External Equipment Interface Specification**

That document is Toshiba TEC's copyright and is **not redistributed in this
repository**. Fetch your own copy, for example:

* <http://www.printmark.de/downloads/prog_manuals/Prog_handb_B-EV4.pdf>
* <https://www.toshiba-tec.com.cn/Product/extranet/uploads/B-EV4_Ifm_6th.pdf>

Drop it in this directory as `B-EV4_External_Equipment_Interface_Spec.pdf` if
you want it alongside the code; `.gitignore` keeps it out of version control.

## Commands this driver relies on

| Command | Purpose |
| --- | --- |
| `[ESC] D aaaa,bbbb,cccc` | Label size: pitch, effective width, effective length (0.1 mm) |
| `[ESC] AX` / `[ESC] AY` | Position / print-density fine adjust |
| `[ESC] C` | Clear image buffer |
| `[ESC] LC` | Line and rectangle |
| `[ESC] PC` + `[ESC] RC` | Bitmap font format + data |
| `[ESC] XB` + `= data` | Barcode format and inline data |
| `[ESC] SG` | Graphic (nibble / hex / BMP / **TOPIX** / PCX) |
| `[ESC] XS; I,aaaa,bbbcdefgh` | Issue (print) |

### Control codes

The printer auto-selects its control-code family **per command**: a command may
start with `[ESC]` and end `[LF][NUL]`, or start with `{` and end `|}`. In `{…|}`
mode bytes `00H`–`1FH` are discarded *except* while a Graphic Command payload is
being consumed — which is what lets TOPIX-compressed binary graphics travel
inside `{SG;…|}`.
