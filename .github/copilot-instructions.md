# Evalify Evaluator - Copilot Instructions

## Use Case

Evalify Evaluator is a **scalable, asynchronous evaluation microservice** that grades student quiz submissions across multiple question types (MCQ, descriptive, coding). It receives bulk evaluation requests, distributes question-specific grading to specialized workers, and stores results for retrieval by the main Evalify backend.

## Quick Architecture

Evalify Evaluator uses **FastAPI** (API), **Celery** (async tasks), and **Redis** (broker/state). The system routes different question types to specialized workers using a **factory pattern** for evaluator implementations.

**Core Flow**: API receives evaluation request → quiz_job orchestrator → creates per-student jobs → routes to type-specific queues (MCQ, Descriptive, Coding) → workers evaluate using EvaluatorFactory → results stored in Redis.

**Note**: Code architecture is subject to change—always explore the current implementation in `src/evaluator/` before assuming patterns or making changes. Check `src/evaluator/worker/tasks/` for task hierarchy and `src/evaluator/worker/evaluators/` for evaluator implementations.

## Essential Commands

**Always use `uv` for dependency and Python execution:**
```bash
uv sync                    # Install dependencies from pyproject.toml
uv run python file.py      # Run Python files via uv (preferred over `python file.py`)
uv add package_name        # Add dependencies
uv add package_name==version  # Add specific version (>=, <=, etc. supported)
uv remove package_name     # Remove dependencies
```

**Start Services** (in separate terminals):
```bash
redis-server                                    # Redis broker (required first)
uv run uvicorn src.evaluator.main:app --reload  # API server on localhost:4040
./scripts/start_all_workers_tmux.sh --attach    # All 3 workers in tmux (dev-friendly)
```

**Manual Testing**:
```bash
uv run python tests/manual_test_evaluation.py   # End-to-end test with sample data
```

**Individual Workers** (alternative to tmux):
- MCQ/FITB/MATCH: `./scripts/start_mcq_worker.sh` (prefork pool, 4 workers)
- Descriptive: `./scripts/start_desc_worker.sh` (gevent pool, 100 greenlets for I/O)
- Coding: `./scripts/start_coding_worker.sh` (prefork pool, 2 workers)

## Key Architectural Patterns

### 1. Worker Pool Selection
**Prefork** (CPU-bound): MCQ evaluator, code execution → cpu cores-based concurrency
**Gevent** (I/O-bound): Descriptive (LLM calls) → hundreds of greenlets possible
Queue mapping in `src/evaluator/config.py`: `question_type_to_queue` dict

### 2. Evaluator Factory Pattern
- Base: `src/evaluator/worker/evaluators/base.py` - `BaseEvaluator` ABC with auto-registration
- Subclasses (e.g., `MCQEvaluator`) set `question_type` class attr → auto-registers via `__init_subclass__`
- Factory: `src/evaluator/worker/evaluators/factory.py` - `EvaluatorFactory.get_evaluator(type)`
- Task: `src/evaluator/worker/tasks/question.py` uses factory, handles `EvaluationFailedException` (business logic errors) vs system exceptions (retry)

**To add a new evaluator:**
1. Create class in `src/evaluator/worker/evaluators/`, inherit `BaseEvaluator`
2. Set `question_type = "YOUR_TYPE"` and implement `evaluate(question_data) → EvaluatorResult`
3. Auto-registers; add queue mapping in config; ensure worker listens to that queue

### 3. Task Hierarchy
- `quiz_job` (entry point): Orchestrates all student evaluations, creates Celery group of `student_job` tasks
- `student_job`: Orchestrates questions for one student, creates group of `process_question_task` tasks
- `process_question_task` (generic worker task): Delegates to factory-selected evaluator

See `src/evaluator/worker/tasks/` files for exception handling and retry strategies.

### 4. Pydantic Schemas for Type Safety
Located in `src/evaluator/core/schemas/`:
- `api.py`: `EvaluationJobRequest`, `EvaluationAcceptedResponse`
- `tasks.py`: `TaskPayload`, `QuestionPayload`, `EvaluatorResult`, `QuestionEvaluationResult`

Always use these for validation; Celery serializes/deserializes via `.model_dump()` and `.model_validate()`.

## Configuration & Environment

**Settings** (both use Pydantic, env vars override defaults):
- `Settings`: Core app (Redis URL, Evalify backend URL, CORS, logging, queue mapping)
- `CelerySettings`: Broker/backend URLs, pool settings, result expiry, heartbeat intervals

Environment variables: Prefix with `CELERY_` for Celery config (e.g., `CELERY_BROKER_URL`). See `src/evaluator/config.py` for all options and defaults. Complex fields (list, dict) accept JSON strings via env.

