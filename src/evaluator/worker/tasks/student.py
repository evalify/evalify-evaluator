"""Student Level Job for Evaluation"""

from ...celery_app import app as current_app
from celery import group
from celery.utils.log import get_task_logger

from ...core.schemas import StudentPayload
from ...config import settings
from .question import process_question_task

logger = get_task_logger(__name__)


@current_app.task(
    bind=True, queue="desc-queue"
)  # An I/O-bound queue is fine for orchestration
def student_job(self, evaluation_id: str, quiz_id: str, student_payload_dict: dict):
    """
    Aggregates all question evaluations for a single student.
    Dynamically creates and routes question tasks to configured queues based on their type.

    Set Question to Queue Mapping in Settings
    """
    student_payload = StudentPayload.model_validate(student_payload_dict)
    student_id = student_payload.student_id
    logger.info(
        f"Starting evaluation for student_id={student_id} in quiz_id={quiz_id} (evaluation_id={evaluation_id})"
    )

    sub_tasks = []
    for question_data in student_payload.questions:
        # Step 1: Look up the correct queue from our central config
        queue_name = settings.question_type_to_queue.get(question_data.question_type)
        if not queue_name:
            logger.error(
                f"No queue configured for question type: {question_data.question_type}"
            )
            # Handle this case - maybe a default queue or fail fast
            continue

        # Step 2: Create the task payload for the generic question worker
        task_payload = {
            "quiz_id": quiz_id,
            "student_id": student_id,
            "question_data": question_data.model_dump(),
        }

        # Step 3: Create a Celery signature and set its queue dynamically
        task_signature = process_question_task.s(task_payload).set(queue=queue_name)  # pyright: ignore[reportFunctionMemberAccess]
        sub_tasks.append(task_signature)

    if not sub_tasks:
        logger.warning(f"No valid tasks to process for student_id={student_id}")
        return {"student_id": student_id, "results": []}  # Return empty if no questions

    # Step 4: Execute the group of question tasks and wait for them all to finish
    group_job = group(sub_tasks).apply_async()
    group_result = group_job.get(  # noqa: F841
        propagate=False
    )  # Wait for all, do not fail this task if a sub-task fails

    # Step 5: Aggregate the results, adding metadata
    aggregated_results = []
    for i, r in enumerate(group_job.results):
        if r.failed():
            # This indicates a SYSTEM failure (the task itself failed in Celery)
            aggregated_results.append(
                {
                    "job_id": r.id,  # Celery task id for the failed subtask
                    "status": "system_error",
                    "error": str(r.result),
                    "traceback": r.traceback,
                }
            )
        else:
            # This is a successful task execution, which could contain a business logic failure
            aggregated_results.append(
                r.result
            )  # r.result is the dict returned by process_question_task

    # Step 6: This task's final return value is the aggregated payload
    return {
        "student_id": student_id,
        "results": aggregated_results,
    }
