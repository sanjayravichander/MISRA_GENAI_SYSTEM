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

KNOWLEDGE_DIR    = DATA_DIR / "knowledge"
KB_OUTPUT_DIR    = KNOWLEDGE_DIR / "output_processed_01" / "misra_kb_output"
# FAISS kept for reference only — retrieval now uses Qdrant
FAISS_INDEX_DIR  = KNOWLEDGE_DIR / "output_processed_01" / "faiss_index"

# Qdrant + Excel KB paths (active retrieval system)
QDRANT_INDEX_DIR = KNOWLEDGE_DIR / "qdrant_index"
EXCEL_KB_PATH    = KNOWLEDGE_DIR / "excel_kb" / "misra_excel_kb.json"

OUTPUT_DIR = DATA_DIR / "output"
AUDIT_DIR  = DATA_DIR / "audit"
CACHE_DIR  = DATA_DIR / "cache"

# Two separate caches — both in use
CACHE_PATH           = CACHE_DIR / "results_cache.db"          # result-level cache
RETRIEVAL_CACHE_PATH = CACHE_DIR / "retrieval_cache.sqlite3"   # retrieval-level cache

# ---------------------------------------------------------------------------
# llama-server  (Phase 7 — HTTP API)
# ---------------------------------------------------------------------------
LLAMA_HOST    = "127.0.0.1"
LLAMA_PORT    = 8080
LLAMA_TIMEOUT = 300

# ---------------------------------------------------------------------------
# llama-cpp Python bindings  (generate_misra_response.py)
# Model path used by GenerationConfig in generate_misra_response.py
# ---------------------------------------------------------------------------
LOCAL_MODEL_PATH = r"C:\models\Mistral-7B-Instruct-v0.3-Q4_K_M.gguf"

# ---------------------------------------------------------------------------
# LLM generation settings
# ---------------------------------------------------------------------------
LLM_TEMPERATURE     = 0.0
LLM_MAX_TOKENS      = 3500
LLM_MAX_TOKENS_EVAL = 1536

# ---------------------------------------------------------------------------
# Retrieval  (Qdrant + BGE — active system)
# ---------------------------------------------------------------------------
EMBEDDING_MODEL   = "BAAI/bge-base-en-v1.5"   # single authoritative value
COLLECTION_NAME   = "misra_excel_kb"
TOP_K_EXACT       = 10
TOP_K_SEMANTIC    = 6

# ---------------------------------------------------------------------------
# Postprocessor threshold
# Lower this if too many warnings return 0 rules after filtering
# ---------------------------------------------------------------------------
RETRIEVAL_MIN_SCORE = 0.70   # was 0.85 — too aggressive, caused empty outputs

# ---------------------------------------------------------------------------
# Prompt limits
# ---------------------------------------------------------------------------
MAX_SOURCE_LINES  = 40
MAX_KB_CHARS      = 2500
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
WEB_HOST      = "127.0.0.1"
WEB_PORT      = 5000
WEB_DEBUG     = False
MAX_UPLOAD_MB = 50