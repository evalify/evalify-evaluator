#!/bin/bash
#
# Start All Workers in tmux
#
# This script starts three Celery workers in a tmux session with the following layout:
#
#     ┌─────────────────┬─────────────────┐
#     │                 │                 │
#     │   MCQ Worker    │  Desc Worker    │
#     │                 │                 │
#     │                 ├─────────────────┤
#     │                 │                 │
#     │                 │  Coding Worker  │
#     │                 │                 │
#     └─────────────────┴─────────────────┘
#
# The pane configuration is: MCQ | (Descriptive / Coding)
# This allows monitoring all three workers simultaneously.
#

set -e

SESSION_NAME="evaluator-workers"
PROJECT_ROOT="$(dirname "$0")/.."
ATTACH=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--attach)
            ATTACH=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [-a|--attach]"
            echo ""
            echo "Options:"
            echo "  -a, --attach    Attach to tmux session after starting workers"
            exit 1
            ;;
    esac
done

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "❌ tmux is not installed. Please install tmux first."
    exit 1
fi

# Kill existing session if it exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "🗑️  Killing existing '$SESSION_NAME' session..."
    tmux kill-session -t "$SESSION_NAME"
fi

echo "🚀 Starting all workers in tmux session: $SESSION_NAME"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create new tmux session with the first window
tmux new-session -d -s "$SESSION_NAME" -x 200 -y 50

# Create the pane layout: split vertically first (MCQ | Right side)
# Then split the right side horizontally (Descriptive / Coding)
tmux split-window -h
tmux split-window -v -t "$SESSION_NAME:0.1"

# Pane 0: MCQ Worker (left)
echo "📍 Pane 0: Starting MCQ Worker..."
tmux send-keys -t "$SESSION_NAME:0.0" "cd '$PROJECT_ROOT' && source .venv/bin/activate && bash scripts/start_mcq_worker.sh" Enter

# Pane 1: Descriptive Worker (top right)
echo "📍 Pane 1: Starting Descriptive Worker..."
tmux send-keys -t "$SESSION_NAME:0.1" "cd '$PROJECT_ROOT' && source .venv/bin/activate && bash scripts/start_desc_worker.sh" Enter

# Pane 2: Coding Worker (bottom right)
echo "📍 Pane 2: Starting Coding Worker..."
tmux send-keys -t "$SESSION_NAME:0.2" "cd '$PROJECT_ROOT' && source .venv/bin/activate && bash scripts/start_coding_worker.sh" Enter

# Set the pane sizes to the desired ratio
tmux resize-pane -t "$SESSION_NAME:0.0" -x 100
tmux resize-pane -t "$SESSION_NAME:0.1" -y 25

echo ""
echo "✅ All workers started in tmux!"
echo ""
echo "Attach to the session with:"
echo "  tmux attach-session -t $SESSION_NAME"
echo ""
echo "Or use shortcuts:"
echo "  tmux send-keys -t $SESSION_NAME:0.0 C-c  # Stop MCQ worker"
echo "  tmux send-keys -t $SESSION_NAME:0.1 C-c  # Stop Descriptive worker"
echo "  tmux send-keys -t $SESSION_NAME:0.2 C-c  # Stop Coding worker"
echo ""
echo "To kill the entire session:"
echo "  tmux kill-session -t $SESSION_NAME"
echo ""

# Attach to session if --attach flag was provided
if [ "$ATTACH" = true ]; then
    echo "Attaching to $SESSION_NAME..."
    tmux attach-session -t "$SESSION_NAME"
fi
