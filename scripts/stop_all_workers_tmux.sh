#!/bin/bash
#
# Stop All Workers in tmux
#
# This script kills the tmux session running all three Celery workers.
# It gracefully terminates the evaluator-workers session if it's running.
#

set -e

SESSION_NAME="evaluator-workers"

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "❌ tmux is not installed."
    exit 1
fi

# Check if session exists
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "ℹ️  Session '$SESSION_NAME' is not running."
    exit 0
fi

echo "🛑 Stopping all workers in tmux session: $SESSION_NAME"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Kill the session
tmux kill-session -t "$SESSION_NAME"

echo "✅ Session '$SESSION_NAME' has been terminated."
echo ""
