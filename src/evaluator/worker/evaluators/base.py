from abc import ABC, abstractmethod
from ...core.schemas import QuestionPayload, EvaluatorResult, EvaluatorContext


class BaseEvaluator(ABC):
    """
    Abstract Base Class for all evaluation strategies.
    It includes the logic to auto-register any subclass with the factory.
    """

    question_type: str  # Each subclass MUST define its question type string

    def __init_subclass__(cls, **kwargs):
        """
        This special method is called when a class inherits from BaseEvaluator.
        It automatically registers the new evaluator class in the factory.
        """
        super().__init_subclass__(**kwargs)
        from .factory import (
            register_evaluator,
        )  # Local import to avoid circular dependency

        register_evaluator(cls.question_type, cls)

    @abstractmethod
    def evaluate(
        self, question_data: QuestionPayload, context: EvaluatorContext
    ) -> EvaluatorResult:
        """
        Executes the evaluation logic for a given question payload.

        Args:
            question_data: The Pydantic model containing all necessary data.
            context: Shared evaluation context (e.g., quiz-wide settings).

        Returns:
            An EvaluationResult object with the score and feedback.
        """
        pass


class EvaluationFailedException(Exception):
    """Custom exception for predictable business logic failures."""

    pass
