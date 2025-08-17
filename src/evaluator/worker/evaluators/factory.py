from typing import Dict, Type
from .base import BaseEvaluator

# The private registry. This will be populated automatically.
_EVALUATOR_REGISTRY: Dict[str, Type[BaseEvaluator]] = {}


def register_evaluator(question_type: str, evaluator_class: Type[BaseEvaluator]):
    """
    Called by BaseEvaluator's __init_subclass__ to register new evaluators.
    """
    if question_type in _EVALUATOR_REGISTRY:
        raise ValueError(f"Duplicate evaluator registered for type: {question_type}")
    _EVALUATOR_REGISTRY[question_type] = evaluator_class


class EvaluatorFactory:
    @staticmethod
    def get_evaluator(question_type: str) -> BaseEvaluator:
        """
        Retrieves an evaluator instance for the given question type.
        This is the main method the Celery task will call.
        """
        evaluator_class = _EVALUATOR_REGISTRY.get(question_type)
        if not evaluator_class:
            raise NotImplementedError(
                f"No evaluator implemented for question type: {question_type}"
            )
        return evaluator_class()  # Return an instance of the class
