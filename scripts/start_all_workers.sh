#!/bin/bash
#
# Start All Workers
#
# This script starts all Celery workers for all queue types:
# - MCQ Worker (mcq-queue, prefork pool)
# - Descriptive Worker (desc-queue, gevent pool)
# - Coding Worker (coding-queue, prefork pool)
#
# Each worker runs in the background. Use stop_all_workers.sh to stop them.
#

set -e

# Navigate to project root
SCRIPT_DIR="$(dirname "$0")"
cd "$SCRIPT_DIR/.."

echo "🚀 Starting All Celery Workers..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start MCQ worker in background
echo "▶ Starting MCQ Worker (mcq-queue, prefork)..."
celery -A evaluator.celery_app worker \
    --loglevel=info \
    --pool=prefork \
    --concurrency=4 \
    -Q mcq-queue \
    -n mcq-worker@%h \
    --detach \
    --pidfile=.celery/mcq-worker.pid \
    --logfile=.celery/mcq-worker.log

echo "  ✓ MCQ Worker started (PID: $(cat .celery/mcq-worker.pid))"
echo ""

# Start Descriptive worker in background
echo "▶ Starting Descriptive Worker (desc-queue, gevent)..."
celery -A evaluator.celery_app worker \
    --loglevel=info \
    --pool=gevent \
    --concurrency=100 \
    -Q desc-queue \
    -n desc-worker@%h \
    --detach \
    --pidfile=.celery/desc-worker.pid \
    --logfile=.celery/desc-worker.log

echo "  ✓ Descriptive Worker started (PID: $(cat .celery/desc-worker.pid))"
echo ""

# Start Coding worker in background
echo "▶ Starting Coding Worker (coding-queue, prefork)..."
celery -A evaluator.celery_app worker \
    --loglevel=info \
    --pool=prefork \
    --concurrency=2 \
    -Q coding-queue \
    -n coding-worker@%h \
    --detach \
    --pidfile=.celery/coding-worker.pid \
    --logfile=.celery/coding-worker.log

echo "  ✓ Coding Worker started (PID: $(cat .celery/coding-worker.pid))"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All workers started successfully!"
echo ""
echo "Logs are available in:"
echo "  - .celery/mcq-worker.log"
echo "  - .celery/desc-worker.log"
echo "  - .celery/coding-worker.log"
echo ""
echo "To stop all workers, run: ./scripts/stop_all_workers.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
