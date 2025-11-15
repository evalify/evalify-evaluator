#!/bin/bash
#
# Start Descriptive Worker
#
# This script starts a Celery worker dedicated to processing DESCRIPTIVE question
# evaluations. Descriptive questions typically require LLM/AI evaluation and are
# I/O-bound, so we use the gevent pool for efficient async processing.
#
# Queue: desc-queue
# Pool: gevent
# Concurrency: 100 (gevent can handle many concurrent I/O operations)
#

set -e

# Navigate to project root
cd "$(dirname "$0")/.." && source .venv/bin/activate

echo "🚀 Starting Descriptive Worker..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Queue:       desc-queue"
echo "Pool:        gevent"
echo "Concurrency: 100"
echo "Log Level:   info"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start the Celery worker
celery -A evaluator.celery_app worker \
    --loglevel=info \
    --pool=gevent \
    --concurrency=100 \
    --heartbeat-interval=2 \
    -E \
    -Q desc-queue \
    -n desc-worker@%h
