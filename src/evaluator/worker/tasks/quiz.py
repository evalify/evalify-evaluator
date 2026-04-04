"""Quiz Level Tasks for Evaluation"""

from typing import List, Optional
from celery import group
from celery.result import AsyncResult
from celery.canvas import Signature
from celery.utils.log import get_task_logger

from ...celery_app import app as current_app
from ...core.schemas.api import EvaluationJobRequest
from ...core.schemas.tasks import StudentPayload, QuestionPayload
from ...core.schemas.backend_api import QuizSettings
from ...core.schemas.backend_api import (
    QuizQuestion,
    QuizResponseRecord,
)
from ...clients.backend_client import BackendEvaluationAPIClient
from ..utils.progress import EvaluationProgressStore
from .student import create_student_job_signature

logger = get_task_logger(__name__)

QUIZ_JOB_TASK_NAME = "evaluator.worker.tasks.quiz.quiz_job"


progress_store = EvaluationProgressStore(current_app)


def enqueue_quiz_job(
    evaluation_id: str,
    request: EvaluationJobRequest,
    *,
    queue: str = "desc-queue",
) -> AsyncResult:
    """Enqueue the quiz orchestration task using typed request input."""

    return quiz_job.apply_async(  # pyright: ignore[reportFunctionMemberAccess]
        args=[evaluation_id, request.model_dump(mode="json")],
        task_id=evaluation_id,
        queue=queue,
    )


def _map_response_to_student_payload(
    student_response: QuizResponseRecord,
    questions: List[QuizQuestion],
    quiz_settings: QuizSettings,
    question_ids_filter: Optional[List[str]] = None,
) -> StudentPayload:
    """
    Maps a student's quiz response to a StudentPayload for evaluation.

    Parameters:
        student_response: The student's quiz response record.
        questions: The list of all quiz questions.
        quiz_settings: The quiz-wide settings.
        question_ids_filter: Optional list of question IDs to include. If provided, only these questions are mapped.
    """
    question_payloads = []
    student_answers = student_response.response or {}

    for question in questions:
        # Skip this question if question_ids_filter is provided and doesn't include it
        if question_ids_filter is not None and question.id not in question_ids_filter:
            continue

        student_ans = student_answers.get(question.id)

        # TODO: Raise an error if expected answer is missing
        expected_ans = question.solution.data if question.solution else None

        # Create QuestionPayload
        q_payload = QuestionPayload(
            question_id=question.id,
            question_type=question.type,
            student_answer=student_ans,
            expected_answer=expected_ans,
            question_data=question.questionData.data,
            grading_guidelines=None,  # TODO: Extract if available in questionData
            total_score=question.marks,
            quiz_settings=quiz_settings,
        )
        question_payloads.append(q_payload)

    return StudentPayload(
        student_id=student_response.studentId,
        questions=question_payloads,
    )


@current_app.task(name=QUIZ_JOB_TASK_NAME, bind=True, queue="desc-queue")
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

        # Fetch questions and responses from backend
        with BackendEvaluationAPIClient() as client:
            logger.info(f"Fetching questions for quiz_id={request.quiz_id}")
            questions_resp = client.get_quiz_questions(request.quiz_id)
            questions = questions_resp.data

            logger.info(f"Fetching quiz settings for quiz_id={request.quiz_id}")
            quiz_settings = client.get_quiz_settings(request.quiz_id)

            logger.info(f"Fetching student responses for quiz_id={request.quiz_id}")
            responses_resp = client.get_quiz_responses(request.quiz_id)
            student_responses = responses_resp.responses

        # Update total students count in progress store
        total_students = len(student_responses)
        progress_store.update(request.quiz_id, total_students=total_students)
        logger.info(
            f"Found {total_students} students to evaluate for quiz_id={request.quiz_id}"
        )

        if total_students == 0:
            logger.warning(f"No student responses found for quiz_id={request.quiz_id}")
            progress_store.mark_completed(request.quiz_id)
            return None

        # Filter students if student_ids filter is provided
        filtered_responses = student_responses
        if request.student_ids is not None:
            student_ids_set = set(request.student_ids)
            filtered_responses = [
                resp for resp in student_responses if resp.studentId in student_ids_set
            ]
            logger.info(
                f"Filtered to {len(filtered_responses)} students based on student_ids filter for quiz_id={request.quiz_id}"
            )

        # Create one student_job for each student
        sub_tasks: list[Signature] = []
        for response in filtered_responses:
            # Map to StudentPayload
            student_payload = _map_response_to_student_payload(
                response,
                questions,
                quiz_settings,
                question_ids_filter=request.question_ids,
            )

            # Create task signature
            sub_tasks.append(
                create_student_job_signature(
                    evaluation_id=evaluation_id,
                    quiz_id=request.quiz_id,
                    student_payload=student_payload,
                )
            )

        # This creates a 'group of groups'
        # The result of this can be tracked to know when the entire quiz is done.
        quiz_group_job = group(sub_tasks).apply_async()

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
