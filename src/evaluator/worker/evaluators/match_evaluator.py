from .base import BaseEvaluator, EvaluatorResult, EvaluationFailedException
from ...core.schemas import QuestionPayload, EvaluatorContext
from ...core.schemas.backend_api import MatchingSolution, MatchStudentAnswer
from typing import Dict, Set
from pydantic import ValidationError


class MatchEvaluator(BaseEvaluator):
    """Evaluates Matching Questions."""

    question_type = "MATCHING"  # This is the registration key

    def evaluate(
        self, question_data: QuestionPayload, context: EvaluatorContext
    ) -> EvaluatorResult:
        """Evaluate Matching question by comparing match pairs.

        Expected answer format: MatchingSolution object/dict or List[Dict]
        Student answer format: List[Dict] with keys 'id' and 'matchPairIds'
        """

        def normalize_matching_pairs(value) -> Dict[str, Set[str]]:
            """
            Convert matching pairs list to a dictionary mapping left item IDs to sets of right item IDs.

            Args:
                value: List of dicts with 'id' and 'matchPairIds' keys

            Returns:
                Dict mapping left item ID to set of right item IDs
            """
            if not isinstance(value, list):
                raise EvaluationFailedException(
                    f"Invalid matching answer format: expected list, got {type(value).__name__}"
                )

            result = {}
            for item in value:
                if not isinstance(item, dict):
                    raise EvaluationFailedException(
                        f"Invalid matching item format: expected dict, got {type(item).__name__}"
                    )

                if "id" not in item or "matchPairIds" not in item:
                    raise EvaluationFailedException(
                        "Invalid matching item: missing 'id' or 'matchPairIds' key"
                    )

                item_id = item["id"]
                match_pair_ids = item["matchPairIds"]

                if not isinstance(match_pair_ids, list):
                    raise EvaluationFailedException(
                        f"Invalid matchPairIds format for item {item_id}: expected list, got {type(match_pair_ids).__name__}"
                    )

                # Convert to set for comparison (order doesn't matter)
                result[item_id] = set(match_pair_ids)

            return result

        if question_data.student_answer is None:
            return EvaluatorResult(score=0.0, feedback="No answer provided")

        try:
            # Validate Student Answer Schema
            try:
                student_ans_obj = MatchStudentAnswer.model_validate(
                    question_data.student_answer
                )
                # Convert Pydantic models to list of dicts for normalize_matching_pairs
                raw_student_answer = [
                    item.model_dump() for item in student_ans_obj.studentAnswer
                ]
            except ValidationError as e:
                raise EvaluationFailedException(f"Invalid Student Answer Schema: {e}")

            student_pairs = normalize_matching_pairs(raw_student_answer)

            # Parse expected answer using strict schema
            if isinstance(question_data.expected_answer, dict):
                solution = MatchingSolution.model_validate(
                    question_data.expected_answer
                )
                # Convert MatchingSolution to the list format normalize_matching_pairs expects
                expected_list = [opt.model_dump() for opt in solution.options]
                expected_pairs = normalize_matching_pairs(expected_list)
            elif isinstance(question_data.expected_answer, MatchingSolution):
                expected_list = [
                    opt.model_dump() for opt in question_data.expected_answer.options
                ]
                expected_pairs = normalize_matching_pairs(expected_list)
            else:
                # Fallback for direct list format
                expected_pairs = normalize_matching_pairs(question_data.expected_answer)

        except EvaluationFailedException:
            raise
        except Exception as e:
            raise EvaluationFailedException(f"Error normalizing matching pairs: {e}")

        # Check if all expected left items are present in student answer
        if set(expected_pairs.keys()) != set(student_pairs.keys()):
            raise EvaluationFailedException(
                "Student answer does not contain all required matching items"
            )

        # Compare each matching pair
        is_correct = all(
            student_pairs.get(item_id, set()) == expected_pairs[item_id]
            for item_id in expected_pairs
        )

        return EvaluatorResult(
            score=question_data.total_score if is_correct else 0.0,
            feedback="Correct" if is_correct else "Incorrect",
        )
