"""
Main Processing Pipeline
Coordinates execution of each stage
"""

import os
from typing import Optional, Literal
from pathlib import Path

from ..llm.base import LLMClient
from ..llm.openai_client import OpenAIClient
from ..llm.mock_client import MockLLMClient
from ..ingest.pdf_to_images import pdf_to_images, PDFConversionError
from ..ingest.vision_extract import VisionQuestionExtractor
from ..ingest.ocr_extract import OCRExtractor, OCR_AVAILABLE
from ..ingest.text_extract import TextQuestionExtractor
from .solver import QuestionSolver
from .diagnose import ErrorDiagnoser
from .models import SessionResult, SolveResult, Question
from ..io.json_io import (
    save_json,
    save_transcribed,
    save_session_result,
    create_session_output
)
from ..io.report_md import save_report_md, print_summary
from ..io.answers import (
    collect_answers_interactive, 
    load_answers_from_json,
    ask_correct_answers_choice,
    ask_user_answers_choice
)
from ..io.student_simulator import ask_simulate_student
from ..utils.logging import Logger, create_session_logger
from ..utils.time import generate_session_id


RunMode = Literal["transcribe_only", "solve", "diagnose"]
SubjectType = Literal["math", "english"]


def load_correct_answers_as_solve_results(
    json_path: str, 
    questions: list[Question]
) -> list[SolveResult]:
    """
    Load answers from correct answers JSON file, convert to SolveResult list
    
    Args:
        json_path: Correct answers JSON file path
        questions: Question list (for question info)
    
    Returns:
        SolveResult list
    """
    import json
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    question_map = {q.id: q for q in questions}
    
    solve_results = []
    
    # Support two formats:
    # 1. Simple: {"p1_q1": "A", "p1_q2": "B"}
    # 2. Detailed: {"p1_q1": {"answer": "A", "topic": "algebra", "steps": [...]}}
    
    for q_id, value in data.items():
        if q_id.startswith("_"):
            continue
        if q_id not in question_map:
            continue
        
        question = question_map[q_id]
        
        if isinstance(value, dict):
            solve_results.append(SolveResult(
                question_id=q_id,
                correct_answer=str(value.get("answer", value.get("correct_answer", ""))),
                topic=value.get("topic", "unknown"),
                key_steps=value.get("steps", value.get("key_steps", ["Standard answer (no solution steps)"])),
                final_reason=value.get("reason", value.get("final_reason", "From correct answers file")),
                confidence=value.get("confidence", 1.0)
            ))
        else:
            solve_results.append(SolveResult(
                question_id=q_id,
                correct_answer=str(value),
                topic="unknown",
                key_steps=["Standard answer (no solution steps)"],
                final_reason="From correct answers file",
                confidence=1.0
            ))
    
    return solve_results


