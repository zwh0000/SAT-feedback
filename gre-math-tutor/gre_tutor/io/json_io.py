"""
JSON 输入输出模块
处理结构化数据的读写
"""

import json
import os
from typing import Any, Optional
from datetime import datetime

from ..core.models import (
    Question,
    SolveResult,
    DiagnoseResult,
    TranscribeOutput,
    SessionResult
)


def save_json(data: Any, file_path: str, indent: int = 2) -> None:
    """
    保存数据到 JSON 文件
    
    Args:
        data: 要保存的数据（支持 Pydantic 模型）
        file_path: 输出路径
        indent: 缩进空格数
    """
    os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
    
    # 处理 Pydantic 模型
    if hasattr(data, 'model_dump'):
        data = data.model_dump()
    elif isinstance(data, list):
        data = [item.model_dump() if hasattr(item, 'model_dump') else item for item in data]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent, default=str)


def load_json(file_path: str) -> Any:
    """
    从 JSON 文件加载数据
    
    Args:
        file_path: 文件路径
    
    Returns:
        解析后的数据
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_transcribed(questions: list[Question], file_path: str) -> None:
    """保存抽题结果"""
    data = {
        "questions": [q.model_dump() for q in questions],
        "total": len(questions),
        "timestamp": datetime.now().isoformat()
    }
    save_json(data, file_path)


def load_transcribed(file_path: str) -> list[Question]:
    """加载抽题结果"""
    data = load_json(file_path)
    questions_data = data.get("questions", data) if isinstance(data, dict) else data
    return [Question.model_validate(q) for q in questions_data]


def save_solve_results(results: list[SolveResult], file_path: str) -> None:
    """保存求解结果"""
    data = {
        "solve_results": [r.model_dump() for r in results],
        "total": len(results),
        "timestamp": datetime.now().isoformat()
    }
    save_json(data, file_path)


def load_solve_results(file_path: str) -> list[SolveResult]:
    """加载求解结果"""
    data = load_json(file_path)
    results_data = data.get("solve_results", data) if isinstance(data, dict) else data
    return [SolveResult.model_validate(r) for r in results_data]


def save_session_result(result: SessionResult, file_path: str) -> None:
    """保存完整 session 结果"""
    save_json(result.model_dump(), file_path)


def load_session_result(file_path: str) -> SessionResult:
    """加载 session 结果"""
    data = load_json(file_path)
    return SessionResult.model_validate(data)


def create_session_output(
    session_id: str,
    pdf_path: str,
    mode: str,
    questions: list[Question],
    failed_pages: list[int],
    errors: list[str],
    solve_results: Optional[list[SolveResult]] = None,
    diagnose_results: Optional[list[DiagnoseResult]] = None,
    user_answers: Optional[dict[str, str]] = None
) -> SessionResult:
    """
    创建 session 输出对象
    
    Args:
        session_id: 会话 ID
        pdf_path: PDF 路径
        mode: 运行模式
        questions: 抽取的题目
        failed_pages: 失败的页码
        errors: 错误信息
        solve_results: 求解结果
        diagnose_results: 诊断结果
        user_answers: 用户答案
    
    Returns:
        SessionResult 对象
    """
    # 计算统计信息
    total_questions = len(questions)
    answered_questions = len(user_answers) if user_answers else 0
    correct_count = 0
    incorrect_ids = []
    
    if diagnose_results:
        for dr in diagnose_results:
            if dr.is_correct:
                correct_count += 1
            else:
                incorrect_ids.append(dr.question_id)
    
    return SessionResult(
        session_id=session_id,
        pdf_path=pdf_path,
        mode=mode,
        timestamp=datetime.now().isoformat(),
        transcribed=TranscribeOutput(
            questions=questions,
            total_pages=len(set(q.source.page for q in questions)) if questions else 0,
            failed_pages=failed_pages,
            errors=errors
        ),
        solve_results=solve_results or [],
        diagnose_results=diagnose_results or [],
        total_questions=total_questions,
        answered_questions=answered_questions,
        correct_count=correct_count,
        incorrect_ids=incorrect_ids
    )

