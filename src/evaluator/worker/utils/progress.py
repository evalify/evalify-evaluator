"""Utilities for storing and retrieving quiz evaluation progress via Celery's backend."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from celery.app.base import Celery

logger = logging.getLogger(__name__)


class EvaluationProgressStore:
    """Persists quiz-level evaluation progress in the Celery result backend."""

    _KEY_PREFIX = "quiz-progress::"

    def __init__(self, celery_app: Celery):
        """
        Create an EvaluationProgressStore bound to the provided Celery application's result backend.

        The instance will use the Celery app's backend to persist and retrieve quiz evaluation progress.
        """
        self._backend = celery_app.backend

    def _key(self, quiz_id: str) -> str:
        """
        Compose the backend storage key for a quiz.

        Parameters:
            quiz_id (str): Quiz identifier used to form the backend key.

        Returns:
            str: Backend key string combining the module key prefix and `quiz_id`.
        """
        return f"{self._KEY_PREFIX}{quiz_id}"

    def _store(self, quiz_id: str, data: Dict[str, Any]) -> None:
        """
        Persist the given progress payload in the Celery result backend under the quiz-specific key.

        Parameters:
                quiz_id (str): Quiz identifier used to construct the backend key.
                data (Dict[str, Any]): Payload to store; the 'status' field will be used if present, otherwise "QUEUED" is applied.
        """
        status = data.get("status", "QUEUED")
        self._backend.store_result(self._key(quiz_id), data, status)

    @staticmethod
    def _now_iso() -> str:
        """
        Return the current UTC time formatted as an ISO-8601 string.

        Returns:
            str: Current UTC time in ISO-8601 format with UTC offset (e.g., "2025-11-16T12:34:56+00:00").
        """
        return datetime.now(timezone.utc).isoformat()

    def initialize(
        self,
        quiz_id: str,
        evaluation_task_id: str,
        total_students: int,
    ) -> Dict[str, Any]:
        """
        Create and persist the initial progress record for a quiz evaluation.

        Parameters:
            quiz_id (str): Identifier of the quiz.
            evaluation_task_id (str): Celery task id that will track the evaluation.
            total_students (int): Total number of students to evaluate.

        Returns:
            Dict[str, Any]: The stored progress payload with keys "quiz_id", "evaluation_task_id", "group_id", "total_students", "status", "created_at", and "updated_at".
        """
        timestamp = self._now_iso()
        payload = {
            "quiz_id": quiz_id,
            "evaluation_task_id": evaluation_task_id,
            "group_id": None,
            "total_students": total_students,
            "status": "QUEUED",
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        self._store(quiz_id, payload)
        return payload

    def get(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches stored evaluation progress for the given quiz from the Celery result backend.

        Parameters:
            quiz_id (str): Identifier of the quiz whose progress to retrieve.

        Returns:
            Optional[Dict[str, Any]]: The stored progress payload as a dictionary, or `None` if no progress is stored.
        """
        meta = self._backend.get_task_meta(self._key(quiz_id))
        result = meta.get("result") if meta else None
        if result is None:
            return None
        return result

    def update(self, quiz_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
        """
        Merge provided fields into the existing progress record for a quiz and persist the updated payload.

        If no progress record exists for quiz_id, logs a warning and returns None. Ensures the payload has a "status" defaulting to "QUEUED" if not already set, updates "updated_at" to the provided value or the current UTC ISO timestamp, stores the result in the backend, and returns the updated payload.

        Parameters:
            quiz_id (str): Identifier of the quiz whose progress will be updated.
            **fields: Any: Arbitrary fields to merge into the existing payload. If "updated_at" is included it will be used; otherwise the current UTC ISO timestamp is set.

        Returns:
            dict | None: The updated payload dictionary if the record existed and was updated, `None` if no record was found.
        """
        payload = self.get(quiz_id)
        if payload is None:
            logger.warning(
                f"Attempted to update quiz_id={quiz_id}, but no metadata found in backend"
            )
            return None

        payload.update(fields)
        payload.setdefault("status", "QUEUED")
        payload["updated_at"] = fields.get("updated_at", self._now_iso())
        self._store(quiz_id, payload)
        return payload

    def mark_running(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        """
        Set the stored progress status for a quiz to "RUNNING".

        Returns:
            Optional[Dict[str, Any]]: The updated progress payload, or `None` if no existing record was found.
        """
        return self.update(quiz_id, status="RUNNING")

    def attach_group(self, quiz_id: str, group_id: str) -> Optional[Dict[str, Any]]:
        """
        Associate a Celery group identifier with the stored evaluation progress for a quiz.

        Parameters:
            quiz_id (str): Quiz identifier used to locate the progress record.
            group_id (str): Group identifier to attach to the progress payload.

        Returns:
            dict | None: The updated progress payload dictionary, or `None` if no existing record was found.
        """
        return self.update(quiz_id, group_id=group_id)

    def mark_failed(
        self, quiz_id: str, reason: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Mark a quiz evaluation as failed and optionally record a failure reason.

        Parameters:
            quiz_id (str): Identifier of the quiz whose progress should be marked failed.
            reason (Optional[str]): Optional human-readable reason for the failure; when provided it is saved into the payload under `failure_reason`.

        Returns:
            dict: The updated progress payload if an existing record was found and updated.
            None: If no existing progress payload was found for the given `quiz_id`.
        """
        payload = self.update(quiz_id, status="FAILED")
        if payload is None:
            logger.error(
                f"Failed to mark quiz_id={quiz_id} as FAILED: quiz metadata not found in backend"
            )
            return None

        if reason:
            payload["failure_reason"] = reason
            self._store(quiz_id, payload)
        return payload

    def mark_completed(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        """
        Mark the evaluation progress for a quiz as completed.

        Sets the stored progress status to "COMPLETED" and persists the updated payload.

        Returns:
            dict: The updated progress payload, or `None` if no existing progress was found.
        """
        return self.update(quiz_id, status="COMPLETED")
