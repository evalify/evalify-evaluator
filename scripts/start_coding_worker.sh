#!/bin/bash
#
# Start Coding Worker
#
# This script starts a Celery worker dedicated to processing CODING question
# evaluations. Coding questions involve running code and tests, which are
# CPU-intensive, so we use the prefork pool.
#
# Queue: coding-queue
# Pool: prefork
# Concurrency: 2 (adjust based on available CPU cores, coding tasks are heavy)
#

set -e

# Navigate to project root
cd "$(dirname "$0")/.." && source .venv/bin/activate

echo "🚀 Starting Coding Worker..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Queue:       coding-queue"
echo "Pool:        prefork"
echo "Concurrency: 2"
echo "Log Level:   info"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start the Celery worker
celery -A evaluator.celery_app worker \
    --loglevel=info \
    --pool=prefork \
    --concurrency=2 \
    --heartbeat-interval=2 \
    -E \
    -Q coding-queue \
    -n coding-worker@%h
