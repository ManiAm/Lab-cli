#!/bin/bash

# 1. Capture the parameter passed from Klish
TARGET=$1

echo "--------------------------------"
echo " Checking System: $TARGET"
echo "--------------------------------"

# 2. Logic based on the parameter
if [ "$TARGET" == "cpu" ]; then
    # Show load average and processor count
    uptime
    echo "Processors: $(nproc)"

elif [ "$TARGET" == "memory" ]; then
    # Show memory in human readable format
    free -h

elif [ "$TARGET" == "disk" ]; then
    # Show usage of the root partition
    df -h /

else
    echo "Error: Unknown target '$TARGET'. Please use cpu, memory, or disk."
fi

echo "--------------------------------"
