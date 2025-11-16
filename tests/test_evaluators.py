"""Pytest coverage for the evaluator implementations."""

from __future__ import annotations

from copy import deepcopy

import pytest

from evaluator.worker.evaluators.factory import EvaluatorFactory
from evaluator.core.schemas import QuestionPayload


def _question(
    *,
    question_type: str,
    student_answer,
    expected_answer,
    total_score: float = 1.0,
    question_id: str = "question",
) -> QuestionPayload:
    """Helper to keep QuestionPayload construction consistent."""

    return QuestionPayload(
        question_id=question_id,
        question_type=question_type,
        student_answer=student_answer,
        expected_answer=expected_answer,
        grading_guidelines=None,
        total_score=total_score,
    )


@pytest.fixture()
def mcq_evaluator():
    return EvaluatorFactory.get_evaluator("MCQ")


@pytest.fixture()
def true_false_evaluator():
    return EvaluatorFactory.get_evaluator("TRUE_FALSE")


@pytest.fixture()
def match_evaluator():
    return EvaluatorFactory.get_evaluator("MATCHING")


def test_mcq_evaluator_accepts_unordered_answers(mcq_evaluator):
    expected = ["opt-1", "opt-2"]
    question = _question(
        question_type="MCQ",
        student_answer=["opt-2", "opt-1"],
        expected_answer=expected,
        total_score=2.0,
    )

    result = mcq_evaluator.evaluate(question)

    assert result.score == pytest.approx(2.0)
    assert result.feedback == "Correct"


def test_mcq_evaluator_flags_missing_options(mcq_evaluator):
    expected = ["opt-1", "opt-2"]
    question = _question(
        question_type="MCQ",
        student_answer=["opt-1"],
        expected_answer=expected,
        total_score=2.0,
    )

    result = mcq_evaluator.evaluate(question)

    assert result.score == pytest.approx(0.0)
    assert result.feedback == "Incorrect"


def test_mcq_evaluator_accepts_string_answers(mcq_evaluator):
    question = _question(
        question_type="MCQ",
        student_answer="opt-1",
        expected_answer=["opt-1"],
        total_score=1.0,
    )

    result = mcq_evaluator.evaluate(question)

    assert result.score == pytest.approx(1.0)
    assert result.feedback == "Correct"


def test_true_false_evaluator_boolean_inputs(true_false_evaluator):
    question = _question(
        question_type="TRUE_FALSE",
        student_answer=True,
        expected_answer=True,
    )

    result = true_false_evaluator.evaluate(question)

    assert result.score == pytest.approx(1.0)
    assert result.feedback == "Correct"


def test_true_false_evaluator_incorrect_answer(true_false_evaluator):
    question = _question(
        question_type="TRUE_FALSE",
        student_answer=False,
        expected_answer=True,
    )

    result = true_false_evaluator.evaluate(question)

    assert result.score == pytest.approx(0.0)
    assert result.feedback == "Incorrect"


def test_true_false_evaluator_normalizes_strings(true_false_evaluator):
    question_true = _question(
        question_type="TRUE_FALSE",
        student_answer="true",
        expected_answer=True,
    )
    question_false = _question(
        question_type="TRUE_FALSE",
        student_answer="FALSE",
        expected_answer=False,
    )

    assert true_false_evaluator.evaluate(question_true).score == pytest.approx(1.0)
    assert true_false_evaluator.evaluate(question_false).score == pytest.approx(1.0)


def _matching_options():
    return [
        {
            "id": "left-sky",
            "matchPairIds": ["right-blue"],
        },
        {
            "id": "left-grass",
            "matchPairIds": ["right-green"],
        },
        {
            "id": "left-ocean",
            "matchPairIds": [
                "right-blue",
                "right-green",
            ],
        },
        {"id": "right-blue", "matchPairIds": []},
        {"id": "right-green", "matchPairIds": []},
        {"id": "right-orange", "matchPairIds": []},
    ]


def test_match_evaluator_accepts_correct_pairs(match_evaluator):
    expected = _matching_options()
    question = _question(
        question_type="MATCHING",
        student_answer=deepcopy(expected),
        expected_answer=expected,
    )

    result = match_evaluator.evaluate(question)

    assert result.score == pytest.approx(1.0)
    assert result.feedback == "Correct"


def test_match_evaluator_detects_wrong_pairs(match_evaluator):
    expected = _matching_options()
    student_answer = deepcopy(expected)
    student_answer[0]["matchPairIds"] = ["right-green"]

    question = _question(
        question_type="MATCHING",
        student_answer=student_answer,
        expected_answer=expected,
    )

    result = match_evaluator.evaluate(question)

    assert result.score == pytest.approx(0.0)
    assert result.feedback == "Incorrect"


def test_match_evaluator_ignores_pair_order(match_evaluator):
    expected = _matching_options()
    student_answer = deepcopy(expected)
    student_answer[2]["matchPairIds"].reverse()

    question = _question(
        question_type="MATCHING",
        student_answer=student_answer,
        expected_answer=expected,
    )

    result = match_evaluator.evaluate(question)

    assert result.score == pytest.approx(1.0)
    assert result.feedback == "Correct"
