"""Main Celery application instance."""

from celery import Celery
from celery.app.task import Task

from .config import celery_settings


# Create Celery app instance
app: Celery = Celery("celery_app")

# Load configuration
app.config_from_object(celery_settings)

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
