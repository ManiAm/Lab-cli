#!/bin/bash
# enable_secret.sh — Set or change the enable password.
#
# Usage:
#   enable_secret.sh set           Prompt for a new password interactively
#   enable_secret.sh remove        Remove the enable password (lab mode)
#   enable_secret.sh status        Show whether a password is configured
#
# The hash is stored in /etc/netlab/enable.secret (SHA-512, same
# format as /etc/shadow).

HASH_FILE="/etc/netlab/enable.secret"

case "${1:-status}" in

    set)
        read -s -p "New enable password: " pass1
        echo ""
        read -s -p "Confirm password: " pass2
        echo ""

        if [ -z "$pass1" ]; then
            echo "% Password cannot be empty"
            exit 1
        fi

        if [ "$pass1" != "$pass2" ]; then
            echo "% Passwords do not match"
            exit 1
        fi

        mkdir -p "$(dirname "$HASH_FILE")"
        salt=$(openssl rand -hex 8)
        openssl passwd -6 -salt "$salt" "$pass1" > "$HASH_FILE"
        chmod 600 "$HASH_FILE"
        echo "% Enable password has been set"
        ;;

    remove)
        rm -f "$HASH_FILE"
        echo "% Enable password removed (lab mode — no password required)"
        ;;

    status)
        if [ -s "$HASH_FILE" ]; then
            echo "Enable password: configured"
        else
            echo "Enable password: not configured (lab mode — no password required)"
        fi
        ;;

    *)
        echo "Usage: enable_secret.sh {set|remove|status}"
        exit 1
        ;;
esac
