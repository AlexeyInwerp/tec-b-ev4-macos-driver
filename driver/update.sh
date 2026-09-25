#!/bin/bash
# Update an existing Toshiba TEC B-EV4 driver install.
#
#   git pull && sudo driver/update.sh
#
# Replaces the filter binaries and the shipped PPDs, but leaves your queues
# and their settings (darkness, speed, media size) alone.
#
# If the PPD itself changed, the queue keeps using its existing copy until you
# re-apply it -- that step resets queue options to defaults, so it is opt-in:
#
#   sudo APPLY_PPD=1 driver/update.sh
set -euo pipefail
cd "$(dirname "$0")"

FILTER_DIR="${FILTER_DIR:-/Library/Printers/TEC/filter}"
PPD_DIR="${PPD_DIR:-/Library/Printers/PPDs/Contents/Resources}"
QUEUE="${QUEUE:-TEC_B_EV4}"
PPD="${PPD:-tecbev4d.ppd}"
STAMP="$FILTER_DIR/.version"

if [ "$(id -u)" != "0" ]; then
  echo "!! Must run as root:  sudo $0" >&2
  exit 1
fi
if [ ! -x "$FILTER_DIR/rastertotpcl" ]; then
  echo "!! Not installed yet - run:  sudo ./install.sh" >&2
  exit 1
fi

BUILD_USER="${SUDO_USER:-root}"
echo "==> Building (as $BUILD_USER) ..."
sudo -u "$BUILD_USER" FILTER_DIR="$FILTER_DIR" ./build.sh >/dev/null

NEW_SUM="$(cat rastertotpcl.c tectpcl2.drv labelmedia.h | shasum -a 256 | cut -d' ' -f1)"
OLD_SUM="$(cat "$STAMP" 2>/dev/null || echo none)"
NEW_PPD_SUM="$(shasum -a 256 <"ppd/$PPD" | cut -d' ' -f1)"
OLD_PPD_SUM="$(shasum -a 256 <"$PPD_DIR/$PPD" 2>/dev/null | cut -d' ' -f1 || echo none)"

# Swapping the filter binary is always safe: CUPS exec's it per job.
echo "==> Refreshing filter in $FILTER_DIR"
install -o root -g wheel -m 0755 rastertotpcl "$FILTER_DIR/rastertotpcl"
install -o root -g wheel -m 0755 rastertotpcl-debug "$FILTER_DIR/rastertotpcl-debug"
if [ -f ../packaging/icon/TECBEV4.icns ]; then
  install -o root -g wheel -m 0644 ../packaging/icon/TECBEV4.icns \
          "$(dirname "$FILTER_DIR")/TECBEV4.icns"
fi

echo "==> Refreshing PPDs in $PPD_DIR"
install -o root -g wheel -m 0644 ppd/*.ppd "$PPD_DIR/"
echo "$NEW_SUM" >"$STAMP"

if [ "$NEW_PPD_SUM" != "$OLD_PPD_SUM" ]; then
  if [ "${APPLY_PPD:-0}" = "1" ]; then
    if lpstat -p "$QUEUE" >/dev/null 2>&1; then
      # Applying a PPD resets every option on the queue. Per-queue settings
      # are not visible to `lpoptions` - that only reports IPP attributes and
      # explicit overrides - they live as *Default<Option> lines inside the
      # queue's own copy of the PPD. So diff those against the new PPD and
      # replay only what the user actually changed.
      QPPD="/etc/cups/ppd/$QUEUE.ppd"
      URI="$(lpstat -v "$QUEUE" 2>/dev/null | sed 's/.*: //')"
      echo "==> Re-applying PPD to '$QUEUE'"

      RESTORE=""
      if [ -r "$QPPD" ]; then
        while IFS= read -r line; do
          opt="${line%%:*}"; opt="${opt#\*Default}"
          val="${line#*: }"; val="${val%\"}"; val="${val#\"}"
          case "$opt" in
            PageRegion|ImageableArea|PaperDimension|Font|ColorSpace|Resolution) continue ;;
          esac
          # Only replay it if the new PPD would default to something else.
          newdef="$(grep -m1 "^\*Default$opt:" "ppd/$PPD" 2>/dev/null | sed 's/.*: *//; s/"//g')"
          [ -z "$newdef" ] && continue
          [ "$val" = "$newdef" ] && continue
          # ...and only if the new PPD still offers that choice.
          grep -q "^\*$opt $val[/:]" "ppd/$PPD" 2>/dev/null || continue
          RESTORE="$RESTORE -o $opt=$val"
        done <<EOF
$(grep '^\*Default' "$QPPD" 2>/dev/null)
EOF
      fi

      # shellcheck disable=SC2086
      lpadmin -p "$QUEUE" -P "ppd/$PPD" $RESTORE
      [ -n "$URI" ] && lpadmin -p "$QUEUE" -v "$URI"
      cupsenable "$QUEUE"; cupsaccept "$QUEUE"
      if [ -n "$RESTORE" ]; then
        echo "    carried over:$(echo "$RESTORE" | sed 's/ -o / /g')"
      else
        echo "    no customised options to carry over"
      fi
    else
      echo "!! Queue '$QUEUE' does not exist - nothing to re-apply the PPD to."
    fi
  else
    echo
    echo "!! The PPD changed, but '$QUEUE' still uses its existing copy."
    echo "   New media sizes, the icon and new options will not appear until"
    echo "   it is re-applied. This now preserves your settings:"
    echo "     sudo APPLY_PPD=1 $0"
  fi
fi

[ "$NEW_SUM" = "$OLD_SUM" ] && echo "==> Driver source unchanged (filter still refreshed)."
echo "==> Update complete."
