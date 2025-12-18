"""
Diagnosis Module (Stage D)
Compares user answers with correct answers and performs error analysis.
Supports Multiple Choice (multiple_choice) and Numeric Entry (numeric_entry).
"""

from typing import Optional
import re

from ..llm.base import LLMClient
from ..llm.prompts import (
    DIAGNOSE_SYSTEM_PROMPT_CHOICE,
    DIAGNOSE_USER_PROMPT_TEMPLATE_CHOICE,
    DIAGNOSE_SYSTEM_PROMPT_NUMERIC,
    DIAGNOSE_USER_PROMPT_TEMPLATE_NUMERIC,
    DIAGNOSE_SCHEMA_HINT
)
from .models import Question, SolveResult, DiagnoseResult, OptionAnalysis
from .validators import validate_diagnose_result, extract_json_from_text
from ..utils.logging import Logger

import json


def normalize_numeric_answer(answer: str) -> Optional[float]:
    """
    Normalizes a numeric answer string into a float for comparison.
    Supports: integers, decimals, fractions, and negative numbers.
    
    Args:
        answer: The answer string.
    
    Returns:
        Float value or None (if parsing fails).
    """
    answer = answer.strip().replace(" ", "")
    
    try:
        # Direct numeric conversion
        return float(answer)
    except ValueError:
        pass
    
    # Handle fractions (e.g., "1/2", "-3/4")
    fraction_match = re.match(r'^(-?\d+)/(-?\d+)$', answer)
    if fraction_match:
        try:
            numerator = float(fraction_match.group(1))
            denominator = float(fraction_match.group(2))
            if denominator != 0:
                return numerator / denominator
        except ValueError:
            pass
    
    return None


def compare_numeric_answers(user_answer: str, correct_answer: str, tolerance: float = 1e-6) -> bool:
    """
    Compares two numeric answers for equality.
    
    Args:
        user_answer: User's answer.
        correct_answer: Correct answer.
        tolerance: Allowed precision error.
    
    Returns:
        True if equal, False otherwise.
    """
    # Try exact string match first
    if user_answer.strip().lower() == correct_answer.strip().lower():
        return True
    
    # Try numeric comparison
    user_val = normalize_numeric_answer(user_answer)
    correct_val = normalize_numeric_answer(correct_answer)
    
    if user_val is not None and correct_val is not None:
        return abs(user_val - correct_val) < tolerance
    
    return False


