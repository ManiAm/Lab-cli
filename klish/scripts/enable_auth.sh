#!/bin/bash
# enable_auth.sh — Verify the enable password before granting Privileged EXEC.
#
# The password hash is stored in /etc/netlab/enable.secret (SHA-512 format).
# If the file is missing or empty, access is granted without a password
# (lab/development mode).
#
# Usage: called by Klish <ACTION sym="script" in="tty" out="tty">
#        exit 0 = password correct (Klish proceeds to nav push)
#        exit 1 = password wrong   (Klish stops, stays in User EXEC)

HASH_FILE="/etc/netlab/enable.secret"

# If no password file exists, allow access without prompting (lab mode)
if [ ! -s "$HASH_FILE" ]; then
    exit 0
fi

stored=$(cat "$HASH_FILE" 2>/dev/null)

# Extract the salt from the stored hash: $6$<salt>$<hash>
salt=$(echo "$stored" | cut -d'$' -f3)

if [ -z "$salt" ]; then
    echo "% Error: malformed password hash in $HASH_FILE"
    exit 1
fi

# Prompt for password (hidden input)
read -s -p "Password: " password
echo ""

if [ -z "$password" ]; then
    echo "% Access denied"
    exit 1
fi

# Hash the input with the same salt and compare
computed=$(openssl passwd -6 -salt "$salt" "$password")

if [ "$computed" = "$stored" ]; then
    exit 0
else
    echo "% Access denied"
    exit 1
fi
