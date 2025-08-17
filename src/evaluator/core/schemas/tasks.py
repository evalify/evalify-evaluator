from pydantic import BaseModel, Field
from typing import List, Optional, Any
import uuid

# ==============================================================================
# 1. High Level Models
# ==============================================================================


class QuestionPayload(BaseModel):
    """
    Represents a single question to be evaluated, containing all
    necessary data for the worker to process it without further lookups.
    """

    question_id: str = Field(..., description="The unique identifier for the question.")
    question_type: str = Field(
        ..., description="The type of question (e.g., 'MCQ', 'DESCRIPTIVE', 'CODING')."
    )
    student_answer: Any = Field(
        ..., description="The student's submitted answer for this question."
    )
    expected_answer: Any = Field(
        ..., description="The correct or expected answer/rubric for this question."
    )
    grading_guidelines: Optional[str] = Field(
        None, description="Specific guidelines or rubrics for Descriptive evaluation."
    )
    total_score: float = Field(
        ..., description="The maximum possible score for this question."
    )


class StudentPayload(BaseModel):
    """
    Represents a single student and all their question submissions for the quiz.
    """

    student_id: str = Field(..., description="The unique identifier for the student.")
    questions: List[QuestionPayload] = Field(
        ..., description="A list of all questions and answers for this student."
    )


# ==============================================================================
# 2. Result Models
# ==============================================================================


class EvaluatorResult(BaseModel):
    """Standardized result object from any evaluator."""

    score: float
    feedback: Optional[str]


class QuestionEvaluationResult(BaseModel):
    """
    Represents the evaluation result for a single question.
    """

    question_id: str
    evaluated_result: Optional[EvaluatorResult]

    # Redundant Stuff
    quiz_id: str
    student_id: str

    # Job stuff
    job_id: uuid.UUID
    status: str  # "success" or "failed"


class StudentEvaluationResult(BaseModel):
    """
    Represents the aggregated evaluation result for a single student.
    """

    # Redundant keys
    quiz_id: str
    student_id: str  # The student_id
    aggregated_evaluation_results: List[QuestionEvaluationResult]


# ==============================================================================
# 3. Internal Data Level Models
# ==============================================================================


class TaskPayload(BaseModel):
    """
    The data payload sent to a Celery worker for a single, atomic task.
    """

    quiz_id: str  # For logging
    student_id: str  # The student_id
    question_data: QuestionPayload
