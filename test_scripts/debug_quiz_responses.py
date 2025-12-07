import sys
from pathlib import Path
from rich.console import Console
from rich.pretty import pprint

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from evaluator.clients.backend_client import BackendEvaluationAPIClient

console = Console()


def inspect_quiz_data(quiz_id: str):
    try:
        with BackendEvaluationAPIClient() as client:
            console.print(f"[bold]Fetching data for quiz: {quiz_id}[/bold]")

            # 1. Get Questions to map IDs
            questions_resp = client.get_quiz_questions(quiz_id)
            questions = {q.id: q for q in questions_resp.data}
            console.print(f"Found {len(questions)} questions.")

            # 2. Get Responses
            responses_resp = client.get_quiz_responses(quiz_id)
            responses = responses_resp.responses
            console.print(f"Found {len(responses)} student responses.")

            for resp in responses:
                console.print(f"\n[bold cyan]Student: {resp.studentId}[/bold cyan]")
                console.print(f"Submission Status: {resp.submissionStatus}")

                student_answers = resp.response or {}
                console.print(f"Raw Response Keys: {list(student_answers.keys())}")

                for q_id, q_data in questions.items():
                    ans = student_answers.get(q_id)
                    console.print(
                        f"  Q: {q_id} ({q_data.type}) -> Answer: {ans} (Type: {type(ans)})"
                    )

                    if q_data.type == "MCQ":
                        if not ans:
                            console.print(
                                f"    [bold red]WARNING: Empty answer for MCQ question {q_id}[/bold red]"
                            )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if hasattr(e, "payload"):
            console.print(f"Payload: {e.payload}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    inspect_quiz_data("843ba741-4f97-4b66-ba6a-28ccd94d59b2")
