#!/usr/bin/env python3
"""
setup_and_upgrade.py  —  MISRA GenAI System: One-shot cleanup + upgrade

Run from the project root (where venv310/ lives):
    cd C:\\Users\\sanjay.ravichander\\misra_genai_system\\misra_genai_system
    venv310\\Scripts\\activate
    python setup_and_upgrade.py

What this script does
---------------------
1.  Removes dead stub/duplicate files and the superseded prototype test folder.
2.  Upgrades app/config/settings.py  (adds CACHE_PATH, DEFAULT_BATCH_SIZE,
    bumps LLM_MAX_TOKENS to 1536).
3.  Upgrades app/pipeline/generate_fixes.py  (new system prompt that forces
    2-3 MISRA-specific patches with actual BEFORE/AFTER code).
4.  Creates  app/pipeline/result_cache.py  (NEW: SQLite cache keyed by
    SHA-256 of rule_id + source_context + top-3 KB chunks).
5.  Upgrades app/web/server.py  (cache look-up, per-record SSE streaming,
    batch-size control, attaches _excel_row + _source_context to every result).
6.  Upgrades app/web/templates/index.html  (dark upload UI + live stream table).
7.  Creates   app/web/templates/results.html  (full warning cards with patch
    tabs, Excel row table, highlighted violated code, BEFORE/AFTER diffs).
8.  Upgrades app/web/static/style.css  (dark industrial theme).
9.  Upgrades app/web/static/script.js  (SSE streaming + patch tabs +
    Excel/code display).
10. Creates   run.bat  (double-click launcher).
11. Creates   data/cache/  directory for the SQLite result cache.
"""

from __future__ import annotations

import os
import shutil
import sys
import textwrap
from pathlib import Path

# ---------------------------------------------------------------------------
# Locate project root
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent

def confirm(prompt: str) -> bool:
    try:
        return input(prompt + " [y/N] ").strip().lower() == "y"
    except (EOFError, KeyboardInterrupt):
        return False

