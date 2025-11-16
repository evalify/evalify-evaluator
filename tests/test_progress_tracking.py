from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Generator, List, Tuple

import pytest
from fastapi.testclient import TestClient

from evaluator.main import app
from evaluator.api.routers import evaluation as evaluation_module

UTC = timezone.utc


class DummyChildResult:
    def __init__(
        self, ready: bool, failed: bool = False, date_done: datetime | None = None
    ):
        """
        Initialize a DummyChildResult representing a child task's completion state.

        Parameters:
            ready (bool): Whether the child task is marked ready (completed).
            failed (bool): Whether the child task has failed. Defaults to False.
            date_done (datetime | None): Timestamp when the child task completed or failed; None if unknown.
        """
        self._ready = ready
        self._failed = failed
        self.date_done = date_done

    def ready(self) -> bool:  # pragma: no cover - trivial
        """
        Indicates whether this child task has finished processing.

        Returns:
            True if the child task is ready, False otherwise.
        """
        return self._ready

    def failed(self) -> bool:  # pragma: no cover - trivial
        """
        Indicates whether the async result represents a failed task.

        Returns:
            `true` if the task failed, `false` otherwise.
        """
        return self._failed


class DummyGroupResult:
    def __init__(self, children: List[DummyChildResult]):
        """
        Initialize the group result with the provided child results.

        Parameters:
            children (List[DummyChildResult]): List of child task results to store on the instance as `results`.
        """
        self.results = children

    def ready(self) -> bool:
        """
        Indicates whether every child result in this group is ready.

        Returns:
            `true` if every child result is ready, `false` otherwise.
        """
        return all(child.ready() for child in self.results)


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """
    Provide a TestClient connected to the FastAPI application for use in tests.

    Returns:
        test_client (TestClient): A TestClient instance configured for the application.
    """
    with TestClient(app) as test_client:
        yield test_client


