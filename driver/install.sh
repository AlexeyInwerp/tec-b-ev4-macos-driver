#!/bin/bash
# Install the Toshiba TEC B-EV4 CUPS driver on macOS.
#
#   sudo ./install.sh
#
# CUPS refuses to run a filter unless it is owned by root and not
# group/world writable, so this must run with sudo.
set -euo pipefail
cd "$(dirname "$0")"

FILTER_DIR="${FILTER_DIR:-/Library/Printers/TEC/filter}"
PPD_DIR="${PPD_DIR:-/Library/Printers/PPDs/Contents/Resources}"
QUEUE="${QUEUE:-TEC_B_EV4}"
PPD="${PPD:-tecbev4d.ppd}"

if [ "$(id -u)" != "0" ]; then
  echo "!! Must run as root:  sudo $0" >&2
  exit 1
fi

# Build as the invoking user so the artefacts are not root-owned in the tree.
BUILD_USER="${SUDO_USER:-root}"
echo "==> Building (as $BUILD_USER) ..."
sudo -u "$BUILD_USER" FILTER_DIR="$FILTER_DIR" ./build.sh

echo "==> Installing filter into $FILTER_DIR"
mkdir -p "$FILTER_DIR"
install -o root -g wheel -m 0755 rastertotpcl "$FILTER_DIR/rastertotpcl"
install -o root -g wheel -m 0755 rastertotpcl-debug "$FILTER_DIR/rastertotpcl-debug"

echo "==> Installing PPDs into $PPD_DIR"
mkdir -p "$PPD_DIR"
install -o root -g wheel -m 0644 ppd/*.ppd "$PPD_DIR/"

# Record what was built, so update.sh can tell whether anything changed.
cat rastertotpcl.c tectpcl2.drv labelmedia.h | shasum -a 256 | cut -d' ' -f1 \
    > "$FILTER_DIR/.version"

# A URI without ?location= survives replugging into a different port/hub.
URI="$(lpinfo -v 2>/dev/null | awk '/usb:\/\/TEC/{print $2; exit}')"
URI="${URI%%\?*}"
URI="${URI:-usb://TEC/B-EV4-G}"

echo "==> Creating queue '$QUEUE' on $URI"
lpadmin -p "$QUEUE" -E -v "$URI" -P "ppd/$PPD" \
        -o PageSize=w283h425 \
        -o teMediaTracking=2 \
        -o MediaType=Direct \
        -o Resolution=203dpi \
        -o Gap=2 \
        -o printer-is-shared=false
cupsenable "$QUEUE"
cupsaccept "$QUEUE"

# Optional verbose queue: every job is dumped to /tmp/tpcl-debug for replay.
if [ "${DEBUG_QUEUE:-0}" = "1" ]; then
  echo "==> Creating debug queue '${QUEUE}_DEBUG'"
  lpadmin -p "${QUEUE}_DEBUG" -E -v "$URI" -P "ppd-debug/$PPD" \
          -o PageSize=w283h425 -o teMediaTracking=2 -o MediaType=Direct \
          -o Resolution=203dpi -o Gap=2 -o printer-is-shared=false
  cupsenable "${QUEUE}_DEBUG"; cupsaccept "${QUEUE}_DEBUG"
  echo "    cupsctl LogLevel=debug   # then watch /var/log/cups/error_log"
fi

echo
echo "==> Installed. Test with:"
echo "     lp -d $QUEUE some-100x150-label.pdf"
lpstat -v "$QUEUE"
