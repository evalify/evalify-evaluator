from __future__ import annotations

import httpx
import pytest

from evaluator.clients.judge0_client import Judge0APIError, Judge0Client
from evaluator.core.schemas.backend_api import CodingLanguage


class MockJudge0Transport:
    def __init__(self) -> None:
        self.last_request: httpx.Request | None = None

    def success(self, request: httpx.Request) -> httpx.Response:
        self.last_request = request
        return httpx.Response(
            200,
            json={
                "stdout": "42\n",
                "stderr": None,
                "compile_output": None,
                "message": None,
                "status": {"id": 3, "description": "Accepted"},
                "time": "0.001",
                "memory": 1234,
                "exit_code": 0,
            },
        )

    def failure(self, request: httpx.Request) -> httpx.Response:
        self.last_request = request
        return httpx.Response(422, json={"error": "bad submission"})


def test_judge0_client_normalizes_base_url_and_serializes_request():
    transport = MockJudge0Transport()
    with httpx.Client(
        base_url="http://localhost:2358",
        transport=httpx.MockTransport(transport.success),
    ) as httpx_client:
        client = Judge0Client(base_url="localhost:2358", client=httpx_client)
        result = client.run_code(
            source_code="print(42)",
            language=CodingLanguage.PYTHON,
            stdin="",
            cpu_time_limit_seconds=1.5,
            memory_limit_kb=65536,
        )

    assert result.stdout == "42\n"
    assert transport.last_request is not None
    assert transport.last_request.url.path == "/submissions"
    assert transport.last_request.url.query == b"base64_encoded=false&wait=true"


def test_judge0_client_raises_on_error_response():
    transport = MockJudge0Transport()
    with httpx.Client(
        base_url="http://localhost:2358",
        transport=httpx.MockTransport(transport.failure),
    ) as httpx_client:
        client = Judge0Client(base_url="localhost:2358", client=httpx_client)
        with pytest.raises(Judge0APIError) as excinfo:
            client.run_code(
                source_code="print(42)",
                language=CodingLanguage.PYTHON,
            )

    assert excinfo.value.status_code == 422
    assert excinfo.value.payload["error"] == "bad submission"


def test_judge0_client_still_accepts_explicit_language_id():
    transport = MockJudge0Transport()
    with httpx.Client(
        base_url="http://localhost:2358",
        transport=httpx.MockTransport(transport.success),
    ) as httpx_client:
        client = Judge0Client(base_url="localhost:2358", client=httpx_client)
        result = client.run_code(source_code="print(42)", language_id=71)

    assert result.stdout == "42\n"
