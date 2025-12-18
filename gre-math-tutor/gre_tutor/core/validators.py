"""
数据验证工具
用于验证 LLM 输出的 JSON 是否符合 schema
"""

import json
from typing import Type, TypeVar, Optional
from pydantic import BaseModel, ValidationError

from .models import Question, SolveResult, DiagnoseResult

T = TypeVar('T', bound=BaseModel)


class ValidationResult:
    """验证结果"""
    def __init__(self, success: bool, data: Optional[BaseModel] = None, error: Optional[str] = None):
        self.success = success
        self.data = data
        self.error = error


def validate_json_to_model(json_str: str, model_class: Type[T]) -> ValidationResult:
    """
    将 JSON 字符串验证并转换为 Pydantic 模型
    
    Args:
        json_str: JSON 字符串
        model_class: 目标 Pydantic 模型类
    
    Returns:
        ValidationResult 包含成功标志、数据或错误信息
    """
    try:
        # 尝试解析 JSON
        data = json.loads(json_str)
        # 验证并创建模型实例
        instance = model_class.model_validate(data)
        return ValidationResult(success=True, data=instance)
    except json.JSONDecodeError as e:
        return ValidationResult(success=False, error=f"JSON 解析失败: {str(e)}")
    except ValidationError as e:
        return ValidationResult(success=False, error=f"Schema 验证失败: {str(e)}")


def validate_dict_to_model(data: dict, model_class: Type[T]) -> ValidationResult:
    """
    将字典验证并转换为 Pydantic 模型
    """
    try:
        instance = model_class.model_validate(data)
        return ValidationResult(success=True, data=instance)
    except ValidationError as e:
        return ValidationResult(success=False, error=f"Schema 验证失败: {str(e)}")


def extract_json_from_text(text: str) -> Optional[str]:
    """
    从文本中提取 JSON 内容
    处理 LLM 可能输出的 markdown 代码块
    """
    text = text.strip()
    
    # 尝试找到 JSON 代码块
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end != -1:
            return text[start:end].strip()
    
    # 尝试找到普通代码块
    if "```" in text:
        start = text.find("```") + 3
        # 跳过可能的语言标识
        if text[start:start+10].strip().startswith('{') or text[start:start+10].strip().startswith('['):
            pass
        else:
            newline = text.find('\n', start)
            if newline != -1:
                start = newline + 1
        end = text.find("```", start)
        if end != -1:
            return text[start:end].strip()
    
    # 尝试直接找 JSON 对象或数组
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = text.find(start_char)
        if start != -1:
            # 找到匹配的结束符
            depth = 0
            for i, c in enumerate(text[start:]):
                if c == start_char:
                    depth += 1
                elif c == end_char:
                    depth -= 1
                    if depth == 0:
                        return text[start:start+i+1]
    
    return None


def validate_questions_list(json_str: str) -> ValidationResult:
    """验证题目列表"""
    try:
        extracted = extract_json_from_text(json_str)
        if extracted is None:
            return ValidationResult(success=False, error="无法从文本中提取 JSON")
        
        data = json.loads(extracted)
        
        # 处理单个题目或题目列表
        if isinstance(data, dict):
            if 'questions' in data:
                questions_data = data['questions']
            else:
                questions_data = [data]
        elif isinstance(data, list):
            questions_data = data
        else:
            return ValidationResult(success=False, error="JSON 格式不正确：期望对象或数组")
        
        # 验证每个题目
        questions = []
        for q_data in questions_data:
            result = validate_dict_to_model(q_data, Question)
            if result.success:
                questions.append(result.data)
            else:
                return ValidationResult(success=False, error=f"题目验证失败: {result.error}")
        
        return ValidationResult(success=True, data=questions)
    except json.JSONDecodeError as e:
        return ValidationResult(success=False, error=f"JSON 解析失败: {str(e)}")


def validate_solve_result(json_str: str) -> ValidationResult:
    """验证求解结果"""
    extracted = extract_json_from_text(json_str)
    if extracted is None:
        return ValidationResult(success=False, error="无法从文本中提取 JSON")
    return validate_json_to_model(extracted, SolveResult)


def validate_diagnose_result(json_str: str) -> ValidationResult:
    """验证诊断结果"""
    extracted = extract_json_from_text(json_str)
    if extracted is None:
        return ValidationResult(success=False, error="无法从文本中提取 JSON")
    return validate_json_to_model(extracted, DiagnoseResult)

