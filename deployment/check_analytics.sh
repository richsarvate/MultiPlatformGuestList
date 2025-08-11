#!/bin/bash
# Auto-restart script for Setup Comedy Analytics Dashboard
# Add this to crontab to run every 5 minutes: */5 * * * * /home/ec2-user/GuestListScripts/check_analytics.sh

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Check if the process is running on port 8080
PID=$(netstat -tlnp 2>/dev/null | grep :8080 | awk '{print $7}' | cut -d'/' -f1)

if [ -z "$PID" ]; then
    echo "$(date): Analytics Dashboard not running, starting it..." >> logs/auto_restart.log
    ./start_analytics.sh >> logs/auto_restart.log 2>&1
else
    # Optional: Check if the service is actually responding
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ || echo "000")
    if [ "$HTTP_STATUS" != "200" ]; then
        echo "$(date): Analytics Dashboard not responding (HTTP $HTTP_STATUS), restarting..." >> logs/auto_restart.log
        ./stop_analytics.sh >> logs/auto_restart.log 2>&1
        sleep 5
        ./start_analytics.sh >> logs/auto_restart.log 2>&1
    fi
fi
