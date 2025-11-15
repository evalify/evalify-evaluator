#!/bin/bash
#
# Start MCQ Worker
#
# This script starts a Celery worker dedicated to processing MCQ (Multiple Choice Question)
# evaluations. MCQ questions are lightweight and can be processed quickly, so we use
# the prefork pool for efficient parallel processing.
#
# Queue: mcq-queue
# Pool: prefork (default)
# Concurrency: 4 workers (adjust based on your CPU cores)
#

set -e

# Navigate to project root
cd "$(dirname "$0")/.." && source .venv/bin/activate

echo "🚀 Starting MCQ Worker..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Queue:       mcq-queue"
echo "Pool:        prefork"
echo "Concurrency: 4"
echo "Log Level:   info"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start the Celery worker
celery -A evaluator.celery_app worker \
    --loglevel=info \
    --pool=prefork \
    --concurrency=4 \
    -Q mcq-queue \
    -n mcq-worker@%h
