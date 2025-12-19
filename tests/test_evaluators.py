"""Pytest coverage for the evaluator implementations."""

from __future__ import annotations

from copy import deepcopy

import pytest

from evaluator.worker.evaluators.factory import EvaluatorFactory
from evaluator.core.schemas import QuestionPayload, EvaluatorContext
from evaluator.core.schemas.backend_api import (
    MCQStudentAnswer,
    TrueFalseStudentAnswer,
    MatchStudentAnswer,
    MatchStudentAnswerItem,
    QuizSettings,
)


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
        quiz_settings=_quiz_settings(),
    )


def _quiz_settings() -> QuizSettings:
    return QuizSettings(
        id="quiz-1",
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


def _context() -> EvaluatorContext:
    return EvaluatorContext(quiz_settings=_quiz_settings())


@pytest.fixture()
def mcq_evaluator():
    return EvaluatorFactory.get_evaluator("MCQ")


@pytest.fixture()
def true_false_evaluator():
    return EvaluatorFactory.get_evaluator("TRUE_FALSE")


@pytest.fixture()
def match_evaluator():
    return EvaluatorFactory.get_evaluator("MATCHING")


def test_mcq_evaluator_accepts_single_string_answer(mcq_evaluator):
    expected = ["opt-1"]
    question = _question(
        question_type="MCQ",
        student_answer=MCQStudentAnswer(studentAnswer="opt-1").model_dump(),
        expected_answer=expected,
        total_score=1.0,
    )

    result = mcq_evaluator.evaluate(question, _context())

    assert result.score == pytest.approx(1.0)
    assert result.feedback == "Correct"


def test_mcq_evaluator_flags_missing_options(mcq_evaluator):
    expected = ["opt-1", "opt-2"]
    question = _question(
        question_type="MCQ",
        student_answer=MCQStudentAnswer(studentAnswer="opt-1").model_dump(),
        expected_answer=expected,
        total_score=2.0,
    )

    result = mcq_evaluator.evaluate(question, _context())

    assert result.score == pytest.approx(0.0)
    assert result.feedback == "Incorrect"


def test_mcq_evaluator_accepts_string_answers(mcq_evaluator):
    question = _question(
        question_type="MCQ",
        student_answer=MCQStudentAnswer(studentAnswer="opt-1").model_dump(),
        expected_answer=["opt-1"],
        total_score=1.0,
    )

    result = mcq_evaluator.evaluate(question, _context())

    assert result.score == pytest.approx(1.0)
    assert result.feedback == "Correct"


def test_mcq_evaluator_rejects_invalid_schema(mcq_evaluator):
    question = _question(
        question_type="MCQ",
        student_answer={"answer": "opt-1"},  # missing studentAnswer key
        expected_answer=["opt-1"],
        total_score=1.0,
    )

    with pytest.raises(Exception):
        mcq_evaluator.evaluate(question, _context())


def test_true_false_evaluator_boolean_inputs(true_false_evaluator):
    question = _question(
        question_type="TRUE_FALSE",
        student_answer=TrueFalseStudentAnswer(studentAnswer=True).model_dump(),
        expected_answer={"trueFalseAnswer": True},
    )

    result = true_false_evaluator.evaluate(question, _context())

    assert result.score == pytest.approx(1.0)
    assert result.feedback == "Correct"


def test_true_false_evaluator_incorrect_answer(true_false_evaluator):
    question = _question(
        question_type="TRUE_FALSE",
        student_answer=TrueFalseStudentAnswer(studentAnswer=False).model_dump(),
        expected_answer={"trueFalseAnswer": True},
    )

    result = true_false_evaluator.evaluate(question, _context())

    assert result.score == pytest.approx(0.0)
    assert result.feedback == "Incorrect"


def test_true_false_evaluator_normalizes_strings(true_false_evaluator):
    question_true = _question(
        question_type="TRUE_FALSE",
        student_answer=TrueFalseStudentAnswer(studentAnswer="true").model_dump(),
        expected_answer={"trueFalseAnswer": True},
    )
    question_false = _question(
        question_type="TRUE_FALSE",
        student_answer=TrueFalseStudentAnswer(studentAnswer="FALSE").model_dump(),
        expected_answer={"trueFalseAnswer": False},
    )

    assert true_false_evaluator.evaluate(
        question_true, _context()
    ).score == pytest.approx(1.0)
    assert true_false_evaluator.evaluate(
        question_false, _context()
    ).score == pytest.approx(1.0)


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
        student_answer=MatchStudentAnswer(
            studentAnswer=[
                MatchStudentAnswerItem.model_validate(item).model_dump()
                for item in expected
            ]
        ).model_dump(),
        expected_answer=expected,
    )

    result = match_evaluator.evaluate(question, _context())

    assert result.score == pytest.approx(1.0)
    assert result.feedback == "Correct"


def test_match_evaluator_detects_wrong_pairs(match_evaluator):
    expected = _matching_options()
    student_answer = deepcopy(expected)
    student_answer[0]["matchPairIds"] = ["right-green"]

    question = _question(
        question_type="MATCHING",
        student_answer=MatchStudentAnswer(
            studentAnswer=[
                MatchStudentAnswerItem.model_validate(item).model_dump()
                for item in student_answer
            ]
        ).model_dump(),
        expected_answer=expected,
    )

    result = match_evaluator.evaluate(question, _context())

    assert result.score == pytest.approx(0.0)
    assert result.feedback == "Incorrect"


def test_match_evaluator_ignores_pair_order(match_evaluator):
    expected = _matching_options()
    student_answer = deepcopy(expected)
    student_answer[2]["matchPairIds"].reverse()

    question = _question(
        question_type="MATCHING",
        student_answer=MatchStudentAnswer(
            studentAnswer=[
                MatchStudentAnswerItem.model_validate(item).model_dump()
                for item in student_answer
            ]
        ).model_dump(),
        expected_answer=expected,
    )

    result = match_evaluator.evaluate(question, _context())

    assert result.score == pytest.approx(1.0)
    assert result.feedback == "Correct"
