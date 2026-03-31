"""
settings.py — Central configuration for the MISRA GenAI system.

All paths, ports, model settings, and thresholds are defined here.
No other script should hardcode paths or config values.
"""

from __future__ import annotations
from pathlib import Path

# ---------------------------------------------------------------------------
# Base paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

APP_DIR  = PROJECT_ROOT / "app"
DATA_DIR = PROJECT_ROOT / "data"

INPUT_DIR           = DATA_DIR / "input"
SOURCE_CODE_DIR     = INPUT_DIR / "source_code"
WARNING_REPORTS_DIR = INPUT_DIR / "warning_reports"

KNOWLEDGE_DIR   = DATA_DIR / "knowledge"
KB_OUTPUT_DIR   = KNOWLEDGE_DIR / "output_processed_01" / "misra_kb_output"
FAISS_INDEX_DIR = KNOWLEDGE_DIR / "output_processed_01" / "faiss_index"

OUTPUT_DIR = DATA_DIR / "output"
AUDIT_DIR  = DATA_DIR / "audit"
CACHE_DIR  = DATA_DIR / "cache"
CACHE_PATH = CACHE_DIR / "results_cache.db"

# ---------------------------------------------------------------------------
# llama-server
# ---------------------------------------------------------------------------
LLAMA_HOST    = "127.0.0.1"
LLAMA_PORT    = 8080
LLAMA_TIMEOUT = 300

# ---------------------------------------------------------------------------
# LLM generation
# ---------------------------------------------------------------------------
LLM_TEMPERATURE     = 0.0
LLM_MAX_TOKENS      = 1536   # bumped from 1024 — gives model room for full patches
LLM_MAX_TOKENS_EVAL = 1536

# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_K_EXACT     = 10
TOP_K_SEMANTIC  = 6

# ---------------------------------------------------------------------------
# Prompt limits
# ---------------------------------------------------------------------------
MAX_SOURCE_LINES  = 40
MAX_KB_CHARS      = 2500   # bumped from 2000
MAX_KB_CHARS_EVAL = 3000

# ---------------------------------------------------------------------------
# Batch / UI
# ---------------------------------------------------------------------------
DEFAULT_BATCH_SIZE = 5

# ---------------------------------------------------------------------------
# Evaluation thresholds
# ---------------------------------------------------------------------------
LOW_CONFIDENCE_THRESHOLD = "Medium"

# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
REPORT_TITLE = "MISRA C 2012 — Fix Suggestions Report"
COMPANY_NAME = "MISRA GenAI Analysis System"

# ---------------------------------------------------------------------------
# Web server
# ---------------------------------------------------------------------------
WEB_HOST     = "127.0.0.1"
WEB_PORT     = 5000
WEB_DEBUG    = False
MAX_UPLOAD_MB = 50
