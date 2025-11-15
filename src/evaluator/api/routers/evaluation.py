"""
Evaluation API routes for managing quiz evaluation jobs.
"""

from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from ...core.schemas.api import (
    EvaluationJobRequest,
    EvaluationAcceptedResponse,
)

from ...celery_app import app as celery_app


router = APIRouter(prefix="/api/v1/evaluations", tags=["evaluations"])


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
    Start a new evaluation job for a quiz.

    This endpoint accepts a quiz evaluation request containing all student submissions
    and queues them for asynchronous processing. It returns immediately with a job ID
    and progress URL.

    Args:
        request: The evaluation job request containing quiz_id, students, and options

    Returns:
        EvaluationAcceptedResponse: Job acceptance confirmation with progress URL

    Raises:
        HTTPException: If the job cannot be queued
    """
    # Generate a unique evaluation ID
    evaluation_id = str(uuid4())

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
            progress_url=f"/api/v1/evaluations/{evaluation_id}/progress",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start evaluation job: {str(e)}",
        )
