"""Worker Evaluators Package for Evaluator

This package auto-registers evaluator implementations with the factory
via BaseEvaluator.__init_subclass__. To ensure registration happens on
import, we eagerly import the concrete evaluator modules here.
"""

# Eagerly import concrete evaluators so they register themselves
# with the EvaluatorFactory upon package import.
from . import mcq_evaluator  # noqa: F401  (imported for side effects)
