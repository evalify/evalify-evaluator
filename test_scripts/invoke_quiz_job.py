#!/usr/bin/env python3
"""
Direct invocation script for quiz_job task.

This script directly invokes the quiz_job Celery task with a specified quiz_id.
Unlike the API endpoint, this bypasses HTTP and directly queues the task.

Usage:
    uv run python scripts/invoke_quiz_job.py <quiz_id> [--evaluation-id <id>] [--timeout <seconds>]

Examples:
    # Basic invocation
    uv run python scripts/invoke_quiz_job.py quiz_test_001

    # With custom evaluation ID
    uv run python scripts/invoke_quiz_job.py quiz_test_001 --evaluation-id eval_custom_123

    # With custom timeout
    uv run python scripts/invoke_quiz_job.py quiz_test_001 --timeout 120

Requirements:
    - Redis running on localhost:6379
    - Celery workers running (especially desc-queue worker for quiz_job)
    - Backend API accessible if quiz data needs to be fetched
"""

import sys
import argparse
import time
from pathlib import Path
from uuid import uuid4

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from celery.result import GroupResult
from evaluator.celery_app import app as celery_app
from evaluator.core.schemas.api import EvaluationJobRequest

# Initialize Rich console
console = Console()


def invoke_quiz_job(
    quiz_id: str, evaluation_id: str, timeout: int = 60
) -> tuple[str, dict]:
    """
    Directly invoke the quiz_job Celery task.

    Args:
        quiz_id (str): The quiz identifier
        evaluation_id (str): The evaluation run identifier
        timeout (int): Maximum seconds to wait for task completion

    Returns:
        tuple: (task_id, task_result)

    Raises:
        RuntimeError: If task fails or times out
    """
    # Create request payload
    request = EvaluationJobRequest(
        quiz_id=quiz_id,
        override_evaluated=False,
    )

    console.print(
        Panel.fit(
            "[bold cyan]Invoking quiz_job[/bold cyan]",
            border_style="cyan",
        )
    )

    # Display invocation details
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Parameter", style="cyan", width=20)
    table.add_column("Value", style="white")

    table.add_row("Quiz ID", quiz_id)
    table.add_row("Evaluation ID", evaluation_id)
    table.add_row("Timeout (seconds)", str(timeout))

    console.print(table)
    console.print()

    # Invoke the task directly
    console.print("[bold green]→[/bold green] Invoking quiz_job task on desc-queue...")

    task_result = celery_app.send_task(
        "evaluator.worker.tasks.quiz.quiz_job",
        args=(evaluation_id, request.model_dump()),
        queue="desc-queue",
    )
    task_id = task_result.id

    console.print(
        f"[bold green]✓[/bold green] Task queued with ID: [cyan]{task_id}[/cyan]"
    )
    console.print()

    # Wait for task completion
    console.print("[bold green]→[/bold green] Waiting for quiz_job to complete...")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            description="Waiting for quiz job to dispatch student jobs...", total=None
        )

        start_time = time.time()
        while not task_result.ready():
            elapsed = time.time() - start_time
            if elapsed > timeout:
                console.print(
                    f"[bold red]✗[/bold red] Timeout waiting for quiz_job after {timeout}s"
                )
                raise RuntimeError(
                    f"Task did not complete within {timeout} seconds. "
                    f"Task ID: {task_id}"
                )
            time.sleep(0.5)

        progress.update(task, completed=True)

    # Handle task result
    if task_result.failed():
        error_msg = str(task_result.result)
        traceback_str = task_result.traceback or "No traceback available"
        console.print("[bold red]✗[/bold red] Quiz job failed!")
        console.print(f"[bold]Error:[/bold] {error_msg}")
        console.print(f"[dim]Traceback:[/dim]\n{traceback_str}")
        raise RuntimeError(f"Task failed: {error_msg}")

    group_id = task_result.result
    console.print("[bold green]✓[/bold green] Quiz job completed successfully!")
    console.print(f"  Group ID: [cyan]{group_id}[/cyan]")
    console.print(f"  Task ID: [cyan]{task_id}[/cyan]")

    # Wait for student jobs to complete
    console.print()
    console.print("[bold green]→[/bold green] Waiting for student jobs to complete...")

    group_result = GroupResult.restore(group_id, app=celery_app)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            description="Waiting for student evaluations...", total=None
        )

        # We use a simple loop here. In a real app, you might want to check progress more granularly.
        while not group_result.ready():
            time.sleep(0.5)

        progress.update(task, completed=True)

    student_results = group_result.get(propagate=False)
    console.print("[bold green]✓[/bold green] All student jobs completed!")

    return task_id, {
        "status": "success",
        "group_id": group_id,
        "task_id": task_id,
        "evaluation_id": evaluation_id,
        "quiz_id": quiz_id,
        "results": student_results,
    }


