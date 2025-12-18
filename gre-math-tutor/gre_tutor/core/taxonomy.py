"""
GRE 数学错误类型分类体系
用于诊断阶段的误区分类
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class MisconceptionType:
    """误区类型"""
    code: str
    name: str
    description: str
    examples: list[str]


# GRE 数学常见误区分类
MISCONCEPTION_TAXONOMY = {
    # 计算类错误
    "CALC_SIGN": MisconceptionType(
        code="CALC_SIGN",
        name="符号错误",
        description="正负号处理错误，如减法变加法",
        examples=["-(−3) 误算为 -3", "移项忘记变号"]
    ),
    "CALC_ORDER": MisconceptionType(
        code="CALC_ORDER",
        name="运算顺序错误",
        description="未按正确的运算优先级计算",
        examples=["2+3×4 计算为 20 而非 14", "先算加减后算乘除"]
    ),
    "CALC_DECIMAL": MisconceptionType(
        code="CALC_DECIMAL",
        name="小数/分数计算错误",
        description="小数点位置或分数运算出错",
        examples=["0.1 × 0.1 = 0.01 误算为 0.1", "通分计算错误"]
    ),
    "CALC_POWER": MisconceptionType(
        code="CALC_POWER",
        name="指数运算错误",
        description="幂运算规则应用错误",
        examples=["(x²)³ 误算为 x⁵", "x² × x³ 误算为 x⁶"]
    ),
    
    # 概念类错误
    "CONCEPT_FORMULA": MisconceptionType(
        code="CONCEPT_FORMULA",
        name="公式记忆错误",
        description="记错或混淆相关公式",
        examples=["圆面积用 2πr 代替 πr²", "混淆排列与组合公式"]
    ),
    "CONCEPT_DEFINITION": MisconceptionType(
        code="CONCEPT_DEFINITION",
        name="定义理解偏差",
        description="对数学概念的定义理解不准确",
        examples=["误解中位数的定义", "混淆因数和倍数"]
    ),
    "CONCEPT_PROPERTY": MisconceptionType(
        code="CONCEPT_PROPERTY",
        name="性质理解错误",
        description="对数学性质的理解或应用错误",
        examples=["负数平方仍为负", "平行线性质应用错误"]
    ),
    
    # 审题类错误
    "READ_CONDITION": MisconceptionType(
        code="READ_CONDITION",
        name="遗漏条件",
        description="忽略题目中的重要条件或限制",
        examples=["忽略 x > 0 的限制", "遗漏'整数'条件"]
    ),
    "READ_QUESTION": MisconceptionType(
        code="READ_QUESTION",
        name="误读问题",
        description="对题目要求的理解有偏差",
        examples=["求周长却算面积", "求最大值却求最小值"]
    ),
    "READ_UNITS": MisconceptionType(
        code="READ_UNITS",
        name="单位转换错误",
        description="忽略或错误处理单位转换",
        examples=["分钟与小时混用", "厘米与米未转换"]
    ),
    
    # 陷阱类错误
    "TRAP_INTERMEDIATE": MisconceptionType(
        code="TRAP_INTERMEDIATE",
        name="中间结果陷阱",
        description="将计算过程中的中间结果当作最终答案",
        examples=["求 2x 却只算出 x 就选答案", "约分前的结果"]
    ),
    "TRAP_SIMILAR": MisconceptionType(
        code="TRAP_SIMILAR",
        name="相似数值陷阱",
        description="选择了与正确答案相近的干扰项",
        examples=["正确是 12，误选 21", "正确是 3/4，误选 4/3"]
    ),
    "TRAP_COMMON": MisconceptionType(
        code="TRAP_COMMON",
        name="常见错误陷阱",
        description="选项设计为常见错误的结果",
        examples=["设计为符号错误的结果", "设计为少算一步的结果"]
    ),
    
    # 方法类错误
    "METHOD_WRONG": MisconceptionType(
        code="METHOD_WRONG",
        name="方法选择错误",
        description="使用了不适用于该题的解法",
        examples=["应该列方程却用算术法", "不等式两边除以负数忘变号"]
    ),
    "METHOD_INCOMPLETE": MisconceptionType(
        code="METHOD_INCOMPLETE",
        name="解法不完整",
        description="解题步骤遗漏或不完整",
        examples=["方程只解出一个根", "忘记验算舍去根"]
    ),
    
    # 逻辑类错误
    "LOGIC_REVERSE": MisconceptionType(
        code="LOGIC_REVERSE",
        name="因果颠倒",
        description="颠倒了条件和结论的关系",
        examples=["充分条件与必要条件混淆", "逆命题当原命题"]
    ),
    "LOGIC_SCOPE": MisconceptionType(
        code="LOGIC_SCOPE",
        name="范围判断错误",
        description="对取值范围或集合关系判断错误",
        examples=["不等式解集判断错误", "交集并集混淆"]
    )
}


def get_misconception_by_code(code: str) -> Optional[MisconceptionType]:
    """根据代码获取误区类型"""
    return MISCONCEPTION_TAXONOMY.get(code)


def get_misconceptions_by_topic(topic: str) -> list[MisconceptionType]:
    """根据题目主题获取可能的误区类型"""
    topic_misconceptions = {
        "algebra": ["CALC_SIGN", "CALC_ORDER", "CONCEPT_FORMULA", "METHOD_WRONG", "READ_CONDITION"],
        "geometry": ["CONCEPT_FORMULA", "CONCEPT_PROPERTY", "READ_UNITS", "CALC_DECIMAL"],
        "arithmetic": ["CALC_ORDER", "CALC_DECIMAL", "CALC_POWER", "READ_UNITS"],
        "data_analysis": ["CONCEPT_DEFINITION", "READ_QUESTION", "CALC_DECIMAL"],
        "number_theory": ["CONCEPT_DEFINITION", "CONCEPT_PROPERTY", "READ_CONDITION"],
        "word_problems": ["READ_CONDITION", "READ_QUESTION", "READ_UNITS", "METHOD_WRONG"]
    }
    
    codes = topic_misconceptions.get(topic, list(MISCONCEPTION_TAXONOMY.keys())[:5])
    return [MISCONCEPTION_TAXONOMY[code] for code in codes if code in MISCONCEPTION_TAXONOMY]


def format_misconception_for_prompt(misconception: MisconceptionType) -> str:
    """格式化误区类型供 prompt 使用"""
    return f"- {misconception.name}: {misconception.description}"


def get_all_misconceptions_prompt() -> str:
    """获取所有误区类型的 prompt 格式文本"""
    lines = ["常见 GRE 数学误区分类："]
    for m in MISCONCEPTION_TAXONOMY.values():
        lines.append(format_misconception_for_prompt(m))
    return "\n".join(lines)