class ErrorDiagnoser:
    """
    Error Diagnoser
    Analyzes user errors and provides diagnosis and corrective guidance.
    Supports Multiple Choice and Numeric Entry.
    """
    
    def __init__(self, llm_client: LLMClient, logger: Optional[Logger] = None):
        """
        Initializes the diagnoser.
        
        Args:
            llm_client: LLM Client.
            logger: Logger instance.
        """
        self.llm = llm_client
        self.logger = logger
    
    def _log(self, message: str, level: str = "info"):
        """Log a message."""
        if self.logger:
            self.logger.log(message, level)
    
    def _check_answer_correct(
        self, 
        user_answer: str, 
        correct_answer: str, 
        problem_type: str
    ) -> bool:
        """
        Checks if the answer is correct.
        
        Args:
            user_answer: User's answer.
            correct_answer: Correct answer.
            problem_type: Type of the problem.
        
        Returns:
            True if correct, False otherwise.
        """
        if problem_type == "numeric_entry":
            # Numeric Entry: numeric comparison
            return compare_numeric_answers(user_answer, correct_answer)
        else:
            # Multiple Choice: letter comparison (case-insensitive)
            return user_answer.upper().strip() == correct_answer.upper().strip()
    
    def diagnose(
        self,
        question: Question,
        solve_result: SolveResult,
        user_answer: str,
        retry_on_failure: bool = True
    ) -> tuple[Optional[DiagnoseResult], Optional[str]]:
        """
        Diagnoses an error for a single question.
        
        Args:
            question: Question object.
            solve_result: Result from the solver.
            user_answer: User's submitted answer.
            retry_on_failure: Whether to retry on parsing failure.
        
        Returns:
            (Diagnosis Result, Error Message or None)
        """
        user_answer = user_answer.strip()
        correct_answer = solve_result.correct_answer.strip()
        problem_type = question.problem_type
        
        # Check if the answer is correct
        is_correct = self._check_answer_correct(user_answer, correct_answer, problem_type)
        
        self._log(f"Diagnosing question {question.id} [{problem_type}]. User: {user_answer}, Correct: {correct_answer}")
        
        # If correct, return a simple success result
        if is_correct:
            self._log(f"Question {question.id} answered correctly.")
            
            if problem_type == "numeric_entry":
                # Numeric entry correct: no option analysis needed
                return DiagnoseResult(
                    question_id=question.id,
                    user_answer=user_answer,
                    correct_answer=correct_answer,
                    is_correct=True,
                    why_user_choice_is_tempting=None,
                    likely_misconceptions=[],
                    how_to_get_correct=None,
                    option_analysis=[]
                ), None
            else:
                # Multiple choice correct: include option analysis
                content = question.choices.get(correct_answer.upper(), "")
                if content is None:
                    content = "UNKNOWN"
                
                return DiagnoseResult(
                    question_id=question.id,
                    user_answer=user_answer.upper(),
                    correct_answer=correct_answer.upper(),
                    is_correct=True,
                    why_user_choice_is_tempting=None,
                    likely_misconceptions=[],
                    how_to_get_correct=None,
                    option_analysis=[
                        OptionAnalysis(
                            option=correct_answer.upper(),
                            content=content,
                            analysis="Correct Answer",
                            is_correct=True,
                            is_user_choice=True
                        )
                    ]
                ), None
        
        # ========== Incorrect answer, detailed diagnosis required ==========
        self._log(f"Question {question.id} incorrect. Starting detailed diagnosis...")
        
        # Prepare solving steps for context
        solve_steps = "\n".join([f"{i+1}. {step}" for i, step in enumerate(solve_result.key_steps)])
        solve_steps += f"\nFinal Conclusion: {solve_result.final_reason}"
        
        # Choose prompt based on problem type
        if problem_type == "numeric_entry":
            # Numeric entry diagnosis
            return self._diagnose_numeric_entry(
                question, solve_result, user_answer, correct_answer, 
                solve_steps, retry_on_failure
            )
        else:
            # Multiple choice diagnosis
            return self._diagnose_multiple_choice(
                question, solve_result, user_answer.upper(), correct_answer.upper(),
                solve_steps, retry_on_failure
            )
    
    def _diagnose_multiple_choice(
        self,
        question: Question,
        solve_result: SolveResult,
        user_answer: str,
        correct_answer: str,
        solve_steps: str,
        retry_on_failure: bool
    ) -> tuple[Optional[DiagnoseResult], Optional[str]]:
        """Diagnoses Multiple Choice errors."""
        
        # Prepare option contents
        choices = question.choices
        choice_a = choices.get("A", "N/A")
        choice_b = choices.get("B", "N/A")
        choice_c = choices.get("C", "N/A")
        choice_d = choices.get("D", "N/A")
        choice_e = choices.get("E", "N/A")
        
        # Construct user prompt
        user_prompt = DIAGNOSE_USER_PROMPT_TEMPLATE_CHOICE.format(
            question_id=question.id,
            stem=question.stem,
            choice_a=choice_a,
            choice_b=choice_b,
            choice_c=choice_c,
            choice_d=choice_d,
            choice_e=choice_e,
            user_answer=user_answer,
            correct_answer=correct_answer,
            solve_steps=solve_steps
        )
        
        # Call LLM
        response = self.llm.generate_json(
            system_prompt=DIAGNOSE_SYSTEM_PROMPT_CHOICE,
            user_prompt=user_prompt,
            schema_hint=DIAGNOSE_SCHEMA_HINT,
            temperature=0.3
        )
        
        if not response.success:
            self._log(f"LLM call failed: {response.error}", "error")
            return None, response.error
        
        # Parse response
        result = validate_diagnose_result(response.content)
        
        if result.success:
            diagnose_result = result.data
            diagnose_result.question_id = question.id
            diagnose_result.user_answer = user_answer
            diagnose_result.correct_answer = correct_answer
            diagnose_result.is_correct = False
            self._log(f"Multiple choice diagnosis complete for question {question.id}")
            return diagnose_result, None
        
        # Parsing failed, try to retry
        if retry_on_failure:
            self._log(f"First parsing attempt failed, retrying... Error: {result.error}", "warning")
            
            response = self.llm.generate_json(
                system_prompt=DIAGNOSE_SYSTEM_PROMPT_CHOICE,
                user_prompt=user_prompt + "\n\nPlease output strictly in JSON format without any other text.",
                schema_hint=DIAGNOSE_SCHEMA_HINT,
                temperature=0.1
            )
            
            if response.success:
                result = validate_diagnose_result(response.content)
                if result.success:
                    diagnose_result = result.data
                    diagnose_result.question_id = question.id
                    diagnose_result.user_answer = user_answer
                    diagnose_result.correct_answer = correct_answer
                    diagnose_result.is_correct = False
                    self._log(f"Retry successful, diagnosis complete for question {question.id}")
                    return diagnose_result, None
        
        # Return default multiple choice diagnosis if LLM parsing fails completely
        self._log(f"Diagnosis parsing failed for question {question.id}, using default result.", "warning")
        return self._build_default_choice_result(
            question, user_answer, correct_answer, solve_steps
        ), None
    
    def _diagnose_numeric_entry(
        self,
        question: Question,
        solve_result: SolveResult,
        user_answer: str,
        correct_answer: str,
        solve_steps: str,
        retry_on_failure: bool
    ) -> tuple[Optional[DiagnoseResult], Optional[str]]:
        """Diagnoses Numeric Entry errors."""
        
        # Construct user prompt
        user_prompt = DIAGNOSE_USER_PROMPT_TEMPLATE_NUMERIC.format(
            question_id=question.id,
            stem=question.stem,
            user_answer=user_answer,
            correct_answer=correct_answer,
            solve_steps=solve_steps
        )
        
        # Call LLM
        response = self.llm.generate_json(
            system_prompt=DIAGNOSE_SYSTEM_PROMPT_NUMERIC,
            user_prompt=user_prompt,
            temperature=0.3
        )
        
        if not response.success:
            self._log(f"LLM call failed: {response.error}", "error")
            return None, response.error
        
        # Parse numeric entry diagnosis response
        diagnose_result = self._parse_numeric_diagnose_response(
            response.content, question.id, user_answer, correct_answer
        )
        
        if diagnose_result:
            self._log(f"Numeric entry diagnosis complete for question {question.id}")
            return diagnose_result, None
        
        # Parsing failed, try to retry
        if retry_on_failure:
            self._log(f"First parsing attempt failed, retrying...", "warning")
            
            response = self.llm.generate_json(
                system_prompt=DIAGNOSE_SYSTEM_PROMPT_NUMERIC,
                user_prompt=user_prompt + "\n\nPlease output strictly in JSON format without any other text.",
                temperature=0.1
            )
            
            if response.success:
                diagnose_result = self._parse_numeric_diagnose_response(
                    response.content, question.id, user_answer, correct_answer
                )
                if diagnose_result:
                    self._log(f"Retry successful, diagnosis complete for question {question.id}")
                    return diagnose_result, None
        
        # Return default numeric diagnosis if LLM parsing fails completely
        self._log(f"Diagnosis parsing failed for question {question.id}, using default result.", "warning")
        return self._build_default_numeric_result(
            question.id, user_answer, correct_answer, solve_steps
        ), None
    
    def _parse_numeric_diagnose_response(
        self,
        content: str,
        question_id: str,
        user_answer: str,
        correct_answer: str
    ) -> Optional[DiagnoseResult]:
        """Parses LLM response for numeric entry diagnosis."""
        try:
            extracted = extract_json_from_text(content)
            if not extracted:
                return None
            
            data = json.loads(extracted)
            
            # Map numeric entry fields (supporting potential variation in field names)
            why_wrong = data.get("why_user_answer_is_wrong") or data.get("why_user_choice_is_tempting", "")
            
            return DiagnoseResult(
                question_id=question_id,
                user_answer=user_answer,
                correct_answer=correct_answer,
                is_correct=False,
                why_user_choice_is_tempting=why_wrong,
                likely_misconceptions=data.get("likely_misconceptions", ["Possible calculation error", "Potential conceptual misunderstanding"]),
                how_to_get_correct=data.get("how_to_get_correct", f"The correct answer is {correct_answer}"),
                option_analysis=[]  # No option analysis for numeric entry
            )
        except Exception:
            return None
    
    def _build_default_choice_result(
        self,
        question: Question,
        user_answer: str,
        correct_answer: str,
        solve_steps: str
    ) -> DiagnoseResult:
        """Constructs a default Multiple Choice diagnosis result."""
        return DiagnoseResult(
            question_id=question.id,
            user_answer=user_answer,
            correct_answer=correct_answer,
            is_correct=False,
            why_user_choice_is_tempting=f"Option {user_answer} might be a common distractor and shares similarities with the correct answer {correct_answer}.",
            likely_misconceptions=["Possible calculation error", "Potential misunderstanding of related concepts"],
            how_to_get_correct=f"The correct answer is {correct_answer}. Please refer to the following solving steps:\n{solve_steps}",
            option_analysis=[
                OptionAnalysis(
                    option=user_answer,
                    content=question.choices.get(user_answer, ""),
                    analysis="The incorrect option selected by the user.",
                    is_correct=False,
                    is_user_choice=True
                ),
                OptionAnalysis(
                    option=correct_answer,
                    content=question.choices.get(correct_answer, ""),
                    analysis="The correct answer.",
                    is_correct=True,
                    is_user_choice=False
                )
            ]
        )
    
    def _build_default_numeric_result(
        self,
        question_id: str,
        user_answer: str,
        correct_answer: str,
        solve_steps: str
    ) -> DiagnoseResult:
        """Constructs a default Numeric Entry diagnosis result."""
        return DiagnoseResult(
            question_id=question_id,
            user_answer=user_answer,
            correct_answer=correct_answer,
            is_correct=False,
            why_user_choice_is_tempting=f"Your answer is {user_answer}, but the correct answer is {correct_answer}. An error might have occurred during a step in the calculation.",
            likely_misconceptions=["Possible calculation error", "Potential misunderstanding of formulas or concepts"],
            how_to_get_correct=f"The correct answer is {correct_answer}. Please refer to the following solving steps:\n{solve_steps}",
            option_analysis=[]  # No option analysis for numeric entry
        )
    
    def diagnose_batch(
        self,
        questions: list[Question],
        solve_results: list[SolveResult],
        user_answers: dict[str, str]
    ) -> tuple[list[DiagnoseResult], list[str]]:
        """
        Batch diagnosis.
        
        Args:
            questions: List of Question objects.
            solve_results: List of SolveResult objects.
            user_answers: Dictionary of user answers {question_id: answer}.
        
        Returns:
            (List of DiagnoseResult, List of error messages)
        """
        results = []
        errors = []
        
        # Build a mapping of solving results
        solve_map = {sr.question_id: sr for sr in solve_results}
        
        for question in questions:
            if question.id not in user_answers:
                continue  # Skip if not answered
            
            user_answer = user_answers[question.id]
            if not user_answer:
                continue  # Skip if empty answer
            
            solve_result = solve_map.get(question.id)
            if not solve_result:
                errors.append(f"Missing solving result for question {question.id}")
                continue
            
            result, error = self.diagnose(question, solve_result, user_answer)
            if result:
                results.append(result)
            if error:
                errors.append(error)
        
        return results, errors