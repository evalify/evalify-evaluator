from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


# ==============================================================================
# 1. API Request Models
# ==============================================================================


class EvaluationJobRequest(BaseModel):
    """
    The main request body for initiating a new evaluation job.
    This contains all the pre-fetched data required for the entire evaluation.
    """

    quiz_id: str = Field(
        ..., description="The unique identifier for the quiz being evaluated."
    )
    override_evaluated: bool = Field(
        False,
        description="If true, forces re-evaluation of submissions that already have a grade.",
    )
    student_ids: Optional[List[str]] = Field(
        None,
        description="Optional list of student IDs to evaluate. If provided, only these students will be evaluated.",
    )
    question_ids: Optional[List[str]] = Field(
        None,
        description="Optional list of question IDs to evaluate. If provided, only these questions will be evaluated for each student.",
    )


# ==============================================================================
# 2. API Response Models
# ==============================================================================


class EvaluationAcceptedResponse(BaseModel):
    """
    The response sent when an evaluation job is successfully accepted and queued.
    """

    quiz_id: str = Field(..., description="The quiz_id this evaluation corresponds to.")
    status: str = Field("QUEUED", description="The initial status of the evaluation.")
    progress_url: str = Field(..., description="The URL to poll for progress updates.")


class EvaluationProgressResponse(BaseModel):
    """
    The detailed progress report for an ongoing or completed evaluation.
    """

    quiz_id: str = Field(..., description="The quiz_id this evaluation corresponds to.")
    status: str = Field(
        ...,
        description="The overall status of the evaluation (e.g., 'QUEUED', 'RUNNING', 'COMPLETED', 'FAILED').",
    )
    students_finished: int = Field(
        ..., description="The number of students whose evaluations are complete."
    )
    total_students: int = Field(
        ..., description="The total number of students in this evaluation."
    )
    created_at: datetime = Field(
        ..., description="Timestamp (UTC) when the evaluation was created."
    )
    updated_at: datetime = Field(
        ..., description="Timestamp (UTC) when the evaluation status was last updated."
    )