def write(path: Path, content: str, *, overwrite: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        print(f"  [skip]  {path.relative_to(HERE)}  (already exists)")
        return
    path.write_text(content, encoding="utf-8")
    print(f"  [write] {path.relative_to(HERE)}")

def remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
        print(f"  [del]   {path.relative_to(HERE)}/")
    elif path.is_file():
        path.unlink()
        print(f"  [del]   {path.relative_to(HERE)}")
    else:
        print(f"  [skip]  {path.relative_to(HERE)}  (not found)")

# ============================================================
#  1 — DEAD FILE REMOVAL
# ============================================================

DEAD_DIRS = [
    HERE / "app" / "ai",
    HERE / "app" / "domain",
    HERE / "app" / "validation",
    HERE / "tests" / "pipeline_prototypes_test_folder",
]

DEAD_FILES = [
    HERE / "app" / "knowledge" / "retrieval.py",
    HERE / "app" / "knowledge" / "rule_indexer.py",
    HERE / "app" / "knowledge" / "vector_store.py",
    HERE / "app" / "ingestion" / "normalizer.py",
    HERE / "app" / "ingestion" / "warning_reader.py",
]

# data/knowledge/processed_01/ duplicate scripts
_proc = HERE / "data" / "knowledge" / "processed_01"
for _name in [
    "parse_polyspace.py", "retrieve.py", "build_index.py",
    "generate_fixes.py", "generate_fix_suggestions.py",
]:
    DEAD_FILES.append(_proc / _name)


def step_remove_dead() -> None:
    print("\n── Step 1: Remove dead / stub / duplicate files ──────────────────")
    for d in DEAD_DIRS:
        remove(d)
    for f in DEAD_FILES:
        remove(f)


# ============================================================
#  2 — settings.py
# ============================================================

SETTINGS_PY = '''\
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
'''


# ============================================================
#  3 — generate_fixes.py (SYSTEM_PROMPT upgrade only — rest untouched)
# ============================================================

GENERATE_FIXES_PATCH_MARKER = 'SYSTEM_PROMPT = """'

NEW_SYSTEM_PROMPT = '''\
SYSTEM_PROMPT = """You are a MISRA C 2012 static analysis expert embedded in a CI/CD pipeline.
Your job: analyse each Polyspace warning and produce 2-3 RANKED, CONCRETE patch options.

STRICT RULES — violating any rule produces a useless result:
1. Output ONLY valid JSON matching the schema. No prose, no markdown fences, no text outside JSON.
2. ranked_fixes MUST contain 2 or 3 options (only 1 if the rule has exactly one valid fix).
3. Every fix MUST include code_change with ACTUAL C code lines — not pseudocode, not descriptions.
   Format:  BEFORE:\\n<original lines>\\nAFTER:\\n<corrected lines>
4. Every fix MUST cite the MISRA rule(s) it satisfies in misra_rules_applied.
5. confidence MUST be one of: High | Medium | Low — with these strict definitions:
   - High:   fix fully resolves the violation; no side effects; reviewer can approve immediately.
   - Medium: fix resolves violation but may need context-specific verification.
   - Low:    fix is a best-effort guess; manual review required.
6. Do NOT invent functions that do not exist in standard C (e.g., MISRA_puts does not exist).
7. Be specific to the code shown — never give generic advice.
8. risk_level must be one of: Critical | High | Medium | Low.

Required JSON schema:
{
  "warning_id": "string",
  "rule_id": "string",
  "explanation": "string — why this specific code violates the rule",
  "risk_analysis": "string — safety/quality risk if not fixed",
  "ranked_fixes": [
    {
      "rank": 1,
      "description": "string — one sentence: what to do",
      "code_change": "string — BEFORE:\\n<lines>\\nAFTER:\\n<lines>",
      "misra_rules_applied": ["Rule X.Y", "Rule A.B"],
      "rationale": "string — why this is the safest/best option",
      "risk_level": "string",
      "confidence": "High|Medium|Low"
    }
  ],
  "deviation_advice": "string — when deviation might be justified, or 'No deviation justified.'"
}"""
'''


def patch_generate_fixes() -> None:
    """Replace only the SYSTEM_PROMPT block in generate_fixes.py."""
    gf = HERE / "app" / "pipeline" / "generate_fixes.py"
    if not gf.exists():
        print(f"  [skip]  generate_fixes.py not found at {gf}")
        return

    src = gf.read_text(encoding="utf-8")

    # Find the start of SYSTEM_PROMPT = """
    start = src.find('SYSTEM_PROMPT = """')
    if start == -1:
        print("  [skip]  SYSTEM_PROMPT marker not found in generate_fixes.py")
        return

    # Find the closing triple-quote after it
    close = src.find('"""', start + len('SYSTEM_PROMPT = """'))
    if close == -1:
        print("  [skip]  Could not find closing triple-quote for SYSTEM_PROMPT")
        return

    end = close + 3  # include the closing """

    new_src = src[:start] + NEW_SYSTEM_PROMPT.strip() + "\n" + src[end:]

    # Also patch LLM_MAX_TOKENS if still 1024
    new_src = new_src.replace("LLM_MAX_TOKENS   = 1024", "LLM_MAX_TOKENS   = 1536")
    new_src = new_src.replace("LLM_MAX_TOKENS = 1024",   "LLM_MAX_TOKENS = 1536")

    gf.write_text(new_src, encoding="utf-8")
    print(f"  [patch] {gf.relative_to(HERE)}")


# ============================================================
#  4 — result_cache.py  (NEW)
# ============================================================

RESULT_CACHE_PY = '''\
"""
result_cache.py  —  SQLite result cache for MISRA GenAI pipeline.

Cache key: SHA-256 of (rule_id + source_context + top-3 KB chunk texts).
Same warning on re-run = instant result, no LLM call.

Usage
-----
    from app.pipeline.result_cache import ResultCache

    cache = ResultCache()                        # opens data/cache/results_cache.db
    hit = cache.get(rule_id, source_ctx, chunks) # None if not cached
    if hit is None:
        result = call_llm(...)
        cache.set(rule_id, source_ctx, chunks, result)
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from app.config.settings import CACHE_PATH
except ImportError:
    CACHE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "cache" / "results_cache.db"


def _fingerprint(rule_id: str, source_context: str, kb_chunks: List[str]) -> str:
    """Stable SHA-256 key for a (rule, source, kb) triple."""
    top3 = "||".join(kb_chunks[:3])
    raw = f"{rule_id.strip()}|||{source_context.strip()}|||{top3}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ResultCache:
    """Thread-safe SQLite-backed result cache."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = Path(db_path or CACHE_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS results (
                fingerprint TEXT PRIMARY KEY,
                rule_id     TEXT,
                result_json TEXT NOT NULL,
                created_at  REAL NOT NULL
            )
        """)
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rule ON results(rule_id)"
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    def get(
        self,
        rule_id: str,
        source_context: str,
        kb_chunks: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Return cached result dict, or None on cache miss."""
        fp = _fingerprint(rule_id, source_context, kb_chunks)
        row = self._conn.execute(
            "SELECT result_json FROM results WHERE fingerprint = ?", (fp,)
        ).fetchone()
        if row is None:
            return None
        try:
            result = json.loads(row[0])
            result["_from_cache"] = True
            return result
        except json.JSONDecodeError:
            return None

    def set(
        self,
        rule_id: str,
        source_context: str,
        kb_chunks: List[str],
        result: Dict[str, Any],
    ) -> None:
        """Store result in cache (upsert)."""
        fp = _fingerprint(rule_id, source_context, kb_chunks)
        # Don't persist the cache flag itself
        to_store = {k: v for k, v in result.items() if k != "_from_cache"}
        self._conn.execute(
            """
            INSERT INTO results (fingerprint, rule_id, result_json, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(fingerprint) DO UPDATE SET
                result_json = excluded.result_json,
                created_at  = excluded.created_at
            """,
            (fp, rule_id, json.dumps(to_store, ensure_ascii=False), time.time()),
        )
        self._conn.commit()

    def stats(self) -> Dict[str, Any]:
        """Return basic cache statistics."""
        row = self._conn.execute(
            "SELECT COUNT(*), COUNT(DISTINCT rule_id) FROM results"
        ).fetchone()
        return {"total_entries": row[0], "distinct_rules": row[1]}

    def clear(self) -> int:
        """Wipe all cached entries. Returns number deleted."""
        n = self._conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
        self._conn.execute("DELETE FROM results")
        self._conn.commit()
        return n

    def close(self) -> None:
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    cache = ResultCache()
    s = cache.stats()
    print(f"Cache at: {cache.db_path}")
    print(f"  entries:        {s[\'total_entries\']}")
    print(f"  distinct rules: {s[\'distinct_rules\']}")
'''


# ============================================================
#  5 — server.py  (full upgrade with cache + batch-size + streaming)
# ============================================================

SERVER_PY = r'''"""
app/web/server.py  —  MISRA GenAI Flask Web UI  (upgraded)

Changes vs original
-------------------
- Result cache: checks ResultCache before LLM call (instant on repeat runs)
- Per-record SSE: emits record_ready after each warning completes
- Batch-size control: user picks 1-15 via upload form (default 5)
- Attaches _excel_row + _source_context to every result record

Run from project root:
    python app/web/server.py
Then open http://127.0.0.1:5000
"""

import json
import os
import queue
import sys
import threading
import time
import uuid
from pathlib import Path

from flask import (Flask, Response, jsonify, render_template,
                   request, stream_with_context)
from flask_cors import CORS
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from app.config.settings import (
        FAISS_INDEX_DIR, KB_OUTPUT_DIR, LLAMA_HOST, LLAMA_PORT,
        OUTPUT_DIR, CACHE_PATH, DEFAULT_BATCH_SIZE,
    )
except ImportError:
    DATA_DIR        = PROJECT_ROOT / "data"
    KNOWLEDGE_DIR   = DATA_DIR / "knowledge"
    KB_OUTPUT_DIR   = KNOWLEDGE_DIR / "output_processed_01" / "misra_kb_output"
    FAISS_INDEX_DIR = KNOWLEDGE_DIR / "output_processed_01" / "faiss_index"
    OUTPUT_DIR      = DATA_DIR / "output"
    CACHE_PATH      = DATA_DIR / "cache" / "results_cache.db"
    DEFAULT_BATCH_SIZE = 5
    LLAMA_HOST      = "127.0.0.1"
    LLAMA_PORT      = 8080

UPLOAD_DIR = PROJECT_ROOT / "data" / "input" / "web_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

ALLOWED_EXCEL = {".xlsx", ".xls"}
ALLOWED_C     = {".c", ".h"}

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
_WEB_DIR      = Path(__file__).resolve().parent
_TEMPLATE_DIR = _WEB_DIR / "templates"
_STATIC_DIR   = _WEB_DIR / "static"

if not _TEMPLATE_DIR.exists():
    raise RuntimeError(
        f"\n\n[server.py] templates/ folder not found at:\n  {_TEMPLATE_DIR}\n\n"
        "Make sure index.html and results.html are in app\\web\\templates\\\n"
    )
if not _STATIC_DIR.exists():
    raise RuntimeError(
        f"\n\n[server.py] static/ folder not found at:\n  {_STATIC_DIR}\n\n"
        "Make sure style.css and script.js are in app\\web\\static\\\n"
    )

app = Flask(
    __name__,
    template_folder=str(_TEMPLATE_DIR),
    static_folder=str(_STATIC_DIR),
)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

JOBS: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Routes — pages
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", default_batch=DEFAULT_BATCH_SIZE)


@app.route("/results/<job_id>")
def results(job_id):
    if job_id not in JOBS:
        return "Job not found", 404
    return render_template("results.html", job_id=job_id)


# ---------------------------------------------------------------------------
# Route — start analysis
# ---------------------------------------------------------------------------
@app.route("/api/analyse", methods=["POST"])
def start_analysis():
    if "warning_report" not in request.files:
        return jsonify(error="No warning report uploaded"), 400
    excel_file = request.files["warning_report"]
    if Path(excel_file.filename).suffix.lower() not in ALLOWED_EXCEL:
        return jsonify(error="Warning report must be .xlsx or .xls"), 400

    c_files = request.files.getlist("source_files")
    if not c_files or all(f.filename == "" for f in c_files):
        return jsonify(error="No C source files uploaded"), 400

    # batch size (1–15)
    try:
        batch_size = max(1, min(15, int(request.form.get("batch_size", DEFAULT_BATCH_SIZE))))
    except (TypeError, ValueError):
        batch_size = DEFAULT_BATCH_SIZE

    job_id  = str(uuid.uuid4())[:8]
    job_dir = UPLOAD_DIR / job_id
    src_dir = job_dir / "source_code"
    src_dir.mkdir(parents=True, exist_ok=True)

    excel_path = job_dir / secure_filename(excel_file.filename)
    excel_file.save(str(excel_path))

    saved_c = []
    for f in c_files:
        if Path(f.filename).suffix.lower() in ALLOWED_C and f.filename:
            dest = src_dir / secure_filename(f.filename)
            f.save(str(dest))
            saved_c.append(dest.name)

    if not saved_c:
        return jsonify(error="No valid .c / .h files received"), 400

    q = queue.Queue()
    JOBS[job_id] = {
        "status":     "queued",
        "queue":      q,
        "result":     None,
        "error":      None,
        "excel":      str(excel_path),
        "src_dir":    str(src_dir),
        "c_files":    saved_c,
        "batch_size": batch_size,
        "started_at": time.time(),
        "records":    [],       # grows as warnings finish
    }

    t = threading.Thread(target=_run_pipeline, args=(job_id,), daemon=True)
    t.start()

    return jsonify(job_id=job_id, c_files=saved_c, batch_size=batch_size)


# ---------------------------------------------------------------------------
# Route — SSE progress stream
# ---------------------------------------------------------------------------
@app.route("/api/progress/<job_id>")
def progress_stream(job_id):
    if job_id not in JOBS:
        return Response('data: {"error": "Job not found"}\n\n',
                        mimetype="text/event-stream")

    def generate():
        q = JOBS[job_id]["queue"]
        while True:
            try:
                msg = q.get(timeout=30)
                yield f"data: {json.dumps(msg)}\n\n"
                if msg.get("type") in ("done", "error"):
                    break
            except queue.Empty:
                yield 'data: {"type": "heartbeat"}\n\n'

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Route — fetch full result JSON
# ---------------------------------------------------------------------------
@app.route("/api/result/<job_id>")
def get_result(job_id):
    if job_id not in JOBS:
        return jsonify(error="Job not found"), 404
    job = JOBS[job_id]
    if job["status"] not in ("done", "running"):
        return jsonify(error="Not ready yet", status=job["status"]), 202
    return jsonify({
        "job_id":   job_id,
        "status":   job["status"],
        "summary":  job.get("summary") or {},
        "warnings": job.get("records") or [],
        "out_dir":  str(PROJECT_ROOT / "data" / "output" / job_id),
    })


# ---------------------------------------------------------------------------
# Route — stream of completed records (for incremental results page)
# ---------------------------------------------------------------------------
@app.route("/api/records/<job_id>")
def get_records(job_id):
    if job_id not in JOBS:
        return jsonify(error="Job not found"), 404
    job = JOBS[job_id]
    after = int(request.args.get("after", 0))
    records = job.get("records", [])
    return jsonify({
        "records": records[after:],
        "total":   len(records),
        "done":    job["status"] == "done",
    })


# ---------------------------------------------------------------------------
# Route — cache stats
# ---------------------------------------------------------------------------
@app.route("/api/cache/stats")
def cache_stats():
    try:
        from app.pipeline.result_cache import ResultCache
        with ResultCache(CACHE_PATH) as c:
            return jsonify(c.stats())
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/api/cache/clear", methods=["POST"])
def cache_clear():
    try:
        from app.pipeline.result_cache import ResultCache
        with ResultCache(CACHE_PATH) as c:
            n = c.clear()
        return jsonify(deleted=n)
    except Exception as e:
        return jsonify(error=str(e)), 500


# ---------------------------------------------------------------------------
# Background pipeline runner
# ---------------------------------------------------------------------------
def _emit(job_id: str, msg: dict) -> None:
    JOBS[job_id]["queue"].put(msg)


def _run_pipeline(job_id: str) -> None:
    job       = JOBS[job_id]
    excel_path = job["excel"]
    src_dir    = job["src_dir"]
    batch_size = job.get("batch_size", DEFAULT_BATCH_SIZE)
    out_dir    = PROJECT_ROOT / "data" / "output" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    job["status"] = "running"

    try:
        # ── Phase 6a ───────────────────────────────────────────────────
        _emit(job_id, {
            "type": "phase_start", "phase": "6a",
            "label": "Parsing warning report",
            "detail": f"Reading {Path(excel_path).name}",
            "progress": 5,
        })
        from app.ingestion.parse_polyspace import parse_report
        parsed_raw = parse_report(Path(excel_path), Path(src_dir))
        parsed = parsed_raw if isinstance(parsed_raw, list) else parsed_raw.get("warnings", parsed_raw)
        (out_dir / "parsed_warnings.json").write_text(
            json.dumps(parsed, indent=2), encoding="utf-8"
        )
        n_warnings = len(parsed)

        # Respect batch_size
        parsed = parsed[:batch_size]
        n_batch = len(parsed)

        _emit(job_id, {
            "type": "phase_done", "phase": "6a",
            "label": "Parsing complete",
            "detail": f"{n_warnings} warnings found — processing {n_batch} (batch size {batch_size})",
            "progress": 15,
        })

        # ── Phase 6b ───────────────────────────────────────────────────
        _emit(job_id, {
            "type": "phase_start", "phase": "6b",
            "label": "Retrieving MISRA context",
            "detail": "Loading FAISS index + embedding model",
            "progress": 16,
        })
        from app.knowledge.retrieve import load_index, retrieve_for_warning
        from sentence_transformers import SentenceTransformer

        index, chunks, by_rule = load_index(Path(FAISS_INDEX_DIR))
        embed_model = SentenceTransformer("all-MiniLM-L6-v2")

        enriched_warnings = []
        for i_w, w in enumerate(parsed, 1):
            retrieved = retrieve_for_warning(w, index, chunks, by_rule, embed_model)
            enriched_warnings.append({**w, "misra_context": retrieved})
            _emit(job_id, {
                "type": "warning_done", "phase": "6b",
                "label": f"Context: {w.get('warning_id','')}",
                "detail": f"{i_w}/{n_batch} enriched",
                "progress": 16 + int((i_w / n_batch) * 14),
                "warning_id": w.get("warning_id", ""),
                "count": i_w, "total": n_batch,
            })

        enriched = {"warning_count": len(enriched_warnings), "warnings": enriched_warnings}
        (out_dir / "enriched_warnings.json").write_text(
            json.dumps(enriched, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        _emit(job_id, {
            "type": "phase_done", "phase": "6b",
            "label": "Context retrieval complete",
            "detail": f"{len(enriched_warnings)} warnings enriched",
            "progress": 30,
        })

        # ── Phase 7 ────────────────────────────────────────────────────
        _emit(job_id, {
            "type": "phase_start", "phase": "7",
            "label": "Generating fix suggestions",
            "detail": f"Mistral-7B processing {n_batch} warnings (~90s each)",
            "progress": 31,
        })

        from app.pipeline.generate_fixes import (
            check_server, build_prompt, call_llm, parse_llm_response,
            _fallback, SYSTEM_PROMPT,
        )

        # Try to load cache
        try:
            from app.pipeline.result_cache import ResultCache
            cache = ResultCache(CACHE_PATH)
            use_cache = True
        except Exception:
            cache = None
            use_cache = False

        check_server(LLAMA_HOST, LLAMA_PORT)

        fix_suggestions = []
        for idx, w in enumerate(enriched_warnings, 1):
            wid = w.get("warning_id", f"W{idx}")
            pct = 31 + int((idx / n_batch) * 34)

            # Build KB chunk texts for cache key
            ctx = w.get("misra_context") or {}
            if isinstance(ctx, list):
                kb_texts = [str(c) for c in ctx[:3]]
            elif isinstance(ctx, dict):
                kb_texts = [str(v) for v in list(ctx.values())[:3]]
            else:
                kb_texts = [str(ctx)]

            rule_id = w.get("rule_id", "")
            src_ctx = w.get("source_context", "") or w.get("source_code", "")

            # Cache lookup
            cached_result = None
            if use_cache and cache:
                try:
                    cached_result = cache.get(rule_id, src_ctx, kb_texts)
                except Exception:
                    pass

            if cached_result is not None:
                cached_result["_from_cache"] = True
                result = cached_result
                _emit(job_id, {
                    "type": "warning_done", "phase": "7",
                    "label": f"[CACHE] {wid} ({rule_id})",
                    "detail": f"{idx}/{n_batch} — from cache",
                    "progress": pct,
                    "warning_id": wid, "count": idx, "total": n_batch,
                    "from_cache": True,
                })
            else:
                _emit(job_id, {
                    "type": "warning_done", "phase": "7",
                    "label": f"Generating: {wid} ({rule_id})",
                    "detail": f"{idx}/{n_batch}",
                    "progress": pct,
                    "warning_id": wid, "count": idx, "total": n_batch,
                    "from_cache": False,
                })
                prompt = build_prompt(w)
                try:
                    raw    = call_llm(LLAMA_HOST, LLAMA_PORT, SYSTEM_PROMPT, prompt)
                    result = parse_llm_response(raw, wid, rule_id)
                    if result.get("parse_error"):
                        retry = prompt + "\n\nIMPORTANT: Output ONLY valid JSON. Start with { and end with }."
                        raw2   = call_llm(LLAMA_HOST, LLAMA_PORT, SYSTEM_PROMPT, retry)
                        res2   = parse_llm_response(raw2, wid, rule_id)
                        if not res2.get("parse_error"):
                            result = res2
                except Exception as exc:
                    result = _fallback(wid, rule_id, "", str(exc))

                # Store in cache
                if use_cache and cache and not result.get("parse_error"):
                    try:
                        cache.set(rule_id, src_ctx, kb_texts, result)
                    except Exception:
                        pass

            # Attach extra context fields
            result["_excel_row"]       = {k: str(v) for k, v in w.items()
                                           if k not in ("misra_context", "source_lines")}
            result["_source_context"]  = w.get("source_context", "") or w.get("source_code", "")

            fix_suggestions.append(result)

        if use_cache and cache:
            try:
                cache.close()
            except Exception:
                pass

        (out_dir / "fix_suggestions.json").write_text(
            json.dumps({"warning_count": len(fix_suggestions), "results": fix_suggestions},
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        _emit(job_id, {
            "type": "phase_done", "phase": "7",
            "label": "Fix generation complete",
            "detail": f"{len(fix_suggestions)}/{n_batch} fixes generated",
            "progress": 65,
        })

        # ── Phase 8 ────────────────────────────────────────────────────
        _emit(job_id, {
            "type": "phase_start", "phase": "8",
            "label": "Evaluating fix quality",
            "detail": "Self-critique pass",
            "progress": 66,
        })

        from app.pipeline.evaluate_fixes import (
            build_eval_prompt, call_llm as eval_call_llm,
            parse_eval_response, _eval_fallback, merge_evaluation,
        )
        try:
            from app.pipeline.evaluate_fixes import SYSTEM_PROMPT as EVAL_SYS
        except ImportError:
            EVAL_SYS = "You are a MISRA C 2012 expert. Evaluate the fix suggestion and return JSON."

        warning_by_id = {w.get("warning_id"): w for w in enriched_warnings}

        evaluated = []
        for idx, fix in enumerate(fix_suggestions, 1):
            wid = fix.get("warning_id", f"W{idx}")
            pct = 66 + int((idx / n_batch) * 29)
            _emit(job_id, {
                "type": "warning_done", "phase": "8",
                "label": f"Evaluating: {wid}",
                "detail": f"{idx}/{n_batch}",
                "progress": pct,
                "warning_id": wid, "count": idx, "total": n_batch,
            })
            warning_data = warning_by_id.get(wid, fix)
            try:
                eval_prompt = build_eval_prompt(warning_data, fix)
                raw_e       = eval_call_llm(LLAMA_HOST, LLAMA_PORT, EVAL_SYS, eval_prompt)
                eval_result = parse_eval_response(raw_e, wid, fix.get("rule_id", ""))
            except Exception as e_err:
                eval_result = _eval_fallback(wid, fix.get("rule_id", ""), str(e_err))

            merged = merge_evaluation(fix, eval_result)
            job["records"].append(merged)   # <-- incremental, results page can poll this

            # Emit per-record SSE so results page updates live
            _emit(job_id, {
                "type":       "record_ready",
                "warning_id": wid,
                "index":      idx - 1,
                "progress":   pct,
                "label":      f"Evaluated: {wid}",
                "detail":     f"{idx}/{n_batch}",
            })

            evaluated.append(merged)

        if not evaluated:
            evaluated = [{**f, "evaluation": {"overall_confidence": "Low"}}
                         for f in fix_suggestions]

        (out_dir / "evaluated_fixes.json").write_text(
            json.dumps(evaluated, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        _emit(job_id, {
            "type": "phase_done", "phase": "8",
            "label": "Evaluation complete",
            "detail": f"{len(evaluated)} warnings evaluated",
            "progress": 95,
        })

        # ── Finish ─────────────────────────────────────────────────────
        summary = _build_summary(evaluated, job)
        job["summary"] = summary
        job["status"]  = "done"

        _emit(job_id, {
            "type": "done",
            "label": "Analysis complete",
            "detail": f"Run saved to data/output/{job_id}/",
            "progress": 100,
            "summary": summary,
        })

    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        job["status"] = "error"
        job["error"]  = str(exc)
        _emit(job_id, {
            "type":      "error",
            "label":     "Pipeline failed",
            "detail":    str(exc),
            "traceback": tb,
            "progress":  0,
        })


def _build_summary(evaluated: list, job: dict) -> dict:
    high = medium = low = manual = cached = 0
    for w in evaluated:
        conf = (w.get("evaluation") or w.get("evaluator_result") or {}).get(
            "overall_confidence", w.get("confidence", "")
        )
        conf = str(conf).lower()
        if conf == "high":    high   += 1
        elif conf == "medium": medium += 1
        else:                  low    += 1
        ev = w.get("evaluation") or w.get("evaluator_result") or {}
        if ev.get("manual_review_required") or ev.get("flag_for_review"):
            manual += 1
        if w.get("_from_cache"):
            cached += 1

    elapsed = time.time() - job["started_at"]
    return {
        "total":   len(evaluated),
        "high":    high,
        "medium":  medium,
        "low":     low,
        "manual":  manual,
        "cached":  cached,
        "elapsed_s": round(elapsed),
        "batch_size": job.get("batch_size", DEFAULT_BATCH_SIZE),
        "excel":   Path(job["excel"]).name,
        "c_files": job["c_files"],
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  MISRA GenAI Web UI  (upgraded)")
    print("  http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
'''


# ============================================================
#  6 — index.html  (dark upload UI + live stream table + batch-size)
# ============================================================

INDEX_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>MISRA GenAI — Analysis</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}" />
</head>
<body>

