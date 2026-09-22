#!/usr/bin/env python3
"""
tpcl.py - TPCL (TEC Printer Command Language) generator for Toshiba TEC B-EV4.

Command syntax per "B-EV4 Series External Equipment Interface Specification".
Control codes: [ESC] (0x1B) ... [LF] (0x0A) [NUL] (0x00)
All coordinates are in 0.1 mm units.
"""

ESC = b'\x1b'
TERM = b'\x0a\x00'


class Label:
    def __init__(self, width_mm=100.0, length_mm=150.0, gap_mm=2.0):
        self.width = int(round(width_mm * 10))    # effective print width, 0.1mm
        self.length = int(round(length_mm * 10))  # effective print length, 0.1mm
        self.pitch = self.length + int(round(gap_mm * 10))
        self.buf = bytearray()

    def cmd(self, body: bytes):
        self.buf += ESC + body + TERM
        return self

    # --- setup -----------------------------------------------------------
    def size(self):
        """[ESC] D aaaa,bbbb,cccc  -> pitch, effective width, effective length"""
        return self.cmd(b'D%04d,%04d,%04d' % (self.pitch, self.width, self.length))

    def clear(self):
        """[ESC] C - clear image buffer"""
        return self.cmd(b'C')

    # --- drawing ---------------------------------------------------------
    def line(self, x0, y0, x1, y1, width_dots=2, rect=False, radius=None):
        """[ESC] LC; aaaa,bbbb,cccc,dddd,e,f(,ggg)"""
        body = b'LC;%04d,%04d,%04d,%04d,%d,%d' % (
            x0, y0, x1, y1, 1 if rect else 0, width_dots)
        if radius is not None:
            body += b',%03d' % radius
        return self.cmd(body)

    def rect(self, x0, y0, x1, y1, width_dots=2, radius=None):
        return self.line(x0, y0, x1, y1, width_dots, rect=True, radius=radius)

    def text(self, n, x, y, data, font=b'H', hmag=1, vmag=1, rot='00', attr=b'B'):
        """[ESC] PCaaa; bbbb,cccc,d,e,ff,ii,j   then  [ESC] RCaaa; data

        Text is encoded cp850, matching the printer's default FONT CODE
        parameter. Change both together if you set a different code page.
        """
        self.cmd(b'PC%03d;%04d,%04d,%d,%d,%s,%s,%s' % (
            n, x, y, hmag, vmag, font, rot.encode(), attr))
        if isinstance(data, str):
            data = data.encode('cp850', 'replace')
        self.cmd(b'RC%03d;' % n + data)
        return self

    def barcode(self, n, x, y, data, btype=b'9', checkdigit=b'1',
                module=3, rot='0', height_mm=15.0):
        """[ESC] XBaa; bbbb,cccc,d,e,ff,k,llll = data

        Layout for WPC/CODE93/CODE128/UCC-EAN128/postal symbologies.
        btype 9 = CODE128 with automatic code-set selection.
        """
        if isinstance(data, str):
            data = data.encode('ascii', 'replace')
        body = b'XB%02d;%04d,%04d,%s,%s,%02d,%s,%04d=' % (
            n, x, y, btype, checkdigit, module, rot.encode(),
            int(round(height_mm * 10)))
        return self.cmd(body + data)

    # --- issue -----------------------------------------------------------
    def issue(self, copies=1, cut_interval=0, sensor='2', mode='C', speed='3',
              ribbon='0', rotation='0', status='0'):
        """[ESC] XS; I, aaaa, bbb c d e f g h"""
        return self.cmd(b'XS;I,%04d,%03d%s%s%s%s%s%s' % (
            copies, cut_interval, sensor.encode(), mode.encode(),
            speed.encode(), ribbon.encode(), rotation.encode(), status.encode()))

    def bytes(self):
        return bytes(self.buf)
