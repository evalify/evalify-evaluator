from .base import BaseEvaluator, EvaluatorResult, EvaluationFailedException
from ...core.schemas import QuestionPayload
from typing import Dict, Set


class MatchEvaluator(BaseEvaluator):
    """Evaluates Matching Questions."""

    question_type = "MATCHING"  # This is the registration key

    def evaluate(self, question_data: QuestionPayload) -> EvaluatorResult:
        """Evaluate Matching question by comparing match pairs.

        Expected answer format: List[Dict] with keys 'id' and 'matchPairIds'
        Example: [
            {"id": "left-item-1", "matchPairIds": ["right-item-1", "right-item-2"]},
            {"id": "left-item-2", "matchPairIds": ["right-item-3"]}
        ]

        Student answer format: Same as expected answer format
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
            raise EvaluationFailedException("Student submission was empty.")

        try:
            student_pairs = normalize_matching_pairs(question_data.student_answer)
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