def display_summary(task_id: str, result: dict):
    """Display execution summary."""
    console.print()
    console.print(
        Panel.fit(
            "[bold green]Execution Summary[/bold green]",
            border_style="green",
        )
    )

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Field", style="cyan", width=20)
    table.add_column("Value", style="white")

    for key, value in result.items():
        if key == "results":
            continue
        table.add_row(key.replace("_", " ").title(), str(value))

    console.print(table)
    console.print()

    if "results" in result:
        console.print(
            Panel.fit(
                "[bold green]Evaluation Results[/bold green]",
                border_style="green",
            )
        )

        for student_res in result["results"]:
            if isinstance(student_res, Exception):
                console.print(f"[bold red]Student Job Failed:[/bold red] {student_res}")
                continue

            student_id = student_res.get("student_id", "Unknown")
            q_results = student_res.get("results", [])

            console.print(f"\n[bold cyan]Student: {student_id}[/bold cyan]")

            r_table = Table(show_header=True, header_style="bold blue")
            r_table.add_column("Q. ID", style="dim")
            r_table.add_column("Status")
            r_table.add_column("Score")
            r_table.add_column("Feedback")

            for qr in q_results:
                if isinstance(qr, dict):
                    q_id = qr.get("question_id", "N/A")
                    status = qr.get("status", "unknown")

                    if status == "success":
                        eval_res = qr.get("evaluated_result", {})
                        score = str(eval_res.get("score", "N/A")) if eval_res else "N/A"
                        feedback = str(eval_res.get("feedback", "")) if eval_res else ""
                        status_style = "[green]Success[/green]"
                    else:
                        score = "-"
                        feedback = qr.get("error", "Failed")
                        status_style = "[red]Failed[/red]"

                    r_table.add_row(q_id, status_style, score, feedback)
                else:
                    r_table.add_row("Unknown", "[red]Error[/red]", "-", str(qr))

            console.print(r_table)
        console.print()

    # Display next steps
    console.print("[bold yellow]Next Steps:[/bold yellow]")
    console.print("  1. Monitor worker logs to track task progress")
    console.print("  2. Check Redis for student job results:")
    console.print(
        f"     [cyan]redis-cli GET celery-task-meta-{result['task_id']}[/cyan]"
    )
    console.print("  3. Use Celery inspect to check worker status:")
    console.print("     [cyan]celery -A evaluator.celery_app inspect active[/cyan]")
    console.print()


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Directly invoke the quiz_job Celery task",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic invocation with auto-generated evaluation ID
  uv run python scripts/invoke_quiz_job.py quiz_test_001

  # With custom evaluation ID
  uv run python scripts/invoke_quiz_job.py quiz_test_001 --evaluation-id eval_custom_123

  # With custom timeout
  uv run python scripts/invoke_quiz_job.py quiz_test_001 --timeout 120
        """,
    )

    parser.add_argument(
        "quiz_id",
        type=str,
        help="The quiz identifier to evaluate",
    )

    parser.add_argument(
        "--evaluation-id",
        type=str,
        default=None,
        help="Custom evaluation ID (defaults to auto-generated UUID)",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Maximum seconds to wait for task completion (default: 60)",
    )

    return parser.parse_args()


def main():
    """Main execution."""
    args = parse_arguments()

    # Generate evaluation ID if not provided
    evaluation_id = args.evaluation_id or f"eval_{uuid4().hex[:8]}"

    console.rule("[bold blue]Quiz Job Invoker")
    console.print()

    try:
        # Invoke quiz_job
        task_id, result = invoke_quiz_job(
            quiz_id=args.quiz_id,
            evaluation_id=evaluation_id,
            timeout=args.timeout,
        )

        # Display summary
        display_summary(task_id, result)

        console.rule("[bold green]Success!")
        return 0

    except KeyboardInterrupt:
        console.print("\n[bold yellow]Interrupted by user[/bold yellow]")
        return 130

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        console.print("[dim]Use --help for usage information[/dim]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
