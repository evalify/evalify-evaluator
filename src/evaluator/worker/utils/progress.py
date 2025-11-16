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
        self._backend = celery_app.backend

    def _key(self, quiz_id: str) -> str:
        return f"{self._KEY_PREFIX}{quiz_id}"

    def _store(self, quiz_id: str, data: Dict[str, Any]) -> None:
        status = data.get("status", "QUEUED")
        self._backend.store_result(self._key(quiz_id), data, status)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def initialize(
        self,
        quiz_id: str,
        evaluation_task_id: str,
        total_students: int,
    ) -> Dict[str, Any]:
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
        meta = self._backend.get_task_meta(self._key(quiz_id))
        result = meta.get("result") if meta else None
        if result is None:
            return None
        return result

    def update(self, quiz_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
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
        return self.update(quiz_id, status="RUNNING")

    def attach_group(self, quiz_id: str, group_id: str) -> Optional[Dict[str, Any]]:
        return self.update(quiz_id, group_id=group_id)

    def mark_failed(
        self, quiz_id: str, reason: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
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
        return self.update(quiz_id, status="COMPLETED")
