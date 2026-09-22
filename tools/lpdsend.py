#!/usr/bin/env python3
"""
Minimal RFC 1179 LPD client for the Toshiba TEC B-EV4.

Use this rather than the raw socket on port 8000: that port silently discards
jobs larger than a few kilobytes, reporting no error while printing nothing.
LPD acknowledges every stage and handles full-size jobs correctly.

    lpdsend.py <host> <file.tpcl> [queue]
"""
import socket, sys, time

if len(sys.argv) < 3:
    sys.exit("usage: lpdsend.py <host> <file.tpcl> [queue]")
IP    = sys.argv[1]
path  = sys.argv[2]
QUEUE = sys.argv[3] if len(sys.argv) > 3 else "lp"
data = open(path,'rb').read()
host = "mac"; user = "cups"; jid = 1

def ack(s, what):
    r = s.recv(1)
    ok = (r == b'\x00')
    print(f"    {what:28} ack={r!r} {'OK' if ok else 'FAIL'}")
    return ok

ctrl = (f"H{host}\n" f"P{user}\n" f"J{path}\n" f"ldfA{jid:03d}{host}\n"
        f"UdfA{jid:03d}{host}\n" f"N{path}\n").encode()

print(f"LPD -> {IP}:515 queue={QUEUE}  ({len(data)} bytes)")
s = socket.create_connection((IP,515), timeout=60); s.settimeout(60)

s.sendall(b'\x02' + QUEUE.encode() + b'\n')
if not ack(s, "receive job"): sys.exit(1)

s.sendall(f"\x02{len(ctrl)} cfA{jid:03d}{host}\n".encode())
if not ack(s, "control file header"): sys.exit(1)
s.sendall(ctrl + b'\x00')
if not ack(s, "control file body"): sys.exit(1)

s.sendall(f"\x03{len(data)} dfA{jid:03d}{host}\n".encode())
if not ack(s, "data file header"): sys.exit(1)
t0=time.time()
s.sendall(data + b'\x00')
print(f"    data sent in {time.time()-t0:.1f}s")
ack(s, "data file body")
s.close()
