"""
User Answer Input Module
Supports interactive input and JSON file import
Supports multiple choice (A-E) and numeric entry (number/fraction/expression)
"""

import json
import os
import textwrap
from typing import Optional

from ..core.models import Question


def load_answers_from_json(json_path: str) -> dict[str, str]:
    """
    Load answers from JSON file
    
    Args:
        json_path: JSON file path
    
    Returns:
        Answer dict {question_id: answer}
    
    Raises:
        FileNotFoundError: File does not exist
        json.JSONDecodeError: JSON parse failed
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Answer file not found: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, dict):
        raise ValueError("Answer file format error: expected dict format {question_id: answer}")
    
    answers = {}
    for q_id, answer in data.items():
        if answer is not None and not q_id.startswith("_"):
            answers[q_id] = str(answer).strip()
    
    return answers


def save_answers_to_json(answers: dict[str, str], json_path: str) -> None:
    """
    Save answers to JSON file
    
    Args:
        answers: Answer dict
        json_path: Output path
    """
    os.makedirs(os.path.dirname(json_path) or '.', exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(answers, f, ensure_ascii=False, indent=2)


def wrap_text(text: str, width: int = 70) -> str:
    """
    Wrap long text for display
    
    Args:
        text: Original text
        width: Max width per line
    
    Returns:
        Wrapped text
    """
    lines = text.split('\n')
    wrapped_lines = []
    for line in lines:
        if len(line) <= width:
            wrapped_lines.append(line)
        else:
            wrapped = textwrap.fill(line, width=width, break_long_words=False, break_on_hyphens=False)
            wrapped_lines.append(wrapped)
    return '\n'.join(wrapped_lines)


def display_all_questions(questions: list[Question]) -> None:
    """
    Display all questions (for preview before batch input)
    
    Args:
        questions: Question list
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    
    console = Console(width=100)
    
    console.print("\n" + "="*70, style="blue")
    console.print("All Questions Preview", style="bold blue")
    console.print("="*70, style="blue")
    
    for i, question in enumerate(questions, 1):
        problem_type = question.problem_type
        is_numeric = problem_type == "numeric_entry"
        type_label = "[Numeric]" if is_numeric else "[Choice]"
        type_color = "magenta" if is_numeric else "cyan"
        
        console.print(f"\n[bold {type_color}]{i}. {question.id}[/bold {type_color}] {type_label}")
        
        stem_wrapped = wrap_text(question.stem, width=65)
        console.print(Panel(stem_wrapped, border_style="dim", padding=(0, 1)))
        
        if not is_numeric and question.choices:
            for opt in ['A', 'B', 'C', 'D', 'E']:
                content = question.choices.get(opt)
                if content and content not in ["N/A", "UNKNOWN", None]:
                    if len(content) > 60:
                        content = content[:57] + "..."
                    console.print(f"    [yellow]{opt}[/yellow]: {content}")
    
    console.print("\n" + "="*70, style="blue")
    
    console.print("\n[bold]Answer file format example:[/bold]")
    console.print('''
```json
{
  "p1_q1": "A",
  "p1_q2": "B", 
  "p1_q3": "7",
  "p1_q4": "1/2"
}
```
''', style="dim")


def ask_correct_answers_choice(questions: list[Question]) -> Optional[str]:
    """
    Ask user if they want to provide correct answers file
    
    Args:
        questions: Question list
    
    Returns:
        Correct answers file path, or None if user chooses not to provide
    """
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    
    console = Console()
    
    console.print("\n" + "="*70, style="yellow")
    console.print("Correct Answers Option", style="bold yellow")
    console.print("="*70, style="yellow")
    
    console.print("""
You can choose:
  [1] Provide correct answers file -> Skip LLM solving, use your answers directly
  [2] Don't provide -> Use LLM to solve questions automatically
""")
    
    choice = Prompt.ask(
        "[yellow]Please choose[/yellow]",
        choices=["1", "2"],
        default="2"
    )
    
    if choice == "1":
        console.print("\n[dim]Answer file format: JSON, e.g. {\"p1_q1\": \"A\", \"p1_q2\": \"7\"}[/dim]")
        
        while True:
            file_path = Prompt.ask(
                "[yellow]Enter correct answers file path[/yellow]",
                default=""
            )
            
            if not file_path:
                if Confirm.ask("[yellow]Sure you don't want to provide correct answers file?[/yellow]", default=True):
                    return None
                continue
            
            if not os.path.exists(file_path):
                console.print(f"[red]File not found: {file_path}[/red]")
                continue
            
            try:
                answers = load_answers_from_json(file_path)
                console.print(f"[green]Successfully loaded {len(answers)} correct answers[/green]")
                
                loaded_ids = set(answers.keys())
                question_ids = {q.id for q in questions}
                missing = question_ids - loaded_ids
                if missing:
                    console.print(f"[yellow]Warning: Missing correct answers for: {list(missing)[:5]}{'...' if len(missing) > 5 else ''}[/yellow]")
                
                return file_path
            except Exception as e:
                console.print(f"[red]File format error: {e}[/red]")
                continue
    
    return None


