#!/usr/bin/env python3
"""
Manual test script for the evaluation API endpoint.

This script:
1. Constructs a test evaluation payload with 2 students and 1 MCQ question each
2. Sends a POST request to start the evaluation
3. Waits for the quiz_job to complete
4. Retrieves the student results from Celery
5. Displays results using rich for clear output

Usage:
    python tests/manual_test_evaluation.py

Requirements:
    - API server running on http://localhost:4040
    - Celery workers running
    - Redis running for result backend
"""

import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import requests
from celery.result import AsyncResult, GroupResult
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from evaluator.celery_app import app as celery_app
from evaluator.core.schemas.api import EvaluationJobRequest
from evaluator.core.schemas.tasks import StudentPayload, QuestionPayload


# Initialize Rich console
console = Console()


def create_test_payload() -> EvaluationJobRequest:
    """
    Create a test evaluation request with 2 students, each having 1 MCQ question.
    """
    # Define an MCQ question
    mcq_question_1 = QuestionPayload(
        question_id="q1",
        question_type="MCQ",
        student_answer="B",
        expected_answer="B",
        grading_guidelines=None,
        total_score=10.0,
    )

    mcq_question_2 = QuestionPayload(
        question_id="q1",
        question_type="MCQ",
        student_answer="A",
        expected_answer="B",
        grading_guidelines=None,
        total_score=10.0,
    )

    # Create two students
    student1 = StudentPayload(
        student_id="student_001",
        questions=[mcq_question_1],
    )

    student2 = StudentPayload(
        student_id="student_002",
        questions=[mcq_question_2],
    )

    # Create the evaluation request
    evaluation_request = EvaluationJobRequest(
        quiz_id="quiz_test_001",
        override_evaluated=False,
        students=[student1, student2],
    )

    return evaluation_request


def display_payload(payload: EvaluationJobRequest):
    """Display the payload being sent."""
    console.print("\n")
    console.print(
        Panel.fit("[bold cyan]Test Evaluation Payload[/bold cyan]", border_style="cyan")
    )

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Field", style="cyan", width=20)
    table.add_column("Value", style="white")

    table.add_row("Quiz ID", payload.quiz_id)
    table.add_row("Number of Students", str(len(payload.students)))
    table.add_row("Override Evaluated", str(payload.override_evaluated))

    console.print(table)
    console.print()

    # Show student details
    for idx, student in enumerate(payload.students, 1):
        console.print(f"[bold yellow]Student {idx}:[/bold yellow] {student.student_id}")
        for q_idx, question in enumerate(student.questions, 1):
            console.print(f"  [dim]Question {q_idx}:[/dim]")
            console.print(f"    Type: {question.question_type}")
            console.print(f"    ID: {question.question_id}")
            console.print(f"    Student Answer: {question.student_answer}")
            console.print(f"    Expected Answer: {question.expected_answer}")
            console.print(f"    Total Score: {question.total_score}")
        console.print()


def send_evaluation_request(api_url: str, payload: EvaluationJobRequest) -> dict:
    """Send POST request to start evaluation."""
    console.print("[bold green]→[/bold green] Sending evaluation request to API...")

    try:
        response = requests.post(
            f"{api_url}/api/v1/evaluations",
            json=payload.model_dump(),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]✗[/bold red] API request failed: {e}")
        sys.exit(1)


def wait_for_quiz_job(evaluation_id: str, timeout: int = 60) -> str:
    """
    Wait for the quiz_job to complete and return the group_id.
    """
    console.print(
        f"[bold green]→[/bold green] Waiting for quiz_job (task_id: {evaluation_id}) to complete..."
    )

    quiz_result = AsyncResult(evaluation_id, app=celery_app)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            description="Waiting for quiz job to dispatch student jobs...", total=None
        )

        start_time = time.time()
        while not quiz_result.ready():
            if time.time() - start_time > timeout:
                console.print("[bold red]✗[/bold red] Timeout waiting for quiz_job")
                sys.exit(1)
            time.sleep(0.5)

        progress.update(task, completed=True)

    if quiz_result.failed():
        console.print(f"[bold red]✗[/bold red] Quiz job failed: {quiz_result.result}")
        console.print(f"[dim]Traceback:[/dim]\n{quiz_result.traceback}")
        sys.exit(1)

    group_id = quiz_result.result
    console.print(
        f"[bold green]✓[/bold green] Quiz job completed. Group ID: [cyan]{group_id}[/cyan]"
    )
    return group_id


