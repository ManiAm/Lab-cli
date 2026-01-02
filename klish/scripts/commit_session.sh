#!/bin/bash

# 1. Gather Session Context
# We rely on KLISH_PID to find the correct state files for this user.
MODE=$(cat "/tmp/klish_sess_${KLISH_PID}_mode" 2>/dev/null)
SESS_NAME=$(cat "/tmp/klish_sess_${KLISH_PID}_sess_name" 2>/dev/null)
CANDIDATE_FILE="/tmp/candidates/${SESS_NAME}.conf"

# 2. Validation Checks
if [ "$MODE" != "session" ]; then
    echo "Error: 'commit' is only valid in Session Mode."
    echo "       In Live Mode, commands are applied immediately."
    exit 1
fi

if [ ! -s "$CANDIDATE_FILE" ]; then
    echo "Buffer is empty. Nothing to commit."
    exit 0
fi

# 3. Execution Transaction
echo "Committing transaction '${SESS_NAME}'..."

# We execute the candidate file as a shell script.
# The flag '-e' ensures we stop immediately if one command fails.
/bin/bash -e "$CANDIDATE_FILE"

STATUS=$?

# 4. Cleanup & Feedback
if [ $STATUS -eq 0 ]; then
    echo "Commit successful."
    # Clear the buffer so the user doesn't commit the same thing twice
    > "$CANDIDATE_FILE"
else
    echo "Commit FAILED. Check system logs for errors."
    # In a real production system, you would trigger a rollback here.
    exit 1
fi
