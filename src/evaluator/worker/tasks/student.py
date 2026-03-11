"""Student Level Job for Evaluation"""

import uuid
from typing import Any

from ...celery_app import app as current_app
from celery import group
from celery.canvas import Signature
from celery.result import AsyncResult
from celery.utils.log import get_task_logger

from ...core.schemas import (
    QuestionEvaluationResult,
    QuestionEvaluationStatus,
    QuestionPayload,
    StudentEvaluationSavePayload,
    StudentPayload,
    StudentQuestionEvaluationData,
    TaskPayload,
)
from ...config import settings
from ...clients.backend_client import BackendEvaluationAPIClient
from .question import create_process_question_task_signature

logger = get_task_logger(__name__)

STUDENT_JOB_TASK_NAME = "evaluator.worker.tasks.student.student_job"


def create_student_job_signature(
    evaluation_id: str,
    quiz_id: str,
    student_payload: StudentPayload,
    *,
    queue: str = "desc-queue",
) -> Signature:
    """Build a routed Celery signature for a single student evaluation job."""

    return student_job.s(
        evaluation_id,
        quiz_id,
        student_payload.model_dump(mode="json"),
    ).set(queue=queue)  # pyright: ignore[reportFunctionMemberAccess]


def enqueue_student_job(
    evaluation_id: str,
    quiz_id: str,
    student_payload: StudentPayload,
    *,
    queue: str = "desc-queue",
    **apply_async_kwargs: Any,
) -> AsyncResult:
    """Enqueue a single student evaluation job using typed payload input."""

    return student_job.apply_async(  # pyright: ignore[reportFunctionMemberAccess]
        args=[evaluation_id, quiz_id, student_payload.model_dump(mode="json")],
        queue=queue,
        **apply_async_kwargs,
    )


def _coerce_question_result(
    quiz_id: str,
    student_id: str,
    question_data: QuestionPayload,
    task_result,
) -> QuestionEvaluationResult:
    if task_result.failed():
        return QuestionEvaluationResult(
            quiz_id=quiz_id,
            student_id=student_id,
            question_id=question_data.question_id,
            question_type=question_data.question_type,
            job_id=uuid.UUID(str(task_result.id)),
            evaluation_status=QuestionEvaluationStatus.ERROR,
            evaluated_result=None,
            error=str(task_result.result),
            traceback=task_result.traceback,
        )

    return QuestionEvaluationResult.model_validate(task_result.result)


def _build_student_question_evaluation_data(
    result: QuestionEvaluationResult,
) -> StudentQuestionEvaluationData:
    evaluated = result.evaluated_result

    if (
        result.evaluation_status == QuestionEvaluationStatus.EVALUATED
        and evaluated is not None
    ):
        score = evaluated.score
        remarks = evaluated.feedback or ""
    else:
        score = 0
        remarks = (evaluated.feedback if evaluated else "") or ""

    return StudentQuestionEvaluationData(
        evaluation_status=result.evaluation_status,
        question_type=result.question_type,
        score=score,
        remarks=remarks,
        metrics=result.metrics.model_dump(mode="json") if result.metrics else {},
        error_message=result.error,
        coding=None,
    )


@current_app.task(
    name=STUDENT_JOB_TASK_NAME, bind=True, queue="desc-queue"
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
    queued_questions: list[QuestionPayload] = []
    for question_data in student_payload.questions:
        # Step 1: Look up the correct queue from our central config
        queue_name = settings.question_type_to_queue.get(question_data.question_type)
        if not queue_name:
            if question_data.question_type == "FILE_UPLOAD":
                logger.warning(
                    f"Question type {question_data.question_type} is not supported for evaluation. Skipping question_id={question_data.question_id} for student_id={student_id}"
                )
                continue  # Skip unsupported question types without failing the entire student job

            logger.error(
                f"No queue configured for question type: {question_data.question_type}"
            )
            # Handle this case - maybe a default queue or fail fast
            continue

        # Step 2: Create the task payload for the generic question worker
        task_payload = TaskPayload(
            quiz_id=quiz_id,
            student_id=student_id,
            question_data=question_data,
        )

        # Step 3: Create a Celery signature and set its queue dynamically
        task_signature = create_process_question_task_signature(
            task_payload,
            queue=queue_name,
        )
        sub_tasks.append(task_signature)
        queued_questions.append(question_data)

    if not sub_tasks:
        logger.warning(f"No valid tasks to process for student_id={student_id}")
        return {"student_id": student_id, "results": []}  # Return empty if no questions

    # Step 4: Execute the group of question tasks and wait for them all to finish
    group_job = group(sub_tasks).apply_async()
    group_result = group_job.get(  # noqa: F841
        propagate=False
    )  # Wait for all, do not fail this task if a sub-task fails

    # Step 5: Aggregate the results, adding metadata
    aggregated_results: list[QuestionEvaluationResult] = []
    for question_data, task_result in zip(queued_questions, group_job.results):
        aggregated_results.append(
            _coerce_question_result(
                quiz_id=quiz_id,
                student_id=student_id,
                question_data=question_data,
                task_result=task_result,
            )
        )

    # Build student-level save payload with required schema
    data_map = {
        result.question_id: _build_student_question_evaluation_data(result)
        for result in aggregated_results
    }

    student_save_payload = StudentEvaluationSavePayload(data=data_map)

    # Step 6: Persist student-level result via backend save endpoint
    try:
        with BackendEvaluationAPIClient() as client:
            client.save_student_result(
                quiz_id=quiz_id,
                student_id=student_id,
                result=student_save_payload,
            )
        logger.info(
            f"Saved student result for student_id={student_id}, quiz_id={quiz_id}"
        )
    except Exception:
        logger.exception(
            f"Failed to save student result for student_id={student_id}, quiz_id={quiz_id}"
        )

    # Step 7: Return the aggregated payload
    return {
        "student_id": student_id,
        "results": [result.model_dump(mode="json") for result in aggregated_results],
    }
