# Evaluator Input Contracts

This document summarizes the **strict** request shapes expected by each evaluator. All payloads below are the `student_answer` and `expected_answer` parts of `QuestionPayload` as validated inside the evaluator.

> ✅ Use the Pydantic models from `evaluator.core.schemas.backend_api` to build these shapes in code (e.g., `MCQStudentAnswer(...).model_dump()`).

## MCQ Evaluator
- **Student answer schema**: `MCQStudentAnswer`
  - Shape: `{ "studentAnswer": "<option-id>" }`
  - Single-choice only. Lists belong to `MMCQ`.
- **Expected answer schema**: `MCQSolution` or a plain list of option IDs.
  - Preferred: `{ "data": { "correctOptions": [{"id": "opt1", "isCorrect": true}, ...] }, "version": <int> }`
  - Legacy tolerated: `["opt1", "opt2"]`
- **Failure modes**:
  - Missing `studentAnswer` key, non-string value, or list value ⇒ `EvaluationFailedException` (“Invalid Student Answer Schema”).

## MMCQ Evaluator
- **Student answer schema**: `MMCQStudentAnswer`
  - Shape: `{ "studentAnswer": ["<option-id>", ...] }`
- **Expected answer schema**: `MCQSolution` or a plain list of option IDs.
  - Preferred: `{ "correctOptions": [{"id": "opt1", "isCorrect": true}, ...] }`
  - Legacy tolerated: `["opt1", "opt2", "opt3"]`
- **Scoring**:
  - If any wrong option is selected, the answer is scored as incorrect and uses the quiz's MCQ negative-marking settings when configured.
  - If no wrong option is selected and all correct options are chosen, full marks are awarded.
  - If `mcqGlobalPartialMarking` is enabled and the answer is a strict subset of the correct options, marks are awarded proportionally across the correct options.
  - The current schema does **not** expose per-option weights for MMCQ, so proportional scores are split equally across correct options.
- **Failure modes**:
  - Missing `studentAnswer`, non-list payloads, or malformed expected answers ⇒ `EvaluationFailedException`.

## True/False Evaluator
- **Student answer schema**: `TrueFalseStudentAnswer`
  - Shape: `{ "studentAnswer": true | false | "true" | "false" }`
  - Strings are case-insensitive; coerced to boolean.
- **Expected answer schema**: `TrueFalseSolution` or raw boolean.
  - Preferred: `{ "data": { "trueFalseAnswer": true/false }, "version": <int> }`
  - Legacy tolerated: `true` / `false` (boolean) or "true" / "false" (string).
- **Failure modes**:
  - Missing `studentAnswer`, non-boolean/non-string types, or unparsable strings ⇒ `EvaluationFailedException`.

## Matching Evaluator
- **Student answer schema**: `MatchStudentAnswer`
  - Shape: `{ "studentAnswer": [ { "id": "left-id", "matchPairIds": ["right-id", ...] }, ... ] }`
  - Each item validated by `MatchStudentAnswerItem`.
- **Expected answer schema**: `MatchingSolution` or list of `{id, matchPairIds}`.
  - Preferred: `{ "data": { "options": [ { "id": "left-id", "matchPairIds": [...] }, ... ] }, "version": <int> }`
  - Legacy tolerated: direct list of items.
- **Failure modes**:
  - Missing `studentAnswer`, non-list top-level, items missing `id` or `matchPairIds`, or `matchPairIds` not a list ⇒ `EvaluationFailedException`.
  - Mismatched left-item sets between expected and student answers ⇒ `EvaluationFailedException` (“does not contain all required matching items”).

## Notes
- All evaluators rely on Pydantic validation; malformed schemas raise `EvaluationFailedException` and surface in the Feedback column of the results.
- For new evaluator types, prefer defining a dedicated `*StudentAnswer` model in `backend_api.py` and validating it inside the evaluator before normalization.