<!-- ── Header ──────────────────────────────────────────── -->
<header class="site-header">
  <div class="header-inner">
    <div class="logo-mark">M</div>
    <span class="logo-text">MISRA <span>GenAI</span></span>
    <span class="header-badge">Mistral-7B · Offline · FAISS</span>
  </div>
</header>

<main>
  <section class="page-hero">
    <div class="container">
      <h1>Static Analysis Advisor</h1>
      <p>Upload a Polyspace warning report and your C source files. The system retrieves relevant
         MISRA-C 2012 rules and generates ranked, reviewed fix suggestions — fully offline.</p>
      <div class="pill-row">
        <span class="pill accent">MISRA-C 2012</span>
        <span class="pill">Mistral-7B Q4_K_M</span>
        <span class="pill">FAISS · all-MiniLM-L6-v2</span>
        <span class="pill">SQLite cache</span>
      </div>
    </div>
  </section>

  <div class="container mt-32">

    <!-- ── Upload card ──────────────────────────────────── -->
    <div class="card" id="upload-card">
      <div class="card-title">Input Files</div>

      <div class="upload-grid">

        <!-- Excel drop zone -->
        <div>
          <div class="drop-zone" id="excel-zone">
            <input type="file" id="excel-input" accept=".xlsx,.xls" />
            <svg class="drop-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <path d="M3 9h18M9 21V9"/>
            </svg>
            <div class="drop-label">Warning Report</div>
            <div class="drop-sub">Drag &amp; drop or click to browse</div>
            <div class="drop-accept">.xlsx / .xls</div>
            <div class="file-list" id="excel-list"></div>
          </div>
        </div>

        <!-- C source drop zone -->
        <div>
          <div class="drop-zone" id="c-zone">
            <input type="file" id="c-input" accept=".c,.h" multiple />
            <svg class="drop-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
            <div class="drop-label">C Source Files</div>
            <div class="drop-sub">Select all .c and .h files</div>
            <div class="drop-accept">.c / .h (multiple)</div>
            <div class="file-list" id="c-list"></div>
          </div>
        </div>

      </div><!-- /upload-grid -->

      <!-- Batch size -->
      <div class="batch-row mt-24">
        <label class="batch-label" for="batch-size">Batch size</label>
        <div class="batch-stepper">
          <button type="button" id="batch-minus">−</button>
          <input type="number" id="batch-size" name="batch_size"
                 min="1" max="15" value="{{ default_batch }}" />
          <button type="button" id="batch-plus">+</button>
        </div>
        <span class="batch-hint">warnings per run (1–15)</span>
      </div>

      <!-- Error message -->
      <div id="upload-error" class="error-panel mt-16 hidden"></div>

      <!-- Submit -->
      <div class="mt-24 flex items-center gap-12">
        <button class="btn btn-primary" id="run-btn" disabled>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          Run Analysis
        </button>
        <span class="text-mono text-muted" id="file-summary"></span>
      </div>
    </div><!-- /card -->

    <!-- ── Progress panel ───────────────────────────────── -->
    <div class="card" id="progress-panel">
      <div class="card-title">Pipeline Progress</div>

      <div class="phase-list" id="phase-list">
        <div class="phase-item" data-phase="6a" id="ph-6a">
          <div class="phase-dot">6a</div>
          <div class="phase-body">
            <div class="phase-label">Parse Warning Report</div>
            <div class="phase-detail">Waiting…</div>
          </div>
        </div>
        <div class="phase-item" data-phase="6b" id="ph-6b">
          <div class="phase-dot">6b</div>
          <div class="phase-body">
            <div class="phase-label">Retrieve MISRA Context</div>
            <div class="phase-detail">Waiting…</div>
          </div>
        </div>
        <div class="phase-item" data-phase="7" id="ph-7">
          <div class="phase-dot">7</div>
          <div class="phase-body">
            <div class="phase-label">Generate Fix Suggestions</div>
            <div class="phase-detail">Waiting…</div>
          </div>
        </div>
        <div class="phase-item" data-phase="8" id="ph-8">
          <div class="phase-dot">8</div>
          <div class="phase-body">
            <div class="phase-label">Evaluate Fix Quality</div>
            <div class="phase-detail">Waiting…</div>
          </div>
        </div>
      </div>

      <!-- Live stream table -->
      <div id="stream-table-wrap" class="stream-table-wrap mt-24 hidden">
        <div class="stream-table-title">Live Results Stream</div>
        <table class="stream-table" id="stream-table">
          <thead>
            <tr>
              <th>ID</th><th>Rule</th><th>File</th><th>Phase</th><th>Status</th>
            </tr>
          </thead>
          <tbody id="stream-tbody"></tbody>
        </table>
      </div>

      <div class="progress-bar-wrap mt-24">
        <div class="progress-bar-fill" id="progress-fill"></div>
      </div>
      <div class="status-line" id="status-line">Initialising pipeline…</div>
    </div><!-- /progress-panel -->

  </div><!-- /container -->
