# Installing

Two routes. **Building from source is the recommended one** — it is simpler
than it sounds, and it sidesteps Gatekeeper completely.

## Why this driver is not signed

Signing and notarizing a macOS installer requires membership of the Apple
Developer Program, which costs money annually. This is a free GPLv3 driver for
a printer the manufacturer never supported on the Mac, so that cost is not
being paid.

The consequence is that macOS will refuse to open the `.pkg` normally:

```
$ spctl -a -vv -t install TEC-B-EV4-0.1.0.pkg
TEC-B-EV4-0.1.0.pkg: rejected
source=no usable signature
```

That is a statement about the absence of a certificate, not about the contents.
Since you cannot check a signature, **check the SHA-256 instead** — it is
published next to each release asset:

```sh
shasum -a 256 -c TEC-B-EV4-0.1.0.pkg.sha256
```

## Route 1: build from source (recommended)

Needs the Xcode Command Line Tools (`xcode-select --install`).

```sh
git clone https://github.com/AlexeyInwerp/tec-b-ev4-macos-driver.git
cd tec-b-ev4-macos-driver
sudo driver/install.sh
```

**Gatekeeper never enters into it.** The quarantine attribute is applied by the
*browser* to downloaded files; a binary you compiled locally never has one, so
there is nothing to block. Verifiable:

```sh
$ xattr -l driver/rastertotpcl
$                       # no output - no quarantine attribute
```

You also get the exact source you are running, which for something that
executes as part of the print pipeline is a reasonable thing to want.

## Route 2: install the package

### From the Terminal — the path of least resistance

```sh
sudo installer -pkg TEC-B-EV4-0.1.0.pkg -target /
```

`installer(8)` does not consult Gatekeeper, so an unsigned package installs
without argument. You are already typing `sudo`, so you are already making the
trust decision explicitly.

### From the Finder

Double-clicking will be refused. Then either:

**Allow it once, in System Settings**
1. Double-click the `.pkg`, and let it be blocked.
2. **System Settings → Privacy & Security**, scroll to Security.
3. A line naming the package appears — click **Open Anyway**.
4. Double-click the `.pkg` again and authenticate.

This is the supported route on Ventura and later. On older versions,
Control-click the `.pkg` and choose **Open**, which offers an override dialog
that plain double-clicking does not.

**Or remove the quarantine flag first**

```sh
xattr -dr com.apple.quarantine TEC-B-EV4-0.1.0.pkg
```

Then open it normally. Only do this once you have checked the SHA-256 — you are
removing the one marker that tells macOS the file came from the internet.

## What gets installed

| Path | Contents |
| --- | --- |
| `/Library/Printers/TEC/filter/` | `rastertotpcl`, `rastertotpcl-debug` |
| `/Library/Printers/PPDs/Contents/Resources/` | the PPDs |
| `/Library/Printers/TEC/tools/` | the Python toolkit |

The filter is installed **root-owned and 0755** — CUPS refuses to execute a
filter that is group- or world-writable, so this is not optional.

Nothing is placed in `/usr/libexec/cups/filter`: the macOS system volume is a
sealed read-only snapshot, so that directory cannot be written to at all. The
PPDs carry an absolute `*cupsFilter` path instead, which is the same approach
vendor drivers under `/Library/Printers` use.

## Adding the printer

System Settings → Printers & Scanners → **Add Printer**, then choose
**Toshiba Tec B-EV4D-GS14** as the driver (or `…B-EV4T-GS14` for a 300 dpi
thermal-transfer model).

For a network printer use **LPD**, not the raw socket port:

```sh
lpadmin -p TEC_B_EV4 -E -v lpd://<printer-ip>/lp \
        -P /Library/Printers/PPDs/Contents/Resources/tecbev4d.ppd \
        -o PageSize=w283h425 -o teMediaTracking=2 -o MediaType=Direct \
        -o Resolution=203dpi -o Gap=2
```

`socket://<ip>:8000` looks like it works and then silently discards anything
over a few kilobytes. See the README.

## Requirements

* macOS 10.15 Catalina or later — the package is universal, `x86_64` from
  10.15 and `arm64` from 11.0
* No Xcode needed for the package; needed only to build from source

## Uninstalling

```sh
sudo /Library/Printers/TEC/uninstall.sh   # if installed from source
```

or by hand:

```sh
sudo lpadmin -x TEC_B_EV4
sudo rm -rf /Library/Printers/TEC
sudo rm -f /Library/Printers/PPDs/Contents/Resources/tec*.ppd
```
