"""Question Level Tasks for Evaluation"""

import uuid

from ...celery_app import app as current_app
from celery.utils.log import get_task_logger

from ...core.schemas import (
    TaskPayload,
    QuestionEvaluationResult,
    EvaluatorResult,
    EvaluatorContext,
)
from ..evaluators.factory import EvaluatorFactory
from ..evaluators.base import EvaluationFailedException

logger = get_task_logger(__name__)


@current_app.task(
    bind=True,
    autoretry_for=(Exception,),  # TODO: Set expected Exception types here
    retry_kwargs={"max_retries": 3, "countdown": 5},
    retry_backoff=True,
    retry_jitter=True,
)
def process_question_task(self, task_payload_dict: dict) -> dict:
    """
    The single, generic task for evaluating any question type.
    It uses the EvaluatorFactory to delegate to the correct logic.
    This Task will be automatically forwarded the the configured queue based on the question type.

    Check student job (caller) for queue information.
    """
    task_payload = TaskPayload.model_validate(task_payload_dict)
    logger.info(f"Processing student={task_payload.student_id}")

    try:
        # Step 1: Get the correct evaluator instance from the factory
        evaluator = EvaluatorFactory.get_evaluator(
            task_payload.question_data.question_type
        )

        # Step 2: Execute the specific evaluation logic
        context = EvaluatorContext(
            quiz_settings=task_payload.question_data.quiz_settings
        )
        result: EvaluatorResult = evaluator.evaluate(
            task_payload.question_data, context
        )

        # Step 3: Package the successful result
        result_payload = QuestionEvaluationResult(
            quiz_id=task_payload.quiz_id,
            job_id=uuid.UUID(self.request.id),
            student_id=task_payload.student_id,
            question_id=task_payload.question_data.question_id,
            status="success",
            evaluated_result=result,
        )
        return result_payload.model_dump()

    except EvaluationFailedException as e:
        # Step 4: Handle a predictable business logic failure.
        # This is NOT a task failure for Celery. The task succeeded in determining a failure.
        logger.warning(f"Business logic failure: {e}")
        result_payload = QuestionEvaluationResult(
            quiz_id=task_payload.quiz_id,
            student_id=task_payload.student_id,
            question_id=task_payload.question_data.question_id,
            job_id=uuid.UUID(self.request.id),
            status="failed",
            evaluated_result=None,
            error=str(e),
        )
        return result_payload.model_dump()

    except NotImplementedError as e:
        # Step 5: Handle missing evaluators gracefully
        logger.warning(f"Missing evaluator: {e}")
        result_payload = QuestionEvaluationResult(
            quiz_id=task_payload.quiz_id,
            student_id=task_payload.student_id,
            question_id=task_payload.question_data.question_id,
            job_id=uuid.UUID(self.request.id),
            status="not_implemented",
            evaluated_result=None,
            error=str(e),
        )
        return result_payload.model_dump()

    except Exception:
        # Step 5: An unexpected system error occurred (e.g., Redis down, bug in code).
        # Re-raising the exception tells Celery this task FAILED and should be retried.
        logger.exception("Unexpected system error")
        raise