</main>

<footer class="site-footer">
  MISRA GenAI System · Fully offline · Client data never leaves this machine
</footer>

<script src="{{ url_for('static', filename='script.js') }}"></script>
</body>
</html>
'''


# ============================================================
#  7 — results.html  (full warning cards with patch tabs)
# ============================================================

RESULTS_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>MISRA GenAI — Results</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}" />
</head>
<body>

<!-- ── Header ──────────────────────────────────────────── -->
<header class="site-header">
  <div class="header-inner">
    <div class="logo-mark">M</div>
    <span class="logo-text">MISRA <span>GenAI</span></span>
    <a href="/" class="btn btn-ghost" style="margin-left:auto;font-size:12px;padding:6px 14px;">
      ← New Analysis
    </a>
  </div>
</header>

<main>
  <div class="container mt-32" id="results-root">
    <div class="loading-pulse">
      <div class="loading-dot"></div>
      <div class="loading-dot"></div>
      <div class="loading-dot"></div>
      <span class="text-muted text-mono" style="margin-left:12px;">Loading results…</span>
    </div>
  </div>
</main>

<footer class="site-footer">
  MISRA GenAI System · Fully offline · Client data never leaves this machine
</footer>

<script>
  window.MISRA_JOB_ID = "{{ job_id }}";
</script>
<script src="{{ url_for('static', filename='script.js') }}"></script>
</body>
</html>
'''


# ============================================================
#  8 — style.css  (dark industrial theme — full rewrite)
# ============================================================

