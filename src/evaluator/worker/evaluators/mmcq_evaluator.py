from __future__ import annotations

from pydantic import ValidationError

from .base import BaseEvaluator, EvaluationFailedException, EvaluatorResult
from ...core.schemas import EvaluatorContext, QuestionPayload
from ...core.schemas.backend_api import MCQSolution, MMCQStudentAnswer


class MMCQEvaluator(BaseEvaluator):
    """Evaluates multiple-select multiple choice questions."""

    question_type = "MMCQ"

    def evaluate(
        self, question_data: QuestionPayload, context: EvaluatorContext
    ) -> EvaluatorResult:
        """Evaluate MMCQ submissions with optional partial marking.

        Scoring rules:
        - Blank answer => 0
        - Any wrong selected option => 0 or configured negative score
        - No wrong options:
          - exact match => full marks
          - strict mode => 0 for incomplete subsets
          - partial mode => weighted sum of selected correct options

        The current backend schema does not expose per-option weightage for MMCQ
        correct options, so partial scores are distributed equally across the
        correct options.
        """

        student_items = self._parse_student_answer(question_data.student_answer)
        expected_items = self._parse_expected_answer(question_data.expected_answer)

        if not student_items:
            return EvaluatorResult(score=0.0, feedback="No answer provided")

        if not expected_items:
            raise EvaluationFailedException(
                "MMCQ expected answer has no correct options"
            )

        selected_options = set(student_items)
        correct_options = set(expected_items)
        wrong_selections = selected_options - correct_options

        if wrong_selections:
            return EvaluatorResult(
                score=self._incorrect_score(question_data, context),
                feedback="Incorrect",
            )

        if selected_options == correct_options:
            return EvaluatorResult(
                score=float(question_data.total_score),
                feedback="Correct",
            )

        if not context.quiz_settings.mcqGlobalPartialMarking:
            return EvaluatorResult(score=0.0, feedback="Incorrect")

        weight_per_option = float(question_data.total_score) / len(correct_options)
        partial_score = weight_per_option * len(selected_options)

        return EvaluatorResult(score=partial_score, feedback="Partially correct")

    def _parse_student_answer(self, student_answer: object) -> list[str]:
        try:
            answer = MMCQStudentAnswer.model_validate(student_answer)
        except ValidationError as exc:
            raise EvaluationFailedException(
                f"Invalid Student Answer Schema: {exc}"
            ) from exc

        return self._normalize_to_list(answer.studentAnswer)

    def _parse_expected_answer(self, expected_answer: object) -> list[str]:
        try:
            if isinstance(expected_answer, dict):
                solution = MCQSolution.model_validate(expected_answer)
                return self._normalize_to_list(
                    [
                        option.id
                        for option in solution.correctOptions
                        if option.isCorrect
                    ]
                )

            if isinstance(expected_answer, MCQSolution):
                return self._normalize_to_list(
                    [
                        option.id
                        for option in expected_answer.correctOptions
                        if option.isCorrect
                    ]
                )

            if isinstance(expected_answer, (list, tuple, set, str)):
                return self._normalize_to_list(expected_answer)
        except EvaluationFailedException:
            raise
        except Exception as exc:
            raise EvaluationFailedException(
                f"Failed to parse MMCQ expected answer: {exc}"
            ) from exc

        raise EvaluationFailedException(
            f"Invalid MMCQ expected answer format: {type(expected_answer).__name__}"
        )

    def _normalize_to_list(self, value: object) -> list[str]:
        if value is None:
            return []

        if isinstance(value, str):
            sequence = [value]
        elif isinstance(value, (list, tuple, set)):
            sequence = list(value)
        else:
            raise EvaluationFailedException(
                "Invalid MMCQ answer format: expected list/string, got "
                f"{type(value).__name__} with value {value}"
            )

        normalized: list[str] = []
        seen: set[str] = set()
        for item in sequence:
            normalized_item = str(item).strip().lower()
            if normalized_item and normalized_item not in seen:
                normalized.append(normalized_item)
                seen.add(normalized_item)
        return normalized

    def _incorrect_score(
        self, question_data: QuestionPayload, context: EvaluatorContext
    ) -> float:
        neg_percent = context.quiz_settings.mcqGlobalNegativePercent
        neg_mark = context.quiz_settings.mcqGlobalNegativeMark

        if neg_percent is not None:
            if not 0.0 <= float(neg_percent) <= 1.0:
                raise EvaluationFailedException(
                    "Invalid mcqGlobalNegativePercent: expected float in [0, 1], "
                    f"got {neg_percent}"
                )
            return -float(question_data.total_score) * float(neg_percent)

        if neg_mark is not None:
            return -float(neg_mark)

        return 0.0
