#!/bin/bash
#
# Stop All Workers
#
# This script stops all running Celery workers by sending TERM signals to their PIDs.
#

set -e

# Navigate to project root
SCRIPT_DIR="$(dirname "$0")"
cd "$SCRIPT_DIR/.."

echo "🛑 Stopping All Celery Workers..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Function to stop a worker
stop_worker() {
    local name=$1
    local pidfile=$2
    
    if [ -f "$pidfile" ]; then
        local pid=$(cat "$pidfile")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "▶ Stopping $name (PID: $pid)..."
            kill -TERM "$pid" 2>/dev/null || true
            sleep 2
            
            # Force kill if still running
            if ps -p "$pid" > /dev/null 2>&1; then
                echo "  ⚠ Worker still running, forcing shutdown..."
                kill -KILL "$pid" 2>/dev/null || true
            fi
            echo "  ✓ $name stopped"
        else
            echo "▶ $name (PID: $pid) not running"
        fi
        rm -f "$pidfile"
    else
        echo "▶ $name PID file not found"
    fi
}

# Stop all workers
stop_worker "MCQ Worker" ".celery/mcq-worker.pid"
stop_worker "Descriptive Worker" ".celery/desc-worker.pid"
stop_worker "Coding Worker" ".celery/coding-worker.pid"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All workers stopped"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
