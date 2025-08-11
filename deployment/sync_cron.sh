#!/bin/bash
"""
Cron Job Script for Google Sheets to MongoDB Sync
Runs the sync service and logs output
"""

# Set environment variables
export PYTHONPATH="/home/ec2-user/GuestListScripts:$PYTHONPATH"
export PATH="/home/ec2-user/.local/bin:$PATH"

# Configuration
SCRIPT_DIR="/home/ec2-user/GuestListScripts"
LOG_DIR="$SCRIPT_DIR/logs"
SYNC_SCRIPT="$SCRIPT_DIR/sheets_to_mongo_sync.py"
LOG_FILE="$LOG_DIR/sync_cron.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Run the sync with logging
echo "$(date): Starting Google Sheets to MongoDB sync" >> "$LOG_FILE"

cd "$SCRIPT_DIR"
python3 "$SYNC_SCRIPT" >> "$LOG_FILE" 2>&1

SYNC_STATUS=$?

if [ $SYNC_STATUS -eq 0 ]; then
    echo "$(date): Sync completed successfully" >> "$LOG_FILE"
else
    echo "$(date): Sync failed with exit code $SYNC_STATUS" >> "$LOG_FILE"
fi

# Keep only last 100 lines of log file to prevent it from growing too large
tail -n 100 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"

exit $SYNC_STATUS
