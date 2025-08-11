#!/bin/bash
# Dashboard Service Restart Script

echo "🔄 Restarting dashboard service..."

# Stop existing processes
echo "Stopping gunicorn processes..."
pkill -f "gunicorn.*wsgi:app"
sleep 2

# Start new process
echo "Starting dashboard..."
cd /home/ec2-user/GuestListScripts
python3 -m gunicorn --config config/gunicorn.conf.py wsgi:app --daemon

# Verify it's running
sleep 2
if pgrep -f "gunicorn.*wsgi:app" > /dev/null; then
    echo "✅ Dashboard service started successfully"
    echo "Running processes:"
    ps aux | grep gunicorn | grep -v grep | wc -l
    echo "Service available at: http://localhost:8080"
else
    echo "❌ Failed to start dashboard service"
    exit 1
fi
