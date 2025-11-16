from __future__ import annotations

from contextlib import contextmanager
from typing import cast

import httpx
import pytest

from evaluator.clients.backend_client import BackendAPIError, BackendEvaluationAPIClient
from evaluator.core.schemas.backend_api import MCQQuestionData

QUIZ_RESPONSE = {
    "quiz": {
        "id": "quiz-123",
        "name": "Midterm Examination",
        "description": "Comprehensive midterm exam",
        "instructions": "Answer all questions",
        "startTime": "2025-02-15T10:00:00Z",
        "endTime": "2025-02-15T12:00:00Z",
        "duration": "02:00:00",
        "password": "exam123",
        "fullScreen": True,
        "shuffleQuestions": True,
        "shuffleOptions": True,
        "linearQuiz": False,
        "calculator": False,
        "autoSubmit": True,
        "publishResult": False,
        "publishQuiz": True,
        "kioskMode": False,
        "createdById": "author-1",
        "created_at": "2025-02-01T09:00:00Z",
        "updated_at": "2025-02-10T09:15:00Z",
    }
}

QUIZ_QUESTIONS_RESPONSE = {
    "data": [
        {
            "questionId": "question-1",
            "orderIndex": 1,
            "id": "question-1",
            "type": "MCQ",
            "marks": 2,
            "negativeMarks": 0.5,
            "difficulty": "MEDIUM",
            "courseOutcome": "CO1",
            "bloomTaxonomyLevel": "UNDERSTAND",
            "question": "What is the capital of France?",
            "questionData": {
                "options": [
                    {"id": "opt1", "optionText": "Paris", "orderIndex": 1},
                    {"id": "opt2", "optionText": "London", "orderIndex": 2},
                ]
            },
            "explaination": "Paris is the capital city of France.",
            "solution": {"correctOptions": [{"id": "opt1", "isCorrect": True}]},
            "createdById": "author-1",
            "created_at": "2025-02-01T09:00:00Z",
            "updated_at": "2025-02-10T09:15:00Z",
        }
    ]
}

STUDENT_RESPONSE = {
    "response": {
        "quizId": "quiz-123",
        "studentId": "student-99",
        "startTime": "2025-02-15T10:00:00Z",
        "endTime": "2025-02-15T11:45:00Z",
        "submissionTime": "2025-02-15T11:45:30Z",
        "ip": ["192.168.1.100"],
        "duration": "01:45:30",
        "response": {"question-1": {"answer": "opt1"}},
        "score": 2.0,
        "violations": None,
        "isViolated": False,
        "submissionStatus": "SUBMITTED",
        "evaluationStatus": "EVALUATED",
        "created_at": "2025-02-15T10:00:00Z",
        "updated_at": "2025-02-15T11:50:00Z",
    }
}


class MockHTTPTransport:
    """Test fixture for mocking HTTP requests with predefined route responses."""

    def __init__(self):
        self.routes: dict[str, tuple[int, dict]] = {}
        self.last_request: httpx.Request | None = None

    def add(self, path: str, status_code: int, payload: dict) -> None:
        self.routes[path] = (status_code, payload)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.last_request = request
        if request.url.path not in self.routes:
            return httpx.Response(404, json={"error": "not found"})
        status, payload = self.routes[request.url.path]
        return httpx.Response(status, json=payload)


@contextmanager
def create_mock_backend_client(route_map: MockHTTPTransport):
    transport = httpx.MockTransport(route_map.handler)
    with httpx.Client(
        base_url="http://evalify.test", transport=transport
    ) as httpx_client:
        yield BackendEvaluationAPIClient(
            base_url="http://evalify.test",
            api_key="test-key",
            client=httpx_client,
        )


def test_get_quiz_details_and_questions():
    route_map = MockHTTPTransport()
    route_map.add("/api/eval/quiz/quiz-123", 200, QUIZ_RESPONSE)
    route_map.add("/api/eval/quiz/quiz-123/question", 200, QUIZ_QUESTIONS_RESPONSE)

    with create_mock_backend_client(route_map) as client:
        details = client.get_quiz_details("quiz-123")
        assert details.quiz.id == "quiz-123"
        assert route_map.last_request is not None
        assert route_map.last_request.headers.get("API_KEY") == "test-key"

        questions = client.get_quiz_questions("quiz-123")
        assert len(questions.data) == 1
        mcq = questions.data[0]
        assert mcq.question == "What is the capital of France?"
        mcq_data = cast(MCQQuestionData, mcq.questionData)
        assert mcq_data.options[0].optionText == "Paris"
        assert route_map.last_request is not None
        assert route_map.last_request.headers.get("API_KEY") == "test-key"


def test_get_student_response():
    route_map = MockHTTPTransport()
    route_map.add("/api/eval/quiz/quiz-123/student/student-99", 200, STUDENT_RESPONSE)

    with create_mock_backend_client(route_map) as client:
        response = client.get_student_quiz_response("quiz-123", "student-99")
        assert response.response.studentId == "student-99"
        assert response.response.score == 2.0
        assert route_map.last_request is not None
        assert route_map.last_request.headers.get("API_KEY") == "test-key"


def test_error_response_raises_backend_api_error():
    route_map = MockHTTPTransport()
    route_map.add("/api/eval/quiz/quiz-123", 500, {"error": "Failed", "status": 500})

    with create_mock_backend_client(route_map) as client:
        with pytest.raises(BackendAPIError) as excinfo:
            client.get_quiz_details("quiz-123")
        assert excinfo.value.status_code == 500
        assert excinfo.value.payload["error"] == "Failed"
        assert route_map.last_request is not None
        assert route_map.last_request.headers.get("API_KEY") == "test-key"
