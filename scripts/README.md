# Worker Scripts

This directory contains scripts for managing Celery workers for the evaluation system.

## Available Scripts

### Individual Worker Scripts

#### `start_mcq_worker.sh`
Starts a worker for processing MCQ (Multiple Choice Question) evaluations.

- **Queue**: `mcq-queue`
- **Pool**: `prefork` (CPU-bound processing)
- **Concurrency**: 4 workers
- **Use case**: MCQ, FITB (Fill in the Blank), MATCH questions

```bash
./scripts/start_mcq_worker.sh
```

#### `start_desc_worker.sh`
Starts a worker for processing DESCRIPTIVE question evaluations.

- **Queue**: `desc-queue`
- **Pool**: `gevent` (I/O-bound, async processing)
- **Concurrency**: 100 greenlets
- **Use case**: Descriptive questions requiring LLM/AI evaluation

```bash
./scripts/start_desc_worker.sh
```

#### `start_coding_worker.sh`
Starts a worker for processing CODING question evaluations.

- **Queue**: `coding-queue`
- **Pool**: `prefork` (CPU-intensive code execution)
- **Concurrency**: 2 workers
- **Use case**: Programming/coding questions with test execution

```bash
./scripts/start_coding_worker.sh
```

### Management Scripts

#### `start_all_workers.sh`
Starts all workers in detached mode (background).

```bash
./scripts/start_all_workers.sh
```

This will:
- Start MCQ worker with PID file at `.celery/mcq-worker.pid`
- Start Descriptive worker with PID file at `.celery/desc-worker.pid`
- Start Coding worker with PID file at `.celery/coding-worker.pid`
- Log outputs to `.celery/*.log` files

#### `start_all_workers_tmux.sh`
Starts all three workers in a single tmux session with a split-pane layout for easy monitoring.

```bash
./scripts/start_all_workers_tmux.sh
```

**Layout**:
- Left pane: MCQ Worker
- Top-right pane: Descriptive Worker
- Bottom-right pane: Coding Worker

**Options**:
- `-a, --attach`: Attach to the tmux session immediately after starting
  ```bash
  ./scripts/start_all_workers_tmux.sh --attach
  ```

**Usage**:
- Attach to running session: `tmux attach-session -t evaluator-workers`
- Navigate between panes: `Ctrl+B` followed by arrow keys
- Stop individual worker: Send `Ctrl+C` to specific pane
- Stop all workers: `tmux kill-session -t evaluator-workers`

This script is ideal for development and monitoring as it provides real-time visibility into all three worker types simultaneously.

#### `stop_all_workers.sh`
Stops all running workers gracefully.

```bash
./scripts/stop_all_workers.sh
```

#### `stop_all_workers_tmux.sh`
Kills the tmux session running all three Celery workers.

```bash
./scripts/stop_all_workers_tmux.sh
```

This script will:
- Check if the `evaluator-workers` tmux session is running
- Kill the session if it exists
- Return silently if the session isn't running

Use this to stop workers started with `start_all_workers_tmux.sh`.

## Worker Pool Types

### Prefork Pool
- **Best for**: CPU-bound tasks (MCQ evaluation, code execution)
- **Process model**: Multiple OS processes
- **Concurrency**: Limited by CPU cores
- **Used by**: MCQ Worker, Coding Worker

### Gevent Pool
- **Best for**: I/O-bound tasks (API calls to LLMs, network requests)
- **Process model**: Single process with many greenlets
- **Concurrency**: Can handle 100+ concurrent tasks
- **Used by**: Descriptive Worker

## Queue Mapping

The system maps question types to queues as configured in `src/evaluator/config.py`:

```python
question_type_to_queue = {
    "MCQ": "mcq-queue",
    "FITB": "mcq-queue",
    "MATCH": "mcq-queue",
    "DESCRIPTIVE": "desc-queue",
    "CODING": "coding-queue",
}
```

## Logs and PID Files

When using `start_all_workers.sh`, logs and PID files are stored in `.celery/`:

```
.celery/
├── mcq-worker.pid
├── mcq-worker.log
├── desc-worker.pid
├── desc-worker.log
├── coding-worker.pid
└── coding-worker.log
```

These files are automatically created and cleaned up by the management scripts.

## Development Tips

### Running a Single Worker (Foreground)
For development and debugging, run individual worker scripts which start in foreground mode:

```bash
./scripts/start_mcq_worker.sh
```

Press `Ctrl+C` to stop.

### Adjusting Concurrency
Edit the concurrency value in each script based on your system resources:

- **MCQ Worker**: Adjust based on CPU cores (e.g., 2-8)
- **Descriptive Worker**: Can be high (50-200) for I/O-bound tasks
- **Coding Worker**: Keep low (1-4) as code execution is resource-intensive

### Monitoring Workers
Check worker status:

```bash
celery -A evaluator.celery_app inspect active
celery -A evaluator.celery_app inspect stats
```

Check worker logs:
```bash
tail -f .celery/mcq-worker.log
tail -f .celery/desc-worker.log
tail -f .celery/coding-worker.log
```

### Testing with Manual Script
Use the manual test script to verify workers are processing tasks:

```bash
python tests/manual_test_evaluation.py
```

## Prerequisites

Before running workers, ensure:

1. **Redis is running** (Celery broker and result backend)
   ```bash
   redis-server
   ```

2. **Environment variables are configured** (`.env` file)
   ```bash
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   ```

3. **Dependencies are installed**
   ```bash
   uv sync
   ```

## Troubleshooting

### "No such file or directory" error
Make sure scripts are executable:
```bash
chmod +x scripts/*.sh
```

### Workers not processing tasks
1. Check Redis is running: `redis-cli ping`
2. Verify queue names in worker scripts match configuration
3. Check worker logs for errors
4. Ensure the API is sending tasks to the correct queue

### High CPU usage
- Reduce concurrency in prefork workers
- Check for infinite loops in task code
- Monitor with `celery -A evaluator.celery_app inspect stats`

### Memory issues with gevent
- Reduce concurrency in descriptive worker
- Monitor memory usage with `htop` or `top`
- Consider scaling horizontally (multiple machines)

## See Also

- [Manual Test Script](../tests/README.md)
- [Celery Configuration](../src/evaluator/config.py)
- [System Architecture](../docs/architecture/system_flow.md)
