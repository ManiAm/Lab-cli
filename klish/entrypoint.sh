#!/bin/sh
set -e

echo "Starting NetLab-CLI (Klish sandbox)..."

# Start daemon in foreground mode (-d) but backgrounded by this script
klishd -f /etc/klish/klishd.conf -d -v &
KLISTHD_PID=$!

# Wait for the UNIX socket to appear
SOCKET=/tmp/klish-unix-socket

for i in $(seq 1 50); do
    if [ -S "$SOCKET" ]; then
        break
    fi

    # If daemon died, stop early and show logs
    if ! kill -0 "$KLISTHD_PID" 2>/dev/null; then
        echo "ERROR: klishd exited early; check XML/config" >&2
        wait "$KLISTHD_PID" || true
        exit 1
    fi

    sleep 0.1
done

if [ ! -S "$SOCKET" ]; then
    echo "ERROR: klishd did not create socket $SOCKET" >&2
    wait "$KLISTHD_PID" || true
    exit 1
fi

# Wait for the daemon process so the container doesn't exit
wait "$KLISTHD_PID"
