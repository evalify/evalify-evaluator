from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from ...clients.judge0_client import Judge0APIError, Judge0Client
from ...core.schemas import EvaluatorContext, QuestionPayload
from ...core.schemas.backend_api import (
    CodingLanguage,
    CodingLanguageConfig,
    CodingQuestionData,
    CodingSolution,
    CodingSolutionLanguage,
    CodingStudentAnswer,
    CodingStudentSubmission,
)
from .base import BaseEvaluator, EvaluationFailedException, EvaluatorResult


@dataclass(frozen=True)
class _ExecutionArtifacts:
    language: CodingLanguage
    source_code: str
    language_config: CodingLanguageConfig
    reference_solution: str


class CodingEvaluator(BaseEvaluator):
    """Evaluates coding questions by running code against Judge0."""

    question_type = "CODING"

    def __init__(self, judge_client: Judge0Client | None = None) -> None:
        self._judge_client = judge_client or Judge0Client()
        self._owns_client = judge_client is None

    def __del__(self) -> None:
        if self._owns_client and hasattr(self, "_judge_client"):
            try:
                self._judge_client.close()
            except Exception:  # pragma: no cover
                pass

    def evaluate(
        self, question_data: QuestionPayload, context: EvaluatorContext
    ) -> EvaluatorResult:
        student_submission = self._parse_student_answer(question_data.student_answer)
        coding_question = self._parse_question_data(question_data.question_data)
        coding_solution = self._parse_expected_answer(question_data.expected_answer)
        execution = self._resolve_execution_artifacts(
            student_submission=student_submission,
            coding_question=coding_question,
            coding_solution=coding_solution,
        )

        testcase_weights = self._resolve_testcase_weights(
            coding_question=coding_question,
            total_score=float(question_data.total_score),
        )
        expected_output_by_id = {
            testcase.id: testcase.expectedOutput
            for testcase in coding_solution.testCases
        }

        passed = 0
        earned_score = 0.0
        total_cases = len(coding_question.testCases)

        for testcase in sorted(
            coding_question.testCases, key=lambda item: item.orderIndex
        ):
            if testcase.id not in expected_output_by_id:
                raise EvaluationFailedException(
                    f"Missing expected output for coding test case: {testcase.id}"
                )

            student_result = self._execute(
                source_code=execution.source_code,
                language=execution.language,
                stdin=testcase.input,
                time_limit_ms=coding_question.config.timeLimitMs,
                memory_limit_mb=coding_question.config.memoryLimitMb,
            )
            reference_result = self._execute(
                source_code=execution.reference_solution,
                language=execution.language,
                stdin=testcase.input,
                time_limit_ms=coding_question.config.timeLimitMs,
                memory_limit_mb=coding_question.config.memoryLimitMb,
            )

            reference_expected = expected_output_by_id[testcase.id]
            if not self._matches_expected(reference_result.stdout, reference_expected):
                raise EvaluationFailedException(
                    f"Reference solution output mismatch for test case {testcase.id}"
                )

            if self._matches_expected(student_result.stdout, reference_result.stdout):
                passed += 1
                earned_score += testcase_weights[testcase.id]

        if passed == 0:
            return EvaluatorResult(
                score=0.0,
                feedback=f"Passed 0/{total_cases} test cases",
            )

        if passed == total_cases:
            return EvaluatorResult(
                score=float(question_data.total_score),
                feedback=f"Passed {passed}/{total_cases} test cases",
            )

        if not context.quiz_settings.codingGlobalPartialMarking:
            return EvaluatorResult(
                score=0.0,
                feedback=f"Passed {passed}/{total_cases} test cases",
            )

        return EvaluatorResult(
            score=earned_score,
            feedback=f"Passed {passed}/{total_cases} test cases",
        )

    def _parse_student_answer(self, student_answer: Any) -> CodingStudentSubmission:
        try:
            answer = CodingStudentAnswer.model_validate(student_answer)
        except ValidationError as exc:
            raise EvaluationFailedException(
                f"Invalid Student Answer Schema: {exc}"
            ) from exc

        raw_answer = answer.studentAnswer
        if isinstance(raw_answer, str):
            if not raw_answer.strip():
                raise EvaluationFailedException("Coding submission is empty")
            return CodingStudentSubmission(code=raw_answer)

        if isinstance(raw_answer, CodingStudentSubmission):
            if not raw_answer.code.strip():
                raise EvaluationFailedException("Coding submission is empty")
            return raw_answer

        if isinstance(raw_answer, dict):
            normalized = dict(raw_answer)
            if "sourceCode" in normalized and "code" not in normalized:
                normalized["code"] = normalized.pop("sourceCode")
            try:
                submission = CodingStudentSubmission.model_validate(normalized)
            except ValidationError as exc:
                raise EvaluationFailedException(
                    f"Invalid Coding submission payload: {exc}"
                ) from exc

            if not submission.code.strip():
                raise EvaluationFailedException("Coding submission is empty")
            return submission

        raise EvaluationFailedException(
            f"Unsupported coding answer format: {type(raw_answer).__name__}"
        )

    def _parse_question_data(self, question_data: Any) -> CodingQuestionData:
        if question_data is None:
            raise EvaluationFailedException("Coding evaluator requires question_data")

        try:
            if isinstance(question_data, CodingQuestionData):
                return question_data
            return CodingQuestionData.model_validate(question_data)
        except ValidationError as exc:
            raise EvaluationFailedException(
                f"Invalid Coding question data: {exc}"
            ) from exc

    def _parse_expected_answer(self, expected_answer: Any) -> CodingSolution:
        try:
            if isinstance(expected_answer, CodingSolution):
                return expected_answer
            return CodingSolution.model_validate(expected_answer)
        except ValidationError as exc:
            raise EvaluationFailedException(
                f"Failed to parse Coding expected answer: {exc}"
            ) from exc

    def _resolve_execution_artifacts(
        self,
        *,
        student_submission: CodingStudentSubmission,
        coding_question: CodingQuestionData,
        coding_solution: CodingSolution,
    ) -> _ExecutionArtifacts:
        configured_languages = self._configured_languages(coding_question)
        solution_languages = self._solution_languages(
            coding_solution, configured_languages
        )

        if not configured_languages:
            raise EvaluationFailedException(
                "Coding question has no configured languages"
            )
        if not solution_languages:
            raise EvaluationFailedException(
                "Coding solution has no reference solutions"
            )

        language = student_submission.language
        if language is None:
            if len(configured_languages) == 1:
                language = next(iter(configured_languages))
            else:
                raise EvaluationFailedException(
                    "Coding submission must specify language when multiple languages are configured"
                )

        if language not in configured_languages:
            raise EvaluationFailedException(
                f"Unsupported coding language for this question: {language}"
            )
        if language not in solution_languages:
            raise EvaluationFailedException(
                f"Missing reference solution for language: {language}"
            )

        language_config = configured_languages[language]
        reference_solution = solution_languages[language].referenceSolution
        student_source = self._assemble_source_code(
            boilerplate_code=language_config.boilerplateCode,
            solution_code=student_submission.code,
            driver_code=language_config.driverCode,
        )
        reference_source = self._assemble_source_code(
            boilerplate_code=language_config.boilerplateCode,
            solution_code=reference_solution,
            driver_code=language_config.driverCode,
        )

        return _ExecutionArtifacts(
            language=language,
            source_code=student_source,
            language_config=language_config,
            reference_solution=reference_source,
        )

    def _configured_languages(
        self, coding_question: CodingQuestionData
    ) -> dict[CodingLanguage, CodingLanguageConfig]:
        config = coding_question.config

        if config.languages:
            return {entry.language: entry for entry in config.languages}

        if config.language is not None:
            return {
                config.language: CodingLanguageConfig(
                    language=config.language,
                    boilerplateCode=config.boilerplateCode,
                    driverCode=config.driverCode,
                    lockedLines=config.lockedLines,
                    allowNewLines=config.allowNewLines,
                )
            }

        return {}

    def _solution_languages(
        self,
        coding_solution: CodingSolution,
        configured_languages: dict[CodingLanguage, CodingLanguageConfig],
    ) -> dict[CodingLanguage, CodingSolutionLanguage]:
        if coding_solution.languages:
            return {entry.language: entry for entry in coding_solution.languages}

        if coding_solution.referenceSolution is not None:
            if len(configured_languages) != 1:
                raise EvaluationFailedException(
                    "Legacy coding referenceSolution requires exactly one configured language"
                )

            only_language = next(iter(configured_languages))
            return {
                only_language: CodingSolutionLanguage(
                    language=only_language,
                    referenceSolution=coding_solution.referenceSolution,
                )
            }

        return {}

    def _assemble_source_code(
        self,
        *,
        boilerplate_code: str | None,
        solution_code: str,
        driver_code: str | None,
    ) -> str:
        parts = [
            part for part in [boilerplate_code, solution_code, driver_code] if part
        ]
        return "\n".join(parts)

    def _resolve_testcase_weights(
        self, *, coding_question: CodingQuestionData, total_score: float
    ) -> dict[str, float]:
        if not coding_question.testCases:
            raise EvaluationFailedException("Coding question has no test cases")

        if any(
            testcase.marksWeightage is not None
            for testcase in coding_question.testCases
        ):
            missing = [
                testcase.id
                for testcase in coding_question.testCases
                if testcase.marksWeightage is None
            ]
            if missing:
                raise EvaluationFailedException(
                    "Missing testcase weights for test cases: " + ", ".join(missing)
                )
            return {
                testcase.id: float(testcase.marksWeightage)
                for testcase in coding_question.testCases
            }

        equal_weight = total_score / len(coding_question.testCases)
        return {testcase.id: equal_weight for testcase in coding_question.testCases}

    def _execute(
        self,
        *,
        source_code: str,
        language: CodingLanguage,
        stdin: str,
        time_limit_ms: int | None,
        memory_limit_mb: int | None,
    ):
        try:
            result = self._judge_client.run_code(
                source_code=source_code,
                language=language,
                stdin=stdin,
                cpu_time_limit_seconds=(time_limit_ms / 1000.0)
                if time_limit_ms
                else None,
                memory_limit_kb=(memory_limit_mb * 1024) if memory_limit_mb else None,
            )
        except Judge0APIError as exc:
            raise EvaluationFailedException(f"Judge0 execution failed: {exc}") from exc

        status_id = result.status.get("id")
        if status_id != 3:
            details = (
                result.stderr
                or result.compile_output
                or result.message
                or result.status.get("description", "Unknown Judge0 error")
            )
            raise EvaluationFailedException(f"Code execution failed: {details}")

        return result

    def _matches_expected(self, actual: str | None, expected: str | None) -> bool:
        return self._normalize_output(actual) == self._normalize_output(expected)

    def _normalize_output(self, value: str | None) -> str:
        if value is None:
            return ""
        return value.replace("\r\n", "\n").strip()
