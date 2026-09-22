#!/usr/bin/env python3
"""
bev4ctl - administration tool for the Toshiba TEC B-EV4.

The printer exposes two independent management surfaces:

  * TPCL over the raw socket port (default 8000) - live status, model,
    serial, and any print/feed command.
  * An embedded 'Ethernut' web server on port 80 - the stored configuration
    (parameters, calibration, network), which TPCL offers no way to read back.

This tool talks to both.

  bev4ctl.py --host 192.168.1.50 status
  bev4ctl.py --host 192.168.1.50 info
  bev4ctl.py --host 192.168.1.50 params
  bev4ctl.py --host 192.168.1.50 feed
  bev4ctl.py --host 192.168.1.50 print label.tpcl
"""
import argparse, re, socket, sys, urllib.parse

ESC, TERM = b'\x1b', b'\x0a\x00'

# Detail status codes, B-EV4 interface specification section 9.1.3.
STATUS = {
    "00": "Online, top cover closed (normal)",
    "01": "Top cover open",
    "02": "Operating (analysing / drawing / printing / feeding)",
    "04": "Paused",
    "05": "Waiting for stripping",
    "06": "Command error",
    "07": "RS-232C communication error (parity / overrun / framing)",
    "11": "Paper jam",
    "12": "Cutter error",
    "13": "Label ran out",
    "15": "Feed or issue attempted with the top cover open",
    "16": "Stepping motor overheated",
    "18": "Thermal head overheated",
    "21": "Ribbon ran out / encoder error",
    "23": "Last label issued, label has now run out",
    "40": "Label issue completed normally",
    "41": "Feed terminated normally",
    "50": "SD card write error",
    "51": "SD card format erase error",
    "54": "SD card capacity insufficient",
    "55": "Save mode / SD initialising / EEPROM error",
}

def sock_cmd(host, port, payload, want_reply=True, timeout=8):
    s = socket.create_connection((host, port), timeout=timeout)
    s.settimeout(timeout)
    s.sendall(payload)
    data = b''
    if want_reply:
        try:
            data = s.recv(512)
        except socket.timeout:
            pass
    s.close()
    return data


def http_get(host, path, timeout=20):
    """The embedded server answers some paths in bare HTTP/0.9, so parse loosely."""
    s = socket.create_connection((host, 80), timeout=timeout)
    s.settimeout(timeout)
    s.sendall(f"GET {path} HTTP/1.0\r\nHost: {host}\r\n\r\n".encode())
    buf = b''
    while True:
        try:
            b = s.recv(4096)
        except socket.timeout:
            break
        if not b:
            break
        buf += b
    s.close()
    head, sep, body = buf.partition(b'\r\n\r\n')
    return (body if sep and head.startswith(b'HTTP/1') else buf).decode('windows-1252', 'replace')


def cmd_status(a):
    d = sock_cmd(a.host, a.port, ESC + b'WS' + TERM)
    if not d:
        sys.exit("no reply - is the printer online?")
    # SOH STX <detail:2><type:1><remaining:4> ETX EOT CR LF
    m = re.search(rb'\x01\x02(\d{2})(\d)(\d{4})\x03', d)
    if not m:
        print("raw:", d.hex(' '))
        return
    detail, kind, remain = m.group(1).decode(), m.group(2).decode(), int(m.group(3))
    print(f"status    : {detail}  {STATUS.get(detail, 'unknown code')}")
    print(f"reply type: {kind}  ({'status request' if kind == '1' else 'auto transmission'})")
    print(f"remaining : {remain} label(s) left in the current batch")


def cmd_info(a):
    d = sock_cmd(a.host, a.port, ESC + b'IR' + TERM)
    if len(d) >= 31:
        print(f"model  : {d[:20].decode('ascii','replace').strip()}")
        print(f"serial : {d[20:31].decode('ascii','replace').strip()}")
    else:
        print("raw:", d)
    page = http_get(a.host, '/title.asp')
    for label in ("Version", "Print Milage", "Cut Milage"):
        m = re.search(rf'{label}\s*:</TD><TD>(.*?)</TD>', page, re.S | re.I)
        if m:
            val = re.sub(r'&nbsp;?', ' ', m.group(1))
            print(f"{label.lower():14}: {' '.join(val.split())}")


def cmd_params(a):
    """Read stored configuration out of the web UI - TPCL cannot report it."""
    page = http_get(a.host, '/admin/cgi-bin/parameter.cgi')
    rows = re.findall(r'<TD>([^<]{0,40}?)\s*:\s*</TD><TD>(.*?)</TD>', page, re.S | re.I)
    if not rows:
        sys.exit("could not read the parameter page")
    for label, ctl in rows:
        sel = re.search(r'<SELECT name=(\w+)>(.*?)</SELECT>', ctl, re.S | re.I)
        if sel:
            cur = re.findall(r'<OPTION SELECTED>([^<]*)</OPTION>', sel.group(2), re.I)
            print(f"  {label.strip():16} [{sel.group(1):13}] = {cur[0] if cur else '?'}")
        else:
            inp = re.search(r"name=(\w+)", ctl, re.I)
            val = re.search(r"value='?([^'\s>]*)'?", ctl, re.I)
            if inp:
                print(f"  {label.strip():16} [{inp.group(1):13}] = {val.group(1) if val else ''}")
    print("\nAUTO CALIB. = ON makes the printer feed labels to calibrate the gap\n"
          "sensor at every power-on. Set it to OFF to stop that.")


def cmd_feed(a):
    sock_cmd(a.host, a.port, ESC + b'T' + TERM, want_reply=False)
    print("feed command sent")


def cmd_print(a):
    data = open(a.file, 'rb').read()
    sock_cmd(a.host, a.port, data, want_reply=False)
    print(f"sent {len(data)} bytes to {a.host}:{a.port}")


def main():
    p = argparse.ArgumentParser(description="Toshiba TEC B-EV4 administration")
    p.add_argument('--host', required=True)
    p.add_argument('--port', type=int, default=8000)
    sub = p.add_subparsers(dest='cmd', required=True)
    for name, fn in (("status", cmd_status), ("info", cmd_info),
                     ("params", cmd_params), ("feed", cmd_feed)):
        sub.add_parser(name).set_defaults(fn=fn)
    sp = sub.add_parser("print"); sp.add_argument("file"); sp.set_defaults(fn=cmd_print)
    a = p.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
