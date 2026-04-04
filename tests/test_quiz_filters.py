"""Tests for quiz evaluation filtering (student_ids and question_ids)."""

import pytest
from typing import List, Dict, Any

from evaluator.core.schemas.api import EvaluationJobRequest
from evaluator.core.schemas.backend_api import (
    QuizResponseRecord,
    QuizQuestion,
    SubmissionStatus,
    EvaluationStatus,
    MCQQuizQuestion,
    MCQQuestionData,
    MCQSolution,
    CorrectOption,
    QuestionOption,
    DataWrapper,
    QuizSettings,
)
from evaluator.worker.tasks.quiz import _map_response_to_student_payload


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def quiz_settings() -> QuizSettings:
    """Create a sample QuizSettings fixture."""
    return QuizSettings(
        id="settings-001",
        mcqGlobalPartialMarking=False,
        mcqGlobalNegativeMark=None,
        mcqGlobalNegativePercent=None,
        codingGlobalPartialMarking=False,
        llmEvaluationEnabled=False,
        llmProvider=None,
        llmModelName=None,
        fitbLlmSystemPrompt=None,
        descLlmSystemPrompt=None,
    )


def create_mcq_question(
    question_id: str, question_text: str = "Sample MCQ"
) -> MCQQuizQuestion:
    """Helper to create an MCQ question."""
    return MCQQuizQuestion(
        id=question_id,
        type="MCQ",
        marks=10.0,
        negativeMarks=0.0,
        question=question_text,
        questionData=DataWrapper(
            data=MCQQuestionData(
                options=[
                    QuestionOption(
                        id="opt-1",
                        optionText="Option A",
                        orderIndex=0,
                    ),
                    QuestionOption(
                        id="opt-2",
                        optionText="Option B",
                        orderIndex=1,
                    ),
                ],
            ),
            version=1,
        ),
        solution=DataWrapper(
            data=MCQSolution(
                correctOptions=[
                    CorrectOption(id="opt-1", isCorrect=True),
                ]
            ),
            version=1,
        ),
    )


def create_student_response(
    student_id: str, answers: Dict[str, Any]
) -> QuizResponseRecord:
    """Helper to create a student quiz response."""
    return QuizResponseRecord(
        quizId="quiz-001",
        studentId=student_id,
        response=answers,
        score=None,
        submissionStatus=SubmissionStatus.SUBMITTED,
        evaluationStatus=EvaluationStatus.NOT_EVALUATED,
    )


# ============================================================================
# Tests for _map_response_to_student_payload with question_ids_filter
# ============================================================================


