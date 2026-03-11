from __future__ import annotations

import re
from typing import Any

from pydantic import ValidationError

from .base import BaseEvaluator, EvaluationFailedException, EvaluatorResult
from ...core.schemas import EvaluatorContext, QuestionPayload
from ...core.schemas.backend_api import (
    BlankEvaluationType,
    FillBlankQuestionData,
    FillBlankSolution,
    FillBlankStudentAnswer,
)


class FillInTheBlankEvaluator(BaseEvaluator):
    """Evaluates Fill in the Blank questions."""

    question_type = "FILL_THE_BLANK"

    def evaluate(
        self, question_data: QuestionPayload, context: EvaluatorContext
    ) -> EvaluatorResult:
        """Evaluate FITB questions using strict or normal matching.

        Matching rules:
        - STRICT: remove whitespace, preserve case
        - NORMAL: remove whitespace, compare case-insensitively
        - HYBRID: not implemented yet; reserved for future LLM-based evaluation

        Scoring rules:
        - Each blank is scored independently.
        - If `blankWeights` is configured, matching blanks earn that weight.
        - Otherwise, marks are split equally across the expected blanks.
        """

        student_answers = self._parse_student_answer(question_data.student_answer)
        fitb_question_data = self._parse_question_data(question_data.question_data)
        solution = self._parse_expected_answer(question_data.expected_answer)

        evaluation_type = fitb_question_data.config.evaluationType
        if evaluation_type == BlankEvaluationType.HYBRID:
            raise EvaluationFailedException(
                "HYBRID Fill in the Blank evaluation is not implemented yet"
            )

        acceptable_answers = solution.acceptableAnswers
        if not acceptable_answers:
            raise EvaluationFailedException(
                "Fill in the Blank expected answer has no acceptable answers"
            )

        blank_weights = self._resolve_blank_weights(
            fitb_question_data,
            acceptable_answers.keys(),
            float(question_data.total_score),
        )

        score = 0.0
        matched_count = 0

        for blank_index, acceptable_answer in acceptable_answers.items():
            student_value = student_answers.get(blank_index)
            if student_value is None:
                continue

            if self._is_match(
                student_value=student_value,
                acceptable_values=acceptable_answer.answers,
                evaluation_type=evaluation_type,
            ):
                score += blank_weights[blank_index]
                matched_count += 1

        if matched_count == 0:
            return EvaluatorResult(score=0.0, feedback="Incorrect")

        if matched_count == len(acceptable_answers):
            return EvaluatorResult(score=score, feedback="Correct")

        return EvaluatorResult(score=score, feedback="Partially correct")

    def _parse_student_answer(self, student_answer: Any) -> dict[int, str]:
        try:
            answer = FillBlankStudentAnswer.model_validate(student_answer)
        except ValidationError as exc:
            raise EvaluationFailedException(
                f"Invalid Student Answer Schema: {exc}"
            ) from exc

        normalized_answers: dict[int, str] = {}
        for blank_index, value in answer.studentAnswer.items():
            normalized_answers[int(blank_index)] = "" if value is None else str(value)
        return normalized_answers

    def _parse_question_data(self, question_data: Any) -> FillBlankQuestionData:
        if question_data is None:
            raise EvaluationFailedException(
                "Fill in the Blank evaluator requires question_data with config"
            )

        try:
            if isinstance(question_data, FillBlankQuestionData):
                return question_data
            return FillBlankQuestionData.model_validate(question_data)
        except ValidationError as exc:
            raise EvaluationFailedException(
                f"Invalid FITB question data: {exc}"
            ) from exc

    def _parse_expected_answer(self, expected_answer: Any) -> FillBlankSolution:
        try:
            if isinstance(expected_answer, FillBlankSolution):
                return expected_answer
            return FillBlankSolution.model_validate(expected_answer)
        except ValidationError as exc:
            raise EvaluationFailedException(
                f"Failed to parse FITB expected answer: {exc}"
            ) from exc

    def _resolve_blank_weights(
        self,
        question_data: FillBlankQuestionData,
        blank_indexes,
        total_score: float,
    ) -> dict[int, float]:
        expected_indexes = {int(blank_index) for blank_index in blank_indexes}
        configured_weights = question_data.config.blankWeights or {}

        if configured_weights:
            missing = expected_indexes - {int(index) for index in configured_weights}
            if missing:
                raise EvaluationFailedException(
                    "Missing blank weights for blanks: "
                    + ", ".join(str(index) for index in sorted(missing))
                )

            return {
                int(blank_index): float(configured_weights[int(blank_index)])
                for blank_index in expected_indexes
            }

        if not expected_indexes:
            raise EvaluationFailedException("No blanks configured for FITB evaluation")

        equal_weight = total_score / len(expected_indexes)
        return {blank_index: equal_weight for blank_index in expected_indexes}

    def _is_match(
        self,
        *,
        student_value: str,
        acceptable_values: list[str],
        evaluation_type: BlankEvaluationType,
    ) -> bool:
        normalized_student = self._normalize_value(student_value, evaluation_type)
        normalized_acceptable = {
            self._normalize_value(value, evaluation_type) for value in acceptable_values
        }
        return normalized_student in normalized_acceptable

    def _normalize_value(self, value: str, evaluation_type: BlankEvaluationType) -> str:
        stripped = re.sub(r"\s+", "", str(value))

        if evaluation_type == BlankEvaluationType.STRICT:
            return stripped

        if evaluation_type == BlankEvaluationType.NORMAL:
            return stripped.lower()

        raise EvaluationFailedException(
            f"Unsupported FITB evaluation type: {evaluation_type}"
        )
