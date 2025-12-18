# GRE Math Tutor - 智能数学题诊断系统

一个端到端的 GRE 数学题处理系统，支持 PDF 题目抽取、自动求解和错因诊断。

## 功能特性

- **PDF 转图片**：自动将 PDF 页面转换为高清图片
- **视觉抽题 (Stage T)**：使用 GPT Vision 从图片中提取结构化题目
- **智能求解 (Stage S)**：自动求解题目并给出关键步骤
- **错因诊断 (Stage D)**：对比用户答案，分析错误原因并给出纠错指导

## 系统要求

- Python 3.9+
- Poppler（PDF 转图片依赖）

## 安装步骤

### 1. 安装 Poppler

#### macOS
```bash
brew install poppler
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils
```

#### Windows
1. 下载 Poppler for Windows: https://github.com/oschwartz10612/poppler-windows/releases
2. 解压到 `C:\Program Files\poppler`
3. 添加 `C:\Program Files\poppler\Library\bin` 到系统 PATH

### 2. 创建虚拟环境并安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

复制示例配置文件并填入你的 API Key：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL_VISION=gpt-4o
OPENAI_MODEL_TEXT=gpt-4o-mini
```

## 使用方法

### 基本命令

```bash
# 完整流程：抽题 + 求解 + 错因诊断（交互式输入答案）
python -m gre_tutor.run --pdf data/samples/sample.pdf --mode diagnose

# 仅抽题模式
python -m gre_tutor.run --pdf data/samples/sample.pdf --mode transcribe_only

# 抽题 + 求解（不做诊断）
python -m gre_tutor.run --pdf data/samples/sample.pdf --mode solve

# 指定页码范围
python -m gre_tutor.run --pdf data/samples/sample.pdf --pages "1-3,5" --mode diagnose

# 使用 JSON 文件提供答案
python -m gre_tutor.run --pdf data/samples/sample.pdf --answers data/samples/answers.json --mode diagnose

# 离线模式（使用 mock 数据，无需 API Key）
python -m gre_tutor.run --pdf data/samples/sample.pdf --no-llm --mode transcribe_only

# 使用标准答案文件（跳过 LLM 求解）
python -m gre_tutor.run --pdf data/samples/sample.pdf --correct-answers data/samples/correct_answers.json
```

### 🎭 模拟学生答题

系统支持让 AI 模拟学生做题，生成带有常见错误的答案：

```bash
# 运行完整流程，在答案输入时选择 [3] 模拟学生答题
python -m gre_tutor.run --pdf data/samples/sample.pdf
```

在交互式菜单中选择：
```
📝 用户答案输入方式
======================================================================

你可以选择：
  [1] 逐题交互式输入 → 一道题一道题显示并输入答案
  [2] 批量文件输入   → 先显示所有题目，然后输入答案文件路径
  [3] 🎭 模拟学生答题 → 让 AI 扮演学生做题（会故意犯一些错误）

请选择 [1/2/3]: 3
```

模拟学生会：
- 扮演中等水平学生
- 按配置的正确率（默认 60%-80%）答题
- 犯常见错误（计算粗心、公式记错、审题不仔细等）
- 将模拟答案保存到文件

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--pdf` | PDF 文件路径 | 必填 |
| `--pages` | 页码范围，如 "1-3,5" 或 "all" | all |
| `--mode` | 运行模式：transcribe_only/solve/diagnose | diagnose |
| `--dpi` | 图片分辨率 | 300 |
| `--outdir` | 输出目录 | outputs/ |
| `--answers` | 答案 JSON 文件路径 | 无（交互输入） |
| `--no-llm` | 强制使用 mock 模式 | False |

## 输出结构

每次运行会在输出目录创建一个带时间戳的 session 文件夹：

```
outputs/
  session_20241216_143052/
    pages/                 # PDF 转出的页图
      page_001.png
      page_002.png
    transcribed.json       # 抽题结果
    results.json           # 判分+诊断结果
    report.md              # 人类可读报告
    logs.txt               # 运行日志
```

## 输出示例

### report.md 示例

```markdown
# GRE Math Tutor 诊断报告

**生成时间**: 2024-12-16 14:30:52
**PDF 文件**: sample.pdf
**处理页数**: 2
**题目总数**: 3

---

## 📊 总结

- **作答题数**: 3
- **正确数**: 2
- **正确率**: 66.7%
- **错题**: p1_q2

---

## 📝 题目详情

### 题目 p1_q1 ✅

**题干**: If x + 2 = 5, what is the value of x?

**选项**:
- A: 1
- B: 2
- C: 3 ✓
- D: 4
- E: 5

**用户答案**: C | **正确答案**: C

**关键步骤**:
1. 从等式 x + 2 = 5 出发
2. 两边同时减去 2
3. 得到 x = 3

---

### 题目 p1_q2 ❌

**题干**: What is the area of a circle with radius 3?

**选项**:
- A: 6π
- B: 9π ✓
- C: 12π
- D: 18π
- E: 27π

**用户答案**: A | **正确答案**: B

#### 🔍 错因分析

**为什么容易误选 A**:
选项 A (6π) 是直径乘以 π 的结果，可能是将面积公式 πr² 误记为 2πr（周长公式的一半）...

**可能的认知误区**:
1. 混淆了圆面积公式和圆周长公式
2. 将 r² 误算为 2r

**如何得到正确答案**:
1. 回忆圆面积公式：A = πr²
2. 代入 r = 3
3. 计算：A = π × 3² = 9π
4. 因此正确答案是 B

---
```