class TestMapResponseWithQuestionFilter:
    """Test the _map_response_to_student_payload function with question filtering."""

    def test_no_filter_includes_all_questions(self, quiz_settings):
        """When question_ids_filter is None, all questions should be included."""
        # Arrange
        questions: List[QuizQuestion] = [
            create_mcq_question("q1", "Question 1"),
            create_mcq_question("q2", "Question 2"),
            create_mcq_question("q3", "Question 3"),
        ]
        student_response = create_student_response(
            "student-001", {"q1": "A", "q2": "B", "q3": "C"}
        )

        # Act
        result = _map_response_to_student_payload(
            student_response, questions, quiz_settings, question_ids_filter=None
        )

        # Assert
        assert result.student_id == "student-001"
        assert len(result.questions) == 3
        assert result.questions[0].question_id == "q1"
        assert result.questions[1].question_id == "q2"
        assert result.questions[2].question_id == "q3"

    def test_filter_includes_only_specified_questions(self, quiz_settings):
        """When question_ids_filter is provided, only those questions are included."""
        # Arrange
        questions: List[QuizQuestion] = [
            create_mcq_question("q1", "Question 1"),
            create_mcq_question("q2", "Question 2"),
            create_mcq_question("q3", "Question 3"),
        ]
        student_response = create_student_response(
            "student-001", {"q1": "A", "q2": "B", "q3": "C"}
        )

        # Act
        result = _map_response_to_student_payload(
            student_response,
            questions,
            quiz_settings,
            question_ids_filter=["q1", "q3"],
        )

        # Assert
        assert result.student_id == "student-001"
        assert len(result.questions) == 2
        assert result.questions[0].question_id == "q1"
        assert result.questions[1].question_id == "q3"

    def test_filter_with_single_question(self, quiz_settings):
        """Filter with a single question should return only that question."""
        # Arrange
        questions: List[QuizQuestion] = [
            create_mcq_question("q1", "Question 1"),
            create_mcq_question("q2", "Question 2"),
            create_mcq_question("q3", "Question 3"),
        ]
        student_response = create_student_response(
            "student-001", {"q1": "A", "q2": "B", "q3": "C"}
        )

        # Act
        result = _map_response_to_student_payload(
            student_response,
            questions,
            quiz_settings,
            question_ids_filter=["q2"],
        )

        # Assert
        assert len(result.questions) == 1
        assert result.questions[0].question_id == "q2"

    def test_filter_with_empty_list_returns_no_questions(self, quiz_settings):
        """Filter with empty list should return no questions."""
        # Arrange
        questions: List[QuizQuestion] = [
            create_mcq_question("q1", "Question 1"),
            create_mcq_question("q2", "Question 2"),
        ]
        student_response = create_student_response(
            "student-001", {"q1": "A", "q2": "B"}
        )

        # Act
        result = _map_response_to_student_payload(
            student_response,
            questions,
            quiz_settings,
            question_ids_filter=[],
        )

        # Assert
        assert len(result.questions) == 0

    def test_filter_with_nonexistent_question_id(self, quiz_settings):
        """Filter with nonexistent question ID should be skipped gracefully."""
        # Arrange
        questions: List[QuizQuestion] = [
            create_mcq_question("q1", "Question 1"),
            create_mcq_question("q2", "Question 2"),
        ]
        student_response = create_student_response(
            "student-001", {"q1": "A", "q2": "B"}
        )

        # Act
        result = _map_response_to_student_payload(
            student_response,
            questions,
            quiz_settings,
            question_ids_filter=["q1", "q99"],  # q99 doesn't exist
        )

        # Assert
        assert len(result.questions) == 1
        assert result.questions[0].question_id == "q1"

    def test_filter_preserves_question_data(self, quiz_settings):
        """Filtered questions should retain all their data."""
        # Arrange
        questions: List[QuizQuestion] = [
            create_mcq_question("q1", "Question 1"),
            create_mcq_question("q2", "Question 2"),
        ]
        student_response = create_student_response(
            "student-001", {"q1": "A", "q2": "B"}
        )

        # Act
        result = _map_response_to_student_payload(
            student_response,
            questions,
            quiz_settings,
            question_ids_filter=["q1"],
        )

        # Assert
        q_payload = result.questions[0]
        assert q_payload.question_id == "q1"
        assert q_payload.question_type == "MCQ"
        assert q_payload.student_answer == "A"
        assert q_payload.total_score == 10.0
        assert q_payload.quiz_settings == quiz_settings


# ============================================================================
# Tests for EvaluationJobRequest with filters
# ============================================================================


