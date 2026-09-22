#!/bin/bash
# Move a factory-default Toshiba TEC B-EV4 onto your real LAN, over the network.
#
#   sudo ./lan-setup.sh [--dhcp | --ip 192.168.178.60]
#
# The printer ships on a static 192.168.10.20, so it is invisible from any
# other subnet even though it is physically on the wire. This adds a temporary
# second IP to your interface inside 192.168.10.0/24, talks to the printer
# there, reconfigures it, and removes the alias again.
set -euo pipefail
cd "$(dirname "$0")"

PRINTER_IP="${PRINTER_IP:-192.168.10.20}"
PORT="${PORT:-8000}"
ALIAS_IP="${ALIAS_IP:-192.168.10.99}"
IFACE="${IFACE:-$(route -n get default 2>/dev/null | awk '/interface:/{print $2}')}"

MODE="--dhcp"; STATIC=""
case "${1:-}" in
  --dhcp) MODE="--dhcp" ;;
  --ip)   MODE="--ip"; STATIC="${2:?--ip needs an address}" ;;
  "")     ;;
  *)      echo "usage: $0 [--dhcp | --ip <address>]" >&2; exit 2 ;;
esac

[ "$(id -u)" = "0" ] || { echo "!! Must run as root:  sudo $0 $*" >&2; exit 1; }
[ -n "$IFACE" ] || { echo "!! Could not determine the default interface" >&2; exit 1; }

cleanup() {
  echo "==> Removing temporary alias $ALIAS_IP from $IFACE"
  ifconfig "$IFACE" -alias "$ALIAS_IP" 2>/dev/null || true
}
trap cleanup EXIT

echo "==> Adding temporary alias $ALIAS_IP/24 to $IFACE"
ifconfig "$IFACE" alias "$ALIAS_IP" 255.255.255.0

echo "==> Probing $PRINTER_IP:$PORT for a TPCL printer ..."
if ! python3 - "$PRINTER_IP" "$PORT" <<'PY'
import socket, sys
ip, port = sys.argv[1], int(sys.argv[2])
try:
    s = socket.create_connection((ip, port), timeout=4)
except Exception as e:
    sys.exit(f"   no TCP connection: {e}")
s.settimeout(4)
s.sendall(b'\x1bWS\x0a\x00')          # status request
try:
    d = s.recv(256)
except Exception:
    d = b''
s.close()
if d.startswith(b'HTTP/'):
    sys.exit("   that is an HTTP server, not the printer")
print(f"   reply: {d.hex(' ') if d else '<none>'}")
PY
then
  echo "!! Could not reach a printer at $PRINTER_IP:$PORT."
  echo "   Check the LAN cable/link LED, or configure it over USB instead:"
  echo "     ./netconfig.py --dhcp > net.tpcl && lp -d <usb-queue> -o raw net.tpcl"
  exit 1
fi

if [ "$MODE" = "--dhcp" ]; then
  echo "==> Switching the printer to DHCP"
  ./netconfig.py --dhcp > /tmp/bev4-net.tpcl
else
  echo "==> Setting static address $STATIC"
  ./netconfig.py --ip "$STATIC" --mask 255.255.255.0 \
                 --gw "$(route -n get default | awk '/gateway:/{print $2}')" \
                 > /tmp/bev4-net.tpcl
fi

python3 - "$PRINTER_IP" "$PORT" /tmp/bev4-net.tpcl <<'PY'
import socket, sys
ip, port, f = sys.argv[1], int(sys.argv[2]), sys.argv[3]
data = open(f, 'rb').read()
s = socket.create_connection((ip, port), timeout=6)
s.sendall(data); s.close()
print(f"   sent {len(data)} bytes of configuration")
PY

echo
echo "==> Done. Now POWER-CYCLE the printer."
echo "   Then find it again with:"
echo "     arp -a | grep -i '0:11:32\|toshiba'   # or re-scan the subnet"