def ask_user_answers_choice(
    questions: list[Question],
    llm_client=None,
    solve_results=None,
    session_dir: str = None,
    subject: str = "math"
) -> dict[str, str]:
    """
    Ask user to choose answer input method
    
    Args:
        questions: Question list
        llm_client: LLM client (for student simulation)
        solve_results: Correct answers list (for student simulation reference)
        session_dir: Session directory (for saving simulated answers)
        subject: "math" or "english" - determines which prompts to use for simulation
    
    Returns:
        User answers dict
    """
    from rich.console import Console
    from rich.prompt import Prompt
    
    console = Console()
    
    console.print("\n" + "="*70, style="green")
    console.print("User Answer Input Method", style="bold green")
    console.print("="*70, style="green")
    
    options_text = """
You can choose:
  [1] Interactive input -> Display and input answers one by one
  [2] Batch file input  -> Display all questions first, then input answer file path"""
    
    has_simulator = llm_client is not None
    if has_simulator:
        options_text += """
  [3] Simulate student -> Let AI play student (will intentionally make some mistakes)"""
    
    console.print(options_text)
    console.print()
    
    valid_choices = ["1", "2", "3"] if has_simulator else ["1", "2"]
    choice = Prompt.ask(
        "[green]Please choose[/green]",
        choices=valid_choices,
        default="1"
    )
    
    if choice == "1":
        return collect_answers_interactive(questions)
    elif choice == "2":
        return collect_answers_from_file(questions)
    elif choice == "3" and has_simulator:
        from .student_simulator import ask_simulate_student
        simulated_answers = ask_simulate_student(
            llm_client=llm_client,
            questions=questions,
            solve_results=solve_results,
            session_dir=session_dir,
            subject=subject
        )
        if simulated_answers:
            return simulated_answers
        else:
            console.print("[yellow]Falling back to interactive input...[/yellow]")
            return collect_answers_interactive(questions)
    else:
        return collect_answers_interactive(questions)


def collect_answers_from_file(questions: list[Question]) -> dict[str, str]:
    """
    Display all questions then load user answers from file
    
    Args:
        questions: Question list
    
    Returns:
        User answers dict
    """
    from rich.console import Console
    from rich.prompt import Prompt
    
    console = Console()
    
    display_all_questions(questions)
    
    console.print("\n[bold]Please prepare your answer file, then enter file path[/bold]")
    console.print("[dim]Tip: Answer file format is JSON, refer to question IDs above[/dim]\n")
    
    while True:
        file_path = Prompt.ask(
            "[green]Enter user answers file path[/green]",
            default=""
        )
        
        if not file_path:
            console.print("[yellow]No answer file provided, using empty answers[/yellow]")
            return {}
        
        if not os.path.exists(file_path):
            console.print(f"[red]File not found: {file_path}[/red]")
            continue
        
        try:
            answers = load_answers_from_json(file_path)
            console.print(f"\n[green]Successfully loaded {len(answers)} answers[/green]")
            
            console.print("\n[bold]Loaded answers:[/bold]")
            for q_id, ans in list(answers.items())[:10]:
                console.print(f"  {q_id}: {ans}")
            if len(answers) > 10:
                console.print(f"  ... total {len(answers)} answers")
            
            return answers
        except Exception as e:
            console.print(f"[red]Load failed: {e}[/red]")
            continue


