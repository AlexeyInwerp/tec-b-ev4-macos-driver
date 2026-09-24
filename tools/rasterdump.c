/* Decode a CUPS raster stream to a raw 1-bit dump: "W H\n" then packed rows. */
#include <cups/raster.h>
#include <stdio.h>
#include <stdlib.h>
int main(void) {
  cups_raster_t *r = cupsRasterOpen(0, CUPS_RASTER_READ);
  cups_page_header2_t h;
  if (!r || !cupsRasterReadHeader2(r, &h)) { fprintf(stderr, "no header\n"); return 1; }
  fprintf(stderr, "%ux%u bpc=%u bpp=%u cs=%u bpl=%u\n", h.cupsWidth, h.cupsHeight,
          h.cupsBitsPerColor, h.cupsBitsPerPixel, h.cupsColorSpace, h.cupsBytesPerLine);
  printf("%u %u\n", h.cupsWidth, h.cupsHeight);
  unsigned char *buf = malloc(h.cupsBytesPerLine);
  for (unsigned y = 0; y < h.cupsHeight; y++) {
    if (cupsRasterReadPixels(r, buf, h.cupsBytesPerLine) < 1) break;
    fwrite(buf, 1, h.cupsBytesPerLine, stdout);
  }
  cupsRasterClose(r);
  return 0;
}
