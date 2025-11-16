"""
Evaluation API routes for managing quiz evaluation jobs.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from celery.result import AsyncResult, GroupResult
from fastapi import APIRouter, HTTPException, status

from ...core.schemas.api import (
    EvaluationJobRequest,
    EvaluationAcceptedResponse,
    EvaluationProgressResponse,
)

from ...celery_app import app as celery_app
from ...worker.utils.progress import EvaluationProgressStore


router = APIRouter(prefix="/api/v1/evaluations", tags=["evaluations"])
progress_store = EvaluationProgressStore(celery_app)
logger = logging.getLogger(__name__)


def _parse_datetime(value: Optional[object]) -> Optional[datetime]:
    """
    Convert a datetime-like value into a timezone-aware UTC datetime.

    Parameters:
        value (Optional[object]): A datetime, a numeric Unix timestamp (int/float), an ISO8601 timestamp string, or None.

    Returns:
        Optional[datetime]: A datetime with UTC tzinfo representing the same instant, or `None` if `value` is None or cannot be parsed.
    """

    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    parsed: Optional[datetime] = None
    if isinstance(value, (float, int)):
        parsed = datetime.fromtimestamp(value, tz=timezone.utc)
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            pass

        if parsed is None:
            try:
                parsed = datetime.fromtimestamp(float(value), tz=timezone.utc)
            except (ValueError, TypeError):
                return None

    if parsed is None:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _iso(dt: datetime) -> str:
    """
    Convert a datetime to an ISO 8601 string in UTC.

    Returns:
        An ISO 8601 formatted string representing `dt` converted to UTC.
    """
    tz_aware = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return tz_aware.astimezone(timezone.utc).isoformat()


@router.post(
    "",
    response_model=EvaluationAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a new evaluation job",
    description="Initiates an asynchronous evaluation job for a quiz with all student submissions.",
)
async def start_evaluation(
    request: EvaluationJobRequest,
):
    """
    Start an evaluation job for a quiz and enqueue it for asynchronous processing.

    Returns:
        EvaluationAcceptedResponse: Acceptance details containing `quiz_id`, `status`, and `progress_url`.

    Raises:
        HTTPException: If the job cannot be queued.
    """
    # Generate a unique evaluation ID
    evaluation_id = str(uuid4())
    progress_store.initialize(
        quiz_id=request.quiz_id,
        evaluation_task_id=evaluation_id,
        total_students=len(request.students),
    )

    try:
        # Dispatch the quiz_job task to Celery
        # Using evaluation_id as task_id makes it easy to track results
        # Send to desc-queue since quiz_job is orchestration work (I/O-bound)
        celery_app.send_task(
            "evaluator.worker.tasks.quiz.quiz_job",
            args=[evaluation_id, request.model_dump()],
            task_id=evaluation_id,
            queue="desc-queue",
        )

        return EvaluationAcceptedResponse(
            quiz_id=request.quiz_id,
            status="QUEUED",
            progress_url=f"/api/v1/evaluations/{request.quiz_id}/progress",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start evaluation job: {str(e)}",
        )


@router.get(
    "/{quiz_id}/progress",
    response_model=EvaluationProgressResponse,
    summary="Get evaluation progress",
    description="Returns the latest quiz-level evaluation progress aggregated per student.",
)
async def get_evaluation_progress(quiz_id: str) -> EvaluationProgressResponse:
    """
    Return aggregated per-quiz evaluation progress derived from stored metadata and Celery task/group results.

    Parameters:
        quiz_id (str): Identifier of the quiz whose evaluation progress to retrieve.

    Returns:
        EvaluationProgressResponse: Progress snapshot including quiz_id, status (one of "QUEUED", "RUNNING", "COMPLETED", "FAILED"), students_finished, total_students, created_at (timezone-aware UTC datetime), and updated_at (timezone-aware UTC datetime).
    """
    metadata = progress_store.get(quiz_id)
    if metadata is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No evaluation found for quiz_id={quiz_id}",
        )

    created_at = _parse_datetime(metadata.get("created_at")) or datetime.now(
        timezone.utc
    )
    stored_updated_at = _parse_datetime(metadata.get("updated_at")) or created_at
    total_students = int(metadata.get("total_students") or 0)
    status_value = metadata.get("status", "QUEUED")
    evaluation_task_id: Optional[str] = metadata.get("evaluation_task_id")
    group_id: Optional[str] = metadata.get("group_id")

    students_finished = 0
    latest_completion: Optional[datetime] = None
    updated_fields = {}

    if group_id:
        group_result = GroupResult.restore(group_id, app=celery_app)
        if group_result:
            results = group_result.results or []
            # Correct total_students if it was initially stored as 0 (from group result length)
            if total_students == 0 and results:
                total_students = len(results)
                updated_fields["total_students"] = total_students

            # TODO: Consider this:
            # The calculation of students_finished assumes all ready tasks succeeded, but failed tasks are also ready. This means failed student evaluations are counted as "finished"
            # Should we count only successful completions? Or keep as is to reflect that the evaluation attempt is done regardless of success?
            students_finished = sum(1 for result in results if result.ready())
            completion_dates = [
                _parse_datetime(result.date_done)
                for result in results
                if result.ready() and result.date_done
            ]
            completion_dates = [dt for dt in completion_dates if dt]
            if completion_dates:
                latest_completion = max(completion_dates)

            has_failures = any(result.failed() for result in results)
            if has_failures:
                status_value = "FAILED"
            elif (
                total_students > 0
                and students_finished >= total_students
                and group_result.ready()
            ):
                status_value = "COMPLETED"
            elif students_finished > 0:
                status_value = "RUNNING"
            elif results:
                status_value = "RUNNING"
        else:
            # Could not restore group result (expired/cleared). Keep existing metadata.
            group_result = None

    if status_value != "FAILED" and evaluation_task_id:
        quiz_task = AsyncResult(evaluation_task_id, app=celery_app)
        if quiz_task.failed():
            status_value = "FAILED"
            latest_completion = (
                _parse_datetime(quiz_task.date_done) or latest_completion
            )

    updated_at = latest_completion or stored_updated_at

    # Clamp to prevent over-reporting if students_finished exceeds total due to metadata drift
    if total_students > 0 and students_finished > total_students:
        logger.warning(
            f"Data inconsistency detected for quiz_id={quiz_id}: "
            f"students_finished ({students_finished}) exceeds total_students ({total_students}). "
            f"This indicates metadata drift or counting logic bug. "
            f"group_id={group_id}, evaluation_task_id={evaluation_task_id}"
        )
        students_finished = total_students

    current_updated_iso = _iso(updated_at)
    if status_value != metadata.get("status"):
        updated_fields["status"] = status_value
    if current_updated_iso != metadata.get("updated_at"):
        updated_fields["updated_at"] = current_updated_iso
    if updated_fields:
        updated_fields.setdefault("updated_at", current_updated_iso)
        progress_store.update(quiz_id, **updated_fields)

    return EvaluationProgressResponse(
        quiz_id=quiz_id,
        status=status_value,
        students_finished=students_finished,
        total_students=total_students,
        created_at=created_at,
        updated_at=updated_at,
    )
