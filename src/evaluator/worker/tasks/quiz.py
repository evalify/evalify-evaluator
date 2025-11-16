"""Quiz Level Tasks for Evaluation"""

from celery import group
from celery.utils.log import get_task_logger

from ...celery_app import app as current_app
from ...core.schemas import EvaluationJobRequest
from ..utils.progress import EvaluationProgressStore
from .student import student_job

logger = get_task_logger(__name__)


progress_store = EvaluationProgressStore(current_app)


@current_app.task(bind=True, queue="desc-queue")
def quiz_job(self, evaluation_id: str, request_dict: dict):
    """
    Orchestrates per-student evaluation tasks for a quiz and dispatches them as a Celery group.

    Parameters:
        evaluation_id (str): Identifier for this evaluation run.
        request_dict (dict): Serialized EvaluationJobRequest payload; will be validated and converted to an EvaluationJobRequest.

    Returns:
        group_id (str): The Celery group result ID for the dispatched student jobs.

    Raises:
        RuntimeError: If the student job group could not be initialized or the created group has no valid ID.
    """
    request = EvaluationJobRequest.model_validate(request_dict)
    logger.info(
        f"Starting quiz evaluation for quiz_id={request.quiz_id} (evaluation_id={evaluation_id})"
    )

    try:
        progress_store.mark_running(request.quiz_id)
        # Create one student_job for each student in the payload
        sub_tasks = [
            student_job.s(evaluation_id, request.quiz_id, student.model_dump())  # pyright: ignore[reportFunctionMemberAccess]
            for student in request.students
        ]

        # This creates a 'group of groups'
        # The result of this can be tracked to know when the entire quiz is done.
        quiz_group_job = group(sub_tasks).delay()

        if quiz_group_job is None:
            raise RuntimeError(
                "Failed to initialize student job group - got None result"
            )
        if not hasattr(quiz_group_job, "id") or quiz_group_job.id is None:
            raise RuntimeError("Group was created but has no valid ID")

        # Save the group result to the backend so it can be restored later
        quiz_group_job.save()
        progress_store.attach_group(request.quiz_id, quiz_group_job.id)

        logger.info(
            f"Dispatched all student jobs for evaluation_id={evaluation_id}. Group ID: {quiz_group_job.id}"
        )

        # In a full system, you would save quiz_group_job.id to Redis against the evaluation_id
        # to track the final completion.

        return quiz_group_job.id
    except Exception as e:
        logger.error(
            f"Failed to start quiz job for quiz_id={request.quiz_id}: {str(e)}",
            exc_info=True,
        )
        progress_store.mark_failed(request.quiz_id, reason=str(e))
        raise  # Raise anyway :)
