#!/bin/bash
# Run script for the Evaluator API server
# Usage: ./run_api.sh

# Load environment variables if .env file exists
if [ -f .env ]; then
    set -a  # Automatically export all variables
    source .env
    set +a
fi

# Use environment variables or defaults
HOST=${HOST:-127.0.0.1}
PORT=${PORT:-4040}
RELOAD=${RELOAD:-true}
ENVIRONMENT=${ENVIRONMENT:-production}

echo "Starting Evaluator API server..."
echo "Host: $HOST"
echo "Port: $PORT"
echo "Reload: $RELOAD"
echo "Environment: $ENVIRONMENT"
echo ""

if [ "$RELOAD" = "true" ]; then
    uvicorn src.evaluator.main:app --host $HOST --port $PORT --reload
else
    uvicorn src.evaluator.main:app --host $HOST --port $PORT
fi