## API Usage & Backend Integration

**Evaluator API endpoint**:
```
POST /api/v1/evaluations
Body: EvaluationJobRequest {quiz_id, students: [StudentPayload], override_evaluated}
Returns: 202 {quiz_id, status: "QUEUED", progress_url}
```

Example: `tests/manual_test_evaluation.py` shows full request construction and result retrieval via Celery's `AsyncResult` and `GroupResult`.

**Backend result submission** (TODO - in progress):
After all questions for a student are evaluated by `process_question_task`, the `student_job` task aggregates results and submits them to the Evalify backend via a dedicated client. The backend client should:
- Submit aggregated student evaluation results to backend API endpoint (location TBD)
- Handle retries for transient failures
- Log success/failure
- Be located in `src/evaluator/clients/` (currently only has Redis client)

The `student_job` task in `src/evaluator/worker/tasks/student.py` orchestrates this flow: create question tasks → collect results → call backend client to save results.

## Testing & Debugging

- **Manual test**: `uv run python tests/manual_test_evaluation.py` (requires Redis, API, workers running)
- **Check workers**: `celery -A evaluator.celery_app inspect active` (uses `src/evaluator/config.py`)
- **View logs**: `.celery/*.log` files (when using `start_all_workers.sh`)
- **Inspect results**: Connect to Redis directly via `redis-cli` for debugging state/queues

## Framework Documentation

When working with frameworks used here (uv, FastAPI, Celery, Pydantic, Redis, gevent), use the Context7 MCP tool to fetch up-to-date docs:
```
Use mcp_upstash_conte_get-library-docs with library IDs like:
- /uv/uv (Python package manager)
- /tiangolo/fastapi (async web framework)
- /celery/celery (distributed task queue)
- /pydantic/pydantic (data validation)
- /redis-py/redis-py (Redis client)
- /gevent/gevent (greenlet concurrency)
```

First resolve the library name via `mcp_upstash_conte_resolve-library-id` if needed.

## Code Style & Conventions

- **Imports**: Group stdlib, third-party, local; use absolute imports from `evaluator.*`
- **Pydantic models**: Inherit `BaseModel`, use `Field(...)` for docs, add type hints, use `model_dump()`/`model_validate()` for serialization
- **Celery tasks**: Use `@current_app.task()` from `src/evaluator/celery_app`, set `bind=True` for context, include `retry_kwargs`, log with `get_task_logger(__name__)`
- **Exceptions**: Custom exceptions inherit from base (e.g., `EvaluationFailedException`), caught explicitly in tasks for business logic vs system failures
- **FastAPI routes**: Group in routers under `api/routers/`, use `APIRouter` with prefix, include docstrings and status codes

## File Locations Quick Ref

```
src/evaluator/
├── main.py                    # FastAPI app init, lifespan, health endpoints
├── config.py                  # Settings, CelerySettings, queue mapping
├── celery_app.py              # Celery instance, auto-discovery
├── dependencies.py            # Shared dependencies (Redis client, etc.)
├── clients/                   # External service clients
│   ├── redis_client.py        # Redis sync/async clients
│   └── backend_client.py      # TODO: Evalify backend client for result submission
├── api/routers/
│   └── evaluation.py          # POST /api/v1/evaluations endpoint
├── core/schemas/
│   ├── api.py                 # Request/response models
│   └── tasks.py               # Task payload models
└── worker/
    ├── evaluators/
    │   ├── base.py            # BaseEvaluator ABC
    │   ├── factory.py          # EvaluatorFactory, registry
    │   └── mcq_evaluator.py    # Example: MCQEvaluator implementation
    └── tasks/
        ├── question.py         # process_question_task (generic)
        ├── student.py          # student_job (calls backend client after aggregation)
        └── quiz.py             # quiz_job (orchestrator)

docs/architecture/system_flow.md  # Mermaid sequence diagram
tests/manual_test_evaluation.py    # End-to-end example
scripts/                           # Worker startup scripts
```

## Common Tasks

**Add a new evaluator type**: Create class in `worker/evaluators/`, set `question_type`, implement `evaluate()`, update queue mapping if new queue needed.

**Change worker concurrency**: Edit `scripts/start_*_worker.sh` or use env vars (`CELERY_WORKER_*`).

**Debug task execution**: Check `.celery/*.log`, use `celery inspect active/stats`, connect to Redis to inspect job state.

**Update dependencies**: `uv add` or `uv remove` (updates `pyproject.toml`), then commit; never edit `pyproject.toml` directly.