STYLE_CSS = r'''/* =========================================================
   MISRA GenAI System — stylesheet
   Theme: industrial-precision dark
   Fonts: DM Mono (code/labels) + Sora (UI text)
   ========================================================= */

@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Sora:wght@300;400;500;600;700&display=swap');

/* ── Variables ─────────────────────────────────────────── */
:root {
  --bg:           #0d0f12;
  --surface:      #13161b;
  --surface2:     #1a1e26;
  --surface3:     #20252f;
  --border:       #252932;
  --border-light: #2e3440;
  --text:         #e2e6ef;
  --text-muted:   #6b7280;
  --text-dim:     #3d4455;

  --accent:       #00c2ff;
  --accent-glow:  rgba(0,194,255,0.12);
  --accent-dim:   rgba(0,194,255,0.06);

  --high:         #22c55e;
  --high-bg:      rgba(34,197,94,0.08);
  --medium:       #f59e0b;
  --medium-bg:    rgba(245,158,11,0.08);
  --low:          #ef4444;
  --low-bg:       rgba(239,68,68,0.08);
  --review:       #a78bfa;
  --review-bg:    rgba(167,139,250,0.10);
  --cache:        #38bdf8;
  --cache-bg:     rgba(56,189,248,0.08);

  --font-ui:   'Sora', sans-serif;
  --font-mono: 'DM Mono', 'Courier New', monospace;

  --radius:    6px;
  --radius-lg: 10px;
  --transition: 160ms ease;
}

/* ── Reset ─────────────────────────────────────────────── */
*,*::before,*::after { box-sizing: border-box; margin:0; padding:0; }
html { scroll-behavior: smooth; }
body {
  font-family: var(--font-ui);
  background: var(--bg);
  color: var(--text);
  font-size: 14px;
  line-height: 1.6;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

/* ── Scrollbar ─────────────────────────────────────────── */
::-webkit-scrollbar { width:6px; height:6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border-light); border-radius:3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-dim); }

/* ── Typography ────────────────────────────────────────── */
h1,h2,h3,h4 { font-weight:600; letter-spacing:-0.02em; }
code,pre,.mono { font-family: var(--font-mono); }
a { color: var(--accent); text-decoration:none; }
a:hover { text-decoration:underline; }

/* ── Layout ────────────────────────────────────────────── */
.container { max-width:1080px; margin:0 auto; padding:0 24px; }
.mt-8  { margin-top:8px; }
.mt-16 { margin-top:16px; }
.mt-24 { margin-top:24px; }
.mt-32 { margin-top:32px; }
.hidden { display:none !important; }
.flex { display:flex; }
.items-center { align-items:center; }
.gap-12 { gap:12px; }

/* ── Header ────────────────────────────────────────────── */
.site-header {
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  position: sticky;
  top: 0;
  z-index: 100;
}
.header-inner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 24px;
  max-width: 1080px;
  margin: 0 auto;
}
.logo-mark {
  width:32px; height:32px;
  background: var(--accent);
  border-radius:4px;
  display:flex; align-items:center; justify-content:center;
  font-family: var(--font-mono);
  font-size:11px; font-weight:500;
  color:#000;
  flex-shrink:0;
}
.logo-text { font-size:13px; font-weight:600; color:var(--text); letter-spacing:0.04em; }
.logo-text span { color: var(--accent); }
.header-badge {
  margin-left:auto;
  font-family: var(--font-mono);
  font-size:10px;
  color: var(--text-muted);
  border:1px solid var(--border);
  padding:3px 8px;
  border-radius:20px;
}

/* ── Page hero ─────────────────────────────────────────── */
.page-hero { padding:56px 0 40px; border-bottom:1px solid var(--border); }
.page-hero h1 { font-size:28px; color:var(--text); margin-bottom:8px; }
.page-hero p  { color:var(--text-muted); font-size:14px; max-width:520px; }
.pill-row  { display:flex; flex-wrap:wrap; gap:8px; margin-top:20px; }
.pill {
  font-family: var(--font-mono);
  font-size:10px; padding:4px 10px;
  border-radius:20px;
  border:1px solid var(--border-light);
  color: var(--text-muted);
}
.pill.accent { border-color: var(--accent); color: var(--accent); }

/* ── Card ──────────────────────────────────────────────── */
.card {
  background: var(--surface);
  border:1px solid var(--border);
  border-radius: var(--radius-lg);
  padding:28px;
  margin-bottom:20px;
  display:none;
}
.card.visible, #upload-card { display:block; }
.card-title {
  font-size:11px;
  font-family: var(--font-mono);
  color: var(--text-muted);
  letter-spacing:0.1em;
  text-transform:uppercase;
  margin-bottom:20px;
}

/* ── Upload grid ───────────────────────────────────────── */
.upload-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
@media (max-width:600px) { .upload-grid { grid-template-columns:1fr; } }

/* ── Drop zone ─────────────────────────────────────────── */
.drop-zone {
  border:1.5px dashed var(--border-light);
  border-radius: var(--radius-lg);
  padding:32px 20px;
  text-align:center;
  cursor:pointer;
  transition: border-color var(--transition), background var(--transition);
  position:relative;
  overflow:hidden;
}
.drop-zone input[type=file] {
  position:absolute; inset:0; opacity:0; cursor:pointer; width:100%; height:100%;
}
.drop-zone:hover, .drop-zone.drag-over {
  border-color: var(--accent);
  background: var(--accent-dim);
}
.drop-icon { width:32px; height:32px; color:var(--text-dim); margin:0 auto 12px; display:block; }
.drop-label { font-size:13px; font-weight:600; color:var(--text); margin-bottom:4px; }
.drop-sub   { font-size:11px; color:var(--text-muted); margin-bottom:6px; }
.drop-accept { font-family:var(--font-mono); font-size:10px; color:var(--text-dim); }
.file-list  { margin-top:12px; display:flex; flex-wrap:wrap; gap:6px; justify-content:center; }
.file-chip  {
  background: var(--surface2);
  border:1px solid var(--border);
  border-radius:4px;
  padding:3px 8px;
  font-family:var(--font-mono);
  font-size:10px; color:var(--text);
  display:flex; align-items:center; gap:6px;
}
.file-chip .dot {
  width:5px; height:5px;
  border-radius:50%;
  background:var(--high);
  flex-shrink:0;
}

/* ── Batch stepper ─────────────────────────────────────── */
.batch-row { display:flex; align-items:center; gap:12px; }
.batch-label {
  font-family:var(--font-mono); font-size:11px; color:var(--text-muted);
  white-space:nowrap;
}
.batch-stepper {
  display:flex; align-items:center;
  border:1px solid var(--border-light);
  border-radius: var(--radius);
  overflow:hidden;
}
.batch-stepper button {
  background:var(--surface2); border:none;
  color:var(--text); font-size:16px; line-height:1;
  width:32px; height:32px; cursor:pointer;
  transition: background var(--transition);
}
.batch-stepper button:hover { background: var(--surface3); }
.batch-stepper input[type=number] {
  width:48px; text-align:center;
  background:var(--surface); border:none; border-left:1px solid var(--border); border-right:1px solid var(--border);
  color:var(--text); font-family:var(--font-mono); font-size:13px;
  height:32px; padding:0;
  -moz-appearance:textfield;
}
.batch-stepper input::-webkit-inner-spin-button,
.batch-stepper input::-webkit-outer-spin-button { -webkit-appearance:none; }
.batch-hint { font-size:11px; color:var(--text-dim); }

/* ── Buttons ───────────────────────────────────────────── */
.btn {
  display:inline-flex; align-items:center; gap:7px;
  padding:10px 20px;
  border-radius: var(--radius);
  font-size:13px; font-weight:500;
  cursor:pointer; border:none;
  transition: background var(--transition), opacity var(--transition);
  font-family:var(--font-ui);
}
.btn-primary {
  background: var(--accent);
  color:#000;
}
.btn-primary:hover { background:#00aadd; }
.btn-primary:disabled { opacity:0.4; cursor:not-allowed; }
.btn-ghost {
  background: transparent;
  border:1px solid var(--border-light);
  color: var(--text-muted);
  text-decoration:none;
}
.btn-ghost:hover { border-color:var(--accent); color:var(--accent); text-decoration:none; }

/* ── Error panel ───────────────────────────────────────── */
.error-panel {
  background: rgba(239,68,68,0.08);
  border:1px solid rgba(239,68,68,0.25);
  color: #fca5a5;
  border-radius: var(--radius);
  padding:12px 16px;
  font-size:12px;
  font-family: var(--font-mono);
  white-space: pre-wrap;
}

/* ── Phase list ────────────────────────────────────────── */
.phase-list { display:flex; flex-direction:column; gap:0; }
.phase-item {
  display:flex; align-items:flex-start; gap:14px;
  padding:14px 0;
  border-bottom:1px solid var(--border);
  opacity:0.45;
  transition: opacity var(--transition);
}
.phase-item:last-child { border-bottom:none; }
.phase-item.active { opacity:1; }
.phase-item.done   { opacity:0.65; }
.phase-item.error  { opacity:1; }
.phase-dot {
  width:32px; height:32px; border-radius:6px;
  background: var(--surface2);
  border:1px solid var(--border-light);
  display:flex; align-items:center; justify-content:center;
  font-family:var(--font-mono); font-size:10px; font-weight:500;
  color:var(--text-muted);
  flex-shrink:0;
  transition: background var(--transition), color var(--transition);
}
.phase-item.active .phase-dot { background:var(--accent-dim); border-color:var(--accent); color:var(--accent); }
.phase-item.done   .phase-dot { background:rgba(34,197,94,0.12); border-color:var(--high); color:var(--high); }
.phase-item.error  .phase-dot { background:rgba(239,68,68,0.12); border-color:var(--low);  color:var(--low); }
.phase-body { flex:1; min-width:0; }
.phase-label  { font-size:13px; font-weight:500; color:var(--text); }
.phase-detail { font-size:11px; font-family:var(--font-mono); color:var(--text-muted); margin-top:2px; }

/* ── Progress bar ──────────────────────────────────────── */
.progress-bar-wrap {
  height:4px; background:var(--surface2);
  border-radius:2px; overflow:hidden;
}
.progress-bar-fill {
  height:100%; width:0%;
  background: var(--accent);
  transition: width 300ms ease;
  border-radius:2px;
}
.status-line {
  font-family:var(--font-mono); font-size:11px;
  color:var(--text-muted); margin-top:10px;
}

/* ── Stream table ──────────────────────────────────────── */
.stream-table-wrap { overflow-x:auto; }
.stream-table-title {
  font-family:var(--font-mono); font-size:10px;
  color:var(--text-muted); letter-spacing:0.08em;
  text-transform:uppercase; margin-bottom:10px;
}
.stream-table {
  width:100%; border-collapse:collapse;
  font-family:var(--font-mono); font-size:11px;
}
.stream-table th {
  text-align:left; padding:6px 10px;
  border-bottom:1px solid var(--border);
  color:var(--text-muted); font-weight:400;
  white-space:nowrap;
}
.stream-table td {
  padding:7px 10px;
  border-bottom:1px solid var(--border);
  color:var(--text);
}
.stream-table tr:last-child td { border-bottom:none; }
.stream-table tr.stream-new td { animation: rowFlash 0.8s ease; }
@keyframes rowFlash {
  0%   { background: var(--accent-dim); }
  100% { background: transparent; }
}
.st-badge {
  display:inline-block;
  padding:2px 7px; border-radius:3px;
  font-size:10px; font-weight:500;
}
.st-badge.cached  { background:var(--cache-bg); color:var(--cache); }
.st-badge.running { background:var(--accent-dim); color:var(--accent); }
.st-badge.done    { background:var(--high-bg);   color:var(--high); }

/* ── Stat row (results page) ───────────────────────────── */
.stat-row { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:24px; }
.stat-card {
  flex:1; min-width:100px;
  background:var(--surface);
  border:1px solid var(--border);
  border-radius: var(--radius-lg);
  padding:16px 20px;
  text-align:center;
}
.stat-val { font-size:28px; font-weight:700; font-family:var(--font-mono); }
.stat-lbl { font-size:10px; font-family:var(--font-mono); color:var(--text-muted); margin-top:2px; text-transform:uppercase; }
.s-total  .stat-val { color:var(--text); }
.s-high   .stat-val { color:var(--high); }
.s-medium .stat-val { color:var(--medium); }
.s-low    .stat-val { color:var(--low); }
.s-review .stat-val { color:var(--review); }
.s-cache  .stat-val { color:var(--cache); }

/* ── Filter bar ────────────────────────────────────────── */
.filter-bar { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:20px; }
.filter-btn {
  background: var(--surface);
  border:1px solid var(--border);
  color: var(--text-muted);
  border-radius:4px; padding:5px 12px;
  font-size:11px; font-family:var(--font-mono);
  cursor:pointer;
  transition: border-color var(--transition), color var(--transition);
}
.filter-btn:hover   { border-color:var(--accent); color:var(--accent); }
.filter-btn.active  { border-color:var(--accent); color:var(--accent); background:var(--accent-dim); }

/* ── Warning list ──────────────────────────────────────── */
.warning-list { display:flex; flex-direction:column; gap:10px; }

/* ── Warning card ──────────────────────────────────────── */
.warning-card {
  background: var(--surface);
  border:1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow:hidden;
  transition: border-color var(--transition);
}
.warning-card:hover { border-color: var(--border-light); }
.warning-card.review-flag { border-left:3px solid var(--review); }

.warning-header {
  display:flex; align-items:center; gap:12px;
  padding:14px 18px;
  cursor:pointer;
  user-select:none;
}
.warning-header:hover { background: rgba(255,255,255,0.02); }
.w-id   { font-family:var(--font-mono); font-size:11px; color:var(--accent); min-width:48px; }
.w-rule { font-family:var(--font-mono); font-size:11px; color:var(--text-muted); min-width:52px; }
.w-msg  { flex:1; font-size:12px; color:var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.w-loc  { font-family:var(--font-mono); font-size:10px; color:var(--text-dim); white-space:nowrap; }
.chevron { margin-left:8px; color:var(--text-dim); flex-shrink:0; transition: transform var(--transition); }
.warning-card.open .chevron { transform: rotate(180deg); }

/* ── Conf badge ────────────────────────────────────────── */
.conf-badge {
  font-family:var(--font-mono); font-size:10px;
  padding:3px 8px; border-radius:3px;
  white-space:nowrap; flex-shrink:0;
}
.conf-badge.high   { background:var(--high-bg);   color:var(--high); }
.conf-badge.medium { background:var(--medium-bg); color:var(--medium); }
.conf-badge.low    { background:var(--low-bg);    color:var(--low); }
.conf-badge.review { background:var(--review-bg); color:var(--review); }

/* ── Warning detail ────────────────────────────────────── */
.warning-detail { display:none; padding:0 18px 20px; }
.warning-card.open .warning-detail { display:block; }

.detail-section { margin-top:20px; }
.detail-section-title {
  font-family:var(--font-mono); font-size:10px;
  color:var(--text-dim); letter-spacing:0.1em; text-transform:uppercase;
  margin-bottom:8px;
}

/* ── Excel row table ───────────────────────────────────── */
.excel-table {
  width:100%; border-collapse:collapse;
  font-family:var(--font-mono); font-size:11px;
  background:var(--surface2); border-radius: var(--radius);
  overflow:hidden;
}
.excel-table td {
  padding:6px 10px;
  border-bottom:1px solid var(--border);
  vertical-align:top;
}
.excel-table tr:last-child td { border-bottom:none; }
.excel-table td:first-child {
  color:var(--text-muted); min-width:140px; white-space:nowrap;
}
.excel-table td:last-child { color:var(--text); word-break:break-all; }

/* ── Source code view ──────────────────────────────────── */
.source-block {
  background:var(--surface2);
  border:1px solid var(--border);
  border-radius: var(--radius);
  overflow:auto;
  max-height:260px;
}
.source-block pre {
  font-family:var(--font-mono); font-size:11px;
  color:var(--text-muted); padding:14px 16px;
  white-space:pre; margin:0;
}
.source-block pre .hl { background:rgba(245,158,11,0.18); color:var(--text); display:block; }

/* ── Rule text box ─────────────────────────────────────── */
.rule-box, .eval-note, .deviation-box {
  background:var(--surface2);
  border:1px solid var(--border);
  border-radius: var(--radius);
  padding:12px 14px;
  font-size:12px;
  color:var(--text-muted);
  line-height:1.7;
}
.eval-note   { border-color: rgba(167,139,250,0.25); }
.deviation-box { border-color: rgba(245,158,11,0.25); }

/* ── Fix tabs ──────────────────────────────────────────── */
.fix-tabs { display:flex; gap:4px; flex-wrap:wrap; margin-bottom:12px; }
.fix-tab {
  background:var(--surface2); border:1px solid var(--border);
  border-radius:4px; padding:5px 12px;
  font-size:11px; font-family:var(--font-mono);
  cursor:pointer; color:var(--text-muted);
  transition: all var(--transition);
}
.fix-tab:hover  { border-color:var(--accent); color:var(--accent); }
.fix-tab.active { background:var(--accent-dim); border-color:var(--accent); color:var(--accent); }

.fix-panel { display:none; }
.fix-panel.active { display:block; }

.fix-header {
  display:flex; align-items:center; gap:10px;
  margin-bottom:10px;
}
.fix-rank  { font-family:var(--font-mono); font-size:10px; color:var(--text-dim); }
.fix-title { font-size:13px; font-weight:500; color:var(--text); flex:1; }
.fix-conf-badge {
  font-family:var(--font-mono); font-size:10px;
  padding:2px 8px; border-radius:3px;
}
.fix-conf-badge.High, .fix-conf-badge.high     { background:var(--high-bg);   color:var(--high); }
.fix-conf-badge.Medium, .fix-conf-badge.medium { background:var(--medium-bg); color:var(--medium); }
.fix-conf-badge.Low, .fix-conf-badge.low       { background:var(--low-bg);    color:var(--low); }
.fix-corrected {
  font-family:var(--font-mono); font-size:10px;
  background:rgba(34,197,94,0.12); color:var(--high);
  padding:2px 7px; border-radius:3px;
}
.fix-cached {
  font-family:var(--font-mono); font-size:10px;
  background:var(--cache-bg); color:var(--cache);
  padding:2px 7px; border-radius:3px;
}

/* ── Code diff (BEFORE / AFTER) ────────────────────────── */
.code-diff { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
@media (max-width:700px) { .code-diff { grid-template-columns:1fr; } }
.code-diff-panel {
  background:var(--surface2); border:1px solid var(--border);
  border-radius: var(--radius); overflow:auto;
}
.code-diff-label {
  font-family:var(--font-mono); font-size:9px;
  letter-spacing:0.1em; text-transform:uppercase;
  padding:5px 10px;
  border-bottom:1px solid var(--border);
}
.code-diff-panel.before .code-diff-label { color:var(--low);  background:rgba(239,68,68,0.06); }
.code-diff-panel.after  .code-diff-label { color:var(--high); background:rgba(34,197,94,0.06); }
.code-diff-panel pre {
  font-family:var(--font-mono); font-size:11px;
  padding:10px 12px; margin:0;
  white-space:pre; color:var(--text-muted);
}

/* ── Code block (single) ───────────────────────────────── */
.code-block {
  background:var(--surface2); border:1px solid var(--border);
  border-radius: var(--radius); overflow:auto; margin:10px 0;
}
.code-block pre {
  font-family:var(--font-mono); font-size:11px;
  padding:12px 14px; margin:0;
  white-space:pre; color:var(--text-muted);
}

/* ── Fix meta ──────────────────────────────────────────── */
.fix-meta { margin-top:10px; display:flex; flex-wrap:wrap; gap:8px; }
.fix-meta-item {
  display:flex; align-items:baseline; gap:5px;
  font-size:11px;
}
.fix-meta-key   { font-family:var(--font-mono); color:var(--text-dim); font-size:10px; }
.fix-meta-val   { color:var(--text-muted); }
.fix-rationale  { font-size:12px; color:var(--text-muted); margin-top:10px; line-height:1.6; }

/* ── Issues list ───────────────────────────────────────── */
.issues-list { margin-top:10px; display:flex; flex-direction:column; gap:4px; }
.issue-item {
  background:rgba(239,68,68,0.06); border-left:2px solid var(--low);
  padding:5px 10px; font-size:11px; font-family:var(--font-mono);
  color:var(--text-muted); border-radius:0 3px 3px 0;
}

/* ── Review banner ─────────────────────────────────────── */
.review-banner {
  background: var(--review-bg);
  border:1px solid rgba(167,139,250,0.25);
  border-radius: var(--radius);
  padding:10px 14px;
  font-size:12px; color:var(--review);
  display:flex; align-items:center; gap:8px;
}

/* ── Cache badge (in results) ──────────────────────────── */
.cache-badge {
  display:inline-flex; align-items:center; gap:5px;
  background:var(--cache-bg); border:1px solid rgba(56,189,248,0.2);
  padding:3px 9px; border-radius:20px;
  font-family:var(--font-mono); font-size:10px; color:var(--cache);
}

/* ── Loading pulse ─────────────────────────────────────── */
.loading-pulse { display:flex; align-items:center; padding:40px 0; }
.loading-dot {
  width:6px; height:6px; border-radius:50%;
  background: var(--accent); margin:0 3px;
  animation: pulse 1.4s ease-in-out infinite;
}
.loading-dot:nth-child(1) { animation-delay:0s; }
.loading-dot:nth-child(2) { animation-delay:0.2s; }
.loading-dot:nth-child(3) { animation-delay:0.4s; }
@keyframes pulse {
  0%,80%,100% { transform:scale(0.6); opacity:0.3; }
  40%         { transform:scale(1.0); opacity:1; }
}

/* ── Footer ────────────────────────────────────────────── */
.site-footer {
  border-top:1px solid var(--border);
  padding:20px 24px;
  font-family:var(--font-mono); font-size:10px;
  color:var(--text-dim); text-align:center;
  margin-top:60px;
}

/* ── Misc text utilities ───────────────────────────────── */
.text-mono  { font-family:var(--font-mono); }
.text-muted { color:var(--text-muted); }
.text-dim   { color:var(--text-dim); }
'''


