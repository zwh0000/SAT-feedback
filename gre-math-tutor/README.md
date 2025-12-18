# SAT Tutor - Intelligent Problem Diagnosis System

An end-to-end problem processing system that supports PDF question extraction, automatic solving, and error diagnosis. Works with both **SAT Math** (vision-based) and **SAT English** (OCR-based).

## Features

- **PDF to Images**: Automatically convert PDF pages to high-resolution images
- **Question Extraction (Stage T)**: 
  - Math: Use GPT Vision to extract structured questions from images
  - English: Use OCR + Text LLM to extract questions from text
- **Intelligent Solving (Stage S)**: Automatically solve questions with key steps
- **Error Diagnosis (Stage D)**: Compare user answers, analyze errors, and provide corrective guidance
- **Student Simulation**: Let AI simulate a student answering questions with realistic mistakes

## System Requirements

- Python 3.9+
- Poppler (for PDF to image conversion)
- Tesseract OCR (for SAT English mode only)

## Installation

### 1. Install Poppler (Required)

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
1. Download Poppler for Windows: https://github.com/oschwartz10612/poppler-windows/releases
2. Extract to `C:\Program Files\poppler`
3. Add `C:\Program Files\poppler\Library\bin` to system PATH

### 2. Install Tesseract OCR (Optional - for SAT English)

#### macOS
```bash
brew install tesseract
```

#### Ubuntu/Debian
```bash
sudo apt-get install tesseract-ocr
```

#### Windows
Download from: https://github.com/UB-Mannheim/tesseract/wiki

### 3. Create Virtual Environment and Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example config file and fill in your API Key:

```bash
cp .env.example .env
```

Edit `.env` file:

```env
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL_VISION=gpt-4o
OPENAI_MODEL_TEXT=gpt-4o-mini
```

## Quick Start (Most Common Commands)

### SAT Math - Full Diagnosis
```bash
python -m gre_tutor.run --pdf data/samples/Linear_Equations.pdf --subject math --mode diagnose
```
(Replace `data/samples/Linear_Equations.pdf` with your own PDF file path)

### SAT English - Full Diagnosis
```bash
python -m gre_tutor.run --pdf data/samples/Cross.pdf --subject english --mode diagnose
```
(Replace `data/samples/Cross.pdf` with your own PDF file path)

### With Preset Correct Answers (Skip LLM Solving)
```bash
# Math
python -m gre_tutor.run --pdf data/samples/Linear_Equations.pdf --subject math --correct-answers data/samples/correct_answers_simple.json --mode diagnose

# English
python -m gre_tutor.run --pdf data/samples/Cross.pdf --subject english --correct-answers data/samples/correct_answers_simple.json --mode diagnose
```
(Replace file paths with your own PDF and answer JSON files)

After running, the system will:
1. Convert PDF to images
2. Extract questions (Vision for Math, OCR for English)
3. Solve questions (or use your correct answers file)
4. Ask you to input answers (interactive, file, or simulate student)
5. Diagnose errors and generate report

## Project Structure

```
gre-math-tutor/
├── gre_tutor/
│   ├── __init__.py
│   ├── run.py                    # CLI entry point
│   │
│   ├── core/                     # Core business logic
│   │   ├── models.py             # Pydantic data models (Question, SolveResult, DiagnoseResult)
│   │   ├── pipeline.py           # Main processing pipeline
│   │   ├── solver.py             # Stage S: Question solving logic
│   │   ├── diagnose.py           # Stage D: Error diagnosis logic
│   │   ├── validators.py         # JSON schema validation
│   │   └── taxonomy.py           # Error classification taxonomy
│   │
│   ├── ingest/                   # Input processing
│   │   ├── pdf_to_images.py      # PDF to PNG conversion
│   │   ├── page_range.py         # Page range parsing (e.g., "1-3,5")
│   │   ├── vision_extract.py     # Stage T: Vision-based extraction (Math)
│   │   ├── ocr_extract.py        # OCR text extraction (English)
│   │   └── text_extract.py       # Stage T: Text-based extraction (English)
│   │
│   ├── llm/                      # LLM integration
│   │   ├── base.py               # Abstract LLM client interface
│   │   ├── openai_client.py      # OpenAI API client (supports compatible APIs)
│   │   ├── mock_client.py        # Mock client for testing without API
│   │   └── prompts.py            # All prompt templates for each stage
│   │
│   ├── io/                       # Input/Output handling
│   │   ├── answers.py            # User answer collection (interactive/file)
│   │   ├── json_io.py            # JSON file operations
│   │   ├── report_md.py          # Markdown report generation
│   │   └── student_simulator.py  # AI student simulation
│   │
│   └── utils/                    # Utilities
│       ├── logging.py            # Logging utilities
│       └── time.py               # Timestamp generation
│
├── data/samples/                 # Sample data files
├── outputs/                      # Output directory
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable template
└── README.md                     # This file
```

