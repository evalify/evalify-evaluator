from .base import BaseEvaluator, EvaluatorResult, EvaluationFailedException
from ...core.schemas import QuestionPayload
from ...core.schemas.backend_api import MCQSolution, MCQStudentAnswer
from pydantic import ValidationError


class MCQEvaluator(BaseEvaluator):
    """Evaluates Multiple Choice Questions."""

    question_type = "MCQ"  # This is the registration key

    def evaluate(self, question_data: QuestionPayload) -> EvaluatorResult:
        """Evaluate MCQ by treating both answers as lists and comparing sets.

        - Coerces student and expected answers into lists (if not already)
        - Normalizes items by converting to lowercase trimmed strings
        - Uses set equality for all-or-nothing grading (order/duplicates ignored)
        """

        def to_normalized_list(value) -> list[str]:
            if value is None:
                return []

            # Accept list/tuple/set
            if isinstance(value, (list, tuple, set)):
                seq = list(value)
            # Wrap single string value in a list
            elif isinstance(value, str):
                seq = [value]
            else:
                # If it's still a dict (but not the wrapper we know), or some other type
                # we might want to log it but for now let's try to cast or fail
                raise EvaluationFailedException(
                    f"Invalid MCQ answer format: expected list/string, got {type(value).__name__}"
                    f" with value {value}"
                )

            return [str(x).lower().strip() for x in seq]

        # Validate Student Answer Schema
        try:
            student_ans_obj = MCQStudentAnswer.model_validate(
                question_data.student_answer
            )
            raw_student_answer = student_ans_obj.studentAnswer

        except ValidationError as e:
            raise EvaluationFailedException(f"Invalid Student Answer Schema: {e}")

        student_items = to_normalized_list(raw_student_answer)

        # Parse expected answer using strict schema
        try:
            # It might come as a dict (from Celery serialization) or object
            if isinstance(question_data.expected_answer, dict):
                solution = MCQSolution.model_validate(question_data.expected_answer)
            elif isinstance(question_data.expected_answer, MCQSolution):
                solution = question_data.expected_answer
            else:
                # Fallback for legacy/simple list format if needed, or fail strict
                # For now, let's assume strict schema usage but allow list if it matches old behavior
                if isinstance(question_data.expected_answer, (list, tuple, set, str)):
                    expected_items = to_normalized_list(question_data.expected_answer)
                    # Skip the rest
                    solution = None
                else:
                    raise ValueError(
                        f"Unknown expected answer type: {type(question_data.expected_answer)}"
                    )

            if solution:
                expected_items = [
                    opt.id for opt in solution.correctOptions if opt.isCorrect
                ]
                # Normalize them too just in case
                expected_items = [str(x).lower().strip() for x in expected_items]

        except Exception as e:
            raise EvaluationFailedException(f"Failed to parse MCQ expected answer: {e}")

        if not student_items:
            # Empty submission is not a failure, it's just incorrect (0 marks)
            return EvaluatorResult(score=0.0, feedback="No answer provided")

        is_correct = set(student_items) == set(expected_items)

        return EvaluatorResult(
            score=question_data.total_score if is_correct else 0.0,
            feedback="Correct" if is_correct else "Incorrect",
        )