## 题目 JSON Schema

抽题结果遵循以下结构：

```json
{
  "id": "p1_q1",
  "source": {"pdf": "sample.pdf", "page": 1},
  "exam": "GRE",
  "section": "Math",
  "problem_type": "multiple_choice",
  "stem": "题干文本",
  "choices": {
    "A": "选项A内容",
    "B": "选项B内容",
    "C": "选项C内容",
    "D": "选项D内容",
    "E": "选项E内容"
  },
  "latex_equations": ["x^2 + 2x + 1 = 0"],
  "diagram_description": "图形描述或 null",
  "constraints": [],
  "uncertain_spans": [],
  "confidence": 0.95
}
```

## 环境变量说明

### 主 API 配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `OPENAI_API_KEY` | API 密钥 | 无（必填，除非使用 --no-llm） |
| `OPENAI_API_BASE` | API Base URL（支持第三方兼容 API） | 无（使用 OpenAI 默认） |
| `OPENAI_MODEL_VISION` | 视觉模型名称（用于抽题） | gpt-4o |
| `OPENAI_MODEL_TEXT` | 文本模型名称（用于求解和诊断） | gpt-4o-mini |

### 学生模拟专用配置（可选）

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `STUDENT_API_KEY` | 学生模拟专用 API Key | 同 OPENAI_API_KEY |
| `STUDENT_API_BASE` | 学生模拟专用 API Base URL | 同 OPENAI_API_BASE |
| `STUDENT_MODEL` | 学生模拟使用的模型 | 同 OPENAI_MODEL_TEXT |
| `STUDENT_CORRECT_RATE` | 模拟学生正确率（0-100 的整数） | 70 |

### .env 配置示例

#### 使用 OpenAI

```env
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL_VISION=gpt-4o
OPENAI_MODEL_TEXT=gpt-4o-mini
```

#### 使用 DeepSeek

```env
OPENAI_API_KEY=sk-your-deepseek-key
OPENAI_API_BASE=https://api.deepseek.com
OPENAI_MODEL_VISION=deepseek-chat
OPENAI_MODEL_TEXT=deepseek-chat
```

#### 学生模拟使用不同的 API（如 DeepSeek）

```env
# 主 API 用 OpenAI
OPENAI_API_KEY=sk-openai-key
OPENAI_MODEL_VISION=gpt-4o
OPENAI_MODEL_TEXT=gpt-4o-mini

# 学生模拟用 DeepSeek（更便宜）
STUDENT_API_KEY=sk-deepseek-key
STUDENT_API_BASE=https://api.deepseek.com
STUDENT_MODEL=deepseek-chat
STUDENT_CORRECT_RATE=70
```

#### 常用 API Base URL

| 平台 | API Base URL | 示例模型 |
|------|-------------|----------|
| OpenAI | 默认（不需要设置） | gpt-4o, gpt-4o-mini |
| DeepSeek | https://api.deepseek.com | deepseek-chat |
| 智谱 AI | https://open.bigmodel.cn/api/paas/v4 | glm-4-flash |
| 月之暗面 | https://api.moonshot.cn/v1 | moonshot-v1-8k |
| 本地 Ollama | http://localhost:11434/v1 | llama3, qwen2 |

## 常见问题

### Q: 没有 OpenAI API Key 能运行吗？
A: 可以，使用 `--no-llm` 参数会启用 mock 模式，返回预设的测试数据。

### Q: 支持哪些 PDF 格式？
A: 支持标准 PDF 文件。扫描件和包含数学公式的 PDF 都可以处理。

### Q: 如何提高抽题准确率？
A: 使用更高的 DPI（如 `--dpi 400`）可以提高图片清晰度，从而提升识别准确率。

### Q: 求解阶段答案不准确怎么办？
A: **强烈建议使用 gpt-4o 或更强的模型进行求解**：

```env
# 使用 gpt-4o 进行求解（更准确但更贵）
OPENAI_MODEL_TEXT=gpt-4o

# 或者使用 DeepSeek（性价比高，数学能力强）
OPENAI_API_BASE=https://api.deepseek.com
OPENAI_MODEL_TEXT=deepseek-chat
```

gpt-4o-mini 的数学能力较弱，复杂题目容易出错。如果你有标准答案，建议使用 `--correct-answers` 参数跳过 LLM 求解。

## License

MIT License

