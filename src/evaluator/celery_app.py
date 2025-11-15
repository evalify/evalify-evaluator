"""Main Celery application instance."""

from celery import Celery
from celery.app.task import Task

from .config import celery_settings


# Create Celery app instance
app: Celery = Celery("celery_app")

# Load configuration
app.config_from_object(celery_settings)

# Configure heartbeat and events
# Heartbeats allow monitoring of worker status
# Interval in seconds - higher values reduce overhead but increase detection latency
app.conf.update(
    worker_heartbeat_interval=celery_settings.worker_heartbeat_interval,
    worker_enable_heartbeat=celery_settings.worker_enable_heartbeat,
    worker_max_tasks_per_child=celery_settings.worker_max_tasks_per_child,
    # Enable event capture (required for monitoring and heartbeats)
    # Set to 3 seconds to have reasonable granularity
    # Lower values = more frequent updates but higher overhead
    CELERY_RESULT_EXPIRES=celery_settings.result_expires,
)

# Auto-discover tasks
app.autodiscover_tasks(
    [
        "evaluator.worker.tasks.question",
        "evaluator.worker.tasks.student",
        "evaluator.worker.tasks.quiz",
    ],
    force=True,
)


@app.task(bind=True)
def debug_task(self: Task) -> str:
    """Debug task for testing Celery setup."""
    return f"Request: {self.request!r}"
