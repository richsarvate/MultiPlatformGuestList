#!/bin/bash
# Stop Setup Comedy Analytics Dashboard

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Check if PID file exists
if [ -f "logs/analytics.pid" ]; then
    PID=$(cat logs/analytics.pid)
    echo "Stopping Analytics Dashboard (PID: $PID)..."
    kill $PID 2>/dev/null
    
    # Wait a moment and check if it's really stopped
    sleep 2
    if kill -0 $PID 2>/dev/null; then
        echo "Process still running, force killing..."
        kill -9 $PID 2>/dev/null
    fi
    
    rm -f logs/analytics.pid
    echo "✅ Analytics Dashboard stopped"
else
    # Try to find and kill by port
    PID=$(netstat -tlnp 2>/dev/null | grep :8080 | awk '{print $7}' | cut -d'/' -f1)
    if [ ! -z "$PID" ]; then
        echo "Found process $PID on port 8080, stopping..."
        kill $PID 2>/dev/null
        sleep 2
        echo "✅ Analytics Dashboard stopped"
    else
        echo "No Analytics Dashboard process found on port 8080"
    fi
fi
