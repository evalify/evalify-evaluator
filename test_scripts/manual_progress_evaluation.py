#!/usr/bin/env python3
"""Manual script to exercise quiz progress tracking with STUB_SLEEP questions."""

import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Ensure src/ is on the path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import requests
from celery.result import GroupResult
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table

from evaluator.celery_app import app as celery_app
from evaluator.core.schemas.api import EvaluationJobRequest
from evaluator.core.schemas.tasks import QuestionPayload, StudentPayload
from evaluator.worker.utils.progress import EvaluationProgressStore

API_URL = "http://localhost:4040"
QUIZ_ID = "quiz_stub_sleep_demo"
POLL_INTERVAL_SECONDS = 1.0
POLL_TIMEOUT_SECONDS = 180

console = Console()
progress_store = EvaluationProgressStore(celery_app)


def _build_stub_payload() -> EvaluationJobRequest:
    """Create a payload with STUB_SLEEP + MCQ combinations."""

    stub_question_fast = QuestionPayload(
        question_id="stub_q1",
        question_type="STUB_SLEEP",
        student_answer="placeholder",
        expected_answer="placeholder",
        grading_guidelines=None,
        total_score=5.0,
    )

    stub_question_slow = QuestionPayload(
        question_id="stub_q2",
        question_type="STUB_SLEEP",
        student_answer={"code": "print('hello')"},
        expected_answer=None,
        grading_guidelines=None,
        total_score=5.0,
    )

    mcq_question = QuestionPayload(
        question_id="mcq_q1",
        question_type="MCQ",
        student_answer="B",
        expected_answer="B",
        grading_guidelines=None,
        total_score=10.0,
    )

    student_alpha = StudentPayload(
        student_id="student_alpha",
        questions=[stub_question_fast, stub_question_slow],
    )

    student_bravo = StudentPayload(
        student_id="student_bravo",
        questions=[stub_question_slow, mcq_question],
    )

    return EvaluationJobRequest(
        quiz_id=QUIZ_ID,
        override_evaluated=True,
        students=[student_alpha, student_bravo],
    )


def _send_request(payload: EvaluationJobRequest) -> Dict[str, Any]:
    console.print(
        "[bold green]→[/bold green] Starting evaluation with progress tracking..."
    )
    response = requests.post(
        f"{API_URL}/api/v1/evaluations",
        json=payload.model_dump(),
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def _poll_progress(quiz_id: str) -> Dict[str, Any]:
    console.print(
        f"[bold green]→[/bold green] Polling progress for quiz [cyan]{quiz_id}[/cyan]..."
    )
    start = time.time()
    last_status = None

    with Progress(
        SpinnerColumn(),
        BarColumn(bar_width=None),
        TextColumn("{task.description}"),
        console=console,
    ) as progress_display:
        task_id = progress_display.add_task("Waiting for worker updates", total=1)

        while True:
            if time.time() - start > POLL_TIMEOUT_SECONDS:
                raise TimeoutError("Polling progress timed out")

            resp = requests.get(
                f"{API_URL}/api/v1/evaluations/{quiz_id}/progress",
                timeout=5,
            )
            resp.raise_for_status()
            payload = resp.json()
            students_finished = payload["students_finished"]
            total_students = payload["total_students"]
            if total_students is None or total_students == 0:
                console.print(
                    f"[bold red]Error:[/bold red] total_students is {total_students}. Cannot compute progress."
                )
                raise ValueError(f"Invalid total_students value: {total_students}")
            fraction = students_finished / total_students
            progress_display.update(
                task_id,
                completed=fraction,
                description=f"{students_finished}/{total_students} students finished ({payload['status']})",
            )

            if payload["status"] != last_status:
                console.print(
                    f" • Status changed to [bold]{payload['status']}[/bold] at {payload['updated_at']}"
                )
                last_status = payload["status"]

            if payload["status"] in {"COMPLETED", "FAILED"}:
                progress_display.update(task_id, completed=1)
                return payload

            time.sleep(POLL_INTERVAL_SECONDS)


def _fetch_student_results(quiz_id: str) -> List[Dict[str, Any]]:
    metadata = progress_store.get(quiz_id)
    if not metadata:
        return []

    group_id = metadata.get("group_id")
    if not group_id:
        return []

    group_result = GroupResult.restore(group_id, app=celery_app)
    if not group_result:
        return []

    return group_result.get(timeout=10, disable_sync_subtasks=False)


def _render_results(results: List[Dict[str, Any]]) -> None:
    if not results:
        console.print(
            "[yellow]No student results available (group result missing).[/yellow]"
        )
        return

    console.print("\n[bold blue]Final student breakdown[/bold blue]")
    for student in results:
        console.print(f"[bold]Student:[/bold] {student.get('student_id', 'unknown')}")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Question ID", width=16)
        table.add_column("Status", width=12)
        table.add_column("Score", width=10)
        table.add_column("Feedback")

        for entry in student.get("results", []):
            status = entry.get("status", "?")
            eval_result = entry.get("evaluated_result") or {}
            table.add_row(
                entry.get("question_id", "?"),
                status,
                str(eval_result.get("score", "-")),
                eval_result.get("feedback", ""),
            )
        console.print(table)


def main() -> None:
    payload = _build_stub_payload()
    console.rule("[bold cyan]Manual Progress Evaluation")
    console.print(f"Quiz ID: [cyan]{payload.quiz_id}[/cyan]")
    console.print(
        f"Submitting {len(payload.students)} students / {sum(len(s.questions) for s in payload.students)} questions"
    )

    evaluation_timer_start = time.perf_counter()
    response = _send_request(payload)
    console.print(f"Progress URL: [green]{response['progress_url']}[/green]")

    progress_snapshot = _poll_progress(payload.quiz_id)
    console.print(f"Final status: [bold]{progress_snapshot['status']}[/bold]")

    if progress_snapshot["status"] == "COMPLETED":
        student_results = _fetch_student_results(payload.quiz_id)
        _render_results(student_results)
    else:
        console.print(
            "[red]Evaluation did not complete successfully; skipping result fetch.[/red]"
        )

    elapsed = time.perf_counter() - evaluation_timer_start
    console.print(f"[bold]Total evaluation time:[/bold] {elapsed:.2f} seconds")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Interrupted by user[/bold yellow]")
        sys.exit(1)
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        sys.exit(1)
