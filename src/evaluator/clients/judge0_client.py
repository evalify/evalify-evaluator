from __future__ import annotations

from typing import Any, Optional, Union

import httpx
from pydantic import BaseModel

from ..config import settings
from ..core.schemas.backend_api import CodingLanguage

TimeoutTypes = Union[float, httpx.Timeout, None]


class Judge0APIError(RuntimeError):
    """Raised when Judge0 returns an error or cannot be reached."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        payload: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


class Judge0SubmissionResult(BaseModel):
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    compile_output: Optional[str] = None
    message: Optional[str] = None
    status: dict[str, Any]
    time: Optional[str] = None
    memory: Optional[float] = None
    exit_code: Optional[int] = None


class Judge0Client:
    """Typed client for Judge0 code execution requests."""

    _LANGUAGE_IDS: dict[CodingLanguage, int] = {
        CodingLanguage.C: 50,
        CodingLanguage.CPP: 54,
        CodingLanguage.JAVA: 62,
        CodingLanguage.JAVASCRIPT: 63,
        CodingLanguage.OCTAVE: 64,
        CodingLanguage.PYTHON: 71,
        CodingLanguage.SCALA: 81,
    }

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        timeout: TimeoutTypes = 30.0,
        client: Optional[httpx.Client] = None,
    ) -> None:
        raw_base = (base_url or settings.judge_api).rstrip("/")
        if raw_base.startswith("http://") or raw_base.startswith("https://"):
            normalized_base = raw_base
        else:
            normalized_base = f"http://{raw_base}"

        self._client = client or httpx.Client(base_url=normalized_base, timeout=timeout)
        self._owns_client = client is None

    def __enter__(self) -> "Judge0Client":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def run_code(
        self,
        *,
        source_code: str,
        language: CodingLanguage | None = None,
        language_id: int | None = None,
        stdin: str = "",
        cpu_time_limit_seconds: Optional[float] = None,
        memory_limit_kb: Optional[int] = None,
    ) -> Judge0SubmissionResult:
        resolved_language_id = self._resolve_language_id(
            language=language,
            language_id=language_id,
        )

        payload: dict[str, Any] = {
            "source_code": source_code,
            "language_id": resolved_language_id,
            "stdin": stdin,
        }

        if cpu_time_limit_seconds is not None:
            payload["cpu_time_limit"] = cpu_time_limit_seconds
        if memory_limit_kb is not None:
            payload["memory_limit"] = memory_limit_kb

        try:
            response = self._client.post(
                "/submissions?base64_encoded=false&wait=true",
                json=payload,
            )
        except httpx.HTTPError as exc:  # pragma: no cover - network failure
            raise Judge0APIError(
                "Failed to reach Judge0", payload={"reason": str(exc)}
            ) from exc

        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = {"raw": response.text}
            raise Judge0APIError(
                "Judge0 returned an error",
                status_code=response.status_code,
                payload=payload,
            )

        return Judge0SubmissionResult.model_validate(response.json())

    def _resolve_language_id(
        self,
        *,
        language: CodingLanguage | None,
        language_id: int | None,
    ) -> int:
        if language_id is not None:
            return language_id

        if language is None:
            raise ValueError("Either language or language_id must be provided")

        resolved = self._LANGUAGE_IDS.get(language)
        if resolved is None:
            raise ValueError(f"No Judge0 language mapping configured for {language}")

        return resolved


if __name__ == "__main__":
    # Example usage
    import json

    with Judge0Client() as client:
        result = client.run_code(
            source_code="print(42)",
            language=CodingLanguage.PYTHON,
            cpu_time_limit_seconds=1.5,
            memory_limit_kb=65536,
        )
        print(json.dumps(result.model_dump(), indent=4))