def _configure_progress_store(
    monkeypatch: pytest.MonkeyPatch, metadata: Dict[str, Any]
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Create an in-test fake progress store from `metadata`, patch it into evaluation_module using `monkeypatch`, and return the live store and a record of updates.

    Parameters:
        metadata (Dict[str, Any]): Initial metadata used to populate the fake progress store; the returned store is a mutable copy of this dictionary.

    Returns:
        Tuple[Dict[str, Any], List[Dict[str, Any]]]: A tuple where the first element is the live stored metadata dictionary (updated in-place by the fake store) and the second element is a list of update dictionaries recorded by calls to the fake update function.
    """
    stored_metadata = metadata.copy()
    updates: List[Dict[str, Any]] = []

    def fake_get(quiz_id: str) -> Dict[str, Any]:
        """
        Return the preconfigured metadata for the requested quiz id used by tests.

        Parameters:
            quiz_id (str): Quiz identifier to fetch; must match the internally stored metadata's "quiz_id".

        Returns:
            Dict[str, Any]: The stored metadata dictionary.

        Raises:
            AssertionError: If `quiz_id` does not equal the stored metadata's "quiz_id".
        """
        assert quiz_id == stored_metadata["quiz_id"]
        return stored_metadata

    def fake_update(quiz_id: str, **fields: Any) -> Dict[str, Any]:
        """
        Update the in-test stored metadata with provided fields and record the update.

        Parameters:
            quiz_id (str): Expected quiz identifier; must match stored_metadata["quiz_id"].
            **fields: Any: Key-value pairs to merge into the stored metadata.

        Returns:
            Dict[str, Any]: The updated stored metadata dictionary.

        Raises:
            AssertionError: If `quiz_id` does not match stored_metadata["quiz_id"].

        Side effects:
            - Mutates `stored_metadata` by applying `fields`.
            - Appends `fields` to the `updates` list.
        """
        assert quiz_id == stored_metadata["quiz_id"]
        stored_metadata.update(fields)
        updates.append(fields)
        return stored_metadata

    monkeypatch.setattr(evaluation_module.progress_store, "get", fake_get)
    monkeypatch.setattr(evaluation_module.progress_store, "update", fake_update)
    return stored_metadata, updates


def _patch_group_result(
    monkeypatch: pytest.MonkeyPatch, dummy_group: DummyGroupResult | None
) -> None:
    """
    Patch evaluation_module.GroupResult with a stub whose restore() returns the provided dummy_group.

    Parameters:
        monkeypatch (pytest.MonkeyPatch): Fixture used to replace attributes on modules during tests.
        dummy_group (DummyGroupResult | None): Value to be returned by the stub's restore(group_id, app) call.
    """

    class _GroupResultStub:
        @staticmethod
        def restore(group_id: str, app=None):  # pragma: no cover - called via API
            return dummy_group

    monkeypatch.setattr(evaluation_module, "GroupResult", _GroupResultStub)


def _patch_async_result(
    monkeypatch: pytest.MonkeyPatch,
    failed: bool = False,
    date_done: datetime | None = None,
) -> None:
    """
    Replace evaluation_module.AsyncResult with a test stub that simulates task completion.

    Parameters:
        monkeypatch (pytest.MonkeyPatch): MonkeyPatch fixture used to set the replacement.
        failed (bool): Whether the stubbed task reports failure when queried.
        date_done (datetime | None): Timestamp to expose as the task's completion time.
    """

    class _AsyncResultStub:
        def __init__(self, task_id: str, app=None):
            self.id = task_id
            self._failed = failed
            self.date_done = date_done

        def failed(self) -> bool:  # pragma: no cover - trivial
            return self._failed

    monkeypatch.setattr(evaluation_module, "AsyncResult", _AsyncResultStub)


def _base_metadata(
    quiz_id: str, status: str = "QUEUED", total_students: int = 0
) -> Dict[str, Any]:
    """
    Create a baseline metadata dictionary for an evaluation quiz.

    Parameters:
        quiz_id (str): Unique identifier for the quiz; used to build `group_id` and `evaluation_task_id`.
        status (str): Initial evaluation status (default: "QUEUED").
        total_students (int): Initial total number of students for the quiz (default: 0).

    Returns:
        dict: Metadata containing the following keys:
            - `quiz_id`: the provided quiz identifier.
            - `status`: the provided status.
            - `created_at`: ISO 8601 UTC timestamp for creation (fixed to 2025-01-01).
            - `updated_at`: ISO 8601 UTC timestamp for last update (same as `created_at`).
            - `total_students`: the provided total students count.
            - `group_id`: generated as "group-{quiz_id}".
            - `evaluation_task_id`: generated as "task-{quiz_id}".
    """
    timestamp = datetime(2025, 1, 1, tzinfo=UTC).isoformat()
    return {
        "quiz_id": quiz_id,
        "status": status,
        "created_at": timestamp,
        "updated_at": timestamp,
        "total_students": total_students,
        "group_id": f"group-{quiz_id}",
        "evaluation_task_id": f"task-{quiz_id}",
    }


def test_progress_reports_running_when_only_some_students_finished(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    metadata = _base_metadata("quiz-running", total_students=0)
    stored_metadata, updates = _configure_progress_store(monkeypatch, metadata)

    done_time = datetime.now(tz=UTC)
    dummy_group = DummyGroupResult(
        [
            DummyChildResult(ready=True, failed=False, date_done=done_time),
            DummyChildResult(ready=False, failed=False, date_done=None),
        ]
    )

    _patch_group_result(monkeypatch, dummy_group)
    _patch_async_result(monkeypatch, failed=False)

    response = client.get("/api/v1/evaluations/quiz-running/progress")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "RUNNING"
    assert body["students_finished"] == 1
    assert body["total_students"] == 2  # derived from group result length
    assert stored_metadata["status"] == "RUNNING"
    assert any("status" in update for update in updates)


def test_progress_marks_completed_when_all_students_ready(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    metadata = _base_metadata("quiz-complete", total_students=2)
    stored_metadata, _ = _configure_progress_store(monkeypatch, metadata)

    earlier = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
    latest = earlier + timedelta(seconds=30)
    dummy_group = DummyGroupResult(
        [
            DummyChildResult(True, False, earlier),
            DummyChildResult(True, False, latest),
        ]
    )

    _patch_group_result(monkeypatch, dummy_group)
    _patch_async_result(monkeypatch, failed=False, date_done=latest)

    response = client.get("/api/v1/evaluations/quiz-complete/progress")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["students_finished"] == 2
    assert body["total_students"] == 2
    returned_updated = body["updated_at"].replace("Z", "+00:00")
    assert datetime.fromisoformat(returned_updated) == latest
    assert stored_metadata["status"] == "COMPLETED"


def test_progress_marks_failed_when_any_student_task_failed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    """
    Verify the progress endpoint marks an evaluation as FAILED when any student task has failed.

    Sets up metadata for a two-student quiz where one child task reports failure and asserts that the endpoint returns status "FAILED", reports two students finished, and persists the status change in metadata.
    """
    metadata = _base_metadata("quiz-failed", total_students=2)
    stored_metadata, _ = _configure_progress_store(monkeypatch, metadata)

    fail_time = datetime(2025, 1, 2, tzinfo=UTC)
    dummy_group = DummyGroupResult(
        [
            DummyChildResult(True, True, fail_time),
            DummyChildResult(True, False, fail_time),
        ]
    )

    _patch_group_result(monkeypatch, dummy_group)
    _patch_async_result(monkeypatch, failed=False)

    response = client.get("/api/v1/evaluations/quiz-failed/progress")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "FAILED"
    assert body["students_finished"] == 2
    assert stored_metadata["status"] == "FAILED"


def test_progress_marks_failed_when_quiz_task_fails_without_group(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    """
    Verifies that the progress endpoint marks a quiz as FAILED when the quiz-level task fails and no group result is present.

    Sends a request for a quiz with group_id set to None and a simulated failing AsyncResult, then asserts:
    - HTTP 200 response
    - reported status is "FAILED"
    - reported students_finished is 0
    - persisted metadata status is updated to "FAILED"
    """
    metadata = _base_metadata("quiz-task-failed", total_students=3)
    metadata["group_id"] = None
    stored_metadata, _ = _configure_progress_store(monkeypatch, metadata)

    failure_time = datetime(2025, 1, 3, 0, 0, tzinfo=UTC)
    _patch_group_result(monkeypatch, dummy_group=None)
    _patch_async_result(monkeypatch, failed=True, date_done=failure_time)

    response = client.get("/api/v1/evaluations/quiz-task-failed/progress")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "FAILED"
    assert body["students_finished"] == 0
    assert stored_metadata["status"] == "FAILED"


def test_progress_returns_404_when_no_metadata(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(evaluation_module.progress_store, "get", lambda quiz_id: None)
    response = client.get("/api/v1/evaluations/unknown/progress")
    assert response.status_code == 404


def test_progress_corrects_total_students_in_metadata_when_zero(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    """Test that when total_students=0 initially, it's corrected from group results and persisted."""
    metadata = _base_metadata("quiz-total-correction", total_students=0)
    stored_metadata, updates = _configure_progress_store(monkeypatch, metadata)

    done_time = datetime.now(tz=UTC)
    dummy_group = DummyGroupResult(
        [
            DummyChildResult(ready=True, failed=False, date_done=done_time),
            DummyChildResult(ready=True, failed=False, date_done=done_time),
            DummyChildResult(ready=False, failed=False, date_done=None),
        ]
    )

    _patch_group_result(monkeypatch, dummy_group)
    _patch_async_result(monkeypatch, failed=False)

    response = client.get("/api/v1/evaluations/quiz-total-correction/progress")
    assert response.status_code == 200

    body = response.json()
    assert body["total_students"] == 3  # Derived from group result length
    assert body["students_finished"] == 2
    assert body["status"] == "RUNNING"

    # Verify that total_students was persisted to metadata
    assert stored_metadata["total_students"] == 3
    assert any("total_students" in update for update in updates)


def test_progress_handles_expired_group_result_gracefully(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    """Test that when group result expires (restore returns None), the endpoint keeps existing metadata state."""
    metadata = _base_metadata("quiz-expired-group", status="RUNNING", total_students=2)
    stored_metadata, updates = _configure_progress_store(monkeypatch, metadata)

    # Simulate expired/cleared group result
    _patch_group_result(monkeypatch, dummy_group=None)
    _patch_async_result(monkeypatch, failed=False)

    response = client.get("/api/v1/evaluations/quiz-expired-group/progress")
    assert response.status_code == 200

    body = response.json()
    # Should retain existing metadata state since group result is unavailable
    assert body["status"] == "RUNNING"
    assert body["total_students"] == 2
    assert body["students_finished"] == 0  # No group result, so 0 finished

    # Verify that no spurious updates were made (only timestamp may be refreshed)
    assert all("status" not in update for update in updates)


def test_progress_transitions_to_failed_on_quiz_task_failure_when_group_expired(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    """Test that quiz task failure is detected even when group result has expired."""
    metadata = _base_metadata(
        "quiz-group-expired-task-failed", status="RUNNING", total_students=2
    )
    stored_metadata, updates = _configure_progress_store(monkeypatch, metadata)

    failure_time = datetime(2025, 1, 4, 12, 0, tzinfo=UTC)
    # Group result expired/unavailable
    _patch_group_result(monkeypatch, dummy_group=None)
    # But the quiz task itself failed
    _patch_async_result(monkeypatch, failed=True, date_done=failure_time)

    response = client.get("/api/v1/evaluations/quiz-group-expired-task-failed/progress")
    assert response.status_code == 200

    body = response.json()
    # Should detect failure from quiz task even without group result
    assert body["status"] == "FAILED"
    assert body["students_finished"] == 0
    assert stored_metadata["status"] == "FAILED"


def test_progress_logs_warning_when_students_finished_exceeds_total(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    """Test that data inconsistency is logged when students_finished > total_students."""
    metadata = _base_metadata("quiz-inconsistent", total_students=2)
    stored_metadata, _ = _configure_progress_store(monkeypatch, metadata)

    done_time = datetime.now(tz=UTC)
    # Create 3 students but metadata says only 2 (simulating drift)
    dummy_group = DummyGroupResult(
        [
            DummyChildResult(ready=True, failed=False, date_done=done_time),
            DummyChildResult(ready=True, failed=False, date_done=done_time),
            DummyChildResult(ready=True, failed=False, date_done=done_time),
        ]
    )

    _patch_group_result(monkeypatch, dummy_group)
    _patch_async_result(monkeypatch, failed=False)

    import logging

    caplog.set_level(logging.WARNING)

    response = client.get("/api/v1/evaluations/quiz-inconsistent/progress")
    assert response.status_code == 200

    body = response.json()
    # Should be clamped to total_students
    assert body["students_finished"] == 2
    assert body["total_students"] == 2

    # Verify warning was logged
    assert any(
        "Data inconsistency detected" in record.message
        and "students_finished (3) exceeds total_students (2)" in record.message
        for record in caplog.records
    )