class TestEvaluationJobRequestFilters:
    """Test the EvaluationJobRequest model with filter fields."""

    def test_request_with_no_filters(self):
        """Request without filters should have None values."""
        # Act
        request = EvaluationJobRequest(
            quiz_id="quiz-001",
            override_evaluated=False,
        )

        # Assert
        assert request.quiz_id == "quiz-001"
        assert request.student_ids is None
        assert request.question_ids is None
        assert request.override_evaluated is False

    def test_request_with_student_ids_filter(self):
        """Request can be created with student_ids filter."""
        # Act
        request = EvaluationJobRequest(
            quiz_id="quiz-001",
            student_ids=["student-1", "student-2"],
            override_evaluated=False,
        )

        # Assert
        assert request.student_ids == ["student-1", "student-2"]
        assert request.question_ids is None

    def test_request_with_question_ids_filter(self):
        """Request can be created with question_ids filter."""
        # Act
        request = EvaluationJobRequest(
            quiz_id="quiz-001",
            question_ids=["q1", "q2", "q3"],
            override_evaluated=False,
        )

        # Assert
        assert request.question_ids == ["q1", "q2", "q3"]
        assert request.student_ids is None

    def test_request_with_both_filters(self):
        """Request can be created with both student_ids and question_ids filters."""
        # Act
        request = EvaluationJobRequest(
            quiz_id="quiz-001",
            student_ids=["student-1", "student-3"],
            question_ids=["q1", "q5"],
            override_evaluated=True,
        )

        # Assert
        assert request.student_ids == ["student-1", "student-3"]
        assert request.question_ids == ["q1", "q5"]
        assert request.override_evaluated is True

    def test_request_model_dump_includes_filters(self):
        """model_dump() should include filter fields."""
        # Arrange
        request = EvaluationJobRequest(
            quiz_id="quiz-001",
            student_ids=["student-1", "student-2"],
            question_ids=["q1", "q2"],
        )

        # Act
        dumped = request.model_dump()

        # Assert
        assert dumped["quiz_id"] == "quiz-001"
        assert dumped["student_ids"] == ["student-1", "student-2"]
        assert dumped["question_ids"] == ["q1", "q2"]

    def test_request_model_validate_from_dict(self):
        """model_validate() should accept filter fields."""
        # Arrange
        data = {
            "quiz_id": "quiz-001",
            "student_ids": ["student-1"],
            "question_ids": ["q1", "q2"],
        }

        # Act
        request = EvaluationJobRequest.model_validate(data)

        # Assert
        assert request.quiz_id == "quiz-001"
        assert request.student_ids == ["student-1"]
        assert request.question_ids == ["q1", "q2"]


# ============================================================================
# Integration Tests
# ============================================================================


class TestFilterIntegration:
    """Integration tests for filter behavior across components."""

    def test_question_filter_with_missing_student_answer(self, quiz_settings):
        """Filter should handle cases where student didn't answer a filtered question."""
        # Arrange
        questions: List[QuizQuestion] = [
            create_mcq_question("q1", "Question 1"),
            create_mcq_question("q2", "Question 2"),
            create_mcq_question("q3", "Question 3"),
        ]
        # Student only answered q1 and q3
        student_response = create_student_response(
            "student-001", {"q1": "A", "q3": "C"}
        )

        # Act
        result = _map_response_to_student_payload(
            student_response,
            questions,
            quiz_settings,
            question_ids_filter=["q1", "q2", "q3"],
        )

        # Assert
        assert len(result.questions) == 3
        assert result.questions[0].student_answer == "A"
        assert result.questions[1].student_answer is None  # Not answered
        assert result.questions[2].student_answer == "C"

    def test_question_filter_preserves_order(self, quiz_settings):
        """Filtered questions should maintain the original question list order."""
        # Arrange
        questions: List[QuizQuestion] = [
            create_mcq_question("q1", "Question 1"),
            create_mcq_question("q2", "Question 2"),
            create_mcq_question("q3", "Question 3"),
        ]
        student_response = create_student_response(
            "student-001", {"q1": "A", "q2": "B", "q3": "C"}
        )

        # Act - filter in different order than questions appear
        result = _map_response_to_student_payload(
            student_response,
            questions,
            quiz_settings,
            question_ids_filter=["q3", "q1"],
        )

        # Assert - should follow original question order, not filter order
        assert len(result.questions) == 2
        assert result.questions[0].question_id == "q1"
        assert result.questions[1].question_id == "q3"

    def test_multiple_students_with_question_filter(self, quiz_settings):
        """Filter should work consistently across different students."""
        # Arrange
        questions: List[QuizQuestion] = [
            create_mcq_question("q1", "Question 1"),
            create_mcq_question("q2", "Question 2"),
            create_mcq_question("q3", "Question 3"),
        ]
        student1 = create_student_response(
            "student-1", {"q1": "A", "q2": "B", "q3": "C"}
        )
        student2 = create_student_response(
            "student-2", {"q1": "B", "q2": "A", "q3": "B"}
        )

        question_filter = ["q1", "q3"]

        # Act
        result1 = _map_response_to_student_payload(
            student1, questions, quiz_settings, question_ids_filter=question_filter
        )
        result2 = _map_response_to_student_payload(
            student2, questions, quiz_settings, question_ids_filter=question_filter
        )

        # Assert - both students should have filtered questions
        assert len(result1.questions) == 2
        assert len(result2.questions) == 2
        assert result1.questions[0].question_id == "q1"
        assert result2.questions[0].question_id == "q1"