# ============================================================
#  9 — script.js  (full rewrite)
# ============================================================

SCRIPT_JS = r'''"use strict";
/* =========================================================
   MISRA GenAI — script.js  (upgraded)
   - Upload page: drag-drop, batch-size stepper, SSE, live stream table
   - Results page: incremental card rendering, patch tabs, BEFORE/AFTER diffs,
     Excel row table, highlighted source code
   ========================================================= */

const IS_RESULTS = typeof window.MISRA_JOB_ID !== "undefined";
IS_RESULTS ? initResultsPage() : initIndexPage();

/* ============================================================
   INDEX PAGE
   ============================================================ */
function initIndexPage() {
  const excelInput  = document.getElementById("excel-input");
  const cInput      = document.getElementById("c-input");
  const excelZone   = document.getElementById("excel-zone");
  const cZone       = document.getElementById("c-zone");
  const excelList   = document.getElementById("excel-list");
  const cList       = document.getElementById("c-list");
  const runBtn      = document.getElementById("run-btn");
  const fileSummary = document.getElementById("file-summary");
  const uploadError = document.getElementById("upload-error");
  const batchInput  = document.getElementById("batch-size");
  const batchMinus  = document.getElementById("batch-minus");
  const batchPlus   = document.getElementById("batch-plus");

  let excelFile  = null;
  let cFilesList = [];

  // ── Batch stepper ──
  batchMinus.addEventListener("click", () => {
    batchInput.value = Math.max(1, parseInt(batchInput.value) - 1);
  });
  batchPlus.addEventListener("click", () => {
    batchInput.value = Math.min(15, parseInt(batchInput.value) + 1);
  });

  // ── Drop zones ──
  [excelZone, cZone].forEach(zone => {
    zone.addEventListener("dragover",  e => { e.preventDefault(); zone.classList.add("drag-over"); });
    zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
    zone.addEventListener("drop", e => {
      e.preventDefault(); zone.classList.remove("drag-over");
      const files = [...e.dataTransfer.files];
      if (zone === excelZone) handleExcel(files[0]);
      else handleCFiles(files);
    });
  });

  excelInput.addEventListener("change", () => handleExcel(excelInput.files[0]));
  cInput.addEventListener("change",     () => handleCFiles([...cInput.files]));

  function handleExcel(file) {
    if (!file) return;
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["xlsx","xls"].includes(ext)) { showError("Warning report must be .xlsx or .xls"); return; }
    excelFile = file;
    excelList.innerHTML = chipHTML(file.name);
    updateState();
  }

  function handleCFiles(files) {
    const valid = files.filter(f => /\.(c|h)$/i.test(f.name));
    if (!valid.length) { showError("No .c or .h files found"); return; }
    cFilesList = valid;
    cList.innerHTML = valid.map(f => chipHTML(f.name)).join("");
    updateState();
  }

  function chipHTML(name) {
    return `<div class="file-chip"><span class="dot"></span>${escHtml(name)}</div>`;
  }

  function updateState() {
    const ready = excelFile && cFilesList.length > 0;
    runBtn.disabled = !ready;
    if (ready) {
      fileSummary.textContent = `${excelFile.name} + ${cFilesList.length} source file${cFilesList.length>1?"s":""}`;
    }
  }

  function showError(msg) {
    uploadError.textContent = msg;
    uploadError.classList.remove("hidden");
    setTimeout(() => uploadError.classList.add("hidden"), 5000);
  }

  // ── Run ──
  runBtn.addEventListener("click", async () => {
    if (!excelFile || !cFilesList.length) return;
    uploadError.classList.add("hidden");
    runBtn.disabled = true;
    runBtn.textContent = "Uploading…";

    const fd = new FormData();
    fd.append("warning_report", excelFile);
    cFilesList.forEach(f => fd.append("source_files", f));
    fd.append("batch_size", batchInput.value);

    try {
      const resp = await fetch("/api/analyse", { method:"POST", body:fd });
      const data = await resp.json();
      if (!resp.ok) { showError(data.error || "Server error"); resetRunBtn(); return; }

      document.getElementById("progress-panel").classList.add("visible");
      document.getElementById("upload-card").style.opacity = "0.4";
      document.getElementById("upload-card").style.pointerEvents = "none";
      listenProgress(data.job_id);
    } catch (err) {
      showError("Network error: " + err.message);
      resetRunBtn();
    }
  });

  function resetRunBtn() {
    runBtn.disabled = false;
    runBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run Analysis`;
  }

  // ── SSE progress ──
  function listenProgress(jobId) {
    const fill     = document.getElementById("progress-fill");
    const statusLn = document.getElementById("status-line");
    const stWrap   = document.getElementById("stream-table-wrap");
    const stTbody  = document.getElementById("stream-tbody");
    const streamRows = {};  // warning_id -> <tr>

    const es = new EventSource(`/api/progress/${jobId}`);

    es.onmessage = evt => {
      let msg; try { msg = JSON.parse(evt.data); } catch { return; }
      if (msg.type === "heartbeat") return;

      if (typeof msg.progress === "number") fill.style.width = msg.progress + "%";
      if (msg.label) statusLn.textContent = msg.label + (msg.detail ? " — " + msg.detail : "");

      // Phase item update
      if (msg.phase) {
        const phEl = document.getElementById("ph-" + msg.phase);
        if (phEl) {
          if (msg.type === "phase_start") {
            document.querySelectorAll(".phase-item").forEach(el => el.classList.remove("active"));
            phEl.classList.add("active");
            phEl.querySelector(".phase-detail").textContent = msg.detail || "";
          } else if (msg.type === "phase_done") {
            phEl.classList.remove("active"); phEl.classList.add("done");
            phEl.querySelector(".phase-dot").textContent = "✓";
            phEl.querySelector(".phase-detail").textContent = msg.detail || "";
          } else if (msg.type === "warning_done") {
            phEl.querySelector(".phase-detail").textContent = msg.detail || "";
          }
        }
      }

      // Live stream table
      if (msg.warning_id && (msg.phase === "7" || msg.phase === "8")) {
        stWrap.classList.remove("hidden");
        const wid = msg.warning_id;
        if (!streamRows[wid]) {
          const tr = document.createElement("tr");
          tr.id = "srow-" + wid;
          tr.innerHTML = `
            <td class="st-wid">${escHtml(wid)}</td>
            <td class="st-rule">—</td>
            <td class="st-file">—</td>
            <td class="st-phase">${escHtml(msg.phase)}</td>
            <td class="st-status"><span class="st-badge running">running</span></td>
          `;
          stTbody.prepend(tr);
          streamRows[wid] = tr;
          tr.classList.add("stream-new");
          setTimeout(() => tr.classList.remove("stream-new"), 900);
        } else {
          const tr = streamRows[wid];
          tr.querySelector(".st-phase").textContent = msg.phase;
          if (msg.phase === "8") {
            const cached = msg.from_cache;
            tr.querySelector(".st-status").innerHTML =
              cached
                ? `<span class="st-badge cached">⚡ cache</span>`
                : `<span class="st-badge done">done</span>`;
          }
        }
      }

      if (msg.type === "done") {
        es.close();
        document.querySelectorAll(".phase-item").forEach(el => {
          el.classList.remove("active"); el.classList.add("done");
          el.querySelector(".phase-dot").textContent = "✓";
        });
        statusLn.textContent = "Complete — redirecting to results…";
        setTimeout(() => { window.location.href = `/results/${jobId}`; }, 1500);
      }

      if (msg.type === "error") {
        es.close();
        document.querySelectorAll(".phase-item.active").forEach(el => {
          el.classList.remove("active"); el.classList.add("error");
        });
        statusLn.textContent = "Error: " + msg.detail;
        const ep = document.createElement("div");
        ep.className = "error-panel mt-16";
        ep.textContent = msg.traceback || msg.detail;
        document.getElementById("progress-panel").appendChild(ep);
        document.getElementById("upload-card").style.opacity = "1";
        document.getElementById("upload-card").style.pointerEvents = "auto";
        resetRunBtn();
      }
    };

    es.onerror = () => {
      es.close();
      statusLn.textContent = "Connection lost — check server console.";
    };
  }
}


/* ============================================================
   RESULTS PAGE
   ============================================================ */
function initResultsPage() {
  const root  = document.getElementById("results-root");
  const jobId = window.MISRA_JOB_ID;
  let   allWarnings = [];
  let   jobDone     = false;
  let   pollInterval = null;
  let   lastFetched  = 0;

  // Initial load
  loadResult();

  async function loadResult() {
    try {
      const r    = await fetch(`/api/result/${jobId}`);
      const data = await r.json();
      if (data.error && data.status !== "running") {
        root.innerHTML = `<div class="error-panel">${escHtml(data.error)}</div>`;
        return;
      }

      // First render
      root.innerHTML = buildShell(data);
      allWarnings = data.warnings || [];
      jobDone     = data.status === "done";
      renderWarnings(allWarnings);
      attachFilterHandlers();

      if (!jobDone) {
        // Poll incrementally
        pollInterval = setInterval(pollRecords, 3000);
      }
    } catch(err) {
      root.innerHTML = `<div class="error-panel">Failed to load: ${escHtml(err.message)}</div>`;
    }
  }

  async function pollRecords() {
    try {
      const r    = await fetch(`/api/records/${jobId}?after=${lastFetched}`);
      const data = await r.json();
      if (data.records && data.records.length) {
        data.records.forEach(w => {
          allWarnings.push(w);
          appendWarningCard(w, allWarnings.length - 1);
          lastFetched++;
        });
        // Update summary counts
        updateSummaryCounts(allWarnings);
      }
      if (data.done) {
        clearInterval(pollInterval);
        jobDone = true;
      }
    } catch { /* swallow */ }
  }

  function buildShell(data) {
    const s = data.summary || {};
    const ws = data.warnings || [];
    const elapsed = s.elapsed_s ? fmtDuration(s.elapsed_s) : "…";
    const cachedNote = s.cached ? ` · ${s.cached} cached` : "";
    const batchNote  = s.batch_size ? ` · batch ${s.batch_size}` : "";

    return `
    <div class="page-hero" style="padding:32px 0 24px; border:none;">
      <h1>Analysis Results</h1>
      <p>Run <span class="text-mono">${escHtml(data.job_id)}</span>
         · ${escHtml(s.excel||"")} · ${elapsed}${cachedNote}${batchNote}</p>
    </div>

    <div class="stat-row" id="stat-row">
      <div class="stat-card s-total">
        <div class="stat-val" id="st-total">${s.total || ws.length}</div>
        <div class="stat-lbl">Total</div>
      </div>
      <div class="stat-card s-high">
        <div class="stat-val" id="st-high">${s.high ?? "—"}</div>
        <div class="stat-lbl">High Conf.</div>
      </div>
      <div class="stat-card s-medium">
        <div class="stat-val" id="st-medium">${s.medium ?? "—"}</div>
        <div class="stat-lbl">Medium Conf.</div>
      </div>
      <div class="stat-card s-low">
        <div class="stat-val" id="st-low">${s.low ?? "—"}</div>
        <div class="stat-lbl">Low Conf.</div>
      </div>
      <div class="stat-card s-review">
        <div class="stat-val" id="st-review">${s.manual ?? "—"}</div>
        <div class="stat-lbl">Review</div>
      </div>
      ${s.cached ? `<div class="stat-card s-cache">
        <div class="stat-val" id="st-cache">${s.cached}</div>
        <div class="stat-lbl">Cached</div>
      </div>` : ""}
    </div>

    <div class="filter-bar" id="filter-bar">
      <button class="filter-btn active" data-filter="all">All</button>
      <button class="filter-btn" data-filter="high">High confidence</button>
      <button class="filter-btn" data-filter="medium">Medium confidence</button>
      <button class="filter-btn" data-filter="low">Low confidence</button>
      <button class="filter-btn" data-filter="review">Needs review</button>
    </div>

    <div class="warning-list" id="warning-list"></div>

    <div class="site-footer" style="border:none; margin-top:40px;">
      Output saved → ${escHtml(data.out_dir || "")}
    </div>`;
  }

  function renderWarnings(ws) {
    const list = document.getElementById("warning-list");
    if (!list) return;
    list.innerHTML = ws.map((w, i) => buildWarningCard(w, i)).join("");
    attachCardHandlers();
  }

  function appendWarningCard(w, idx) {
    const list = document.getElementById("warning-list");
    if (!list) return;
    const div = document.createElement("div");
    div.innerHTML = buildWarningCard(w, idx);
    list.appendChild(div.firstElementChild);
    attachCardHandlers();
  }

  function updateSummaryCounts(ws) {
    let h=0, m=0, l=0, r=0, c=0;
    ws.forEach(w => {
      const ev   = w.evaluation || w.evaluator_result || {};
      const conf = (ev.overall_confidence || w.confidence || "").toLowerCase();
      if (conf==="high") h++; else if (conf==="medium") m++; else l++;
      if (ev.manual_review_required || ev.flag_for_review) r++;
      if (w._from_cache) c++;
    });
    const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent=v; };
    set("st-total",  ws.length);
    set("st-high",   h);
    set("st-medium", m);
    set("st-low",    l);
    set("st-review", r);
    set("st-cache",  c);
  }

  function attachFilterHandlers() {
    document.querySelectorAll(".filter-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        const filter = btn.dataset.filter;
        document.querySelectorAll(".warning-card").forEach(card => {
          if (filter==="all")    card.style.display = "";
          else if (filter==="review") card.style.display = card.dataset.review==="true" ? "" : "none";
          else                   card.style.display = card.dataset.conf===filter ? "" : "none";
        });
      });
    });
  }

  function attachCardHandlers() {
    // tab switching is handled via onclick in the HTML
  }
}


/* ============================================================
   BUILD WARNING CARD
   ============================================================ */
function buildWarningCard(w, idx) {
  const ev      = w.evaluation || w.evaluator_result || {};
  const conf    = (ev.overall_confidence || w.confidence || "").toLowerCase();
  const isReview = !!(ev.manual_review_required || ev.flag_for_review);
  const wId     = w.warning_id || `W${idx+1}`;
  const ruleId  = w.rule_id || w.misra_rule || "";
  const msg     = w.message || w.warning_message || "";
  const loc     = w.file_path ? `${baseName(w.file_path)}:${w.line_start||""}` : "";
  const confClass = isReview ? "review" : (conf || "high");
  const confLabel = isReview ? "Review" : (conf ? conf.charAt(0).toUpperCase()+conf.slice(1) : "—");

  return `
  <div class="warning-card ${isReview?"review-flag":""}"
       data-conf="${conf}" data-review="${isReview}" data-id="${escHtml(wId)}">
    <div class="warning-header" onclick="toggleCard('${escHtml(wId)}')">
      <span class="w-id">${escHtml(wId)}</span>
      <span class="w-rule">${escHtml(ruleId)}</span>
      <span class="w-msg">${escHtml(msg)}</span>
      <span class="w-loc">${escHtml(loc)}</span>
      ${w._from_cache ? `<span class="cache-badge">⚡ cache</span>` : ""}
      <span class="conf-badge ${confClass}">${confLabel}</span>
      <svg class="chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="6 9 12 15 18 9"/>
      </svg>
    </div>
    <div class="warning-detail">
      ${buildWarningDetail(w, ev, isReview, wId)}
    </div>
  </div>`;
}

function buildWarningDetail(w, ev, isReview, wId) {
  let html = "";

  // Review banner
  if (isReview) {
    html += `<div class="review-banner mt-16">
      <span>🔍</span> Flagged for manual review — automatic confidence is limited.
    </div>`;
  }

  // Excel row table
  const row = w._excel_row || {};
  const rowKeys = Object.keys(row).filter(k => row[k] && String(row[k]).trim());
  if (rowKeys.length) {
    html += `<div class="detail-section">
      <div class="detail-section-title">Warning Report Record</div>
      <table class="excel-table">
        ${rowKeys.map(k => `<tr>
          <td>${escHtml(k)}</td>
          <td>${escHtml(String(row[k]))}</td>
        </tr>`).join("")}
      </table>
    </div>`;
  }

  // Violated source code
  const srcCtx = w._source_context || w.source_context || w.source_code || "";
  if (srcCtx) {
    const flagLines = new Set();
    if (w.line_start) flagLines.add(parseInt(w.line_start));
    if (w.line_end)   flagLines.add(parseInt(w.line_end));

    const lines = srcCtx.split("\n");
    const lineHtml = lines.map((ln, i) => {
      const lineNo = i + 1;
      const isFlag = flagLines.has(lineNo);
      const cls = isFlag ? " class=\"hl\"" : "";
      return `<span${cls}>${escHtml(ln)}</span>`;
    }).join("\n");

    html += `<div class="detail-section">
      <div class="detail-section-title">Source Context</div>
      <div class="source-block"><pre>${lineHtml}</pre></div>
    </div>`;
  }

  // Explanation
  const expl = w.explanation || ev.explanation || "";
  if (expl) {
    html += `<div class="detail-section">
      <div class="detail-section-title">Explanation</div>
      <div class="rule-box">${escHtml(expl)}</div>
    </div>`;
  }

  // Risk analysis
  const risk = w.risk_analysis || ev.risk_analysis || "";
  if (risk) {
    html += `<div class="detail-section">
      <div class="detail-section-title">Risk Analysis</div>
      <div class="rule-box">${escHtml(risk)}</div>
    </div>`;
  }

  // MISRA rule text
  const ruleText = getRuleText(w);
  if (ruleText) {
    html += `<div class="detail-section">
      <div class="detail-section-title">MISRA Rule ${escHtml(w.rule_id||"")}</div>
      <div class="rule-box">${escHtml(ruleText)}</div>
    </div>`;
  }

  // Fix tabs
  const fixes = w.ranked_fixes || w.fix_suggestions || w.fixes || [];
  if (fixes.length) {
    const tabsHtml = fixes.map((f,i) => {
      const tabConf = (f.confidence||"").toLowerCase();
      return `<button class="fix-tab ${i===0?"active":""}" onclick="switchTab('${escHtml(wId)}',${i})"
        data-tab="${i}">
        Fix ${i+1}${tabConf ? ` · ${tabConf.charAt(0).toUpperCase()}` : ""}
      </button>`;
    }).join("");

    const panelsHtml = fixes.map((f,i) => buildFixPanel(f, i, wId)).join("");

    html += `<div class="detail-section">
      <div class="detail-section-title">Ranked Fix Suggestions (${fixes.length})</div>
      <div class="fix-tabs" id="tabs-${escHtml(wId)}">${tabsHtml}</div>
      <div id="panels-${escHtml(wId)}">${panelsHtml}</div>
    </div>`;
  }

  // Evaluator notes
  const evalNotes = ev.evaluator_notes || ev.notes || ev.summary || "";
  if (evalNotes) {
    html += `<div class="detail-section">
      <div class="detail-section-title">Evaluator Notes</div>
      <div class="eval-note">${escHtml(evalNotes)}</div>
    </div>`;
  }

  // Deviation advice
  const dev = w.deviation_advice || ev.deviation_advice || "";
  if (dev && dev !== "No deviation justified.") {
    html += `<div class="detail-section">
      <div class="detail-section-title">Deviation Advice</div>
      <div class="deviation-box">${escHtml(dev)}</div>
    </div>`;
  }

  return html || `<div class="text-muted mt-16" style="font-size:12px;">No detail available.</div>`;
}

function buildFixPanel(fix, idx, wId) {
  const title     = fix.fix_title || fix.description || fix.title || `Fix ${idx+1}`;
  const conf      = fix.confidence || "";
  const corrected = fix.corrected === true || fix.was_corrected === true;
  const cached    = fix._from_cache === true;
  const rules     = (fix.misra_rules_applied || []).join(", ");
  const rationale = fix.rationale || "";
  const riskLv    = fix.risk_level || "";
  const issues    = fix.issues_found || fix.issues || [];

  // code_change: try to split BEFORE/AFTER
  const codeChange = fix.code_change || fix.fixed_code || fix.code || fix.corrected_code || "";
  let diffHtml = "";
  if (codeChange) {
    const beIdx = codeChange.toUpperCase().indexOf("BEFORE:");
    const afIdx = codeChange.toUpperCase().indexOf("AFTER:");
    if (beIdx !== -1 && afIdx !== -1) {
      const beforeCode = codeChange.slice(beIdx + 7, afIdx).trim();
      const afterCode  = codeChange.slice(afIdx  + 6).trim();
      diffHtml = `
      <div class="code-diff">
        <div class="code-diff-panel before">
          <div class="code-diff-label">Before</div>
          <pre>${escHtml(beforeCode)}</pre>
        </div>
        <div class="code-diff-panel after">
          <div class="code-diff-label">After</div>
          <pre>${escHtml(afterCode)}</pre>
        </div>
      </div>`;
    } else {
      diffHtml = `<div class="code-block"><pre>${escHtml(codeChange)}</pre></div>`;
    }
  }

  return `
  <div class="fix-panel ${idx===0?"active":""}" id="panel-${escHtml(wId)}-${idx}">
    <div class="fix-header">
      <span class="fix-rank">#${idx+1}</span>
      <span class="fix-title">${escHtml(title)}</span>
      ${conf    ? `<span class="fix-conf-badge ${escHtml(conf)}">${escHtml(conf)}</span>` : ""}
      ${corrected ? `<span class="fix-corrected">Auto-corrected</span>` : ""}
      ${cached    ? `<span class="fix-cached">⚡ cache</span>` : ""}
    </div>
    ${diffHtml}
    <div class="fix-meta">
      ${rules   ? `<div class="fix-meta-item"><span class="fix-meta-key">rules:</span><span class="fix-meta-val">${escHtml(rules)}</span></div>` : ""}
      ${riskLv  ? `<div class="fix-meta-item"><span class="fix-meta-key">risk:</span><span class="fix-meta-val">${escHtml(riskLv)}</span></div>` : ""}
    </div>
    ${rationale ? `<div class="fix-rationale">${escHtml(rationale)}</div>` : ""}
    ${issues.length ? `
    <div class="issues-list">
      ${issues.map(i=>`<div class="issue-item">${escHtml(typeof i==="string"?i:JSON.stringify(i))}</div>`).join("")}
    </div>` : ""}
  </div>`;
}


/* ============================================================
   SHARED HELPERS
   ============================================================ */
function toggleCard(wId) {
  const card = document.querySelector(`.warning-card[data-id="${wId}"]`);
  if (card) card.classList.toggle("open");
}

function switchTab(wId, idx) {
  const tabsCont   = document.getElementById("tabs-"   + wId);
  const panelsCont = document.getElementById("panels-" + wId);
  if (!tabsCont || !panelsCont) return;
  tabsCont.querySelectorAll(".fix-tab").forEach((t,i) => t.classList.toggle("active", i===idx));
  panelsCont.querySelectorAll(".fix-panel").forEach((p,i) => p.classList.toggle("active", i===idx));
}

// expose to onclick
window.toggleCard = toggleCard;
window.switchTab  = switchTab;

function getRuleText(w) {
  const ctx = w.misra_context || w.retrieved_context || {};
  if (typeof ctx === "string") return ctx.slice(0, 600);
  return ctx.body_text || ctx.rule_text || ctx.text || ctx.amplification || "";
}

function escHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g,"&amp;")
    .replace(/</g,"&lt;")
    .replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;");
}

function baseName(path) {
  return (path||"").replace(/\\/g,"/").split("/").pop();
}

function fmtDuration(secs) {
  if (secs < 60) return `${secs}s`;
  const m = Math.floor(secs/60), s = secs%60;
  return `${m}m ${s}s`;
}
'''