def fetch_student_results(group_id: str, timeout: int = 120) -> list:
    """
    Restore the GroupResult and fetch all student results.
    Uses polling instead of event listening to avoid timeout issues.
    """
    console.print(
        f"[bold green]→[/bold green] Fetching student results from group: {group_id}..."
    )

    group_result = GroupResult.restore(group_id, app=celery_app)

    if group_result is None:
        console.print(
            "[bold red]✗[/bold red] Could not restore GroupResult. Check Celery result backend configuration."
        )
        sys.exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            description="Retrieving student job results...", total=None
        )

        # Poll for results instead of using event listening (which times out)
        # This is more reliable in environments without proper event transport
        # This is IMPORTANT, else result won't be retrieved
        start_time = time.time()
        poll_interval = 0.5  # Increased from 0.1 for better efficiency

        while True:
            if time.time() - start_time > timeout:
                console.print(
                    "[bold red]✗[/bold red] Timeout waiting for group results"
                )
                sys.exit(1)

            # Check if all tasks in the group are ready
            if group_result.ready():
                break

            time.sleep(poll_interval)

        # Now get the actual results
        student_results = group_result.get(timeout=5, disable_sync_subtasks=False)
        progress.update(task, completed=True)

    console.print(
        f"[bold green]✓[/bold green] Retrieved results for {len(student_results)} students"
    )
    return student_results


def display_results(student_results: list):
    """Display the student evaluation results in a formatted table."""
    console.print("\n")
    console.print(
        Panel.fit("[bold green]Evaluation Results[/bold green]", border_style="green")
    )

    for idx, result in enumerate(student_results, 1):
        console.print(f"\n[bold yellow]Student {idx} Results:[/bold yellow]")

        # Handle case where task failed at system level
        if isinstance(result, dict) and result.get("status") == "system_error":
            console.print(f"  [bold red]System Error:[/bold red] {result.get('error')}")
            continue

        # Display student results
        student_id = result.get("student_id", "Unknown")
        console.print(f"  [cyan]Student ID:[/cyan] {student_id}")

        question_results = result.get("results", [])
        if not question_results:
            console.print("  [dim]No question results[/dim]")
            continue

        # Create table for question results
        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("Question ID", style="cyan", width=15)
        table.add_column("Status", style="white", width=12)
        table.add_column("Score", style="white", width=10)
        table.add_column("Feedback", style="white", width=40)

        for q_result in question_results:
            # Handle system errors at question level
            if isinstance(q_result, dict) and q_result.get("status") == "system_error":
                table.add_row(
                    q_result.get("job_id", "Unknown"),
                    "[red]System Error[/red]",
                    "N/A",
                    q_result.get("error", "Unknown error"),
                )
                continue

            question_id = q_result.get("question_id", "Unknown")
            status = q_result.get("status", "Unknown")

            eval_result = q_result.get("evaluated_result")
            if eval_result:
                score = eval_result.get("score", "N/A")
                feedback = eval_result.get("feedback", "No feedback")
            else:
                score = "N/A"
                feedback = "No evaluation result"

            # Color code status
            status_colored = (
                f"[green]{status}[/green]"
                if status == "success"
                else f"[red]{status}[/red]"
            )

            table.add_row(question_id, status_colored, str(score), feedback or "")

        console.print(table)

    console.print("\n")


def main():
    """Main test execution."""
    API_URL = "http://localhost:4040"

    console.rule("[bold blue]Evaluation API Manual Test")

    # Step 1: Create test payload
    console.print("\n[bold]Step 1:[/bold] Creating test payload...")
    payload = create_test_payload()
    display_payload(payload)

    # Step 2: Send evaluation request
    console.print("[bold]Step 2:[/bold] Sending evaluation request...")
    response_data = send_evaluation_request(API_URL, payload)

    console.print("[bold green]✓[/bold green] Evaluation accepted!")
    console.print(f"  Quiz ID: [cyan]{response_data['quiz_id']}[/cyan]")
    console.print(f"  Status: [cyan]{response_data['status']}[/cyan]")
    console.print(f"  Progress URL: [cyan]{response_data['progress_url']}[/cyan]")

    # Extract evaluation_id from progress URL
    evaluation_id = response_data["progress_url"].split("/")[-2]
    console.print(f"  Evaluation ID: [cyan]{evaluation_id}[/cyan]")
    console.print()

    # Step 3: Wait for quiz job to complete
    console.print(
        "[bold]Step 3:[/bold] Waiting for quiz job to dispatch student jobs..."
    )
    group_id = wait_for_quiz_job(evaluation_id, timeout=60)
    console.print()

    # Step 4: Fetch student results
    console.print("[bold]Step 4:[/bold] Fetching student evaluation results...")
    student_results = fetch_student_results(group_id, timeout=120)

    # Step 5: Display results
    console.print("[bold]Step 5:[/bold] Displaying results...")
    display_results(student_results)

    console.rule("[bold green]Test Complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Test interrupted by user[/bold yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Unexpected error:[/bold red] {e}")
        import traceback

        console.print(traceback.format_exc())
        sys.exit(1)
