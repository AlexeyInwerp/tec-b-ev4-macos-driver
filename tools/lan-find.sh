#!/bin/bash
# Find a Toshiba TEC printer on the local segment when it has no usable IP.
#
#   sudo ./lan-find.sh [seconds]
#
# Purely passive: listens for ARP/DHCP/broadcast traffic and reports any host
# that is not already a known neighbour on our own subnet. A printer sitting on
# a foreign subnet (the B-EV4 ships on 192.168.10.20) is invisible to a ping
# sweep but still chatters on the wire, so this catches it.
set -uo pipefail

SECS="${1:-25}"
IFACE="${IFACE:-$(route -n get default 2>/dev/null | awk '/interface:/{print $2}')}"
MYNET="$(ipconfig getifaddr "$IFACE" 2>/dev/null | cut -d. -f1-3)"

[ "$(id -u)" = "0" ] || { echo "!! Must run as root:  sudo $0 $*" >&2; exit 1; }
[ -n "$IFACE" ] || { echo "!! Could not determine the default interface" >&2; exit 1; }

echo "==> Listening on $IFACE for ${SECS}s (our subnet is ${MYNET}.0/24)"
echo "    Power-cycle the printer now to catch its DHCP/ARP burst."

CAP="$(mktemp -t lanfind).pcap"
tcpdump -i "$IFACE" -w "$CAP" -s 256 \
        'arp or (udp and (port 67 or port 68)) or icmp' >/dev/null 2>&1 &
TPID=$!
sleep "$SECS"
kill "$TPID" 2>/dev/null; wait "$TPID" 2>/dev/null

echo "==> Analysing ..."
tcpdump -nre "$CAP" 2>/dev/null | python3 -c '
import sys, re, collections
mynet = sys.argv[1]
# OUIs historically used by Toshiba TEC / Tokyo Electric
TEC = ("00:80:91", "08:00:1f", "00:00:39", "8c:dc:d4")
seen = collections.defaultdict(set)
for line in sys.stdin:
    macs = re.findall(r"\b([0-9a-f]{2}(?::[0-9a-f]{2}){5})\b", line, re.I)
    ips  = re.findall(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", line)
    for m in macs:
        for ip in ips:
            seen[m.lower()].add(ip)
        seen[m.lower()]  # ensure present
if not seen:
    print("   no traffic captured at all - is the cable in the right port?")
for mac, ips in sorted(seen.items()):
    if mac.startswith(("01:00:5e", "33:33", "ff:ff")):
        continue
    foreign = [i for i in ips if not i.startswith(mynet + ".") and i != "0.0.0.0"]
    tag = ""
    if mac.startswith(TEC):
        tag = "  <== TOSHIBA TEC OUI"
    elif foreign:
        tag = "  <== off-subnet address"
    print(f"   {mac}  {sorted(ips) if ips else \"(no IP seen)\"}{tag}")
' "$MYNET"
rm -f "$CAP"
echo "==> Done."
