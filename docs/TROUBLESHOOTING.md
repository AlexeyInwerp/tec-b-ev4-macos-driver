# Troubleshooting

## A label prints cropped, or scaling seems to do nothing

Almost always this is the **paper size**, not scaling.

Shipping labels are not all the same size. A DHL label may be 100 × 150 mm or
100 × 200 mm, and macOS will happily offer to print at the *document's* size —
this PPD allows custom sizes up to 609 mm, because some people really do run
long labels. Pick that and the driver faithfully tells the printer the label is
200 mm long:

```
Paper Size 100 x 150 mm  ->  {D1519,0998,1499|}   150 mm   correct
Paper Size 99 x 200 mm   ->  {D2020,0998,2000|}   200 mm   wrong media
```

With 150 mm stock loaded, the printer prints the first 150 mm of a 200 mm
layout and the rest is lost. The gap sensor then finds the next label where the
printer was not expecting one, so registration drifts too — which is why it can
look like far more than a third went missing.

**Scale-to-fit cannot rescue this**, because it scales the document onto the
selected paper — and the selected paper is already wrong.

### Fix

In the Print dialog set **both**:

1. **Paper Size → 100 x 150 mm** — the media actually loaded, never the
   document's size
2. **Scale to Fit → Print Entire Image**

A 200 mm label then scales down and prints complete on 150 mm stock.

If your app has no paper-size control, set it in **File → Page Setup** first.

### Checking rather than guessing

You can see exactly what the driver was handed. Capture a job with the debug
queue (README, "Debugging"), then:

```sh
clang -Os -w -o rasterdump tools/rasterdump.c -lcups -lcupsimage
./rasterdump < /tmp/tpcl-debug/<stamp>.raster | tools/rasterpreview.py - out.png
open out.png
```

If `out.png` shows the whole label, rasterization was fine and the problem is
downstream. If it is already cropped, the paper size was wrong before the
driver ever saw it.

The dimensions are the quick tell — at 203 dpi, 100 × 150 mm is **798 × 1198**
dots. A much taller raster means a too-large paper size was selected.

## Nothing prints, and CUPS says the job completed

If the queue is on `socket://…:8000`, that is the cause — switch to
`lpd://<ip>/lp`. The raw socket accepts a job, reports success and discards
anything over a few kilobytes. See the README.

If it is already on LPD, check whether the printer is in an error state:

```sh
tools/bev4ctl.py --host <ip> status
```

Once the printer reports an error it processes **only** status and reset
commands and silently drops everything else, so one bad job makes every job
after it appear to vanish. Clear it:

```sh
tools/bev4ctl.py --host <ip> reset
```

## The printer prints garbage, or feeds without printing

The queue is probably using the wrong driver. macOS cannot identify this
printer over the network — it has neither Bonjour nor SNMP — so adding it by IP
leaves the driver on *Generic PostScript Printer*, which produces a queue that
accepts jobs and prints nothing useful. Set **Use → Select Software…** and pick
**Toshiba Tec B-EV4D-GS14**.

## The printer feeds several blank labels at power-on

`AUTO CALIB.` is on. See [parameters.md](parameters.md).

## The queue worked yesterday and now every job fails

The printer's DHCP lease moved. It has no mDNS, so nothing rediscovers it:

```sh
nmap -p 80,515,8000 192.168.1.0/24 --open
sudo lpadmin -p TEC_B_EV4 -v lpd://<new-ip>/lp
```

Give it a DHCP reservation to stop it recurring.

## The printer icon is the generic one

The icon ships with the driver but a queue keeps its own copy of the PPD, so an
existing queue keeps the old one. After installing or updating:

```sh
sudo lpadmin -p TEC_B_EV4 -P /Library/Printers/PPDs/Contents/Resources/tecbev4d.ppd
```

Note this resets that queue's options to defaults — check `lpoptions -p TEC_B_EV4`
first. A newly added printer picks up the icon without this.
