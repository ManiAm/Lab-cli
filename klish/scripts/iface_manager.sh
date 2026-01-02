#!/bin/bash

# Usage: ./iface_manager.sh <ACTION> [ARGUMENTS]
# Example: ./iface_manager.sh set_ip 192.168.1.1/24
# Example: ./iface_manager.sh shutdown

ACTION=$1
ARG_VALUE=$2

# 1. Read State (Interface, Mode, Session Name)
# We use the KLISH_PID environment variable provided automatically by Klish
IFACE=$(cat "/tmp/klish_sess_${KLISH_PID}_iface" 2>/dev/null)
MODE=$(cat "/tmp/klish_sess_${KLISH_PID}_mode" 2>/dev/null)
SESS_NAME=$(cat "/tmp/klish_sess_${KLISH_PID}_sess_name" 2>/dev/null)

if [ -z "$IFACE" ]; then
    echo "Error: No interface selected."
    exit 1
fi

# 2. Construct the Command based on the Action
CMD=""

case "$ACTION" in
    "set_ip")
        # ARG_VALUE is the IP address
        CMD="ip addr add $ARG_VALUE dev $IFACE"
        ;;
    "shutdown")
        CMD="ip link set dev $IFACE down"
        ;;
    *)
        echo "Unknown action: $ACTION"
        exit 1
        ;;
esac

# 3. Execute or Buffer
if [ "$MODE" = "session" ]; then
    # -- SESSION MODE: Append to file --
    CANDIDATE_FILE="/tmp/candidates/${SESS_NAME}.conf"
    echo "$CMD" >> "$CANDIDATE_FILE"
else
    # -- LIVE MODE: Execute immediately --
    # We print the command being run for user feedback (optional)
    # echo "Applying: $CMD"
    $CMD
fi
