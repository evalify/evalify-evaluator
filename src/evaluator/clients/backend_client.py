from __future__ import annotations

from typing import Optional, Union

import httpx

from ..config import settings
from ..core.schemas.backend_api import (
    QuizDetailsResponse,
    QuizQuestionResponse,
    QuizQuestionsResponse,
    QuizResponsesResponse,
    QuizSettingsResponse,
    QuizStudentResponse,
)

TimeoutTypes = Union[float, httpx.Timeout, None]


class BackendAPIError(RuntimeError):
    """Raised when the Evalify backend evaluation API returns an error."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        payload: Optional[dict] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


class BackendEvaluationAPIClient:
    """Typed HTTP client for interacting with Evalify's /eval backend endpoints.

    This client manages an httpx.Client connection pool internally. To ensure proper
    resource cleanup, always use this client as a context manager:

    Example:
        >>> with BackendEvaluationAPIClient() as client:
        ...     quiz = client.get_quiz_details("quiz-id")

    Alternatively, call close() explicitly when done:
        >>> client = BackendEvaluationAPIClient()
        >>> try:
        ...     quiz = client.get_quiz_details("quiz-id")
        ... finally:
        ...     client.close()
    """

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: TimeoutTypes = 30.0,
        client: Optional[httpx.Client] = None,
    ) -> None:
        normalized_base = (base_url or settings.evalify_url).rstrip("/")
        self._api_key = api_key or settings.evaluation_service_api_key
        if not self._api_key:
            raise ValueError(
                "evaluation_service_api_key is required to call Evalify backend APIs"
            )

        self._client = client or httpx.Client(base_url=normalized_base, timeout=timeout)
        self._owns_client = client is None

    def __enter__(self) -> "BackendEvaluationAPIClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self) -> None:
        """Safety net to close the client if not explicitly closed.

        Note: Relying on __del__ is not recommended. Always use context manager
        or call close() explicitly to ensure timely resource cleanup.
        """
        if self._owns_client and hasattr(self, "_client"):
            try:
                self._client.close()
            except Exception:  # pragma: no cover
                pass  # Suppress exceptions during cleanup

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _request(self, method: str, url: str) -> httpx.Response:
        headers = {"API_KEY": self._api_key}
        try:
            response = self._client.request(method, url, headers=headers)
        except httpx.HTTPError as exc:  # pragma: no cover - network failure
            raise BackendAPIError(
                "Failed to reach Evalify backend", payload={"reason": str(exc)}
            ) from exc

        if response.status_code >= 400:
            message = response.text or "Evalify backend responded with an error"
            try:
                payload = response.json()
            except ValueError:
                payload = {"raw": response.text}
            raise BackendAPIError(
                message, status_code=response.status_code, payload=payload
            )

        return response

    def get_quiz_details(self, quiz_id: str) -> QuizDetailsResponse:
        """Retrieve complete details of a specific quiz.

        Args:
            quiz_id: The unique identifier (UUID) of the quiz.

        Returns:
            QuizDetailsResponse containing the full quiz configuration including
            name, description, timing, settings, and metadata.

        Raises:
            BackendAPIError: If the quiz is not found (404), the request fails,
                or the backend returns an error response.
        """
        response = self._request("GET", f"/eval/quiz/{quiz_id}")
        return QuizDetailsResponse.model_validate(response.json())

    def get_quiz_questions(self, quiz_id: str) -> QuizQuestionsResponse:
        """Retrieve all questions associated with a specific quiz in order.

        Args:
            quiz_id: The unique identifier (UUID) of the quiz.

        Returns:
            QuizQuestionsResponse containing a list of all questions with their
            full details including type, marks, difficulty, question data, and solutions.

        Raises:
            BackendAPIError: If the quiz is not found or the request fails.
        """
        response = self._request("GET", f"/eval/quiz/{quiz_id}/question")
        return QuizQuestionsResponse.model_validate(response.json())

    def get_quiz_question(self, quiz_id: str, question_id: str) -> QuizQuestionResponse:
        """Retrieve a single question from a quiz with full details.

        Args:
            quiz_id: The unique identifier (UUID) of the quiz.
            question_id: The unique identifier (UUID) of the question.

        Returns:
            QuizQuestionResponse containing the complete question details including
            type-specific question data, solution, marks, and metadata.

        Raises:
            BackendAPIError: If the quiz or question is not found (404),
                or the request fails.
        """
        response = self._request(
            "GET", f"/eval/quiz/{quiz_id}/question/{question_id}"
        )
        return QuizQuestionResponse.model_validate(response.json())

    def get_quiz_settings(self, quiz_id: str) -> QuizSettingsResponse:
        """Retrieve quiz settings/configuration.

        Args:
            quiz_id: The unique identifier (UUID) of the quiz.

        Returns:
            QuizSettingsResponse containing the quiz configuration.

        Raises:
            BackendAPIError: If the quiz settings are not found (404) or the request fails.
        """
        response = self._request("GET", f"/eval/quiz/{quiz_id}/settings")
        return QuizSettingsResponse.model_validate(response.json())

    def get_student_quiz_response(
        self, quiz_id: str, student_id: str
    ) -> QuizStudentResponse:
        """Retrieve the quiz response for a specific student.

        Args:
            quiz_id: The unique identifier (UUID) of the quiz.
            student_id: The unique identifier (UUID) of the student.

        Returns:
            QuizStudentResponse containing the student's submission including
            start/end times, answers, score, violations, and evaluation status.

        Raises:
            BackendAPIError: If the quiz or student response is not found (404),
                or the request fails.
        """
        response = self._request(
            "GET", f"/eval/quiz/{quiz_id}/student/{student_id}"
        )
        return QuizStudentResponse.model_validate(response.json())

    def get_quiz_responses(self, quiz_id: str) -> QuizResponsesResponse:
        """Retrieve all student responses for a specific quiz.

        Args:
            quiz_id: The unique identifier (UUID) of the quiz.

        Returns:
            QuizResponsesResponse containing a list of all student submissions
            for the quiz, including their answers, scores, and evaluation status.

        Raises:
            BackendAPIError: If the quiz is not found or the request fails.
        """
        response = self._request("GET", f"/eval/quiz/{quiz_id}/student")
        return QuizResponsesResponse.model_validate(response.json())
