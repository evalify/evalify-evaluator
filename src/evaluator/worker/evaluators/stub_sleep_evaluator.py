"""Stub evaluator that simulates a slow grading pipeline."""

from __future__ import annotations

import time

from .base import BaseEvaluator, EvaluatorResult
from ...core.schemas import QuestionPayload


class StubSleepEvaluator(BaseEvaluator):
    """Evaluator that sleeps for five seconds and then awards full marks."""

    question_type = "STUB_SLEEP"

    def evaluate(self, question_data: QuestionPayload) -> EvaluatorResult:
        time.sleep(5)
        return EvaluatorResult(
            score=question_data.total_score,
            feedback="Stub evaluator awarded full marks after sleep",
        )
