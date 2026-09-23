#!/bin/bash
# Build a distributable macOS installer package.
#
#   packaging/build-pkg.sh [version]
#
# Produces packaging/dist/TEC-B-EV4-<version>.pkg containing a prebuilt
# universal filter and the PPDs, so installing needs no Xcode toolchain.
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${1:-$(cat VERSION)}"
ID="com.github.alexeyinwerp.tec-b-ev4"
STAGE="packaging/stage"
DIST="packaging/dist"
PKG="$DIST/TEC-B-EV4-$VERSION.pkg"

echo "==> Building driver artefacts"
FILTER_DIR=/Library/Printers/TEC/filter driver/build.sh >/dev/null

if ! lipo -archs driver/rastertotpcl | grep -q "x86_64.*arm64\|arm64.*x86_64"; then
  echo "!! filter is not universal - refusing to package a single-arch build" >&2
  exit 1
fi

echo "==> Staging payload"
rm -rf "$STAGE" "$DIST"
mkdir -p "$STAGE/Library/Printers/TEC/filter" \
         "$STAGE/Library/Printers/TEC/tools" \
         "$STAGE/Library/Printers/PPDs/Contents/Resources" \
         "$DIST"

install -m 0755 driver/rastertotpcl       "$STAGE/Library/Printers/TEC/filter/"
install -m 0755 driver/rastertotpcl-debug "$STAGE/Library/Printers/TEC/filter/"
install -m 0644 driver/ppd/*.ppd          "$STAGE/Library/Printers/PPDs/Contents/Resources/"
install -m 0755 tools/*.py tools/*.sh     "$STAGE/Library/Printers/TEC/tools/"
install -m 0644 LICENSE README.md         "$STAGE/Library/Printers/TEC/"
install -m 0755 driver/uninstall.sh       "$STAGE/Library/Printers/TEC/"
install -m 0644 packaging/icon/TECBEV4.icns "$STAGE/Library/Printers/TEC/"

echo "==> Writing postinstall"
mkdir -p packaging/scripts
cat > packaging/scripts/postinstall <<'POST'
#!/bin/bash
# CUPS refuses to run a filter that is not owned by root or that is
# group/world writable, so enforce it regardless of how the payload arrived.
set -e
chown -R root:wheel /Library/Printers/TEC
chmod 0755 /Library/Printers/TEC/filter/rastertotpcl \
           /Library/Printers/TEC/filter/rastertotpcl-debug
chown root:wheel /Library/Printers/PPDs/Contents/Resources/tec*.ppd 2>/dev/null || true
chmod 0644 /Library/Printers/PPDs/Contents/Resources/tec*.ppd 2>/dev/null || true
exit 0
POST
chmod +x packaging/scripts/postinstall

echo "==> pkgbuild"
pkgbuild --root "$STAGE" \
         --scripts packaging/scripts \
         --identifier "$ID" \
         --version "$VERSION" \
         --ownership recommended \
         --install-location / \
         "$DIST/component.pkg" >/dev/null

echo "==> productbuild"
cat > packaging/distribution.xml <<XML
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="2">
    <title>Toshiba TEC B-EV4 driver</title>
    <organization>$ID</organization>
    <options customize="never" require-scripts="false" hostArchitectures="arm64,x86_64"/>
    <volume-check>
        <allowed-os-versions><os-version min="10.15"/></allowed-os-versions>
    </volume-check>
    <license file="LICENSE"/>
    <readme file="welcome.txt"/>
    <choices-outline><line choice="default"/></choices-outline>
    <choice id="default"><pkg-ref id="$ID"/></choice>
    <pkg-ref id="$ID" version="$VERSION" onConclusion="none">component.pkg</pkg-ref>
</installer-gui-script>
XML
cp LICENSE packaging/LICENSE
cat > packaging/welcome.txt <<'TXT'
Toshiba TEC B-EV4 - macOS CUPS driver

Installs the rastertotpcl filter and PPDs. Afterwards add the printer in
System Settings > Printers & Scanners and pick "Toshiba Tec B-EV4D-GS14".

IMPORTANT for network printers: use LPD, not the raw socket port.

    lpd://<printer-ip>/lp        correct
    socket://<printer-ip>:8000   silently discards jobs over ~8 KB

Default media is 100 x 150 mm direct thermal.

This package is not signed or notarized. macOS will warn about an
unidentified developer; right-click the .pkg and choose Open to proceed.

GPLv3. See README.md in /Library/Printers/TEC/.
TXT

productbuild --distribution packaging/distribution.xml \
             --package-path "$DIST" \
             --resources packaging \
             "$PKG" >/dev/null

rm -f "$DIST/component.pkg"
# Without a signature, a published checksum is how people verify the download.
shasum -a 256 "$PKG" | sed "s|$DIST/||" > "$PKG.sha256"

echo
echo "==> Built $PKG"
echo "    sha256: $(cut -d' ' -f1 < "$PKG.sha256")"
ls -lh "$PKG" | awk '{print "    size: "$5}'
pkgutil --check-signature "$PKG" 2>&1 | head -2 | sed 's/^/    /'
