from .base import BaseEvaluator, EvaluatorResult, EvaluationFailedException
from ...core.schemas import QuestionPayload


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
                raise EvaluationFailedException(
                    f"Invalid MCQ answer format: expected list/string, got {type(value).__name__}"
                )

            return seq

        student_items = to_normalized_list(question_data.student_answer)
        expected_items = to_normalized_list(question_data.expected_answer)

        if not student_items:
            raise EvaluationFailedException("Student submission was empty.")

        is_correct = set(student_items) == set(expected_items)

        return EvaluatorResult(
            score=question_data.total_score if is_correct else 0.0,
            feedback="Correct" if is_correct else "Incorrect",
        )