## File Descriptions

### Core Modules (`gre_tutor/core/`)

| File | Description |
|------|-------------|
| `models.py` | Pydantic models: `Question`, `SolveResult`, `DiagnoseResult`, `SessionResult` |
| `pipeline.py` | Main pipeline orchestrating all stages (PDF→Extract→Solve→Diagnose) |
| `solver.py` | Question solving using LLM with step-by-step reasoning |
| `diagnose.py` | Error diagnosis comparing user answer vs correct answer |
| `validators.py` | JSON schema validation for LLM outputs |
| `taxonomy.py` | Classification of error types and misconceptions |

### Input Processing (`gre_tutor/ingest/`)

| File | Description |
|------|-------------|
| `pdf_to_images.py` | Convert PDF pages to PNG images using pdf2image |
| `page_range.py` | Parse page range strings like "1-3,5,7-10" |
| `vision_extract.py` | Extract Math questions using GPT Vision |
| `ocr_extract.py` | Extract text from images using Tesseract OCR |
| `text_extract.py` | Extract English questions from OCR text using LLM |

### LLM Integration (`gre_tutor/llm/`)

| File | Description |
|------|-------------|
| `base.py` | Abstract `LLMClient` interface |
| `openai_client.py` | OpenAI API implementation (supports DeepSeek, etc.) |
| `mock_client.py` | Mock responses for testing without API |
| `prompts.py` | All prompt templates for transcription, solving, diagnosis |

### I/O Handling (`gre_tutor/io/`)

| File | Description |
|------|-------------|
| `answers.py` | Collect user answers (interactive input or JSON file) |
| `json_io.py` | Save/load JSON files and session results |
| `report_md.py` | Generate human-readable Markdown reports |
| `student_simulator.py` | Simulate student answering with configurable accuracy |

## Usage Commands

### Basic Commands

```bash
# Full pipeline: Extract + Solve + Diagnose (interactive answer input)
python -m gre_tutor.run --pdf input.pdf --mode diagnose

# Transcribe only (extract questions)
python -m gre_tutor.run --pdf input.pdf --mode transcribe_only

# Transcribe + Solve (no diagnosis)
python -m gre_tutor.run --pdf input.pdf --mode solve
```

### Subject Selection

```bash
# GRE/SAT Math (default) - uses Vision LLM
python -m gre_tutor.run --pdf math_test.pdf --subject math

# SAT English - uses OCR + Text LLM
python -m gre_tutor.run --pdf english_test.pdf --subject english
```

### Page Selection

```bash
# Process specific pages
python -m gre_tutor.run --pdf input.pdf --pages "1-3,5,7"

# Process all pages (default)
python -m gre_tutor.run --pdf input.pdf --pages all
```

### Answer Input Methods

```bash
# Interactive input (default)
python -m gre_tutor.run --pdf input.pdf --mode diagnose

# Use preset user answers file
python -m gre_tutor.run --pdf input.pdf --answers user_answers.json --mode diagnose

# Use correct answers file (skip LLM solving)
python -m gre_tutor.run --pdf input.pdf --correct-answers correct.json --mode diagnose

# Both preset files (fully automated)
python -m gre_tutor.run --pdf input.pdf --correct-answers correct.json --answers user.json --no-interactive
```

### Advanced Options

```bash
# Higher image resolution (better OCR)
python -m gre_tutor.run --pdf input.pdf --dpi 400

# Custom output directory
python -m gre_tutor.run --pdf input.pdf --outdir my_outputs/

# Offline mode (mock data, no API needed)
python -m gre_tutor.run --pdf input.pdf --no-llm --mode transcribe_only

# Non-interactive mode (use all CLI arguments)
python -m gre_tutor.run --pdf input.pdf --no-interactive --correct-answers correct.json
```

