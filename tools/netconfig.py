#!/usr/bin/env python3
"""
netconfig.py - generate TPCL to put a Toshiba TEC B-EV4 onto the LAN.

Send the generated file to the printer over USB, power-cycle it, then point
CUPS at socket://<ip>:<port>.

Factory defaults:  IP 192.168.10.20 | mask 255.255.255.0 | gw 0.0.0.0
                   socket enabled, port 8000   <- NOT the usual 9100

  # static address
  ./netconfig.py --ip 192.168.1.50 --mask 255.255.255.0 --gw 192.168.1.1 > net.tpcl
  # or DHCP
  ./netconfig.py --dhcp > net.tpcl

  lp -d TEC_B_EV4_G -o raw net.tpcl     # then power-cycle the printer

These commands change the printer's stored configuration, so nothing is sent
unless you pipe the output to the printer yourself.
"""
import argparse, sys

ESC, TERM = b'\x1b', b'\x0a\x00'


def cmd(body: bytes) -> bytes:
    return ESC + body + TERM


def octets(kind: int, addr: str) -> bytes:
    """[ESC] IP; a,bbb,ccc,ddd,eee   a: 2=printer 3=gateway 4=subnet mask"""
    p = addr.split('.')
    if len(p) != 4 or not all(o.isdigit() and 0 <= int(o) <= 255 for o in p):
        sys.exit(f"bad IPv4 address: {addr}")
    return cmd(b'IP;%d,%03d,%03d,%03d,%03d' % (kind, *(int(o) for o in p)))


def main():
    ap = argparse.ArgumentParser(description="Configure B-EV4 network settings via TPCL")
    ap.add_argument('--ip', help="static printer IP address")
    ap.add_argument('--mask', help="subnet mask")
    ap.add_argument('--gw', help="default gateway")
    ap.add_argument('--dhcp', action='store_true', help="enable DHCP instead of a static address")
    ap.add_argument('--port', type=int, default=8000, help="socket port (default 8000)")
    ap.add_argument('--no-socket', action='store_true', help="disable socket communication")
    a = ap.parse_args()

    if not (a.ip or a.dhcp or a.no_socket or a.port != 8000):
        ap.error("nothing to do - give --ip/--mask/--gw, --dhcp, or --port")
    if not 0 <= a.port <= 65535:
        sys.exit("port must be 0..65535")

    out = b''
    if a.dhcp:
        # 'FF' as the first client-ID byte makes the printer use its MAC.
        out += cmd(b'IH;1,' + b'FF' * 16)
    else:
        if a.ip:
            out += cmd(b'IH;0,' + b'FF' * 16)   # static -> DHCP off
            out += octets(2, a.ip)
        if a.gw:
            out += octets(3, a.gw)
        if a.mask:
            out += octets(4, a.mask)

    # [ESC] IS; a,bbbbb  - port number must be exactly 5 digits
    out += cmd(b'IS;%d,%05d' % (0 if a.no_socket else 1, a.port))

    sys.stdout.buffer.write(out)
    sys.stderr.write(
        f"{len(out)} bytes. Send with:  lp -d <queue> -o raw <file>\n"
        f"Then POWER-CYCLE the printer and use socket://<ip>:{a.port}\n")


if __name__ == '__main__':
    main()