def collect_answers_interactive(questions: list[Question]) -> dict[str, str]:
    """
    Interactive collect user answers
    Supports multiple choice (A-E) and numeric entry (number/fraction/expression)
    
    Args:
        questions: Question list
    
    Returns:
        Answer dict {question_id: answer}
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.text import Text
    from rich.markdown import Markdown
    
    console = Console(width=100)
    answers = {}
    
    console.print("\n" + "="*70, style="blue")
    console.print("Interactive Answer Input", style="bold blue")
    console.print("   Multiple choice: Enter A-E", style="dim")
    console.print("   Numeric entry: Enter number, fraction (e.g. 1/2) or expression", style="dim")
    console.print("   Press Enter to skip, enter 'q' to quit", style="dim")
    console.print("="*70 + "\n", style="blue")
    
    for i, question in enumerate(questions, 1):
        problem_type = question.problem_type
        is_numeric = problem_type == "numeric_entry"
        
        type_label = "[Numeric Entry]" if is_numeric else "[Multiple Choice]"
        type_color = "magenta" if is_numeric else "cyan"
        
        console.print(f"\n{'-'*70}")
        console.print(f"[bold {type_color}]Question {i}/{len(questions)}[/bold {type_color}] {type_label} [dim]{question.id}[/dim]")
        console.print()
        
        stem_wrapped = wrap_text(question.stem, width=65)
        console.print(Panel(
            stem_wrapped, 
            title="[bold]Stem[/bold]", 
            border_style="dim",
            padding=(0, 1)
        ))
        
        if question.latex_equations:
            console.print("[dim]Formulas:[/dim]", end=" ")
            console.print(", ".join(question.latex_equations), style="italic")
        
        if question.diagram_description:
            console.print(f"[dim]Diagram:[/dim] {question.diagram_description}")
        
        if not is_numeric:
            choices = question.choices
            console.print()
            for opt in ['A', 'B', 'C', 'D', 'E']:
                content = choices.get(opt)
                if content and content not in ["N/A", "UNKNOWN", None]:
                    if len(content) > 60:
                        content_wrapped = wrap_text(content, width=55)
                        lines = content_wrapped.split('\n')
                        console.print(f"  [yellow]{opt}[/yellow]: {lines[0]}")
                        for line in lines[1:]:
                            console.print(f"      {line}")
                    else:
                        console.print(f"  [yellow]{opt}[/yellow]: {content}")
        
        console.print()
        
        while True:
            if is_numeric:
                prompt_text = "[green]Your answer (number/fraction)[/green]"
            else:
                prompt_text = "[green]Your answer (A-E)[/green]"
            
            answer = Prompt.ask(
                prompt_text,
                default="",
                show_default=False
            )
            
            answer = answer.strip()
            
            if answer.upper() == 'Q':
                console.print("\n[yellow]Exited answering[/yellow]")
                return answers
            
            if answer == '':
                console.print("[dim]Skipped[/dim]")
                break
            
            if is_numeric:
                answers[question.id] = answer
                console.print(f"[green]Recorded: {answer}[/green]")
                break
            else:
                answer_upper = answer.upper()
                if answer_upper in ['A', 'B', 'C', 'D', 'E']:
                    answers[question.id] = answer_upper
                    console.print(f"[green]Recorded: {answer_upper}[/green]")
                    break
                else:
                    console.print("[red]Please enter one of A-E[/red]")
    
    console.print("\n" + "="*70, style="blue")
    console.print(f"Answering complete!", style="bold green")
    
    choice_count = sum(1 for q in questions if q.problem_type != "numeric_entry" and q.id in answers)
    numeric_count = sum(1 for q in questions if q.problem_type == "numeric_entry" and q.id in answers)
    
    console.print(f"   Total answered {len(answers)} questions (Multiple choice: {choice_count}, Numeric entry: {numeric_count})")
    console.print("="*70 + "\n", style="blue")
    
    return answers


def merge_answers(
    existing: dict[str, str],
    new: dict[str, str],
    overwrite: bool = True
) -> dict[str, str]:
    """
    Merge answers
    
    Args:
        existing: Existing answers
        new: New answers
        overwrite: Whether to overwrite existing answers
    
    Returns:
        Merged answers
    """
    result = existing.copy()
    for q_id, answer in new.items():
        if overwrite or q_id not in result:
            result[q_id] = answer
    return result
