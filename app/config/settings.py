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
LLM_MAX_TOKENS      = 6000   # increased: full MISRA JSON with 3+ fixes needs ~4500 tokens
LLM_MAX_TOKENS_EVAL = 1536

# ---------------------------------------------------------------------------
# LLM hardware auto-detection  (stdlib only — no psutil dependency)
# ---------------------------------------------------------------------------
# Reads available RAM and CPU cores at startup and computes the best
# n_ctx, n_threads, and n_gpu_layers for the loaded model automatically.
# You never need to hardcode these values.
# ---------------------------------------------------------------------------

import ctypes as _ctypes
import math   as _math
import os     as _os
import sys    as _sys


def _get_ram_bytes():
    """Return (total_bytes, available_bytes) using stdlib only."""
    if _sys.platform == "win32":
        class _MEMSTATUS(_ctypes.Structure):
            _fields_ = [
                ("dwLength",                _ctypes.c_ulong),
                ("dwMemoryLoad",            _ctypes.c_ulong),
                ("ullTotalPhys",            _ctypes.c_ulonglong),
                ("ullAvailPhys",            _ctypes.c_ulonglong),
                ("ullTotalPageFile",        _ctypes.c_ulonglong),
                ("ullAvailPageFile",        _ctypes.c_ulonglong),
                ("ullTotalVirtual",         _ctypes.c_ulonglong),
                ("ullAvailVirtual",         _ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", _ctypes.c_ulonglong),
            ]
        s = _MEMSTATUS()
        s.dwLength = _ctypes.sizeof(s)
        _ctypes.windll.kernel32.GlobalMemoryStatusEx(_ctypes.byref(s))
        return int(s.ullTotalPhys), int(s.ullAvailPhys)
    else:
        # Linux / macOS
        try:
            info = {}
            for line in open("/proc/meminfo"):
                parts = line.split()
                if len(parts) >= 2:
                    info[parts[0].rstrip(":")] = int(parts[1]) * 1024
            total = info.get("MemTotal", 0)
            avail = info.get("MemAvailable", info.get("MemFree", 0))
            return total, avail
        except Exception:
            return 8 * 1024**3, 4 * 1024**3   # safe fallback


def _cuda_device_count():
    """Return number of CUDA GPUs using ctypes — no torch/nvidia-ml needed."""
    try:
        if _sys.platform == "win32":
            lib = _ctypes.CDLL("nvcuda.dll")
        else:
            lib = _ctypes.CDLL("libcuda.so.1")
        count = _ctypes.c_int(0)
        lib.cuInit(0)
        lib.cuDeviceGetCount(_ctypes.byref(count))
        return count.value
    except Exception:
        return 0


def _auto_llm_config(
    model_size_gb: float = 4.4,    # Mistral-7B Q4_K_M weights on disk
    kv_per_1k_ctx: float = 0.06,   # GB of KV cache per 1024 ctx tokens (Q4_K_M quantised KV, empirical)
    model_max_ctx: int   = 32768,  # model's trained context limit
    os_headroom_gb: float= 1.0,    # keep free for OS + other processes
) -> dict:
    """
    Compute optimal (n_ctx, n_threads, n_gpu_layers) from live hardware.

    n_ctx   — as large as RAM allows, capped at model_max_ctx.
              MINIMUM is 8192 — the MISRA prompt + JSON response needs ~6k tokens.
    n_threads — all physical cores minus 2 for OS  (min 1)
    n_gpu_layers — full offload if CUDA GPU detected, else 0
    """
    total_bytes, avail_bytes = _get_ram_bytes()
    total_gb = total_bytes / 1024**3
    avail_gb = avail_bytes / 1024**3

    # How much RAM is free for the KV cache after model weights + OS headroom
    free_for_kv = avail_gb - model_size_gb - os_headroom_gb

    # Minimum context = 8192 regardless of RAM (prompt alone is ~2k tokens,
    # full JSON response needs ~4k more — 8192 is the safe floor)
    MIN_CTX = 8192

    if free_for_kv < 0.5:
        n_ctx = MIN_CTX
    else:
        raw_ctx = int((free_for_kv / kv_per_1k_ctx) * 1024)
        n_ctx   = min(model_max_ctx, 2 ** int(_math.log2(max(raw_ctx, MIN_CTX))))
        n_ctx   = max(MIN_CTX, n_ctx)

    # CPU threads — leave 2 cores for OS scheduler
    cpu_cores = _os.cpu_count() or 4
    n_threads = max(1, cpu_cores - 2)

    # GPU — full layer offload if CUDA is present
    has_gpu      = _cuda_device_count() > 0
    n_gpu_layers = 33 if has_gpu else 0   # 33 = all layers for Mistral-7B

    return {
        "n_ctx":         n_ctx,
        "n_threads":     n_threads,
        "n_gpu_layers":  n_gpu_layers,
        "ram_total_gb":  round(total_gb, 1),
        "ram_avail_gb":  round(avail_gb, 1),
        "cpu_cores":     cpu_cores,
        "has_gpu":       has_gpu,
    }


# Run once at import time — used by orchestrator.py
_HW = _auto_llm_config()

LLM_N_CTX        = _HW["n_ctx"]
LLM_N_THREADS    = _HW["n_threads"]
LLM_N_GPU_LAYERS = _HW["n_gpu_layers"]

print(
    f"[settings] Hardware auto-detected: "
    f"RAM {_HW['ram_avail_gb']:.1f}/{_HW['ram_total_gb']:.1f} GB  "
    f"CPUs {_HW['cpu_cores']}  "
    f"GPU {'yes' if _HW['has_gpu'] else 'no'}  →  "
    f"n_ctx={LLM_N_CTX}  n_threads={LLM_N_THREADS}  "
    f"n_gpu_layers={LLM_N_GPU_LAYERS}"
)



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