class GREMathPipeline:
    """
    SAT Problem Processing Pipeline
    Coordinates PDF processing, transcription, solving, diagnosis stages
    Supports both Math (vision-based) and English (OCR-based) extraction
    """
    
    def __init__(
        self,
        use_mock: bool = False,
        output_dir: str = "outputs",
        subject: SubjectType = "math"
    ):
        """
        Initialize pipeline
        
        Args:
            use_mock: Whether to use mock client
            output_dir: Output directory
            subject: Subject type - "math" (vision) or "english" (OCR)
        """
        self.output_dir = output_dir
        self.use_mock = use_mock
        self.subject = subject
        
        if use_mock:
            self.llm: LLMClient = MockLLMClient()
        else:
            openai_client = OpenAIClient()
            if openai_client.is_available:
                self.llm = openai_client
            else:
                print("Warning: OpenAI API Key not configured, using Mock mode")
                self.llm = MockLLMClient()
        
        self.session_id: Optional[str] = None
        self.session_dir: Optional[str] = None
        self.logger: Optional[Logger] = None
    
    def _init_session(self) -> None:
        """Initialize session"""
        self.session_id = generate_session_id()
        self.session_dir = os.path.join(self.output_dir, f"session_{self.session_id}")
        os.makedirs(self.session_dir, exist_ok=True)
        os.makedirs(os.path.join(self.session_dir, "pages"), exist_ok=True)
        self.logger = create_session_logger(self.session_dir)
    
    def run(
        self,
        pdf_path: str,
        mode: RunMode = "diagnose",
        pages: str = "all",
        dpi: int = 300,
        answers_json: Optional[str] = None,
        correct_answers_json: Optional[str] = None,
        interactive: bool = True
    ) -> SessionResult:
        """
        Run complete pipeline
        
        Args:
            pdf_path: PDF file path
            mode: Run mode
            pages: Page range
            dpi: Image resolution
            answers_json: User answers JSON file path (CLI preset)
            correct_answers_json: Correct answers JSON file path (CLI preset)
            interactive: Enable interactive selection (default True)
        
        Returns:
            SessionResult object
        """
        self._init_session()
        
        self.logger.info(f"Starting to process PDF: {pdf_path}")
        self.logger.info(f"Run mode: {mode}")
        self.logger.info(f"Subject: {self.subject}")
        self.logger.info(f"Page range: {pages}")
        
        pdf_name = os.path.basename(pdf_path)
        
        # ===== Stage 0: PDF to Images =====
        self.logger.info("Stage 0: PDF to Images")
        
        try:
            pages_dir = os.path.join(self.session_dir, "pages")
            image_paths = pdf_to_images(
                pdf_path=pdf_path,
                output_dir=pages_dir,
                pages=pages,
                dpi=dpi
            )
            self.logger.info(f"Successfully converted {len(image_paths)} pages")
        except PDFConversionError as e:
            self.logger.error(f"PDF conversion failed: {e}")
            raise
        
        # ===== Stage T: Transcribe =====
        self.logger.info("Stage T: Transcribe")
        
        if self.subject == "english":
            # English: OCR + Text LLM extraction
            questions, failed_pages, errors = self._extract_english_questions(
                image_paths=image_paths,
                pdf_name=pdf_name
            )
        else:
            # Math: Vision LLM extraction
            extractor = VisionQuestionExtractor(self.llm, self.logger)
            questions, failed_pages, errors = extractor.extract_from_images(
                image_paths=image_paths,
                pdf_name=pdf_name
            )
        
        self.logger.info(f"Successfully extracted {len(questions)} questions")
        if failed_pages:
            self.logger.warning(f"Failed pages: {failed_pages}")
        
        transcribed_path = os.path.join(self.session_dir, "transcribed.json")
        save_transcribed(questions, transcribed_path)
        
        if mode == "transcribe_only":
            result = create_session_output(
                session_id=self.session_id,
                pdf_path=pdf_path,
                mode=mode,
                questions=questions,
                failed_pages=failed_pages,
                errors=errors
            )
            self._save_and_print(result)
            return result
        
        # ===== Stage S: Solve =====
        use_correct_file = correct_answers_json
        
        if interactive and not correct_answers_json and mode == "diagnose":
            use_correct_file = ask_correct_answers_choice(questions)
        
        if use_correct_file:
            self.logger.info("Stage S: Using correct answers file")
            try:
                solve_results = load_correct_answers_as_solve_results(
                    use_correct_file, questions
                )
                self.logger.info(f"Loaded {len(solve_results)} answers from correct answers file")
                
                loaded_ids = {sr.question_id for sr in solve_results}
                missing_questions = [q for q in questions if q.id not in loaded_ids]
                
                if missing_questions:
                    missing_ids = [q.id for q in missing_questions]
                    self.logger.warning(f"Following questions not found in correct answers file, will use LLM to solve: {missing_ids}")
                    
                    solver = QuestionSolver(self.llm, self.logger)
                    extra_results, extra_errors = solver.solve_batch(missing_questions)
                    
                    solve_results.extend(extra_results)
                    errors.extend(extra_errors)
                    
                    self.logger.info(f"LLM supplemented {len(extra_results)} questions")
                    
            except Exception as e:
                self.logger.error(f"Failed to load correct answers file: {e}")
                raise ValueError(f"Cannot load correct answers file: {e}")
        else:
            self.logger.info("Stage S: LLM Solving")
            
            solver = QuestionSolver(self.llm, self.logger)
            solve_results, solve_errors = solver.solve_batch(questions)
            
            self.logger.info(f"Successfully solved {len(solve_results)} questions")
            errors.extend(solve_errors)
        
        if mode == "solve":
            result = create_session_output(
                session_id=self.session_id,
                pdf_path=pdf_path,
                mode=mode,
                questions=questions,
                failed_pages=failed_pages,
                errors=errors,
                solve_results=solve_results
            )
            self._save_and_print(result)
            return result
        
        # ===== Collect User Answers =====
        self.logger.info("Collecting user answers")
        
        if answers_json:
            try:
                user_answers = load_answers_from_json(answers_json)
                self.logger.info(f"Loaded {len(user_answers)} user answers from {answers_json}")
            except Exception as e:
                self.logger.error(f"Failed to load user answers file: {e}")
                user_answers = {}
        elif interactive:
            user_answers = ask_user_answers_choice(
                questions, 
                llm_client=self.llm,
                solve_results=solve_results,
                session_dir=self.session_dir,
                subject=self.subject
            )
        else:
            user_answers = {}
        
        # ===== Stage D: Diagnose =====
        self.logger.info("Stage D: Diagnose")
        
        diagnoser = ErrorDiagnoser(self.llm, self.logger)
        diagnose_results, diagnose_errors = diagnoser.diagnose_batch(
            questions=questions,
            solve_results=solve_results,
            user_answers=user_answers
        )
        
        self.logger.info(f"Completed diagnosis for {len(diagnose_results)} questions")
        errors.extend(diagnose_errors)
        
        result = create_session_output(
            session_id=self.session_id,
            pdf_path=pdf_path,
            mode=mode,
            questions=questions,
            failed_pages=failed_pages,
            errors=errors,
            solve_results=solve_results,
            diagnose_results=diagnose_results,
            user_answers=user_answers
        )
        
        self._save_and_print(result)
        return result
    
    def _extract_english_questions(
        self,
        image_paths: list[str],
        pdf_name: str
    ) -> tuple[list[Question], list[int], list[str]]:
        """
        Extract English questions using OCR + Text LLM
        
        Args:
            image_paths: List of image file paths
            pdf_name: PDF file name
        
        Returns:
            (questions, failed_pages, errors)
        """
        if not OCR_AVAILABLE:
            error_msg = (
                "OCR is not available. Install with:\n"
                "  pip install pytesseract Pillow\n"
                "  brew install tesseract (macOS) or apt-get install tesseract-ocr (Linux)"
            )
            self.logger.error(error_msg)
            raise ImportError(error_msg)
        
        # Step 1: OCR - Extract text from images
        self.logger.info("Step 1: OCR text extraction")
        ocr_extractor = OCRExtractor(lang="eng", logger=self.logger)
        page_texts, ocr_failed, ocr_errors = ocr_extractor.extract_text_from_images(image_paths)
        
        if ocr_failed:
            self.logger.warning(f"OCR failed for pages: {ocr_failed}")
        
        # Save OCR text for debugging
        ocr_text_path = os.path.join(self.session_dir, "ocr_text.txt")
        combined_text = ocr_extractor.combine_texts(page_texts)
        with open(ocr_text_path, 'w', encoding='utf-8') as f:
            f.write(combined_text)
        self.logger.info(f"OCR text saved to: {ocr_text_path}")
        
        # Step 2: LLM - Extract questions from OCR text
        self.logger.info("Step 2: LLM question extraction from OCR text")
        text_extractor = TextQuestionExtractor(self.llm, self.logger)
        questions, extract_failed, extract_errors = text_extractor.extract_from_page_texts(
            page_texts=page_texts,
            pdf_name=pdf_name
        )
        
        # Combine failures and errors
        failed_pages = list(set(ocr_failed + extract_failed))
        errors = ocr_errors + extract_errors
        
        return questions, failed_pages, errors
    
    def _save_and_print(self, result: SessionResult) -> None:
        """Save results and print summary"""
        results_path = os.path.join(self.session_dir, "results.json")
        save_session_result(result, results_path)
        
        report_path = os.path.join(self.session_dir, "report.md")
        save_report_md(result, report_path)
        
        print_summary(result)
        
        self.logger.info(f"Results saved to: {self.session_dir}")
        self.logger.close()
