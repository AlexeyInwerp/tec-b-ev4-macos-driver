#!/bin/bash
# Remove the Toshiba TEC B-EV4 driver.
#
#   sudo ./uninstall.sh              # remove filter, PPDs and queues
#   KEEP_QUEUES=1 sudo -E ./uninstall.sh   # leave the queues in place
set -euo pipefail

FILTER_DIR="${FILTER_DIR:-/Library/Printers/TEC/filter}"
PPD_DIR="${PPD_DIR:-/Library/Printers/PPDs/Contents/Resources}"
QUEUE="${QUEUE:-TEC_B_EV4}"

if [ "$(id -u)" != "0" ]; then
  echo "!! Must run as root:  sudo $0" >&2
  exit 1
fi

if [ "${KEEP_QUEUES:-0}" != "1" ]; then
  for q in "$QUEUE" "${QUEUE}_DEBUG"; do
    if lpstat -p "$q" >/dev/null 2>&1; then
      echo "==> Removing queue $q"
      lpadmin -x "$q"
    fi
  done
fi

echo "==> Removing $FILTER_DIR"
rm -rf "$FILTER_DIR"
rmdir /Library/Printers/TEC 2>/dev/null || true

echo "==> Removing installed PPDs"
for p in "$PPD_DIR"/tecb*.ppd; do
  [ -e "$p" ] && rm -f "$p" && echo "    $p"
done

echo "==> Uninstalled."
