"""Pytest coverage for the evaluator implementations."""

from __future__ import annotations

from copy import deepcopy

import pytest

from evaluator.worker.evaluators.factory import EvaluatorFactory
from evaluator.core.schemas import QuestionPayload, EvaluatorContext
from evaluator.core.schemas.backend_api import (
    BlankAcceptableAnswer,
    BlankAnswerType,
    BlankEvaluationType,
    FillBlankConfig,
    FillBlankQuestionData,
    FillBlankSolution,
    FillBlankStudentAnswer,
    MCQStudentAnswer,
    MMCQStudentAnswer,
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
    question_data=None,
    total_score: float = 1.0,
    question_id: str = "question",
    quiz_settings: QuizSettings | None = None,
) -> QuestionPayload:
    """Helper to keep QuestionPayload construction consistent."""

    return QuestionPayload(
        question_id=question_id,
        question_type=question_type,
        student_answer=student_answer,
        expected_answer=expected_answer,
        question_data=question_data,
        grading_guidelines=None,
        total_score=total_score,
        quiz_settings=quiz_settings or _quiz_settings(),
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


def _context(*, quiz_settings: QuizSettings | None = None) -> EvaluatorContext:
    return EvaluatorContext(quiz_settings=quiz_settings or _quiz_settings())


@pytest.fixture()
def mcq_evaluator():
    return EvaluatorFactory.get_evaluator("MCQ")


@pytest.fixture()
def true_false_evaluator():
    return EvaluatorFactory.get_evaluator("TRUE_FALSE")


@pytest.fixture()
def mmcq_evaluator():
    return EvaluatorFactory.get_evaluator("MMCQ")


@pytest.fixture()
def match_evaluator():
    return EvaluatorFactory.get_evaluator("MATCHING")


@pytest.fixture()
def fitb_evaluator():
    return EvaluatorFactory.get_evaluator("FILL_THE_BLANK")


def _fitb_question_data(
    *,
    blank_count: int,
    evaluation_type: BlankEvaluationType,
    blank_weights: dict[int, float] | None = None,
) -> FillBlankQuestionData:
    return FillBlankQuestionData(
        config=FillBlankConfig(
            blankCount=blank_count,
            blankWeights=blank_weights,
            evaluationType=evaluation_type,
        )
    )


def _fitb_solution(acceptable_answers: dict[int, list[str]]) -> FillBlankSolution:
    return FillBlankSolution(
        acceptableAnswers={
            blank_index: BlankAcceptableAnswer(
                answers=answers,
                type=BlankAnswerType.TEXT,
            )
            for blank_index, answers in acceptable_answers.items()
        }
    )


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


def test_mcq_evaluator_applies_negative_percent_precedence(mcq_evaluator):
    settings = _quiz_settings().model_copy(
        update={"mcqGlobalNegativePercent": 0.5, "mcqGlobalNegativeMark": 1.0}
    )
    question = _question(
        question_type="MCQ",
        student_answer=MCQStudentAnswer(studentAnswer="opt-2").model_dump(),
        expected_answer=["opt-1"],
        total_score=2.0,
        quiz_settings=settings,
    )

    result = mcq_evaluator.evaluate(question, _context(quiz_settings=settings))

    assert result.score == pytest.approx(-1.0)  # 50% of 2 marks
    assert result.feedback == "Incorrect"


def test_mcq_evaluator_rejects_negative_percent_out_of_range(mcq_evaluator):
    settings = _quiz_settings().model_copy(update={"mcqGlobalNegativePercent": 1.5})
    question = _question(
        question_type="MCQ",
        student_answer=MCQStudentAnswer(studentAnswer="opt-2").model_dump(),
        expected_answer=["opt-1"],
        total_score=2.0,
        quiz_settings=settings,
    )

    with pytest.raises(Exception):
        mcq_evaluator.evaluate(question, _context(quiz_settings=settings))


def test_mcq_evaluator_applies_negative_mark_fallback(mcq_evaluator):
    settings = _quiz_settings().model_copy(
        update={"mcqGlobalNegativePercent": None, "mcqGlobalNegativeMark": 0.5}
    )
    question = _question(
        question_type="MCQ",
        student_answer=MCQStudentAnswer(studentAnswer="opt-2").model_dump(),
        expected_answer=["opt-1"],
        total_score=2.0,
        quiz_settings=settings,
    )

    result = mcq_evaluator.evaluate(question, _context(quiz_settings=settings))

    assert result.score == pytest.approx(-0.5)
    assert result.feedback == "Incorrect"


def test_mcq_evaluator_rejects_invalid_schema(mcq_evaluator):
    question = _question(
        question_type="MCQ",
        student_answer={"answer": "opt-1"},  # missing studentAnswer key
        expected_answer=["opt-1"],
        total_score=1.0,
    )

    with pytest.raises(Exception):
        mcq_evaluator.evaluate(question, _context())


def test_mmcq_evaluator_requires_exact_match_without_partial_marking(mmcq_evaluator):
    question = _question(
        question_type="MMCQ",
        student_answer=MMCQStudentAnswer(studentAnswer=["opt-1", "opt-2"]).model_dump(),
        expected_answer=["opt-1", "opt-2", "opt-3"],
        total_score=3.0,
    )

    result = mmcq_evaluator.evaluate(question, _context())

    assert result.score == pytest.approx(0.0)
    assert result.feedback == "Incorrect"


def test_mmcq_evaluator_supports_partial_marking_for_correct_subset(mmcq_evaluator):
    settings = _quiz_settings().model_copy(update={"mcqGlobalPartialMarking": True})
    question = _question(
        question_type="MMCQ",
        student_answer=MMCQStudentAnswer(studentAnswer=["opt-1", "opt-2"]).model_dump(),
        expected_answer=["opt-1", "opt-2", "opt-3", "opt-4"],
        total_score=8.0,
        quiz_settings=settings,
    )

    result = mmcq_evaluator.evaluate(question, _context(quiz_settings=settings))

    assert result.score == pytest.approx(4.0)
    assert result.feedback == "Partially correct"


def test_mmcq_evaluator_gives_full_marks_for_exact_match(mmcq_evaluator):
    question = _question(
        question_type="MMCQ",
        student_answer=MMCQStudentAnswer(studentAnswer=["opt-1", "opt-2"]).model_dump(),
        expected_answer=["opt-2", "opt-1"],
        total_score=2.0,
    )

    result = mmcq_evaluator.evaluate(question, _context())

    assert result.score == pytest.approx(2.0)
    assert result.feedback == "Correct"


def test_mmcq_evaluator_applies_negative_mark_when_wrong_option_selected(
    mmcq_evaluator,
):
    settings = _quiz_settings().model_copy(update={"mcqGlobalNegativeMark": 0.5})
    question = _question(
        question_type="MMCQ",
        student_answer=MMCQStudentAnswer(studentAnswer=["opt-1", "opt-4"]).model_dump(),
        expected_answer=["opt-1", "opt-2", "opt-3"],
        total_score=3.0,
        quiz_settings=settings,
    )

    result = mmcq_evaluator.evaluate(question, _context(quiz_settings=settings))

    assert result.score == pytest.approx(-0.5)
    assert result.feedback == "Incorrect"


def test_mmcq_evaluator_rejects_invalid_schema(mmcq_evaluator):
    question = _question(
        question_type="MMCQ",
        student_answer={"studentAnswer": "opt-1"},
        expected_answer=["opt-1", "opt-2"],
        total_score=2.0,
    )

    with pytest.raises(Exception):
        mmcq_evaluator.evaluate(question, _context())


def test_fitb_evaluator_strict_mode_is_case_sensitive(fitb_evaluator):
    question = _question(
        question_type="FILL_THE_BLANK",
        student_answer=FillBlankStudentAnswer(
            studentAnswer={0: "Wrapper"}
        ).model_dump(),
        expected_answer=_fitb_solution({0: ["wrapper"]}).model_dump(),
        question_data=_fitb_question_data(
            blank_count=1,
            evaluation_type=BlankEvaluationType.STRICT,
            blank_weights={0: 1.0},
        ).model_dump(),
        total_score=1.0,
    )

    result = fitb_evaluator.evaluate(question, _context())

    assert result.score == pytest.approx(0.0)
    assert result.feedback == "Incorrect"


def test_fitb_evaluator_strict_mode_strips_whitespace(fitb_evaluator):
    question = _question(
        question_type="FILL_THE_BLANK",
        student_answer=FillBlankStudentAnswer(studentAnswer={0: "wraps "}).model_dump(),
        expected_answer=_fitb_solution({0: ["wraps"]}).model_dump(),
        question_data=_fitb_question_data(
            blank_count=1,
            evaluation_type=BlankEvaluationType.STRICT,
            blank_weights={0: 2.0},
        ).model_dump(),
        total_score=2.0,
    )

    result = fitb_evaluator.evaluate(question, _context())

    assert result.score == pytest.approx(2.0)
    assert result.feedback == "Correct"


def test_fitb_evaluator_normal_mode_is_case_insensitive(fitb_evaluator):
    question = _question(
        question_type="FILL_THE_BLANK",
        student_answer=FillBlankStudentAnswer(
            studentAnswer={0: "Wrapper"}
        ).model_dump(),
        expected_answer=_fitb_solution({0: ["wrapper"]}).model_dump(),
        question_data=_fitb_question_data(
            blank_count=1,
            evaluation_type=BlankEvaluationType.NORMAL,
            blank_weights={0: 1.0},
        ).model_dump(),
        total_score=1.0,
    )

    result = fitb_evaluator.evaluate(question, _context())

    assert result.score == pytest.approx(1.0)
    assert result.feedback == "Correct"


def test_fitb_evaluator_uses_configured_blank_weights_for_partial_marking(
    fitb_evaluator,
):
    question = _question(
        question_type="FILL_THE_BLANK",
        student_answer=FillBlankStudentAnswer(
            studentAnswer={0: "typing", 1: "Function", 2: "nope"}
        ).model_dump(),
        expected_answer=_fitb_solution(
            {0: ["typing"], 1: ["function"], 2: ["5"], 3: ["Wrapper"]}
        ).model_dump(),
        question_data=_fitb_question_data(
            blank_count=4,
            evaluation_type=BlankEvaluationType.NORMAL,
            blank_weights={0: 0.5, 1: 0.25, 2: 0.15, 3: 0.1},
        ).model_dump(),
        total_score=1.0,
    )

    result = fitb_evaluator.evaluate(question, _context())

    assert result.score == pytest.approx(0.75)
    assert result.feedback == "Partially correct"


def test_fitb_evaluator_falls_back_to_equal_weights_when_missing(fitb_evaluator):
    question = _question(
        question_type="FILL_THE_BLANK",
        student_answer=FillBlankStudentAnswer(
            studentAnswer={0: "typing", 1: "function"}
        ).model_dump(),
        expected_answer=_fitb_solution(
            {0: ["typing"], 1: ["function"], 2: ["5"], 3: ["wrapper"]}
        ).model_dump(),
        question_data=_fitb_question_data(
            blank_count=4,
            evaluation_type=BlankEvaluationType.NORMAL,
        ).model_dump(),
        total_score=2.0,
    )

    result = fitb_evaluator.evaluate(question, _context())

    assert result.score == pytest.approx(1.0)
    assert result.feedback == "Partially correct"


def test_fitb_evaluator_rejects_hybrid_mode_for_now(fitb_evaluator):
    question = _question(
        question_type="FILL_THE_BLANK",
        student_answer=FillBlankStudentAnswer(studentAnswer={0: "typing"}).model_dump(),
        expected_answer=_fitb_solution({0: ["typing"]}).model_dump(),
        question_data=_fitb_question_data(
            blank_count=1,
            evaluation_type=BlankEvaluationType.HYBRID,
            blank_weights={0: 1.0},
        ).model_dump(),
        total_score=1.0,
    )

    with pytest.raises(Exception):
        fitb_evaluator.evaluate(question, _context())


def test_fitb_evaluator_rejects_invalid_student_schema(fitb_evaluator):
    question = _question(
        question_type="FILL_THE_BLANK",
        student_answer={"studentAnswer": ["typing"]},
        expected_answer=_fitb_solution({0: ["typing"]}).model_dump(),
        question_data=_fitb_question_data(
            blank_count=1,
            evaluation_type=BlankEvaluationType.NORMAL,
            blank_weights={0: 1.0},
        ).model_dump(),
        total_score=1.0,
    )

    with pytest.raises(Exception):
        fitb_evaluator.evaluate(question, _context())


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


def test_match_evaluator_accepts_dict_payload(match_evaluator):
    expected = _matching_options()
    # Backend may send matching answers as a dict: id -> matchPairIds
    student_answer_dict = {item["id"]: item["matchPairIds"] for item in expected}

    question = _question(
        question_type="MATCHING",
        student_answer=MatchStudentAnswer(
            studentAnswer=student_answer_dict
        ).model_dump(),
        expected_answer=expected,
    )

    result = match_evaluator.evaluate(question, _context())

    assert result.score == pytest.approx(1.0)
    assert result.feedback == "Correct"
