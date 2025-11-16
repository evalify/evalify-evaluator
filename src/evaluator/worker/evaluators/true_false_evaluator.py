from .base import BaseEvaluator, EvaluatorResult, EvaluationFailedException
from ...core.schemas import QuestionPayload


class TrueFalseEvaluator(BaseEvaluator):
    """Evaluates True/False Questions."""

    question_type = "TRUE_FALSE"  # This is the registration key

    def evaluate(self, question_data: QuestionPayload) -> EvaluatorResult:
        """Evaluate True/False question by comparing boolean values.

        Expected answer format: boolean (True/False)
        Student answer format: boolean (True/False) or string ("true"/"false", case-insensitive)
        """

        def normalize_boolean(value) -> bool:
            """Convert various formats to boolean."""
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                normalized = value.strip().lower()
                if normalized == "true":
                    return True
                elif normalized == "false":
                    return False
                else:
                    raise EvaluationFailedException(
                        f"Invalid True/False answer format: '{value}' - expected 'true' or 'false'"
                    )
            raise EvaluationFailedException(
                f"Invalid True/False answer type: expected bool/string, got {type(value).__name__}"
            )

        if question_data.student_answer is None:
            raise EvaluationFailedException("Student submission was empty.")

        try:
            student_value = normalize_boolean(question_data.student_answer)
            expected_value = normalize_boolean(question_data.expected_answer)
        except EvaluationFailedException:
            raise
        except Exception as e:
            raise EvaluationFailedException(f"Error normalizing True/False values: {e}")

        is_correct = student_value == expected_value

        return EvaluatorResult(
            score=question_data.total_score if is_correct else 0.0,
            feedback="Correct" if is_correct else "Incorrect",
        )
