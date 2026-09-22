#!/bin/bash
# Build the rastertotpcl CUPS filter and the Toshiba TEC PPDs for macOS.
set -euo pipefail
cd "$(dirname "$0")"

FILTER_DIR="${FILTER_DIR:-/Library/Printers/TEC/filter}"

echo "==> Compiling rastertotpcl ..."
clang -Os -Wall -Wno-deprecated-declarations -Wno-format-extra-args \
      -Wno-unused-but-set-variable \
      -o rastertotpcl rastertotpcl.c -lcups -lcupsimage

echo "==> Generating PPDs ..."
rm -rf ppd ppd-debug
ppdc tectpcl2.drv 2>&1 | grep -v "Unable to find #po file" || true

# The macOS system volume is sealed read-only, so the filter cannot be placed
# in /usr/libexec/cups/filter. CUPS accepts an absolute path in *cupsFilter,
# which is how vendor drivers under /Library/Printers work.
echo "==> Pointing cupsFilter at $FILTER_DIR ..."
for p in ppd/*.ppd; do
  /usr/bin/sed -i '' \
    "s|^\*cupsFilter: \"application/vnd.cups-raster 50 rastertotpcl\"|*cupsFilter: \"application/vnd.cups-raster 50 ${FILTER_DIR}/rastertotpcl\"|" "$p"
done

# Parallel set of PPDs wired to the verbose wrapper, for a debug queue.
echo "==> Generating debug PPDs ..."
cp -r ppd ppd-debug
for p in ppd-debug/*.ppd; do
  /usr/bin/sed -i '' \
    -e "s|${FILTER_DIR}/rastertotpcl|${FILTER_DIR}/rastertotpcl-debug|" \
    -e "s|^\*NickName: \"\(.*\)\"|*NickName: \"\1 (debug)\"|" "$p"
done

echo "==> Built:"
ls -l rastertotpcl rastertotpcl-debug
grep -h '^\*cupsFilter' ppd/tecbev4d.ppd ppd-debug/tecbev4d.ppd
echo "    $(ls ppd/*.ppd | wc -l | tr -d ' ') PPDs + $(ls ppd-debug/*.ppd | wc -l | tr -d ' ') debug PPDs"