### Student Simulation

During interactive mode, you can choose to simulate a student:

```bash
python -m gre_tutor.run --pdf input.pdf --mode diagnose
```

Then select option `[3] Simulate student` when prompted for answer input method.

## Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--pdf` | PDF file path | **Required** |
| `--subject` | Subject type: `math` or `english` | `math` |
| `--mode` | Run mode: `transcribe_only`, `solve`, `diagnose` | `diagnose` |
| `--pages` | Page range, e.g., "1-3,5" or "all" | `all` |
| `--dpi` | Image resolution | `300` |
| `--outdir` | Output directory | `outputs/` |
| `--answers` | Preset user answers JSON file | None |
| `--correct-answers` | Preset correct answers JSON file | None |
| `--no-llm` | Force mock mode (no API needed) | `False` |
| `--no-interactive` | Disable interactive prompts | `False` |

## Output Structure

Each run creates a timestamped session folder:

```
outputs/
  session_20241216_143052/
    pages/                 # PDF converted images
      page_001.png
      page_002.png
    ocr_text.txt           # OCR extracted text (English mode only)
    transcribed.json       # Extracted questions
    results.json           # Solve + Diagnose results
    report.md              # Human-readable report
    logs.txt               # Run logs
    simulated_student_answers.json         # (if simulation used)
    simulated_student_answers_details.json # (detailed simulation output)
```

## Environment Variables

### Main API Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | API key | **Required** (unless `--no-llm`) |
| `OPENAI_API_BASE` | API base URL (for compatible APIs) | OpenAI default |
| `OPENAI_MODEL_VISION` | Vision model (for question extraction) | `gpt-4o` |
| `OPENAI_MODEL_TEXT` | Text model (for solving/diagnosis) | `gpt-4o-mini` |

### Student Simulation Configuration (Optional)

| Variable | Description | Default |
|----------|-------------|---------|
| `STUDENT_API_KEY` | Student simulation API key | Same as `OPENAI_API_KEY` |
| `STUDENT_API_BASE` | Student simulation API base URL | Same as `OPENAI_API_BASE` |
| `STUDENT_MODEL` | Student simulation model | Same as `OPENAI_MODEL_TEXT` |
| `STUDENT_CORRECT_RATE` | Target accuracy rate (0-100) | `70` |

### Example .env Configurations

#### OpenAI
```env
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL_VISION=gpt-4o
OPENAI_MODEL_TEXT=gpt-4o-mini
```

#### DeepSeek
```env
OPENAI_API_KEY=sk-your-deepseek-key
OPENAI_API_BASE=https://api.deepseek.com
OPENAI_MODEL_VISION=deepseek-chat
OPENAI_MODEL_TEXT=deepseek-chat
```

#### Mixed (OpenAI for main, DeepSeek for student simulation)
```env
# Main API uses OpenAI
OPENAI_API_KEY=sk-openai-key
OPENAI_MODEL_VISION=gpt-4o
OPENAI_MODEL_TEXT=gpt-4o-mini

# Student simulation uses DeepSeek (cheaper)
STUDENT_API_KEY=sk-deepseek-key
STUDENT_API_BASE=https://api.deepseek.com
STUDENT_MODEL=deepseek-chat
STUDENT_CORRECT_RATE=70
```

### Supported API Platforms

| Platform | API Base URL | Example Models |
|----------|-------------|----------------|
| OpenAI | (default, no need to set) | gpt-4o, gpt-4o-mini |
| DeepSeek | https://api.deepseek.com | deepseek-chat |
| Zhipu AI | https://open.bigmodel.cn/api/paas/v4 | glm-4-flash |
| Moonshot | https://api.moonshot.cn/v1 | moonshot-v1-8k |
| Local Ollama | http://localhost:11434/v1 | llama3, qwen2 |

## Answer File Formats

### Simple Format (user answers or correct answers)
```json
{
  "p1_q1": "A",
  "p1_q2": "B",
  "p1_q3": "14",
  "p2_q1": "C"
}
```

### Detailed Format (correct answers with explanations)
```json
{
  "p1_q1": {
    "answer": "A",
    "topic": "algebra",
    "steps": ["Step 1...", "Step 2..."],
    "reason": "Because..."
  }
}
```
