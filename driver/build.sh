#!/bin/bash
# Build the rastertotpcl CUPS filter and the Toshiba TEC PPDs for macOS.
set -euo pipefail
cd "$(dirname "$0")"

FILTER_DIR="${FILTER_DIR:-/Library/Printers/TEC/filter}"

# Build a universal binary by default so one install works on both Apple
# Silicon and Intel. arm64 cannot target below 11.0 (Apple Silicon did not
# exist earlier), so each slice gets its own floor.
UNIVERSAL="${UNIVERSAL:-1}"
MACOS_MIN_X86="${MACOS_MIN_X86:-10.15}"   # Catalina
MACOS_MIN_ARM="${MACOS_MIN_ARM:-11.0}"    # Big Sur

WARN="-Wall -Wno-deprecated-declarations -Wno-format-extra-args -Wno-unused-but-set-variable"

echo "==> Compiling rastertotpcl ..."
if [ "$UNIVERSAL" = "1" ] && clang -target "x86_64-apple-macos$MACOS_MIN_X86" \
        -Os $WARN -c rastertotpcl.c -o /dev/null 2>/dev/null; then
  clang -arch x86_64 -mmacosx-version-min="$MACOS_MIN_X86" -Os $WARN \
        -o rastertotpcl.x86_64 rastertotpcl.c -lcups -lcupsimage
  clang -arch arm64  -mmacosx-version-min="$MACOS_MIN_ARM" -Os $WARN \
        -o rastertotpcl.arm64  rastertotpcl.c -lcups -lcupsimage
  lipo -create -output rastertotpcl rastertotpcl.x86_64 rastertotpcl.arm64
  rm -f rastertotpcl.x86_64 rastertotpcl.arm64
  echo "    universal: $(lipo -archs rastertotpcl) (x86_64 >= $MACOS_MIN_X86, arm64 >= $MACOS_MIN_ARM)"
else
  clang -Os $WARN -o rastertotpcl rastertotpcl.c -lcups -lcupsimage
  echo "    native only: $(lipo -archs rastertotpcl 2>/dev/null || uname -m)"
fi

echo "==> Generating PPDs ..."
rm -rf ppd ppd-debug

# The upstream .drv hardcodes Version "1.4", which ppdc puts in *FileVersion and
# on the end of *NickName - and *NickName is what macOS shows in Printers &
# Scanners. Left alone it reports 1.4 whatever we ship, so "which version am I
# running?" is unanswerable from the UI. Build against a copy carrying the
# project version instead. It must sit beside labelmedia.h for the #include.
PROJECT_VERSION="$(cat ../VERSION 2>/dev/null || echo 0.0.0)"
BUILD_DRV="tectpcl2.build.drv"
trap 'rm -f "$BUILD_DRV"' EXIT
/usr/bin/sed "s/^Version \"[^\"]*\"/Version \"$PROJECT_VERSION\"/" \
    tectpcl2.drv > "$BUILD_DRV"

if command -v ppdc >/dev/null 2>&1; then
  ppdc "$BUILD_DRV" 2>&1 | grep -v "Unable to find #po file" || true
elif [ -d ppd-prebuilt ]; then
  # ppdc was removed from some systems; fall back to the checked-in PPDs.
  echo "    ppdc not found - using prebuilt PPDs"
  cp -r ppd-prebuilt ppd
else
  echo "!! ppdc not found and no ppd-prebuilt/ directory" >&2
  exit 1
fi

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