# ============================================================
#  10 — run.bat
# ============================================================

RUN_BAT = r'''@echo off
REM MISRA GenAI System — Quick launcher
REM Double-click this file to start the web UI

title MISRA GenAI System
cd /d %~dp0

echo.
echo ============================================================
echo   MISRA GenAI System
echo ============================================================
echo.
echo  Starting Flask web server...
echo  Open http://127.0.0.1:5000 in your browser
echo.
echo  Make sure llama-server is running first:
echo    C:\Users\sanjay.ravichander\llama_cpp\llama-server.exe ^
echo      -m C:\models\Mistral-7B-Instruct-v0.3-Q4_K_M.gguf ^
echo      --host 127.0.0.1 --port 8080 --ctx-size 4096 --threads 4
echo.
echo ============================================================

call venv310\Scripts\activate.bat
python app\web\server.py

pause
'''


# ============================================================
#  MAIN
# ============================================================

def main() -> None:
    print("=" * 62)
    print("  MISRA GenAI — setup_and_upgrade.py")
    print("  Project root:", HERE)
    print("=" * 62)

    if not (HERE / "app").exists():
        print("\nERROR: 'app/' not found. Run this script from the project root.")
        sys.exit(1)

    # ── 1. Remove dead files ──────────────────────────────────────────
    step_remove_dead()

    # ── 2. settings.py ───────────────────────────────────────────────
    print("\n── Step 2: Upgrade settings.py ───────────────────────────────")
    write(HERE / "app" / "config" / "settings.py", SETTINGS_PY)

    # ── 3. generate_fixes.py (SYSTEM_PROMPT patch) ───────────────────
    print("\n── Step 3: Patch generate_fixes.py system prompt ─────────────")
    patch_generate_fixes()

    # ── 4. result_cache.py (new) ─────────────────────────────────────
    print("\n── Step 4: Create result_cache.py ────────────────────────────")
    write(HERE / "app" / "pipeline" / "result_cache.py", RESULT_CACHE_PY)

    # ── 5. server.py ─────────────────────────────────────────────────
    print("\n── Step 5: Upgrade server.py ─────────────────────────────────")
    write(HERE / "app" / "web" / "server.py", SERVER_PY)

    # ── 6. index.html ────────────────────────────────────────────────
    print("\n── Step 6: Upgrade index.html ────────────────────────────────")
    write(HERE / "app" / "web" / "templates" / "index.html", INDEX_HTML)

    # ── 7. results.html ──────────────────────────────────────────────
    print("\n── Step 7: Upgrade results.html ──────────────────────────────")
    write(HERE / "app" / "web" / "templates" / "results.html", RESULTS_HTML)

    # ── 8. style.css ─────────────────────────────────────────────────
    print("\n── Step 8: Upgrade style.css ─────────────────────────────────")
    write(HERE / "app" / "web" / "static" / "style.css", STYLE_CSS)

    # ── 9. script.js ─────────────────────────────────────────────────
    print("\n── Step 9: Upgrade script.js ─────────────────────────────────")
    write(HERE / "app" / "web" / "static" / "script.js", SCRIPT_JS)

    # ── 10. run.bat ──────────────────────────────────────────────────
    print("\n── Step 10: Create run.bat ───────────────────────────────────")
    write(HERE / "run.bat", RUN_BAT)

    # ── 11. Create cache directory ───────────────────────────────────
    print("\n── Step 11: Ensure data/cache/ exists ────────────────────────")
    cache_dir = HERE / "data" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    print(f"  [ok]    {cache_dir.relative_to(HERE)}/")

    print("\n" + "=" * 62)
    print("  All done!")
    print()
    print("  Next steps:")
    print("  1. Start llama-server (see run.bat for the command)")
    print("  2. Double-click run.bat  OR  python app\\web\\server.py")
    print("  3. Open http://127.0.0.1:5000")
    print("=" * 62)


if __name__ == "__main__":
    main()