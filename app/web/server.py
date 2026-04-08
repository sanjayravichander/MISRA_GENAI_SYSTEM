"""
app/web/server.py  —  MISRA GenAI Flask Web UI  (Results Viewer)

Architecture:
  - The pipeline (Phase 6a -> 6b -> 7 -> 8) runs ONLY via CLI (orchestrator.py)
  - This web server is a pure results viewer — no LLM, no pipeline, no heavy work
  - It reads evaluated_fixes.json from data/output/<run_id>/ and serves it

Routes:
  GET  /                        -> upload page (index.html)
  POST /api/analyse             -> saves uploads, launches orchestrator.py subprocess
  GET  /api/progress/<job_id>   -> SSE stream of pipeline stdout
  GET  /results/<run_id>        -> results viewer page
  GET  /api/result/<run_id>     -> JSON results from saved evaluated_fixes.json
  GET  /api/runs                -> list all completed run directories
  POST /api/commit              -> returns patched code + download URL
  GET  /api/download/<filename> -> download patched file

Run from project root:
    python app/web/server.py
Then open http://127.0.0.1:5000
"""

import json
import os
import queue
import re as _re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from flask import (Flask, Response, jsonify, render_template,
                   request, stream_with_context, send_file)
from flask_cors import CORS
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from app.config.settings import OUTPUT_DIR, CACHE_PATH, DEFAULT_BATCH_SIZE
except ImportError:
    DATA_DIR           = PROJECT_ROOT / "data"
    OUTPUT_DIR         = DATA_DIR / "output"
    CACHE_PATH         = DATA_DIR / "cache" / "results_cache.db"
    DEFAULT_BATCH_SIZE = 5

UPLOAD_DIR = PROJECT_ROOT / "data" / "input" / "web_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Audit Excel — saved to Output_excel_after_run/ inside the project root.
# This resolves to the same absolute folder regardless of where server.py is
# run from, and works on both Windows and Linux without hard-coded user paths.
#
# On your machine this resolves to:
#   C:\Users\sanjay.ravichander\misra_genai_system\misra_genai_system\Output_excel_after_run\audit_report.xlsx
#
AUDIT_EXCEL = PROJECT_ROOT / "Output_excel_after_run" / "audit_report.xlsx"
AUDIT_EXCEL.parent.mkdir(parents=True, exist_ok=True)   # create folder at startup

# ── Auto-delete stale audit Excel at startup (old schema detection) ──────────
# If audit_report.xlsx exists with the old schema (Violated Code / Fixed Code /
# Status columns instead of Warning Details + File Summary sheets), delete it
# so the next save creates a fresh two-sheet workbook automatically.
try:
    if AUDIT_EXCEL.exists():
        import openpyxl as _opx_chk
        _wb_chk = _opx_chk.load_workbook(str(AUDIT_EXCEL), read_only=True)
        _stale_chk = {"Violated Code", "Fixed Code", "Status"}
        _sheets_chk = _wb_chk.sheetnames
        _ws_chk = _wb_chk.active
        _hdrs_chk = {str(c.value).strip() for c in _ws_chk[1] if c.value}
        _wb_chk.close()
        _needs_rebuild = bool(_hdrs_chk & _stale_chk) or "Warning Details" not in _sheets_chk
        if _needs_rebuild:
            import logging
            logging.getLogger(__name__).info(
                "audit_report.xlsx has stale schema — deleting for fresh rebuild on next save"
            )
            try:
                AUDIT_EXCEL.unlink()
            except PermissionError:
                # File open in Excel on Windows — rename it so a new one can be created
                _stale_path = AUDIT_EXCEL.with_name("audit_report_stale_backup.xlsx")
                AUDIT_EXCEL.rename(_stale_path)
except Exception:
    pass  # non-critical — stale detection will also run inside _load_or_init_workbook

ALLOWED_EXCEL = {".xlsx", ".xls"}
ALLOWED_C     = {".c", ".h"}

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
_WEB_DIR      = Path(__file__).resolve().parent
_TEMPLATE_DIR = _WEB_DIR / "templates"
_STATIC_DIR   = _WEB_DIR / "static"

if not _TEMPLATE_DIR.exists():
    raise RuntimeError(f"\n\n[server.py] templates/ not found at:\n  {_TEMPLATE_DIR}\n")
if not _STATIC_DIR.exists():
    raise RuntimeError(f"\n\n[server.py] static/ not found at:\n  {_STATIC_DIR}\n")

app = Flask(
    __name__,
    template_folder=str(_TEMPLATE_DIR),
    static_folder=str(_STATIC_DIR),
)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

# In-memory job tracker (pipeline subprocess jobs)
JOBS: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Config — Excel MISRA rule configuration
# ---------------------------------------------------------------------------
_CONFIG_TMP = PROJECT_ROOT / "data" / "_config_tmp"
_CONFIG_TMP.mkdir(parents=True, exist_ok=True)

# token -> saved Excel path
_CONFIG_FILES: Dict[str, Path] = {}

# Folder where user specification Excel files are saved after Apply Configuration
USER_SPEC_FOLDER = PROJECT_ROOT / "data" / "user_specification_excel_folder"
USER_SPEC_FOLDER.mkdir(parents=True, exist_ok=True)

# Locked original — NEVER written to by the app
ORIGINAL_SPEC = PROJECT_ROOT / "data" / "user_specification.xlsx"

# Single working copy saved under user_specification_excel_folder — updated on every Apply
WORKING_SPEC  = USER_SPEC_FOLDER / "user_specification.xlsx"


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def _normalize_user_category(value: Any) -> str:
    raw = _safe_text(value).upper()
    if not raw:
        return ""
    if raw in {"M", "R", "A"}:
        return raw
    for ch in raw:
        if ch in {"M", "R", "A"}:
            return ch
    return ""


def _display_misra_category(value: Any) -> str:
    raw = _safe_text(value)
    upper = raw.upper()
    if upper == "MISRA-M":
        return "Mandatory"
    if upper == "MISRA-R":
        return "Required"
    if upper == "MISRA-A":
        return "Advisory"
    return raw


def _ensure_user_category_col(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).strip() for c in df.columns]
    if "User Category" not in df.columns:
        df["User Category"] = ""
    return df


def _read_excel_df(path: Path) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext == ".xls":
        try:
            return pd.read_excel(path, engine="xlrd")
        except Exception:
            return pd.read_excel(path)
    return pd.read_excel(path, engine="openpyxl")


def _excel_rows_from_df(df: pd.DataFrame) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for idx, row in df.iterrows():
        rule_raw = _safe_text(row.get("MISRA Rule", ""))
        rule_list = rule_raw.replace("Rule-", "").replace("Rule_", "").strip()
        rows.append({
            "row_index": int(idx),
            "sl_no": _safe_text(row.get("SI.No", idx + 1)),
            "rule_list": rule_list,
            "misra_category": _safe_text(row.get("MISRA Category", "")),
            "misra_category_display": _display_misra_category(row.get("MISRA Category", "")),
            "user_category": _normalize_user_category(row.get("User Category", "")),
            "warning_message_nos": _safe_text(row.get("Warning Message Nos.", "")),
        })
    return rows


def _get_config_path(token: str) -> Optional[Path]:
    token = Path(token).name
    path = _CONFIG_FILES.get(token)
    if path and path.exists():
        return path
    matches = list(_CONFIG_TMP.glob(f"{token}_*.xlsx"))
    if matches:
        return matches[0]
    matches = list(_CONFIG_TMP.glob(f"{token}_*.xls"))
    if matches:
        return matches[0]
    return None


# ---------------------------------------------------------------------------
# Routes — pages
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Model pre-warm  — loads Mistral-7B into RAM in background at server start
# so the first analysis request doesn't wait 30-60s for model loading.
# ---------------------------------------------------------------------------
def _prewarm_model():
    """Load the LLM into RAM once at startup — runs in a daemon thread."""
    try:
        import sys as _sys
        _sys.path.insert(0, str(PROJECT_ROOT))
        from app.config.settings import LOCAL_MODEL_PATH, LLM_N_CTX, LLM_N_THREADS, LLM_N_GPU_LAYERS
        from app.generation.generate_misra_response import GenerationConfig, LocalLlamaRuntime
        cfg = GenerationConfig(
            model_path=LOCAL_MODEL_PATH,
            n_ctx=LLM_N_CTX,
            n_threads=LLM_N_THREADS,
            n_gpu_layers=LLM_N_GPU_LAYERS,
        )
        print(f"[server] Pre-warming model: {LOCAL_MODEL_PATH}", flush=True)
        LocalLlamaRuntime.get_instance(cfg)
        print("[server] Model ready — first analysis will start instantly", flush=True)
    except Exception as exc:
        print(f"[server] Model pre-warm failed (will load on first run): {exc}", flush=True)

_prewarm_thread = threading.Thread(target=_prewarm_model, daemon=True, name="model-prewarm")
_prewarm_thread.start()

@app.route("/")
def index():
    return render_template("index.html", default_batch=DEFAULT_BATCH_SIZE)


@app.route("/results/<run_id>")
def results(run_id):
    return render_template("results.html", run_id=run_id)


@app.route("/results/merged/<path:run_ids>")
def results_merged(run_ids):
    """Show a combined results page for multiple run IDs (comma-separated)."""
    # Prepend "merged/" so MISRA_RUN_ID in JS is "merged/runA,runB"
    # and fetch(`/api/result/${runId}`) correctly hits /api/result/merged/...
    return render_template("results.html", run_id="merged/" + run_ids)


# ---------------------------------------------------------------------------
# Route — get MERGED result for multiple run IDs (comma-separated)
# Used by View Full Report when multiple files have been analysed per-file.
# ---------------------------------------------------------------------------
@app.route("/api/result/merged/<path:run_ids>")
def get_merged_result(run_ids):
    """Merge results from multiple run_ids into one response."""
    # Validate each run ID safely — only allow alphanumeric, underscores, hyphens.
    # Do NOT use secure_filename() here — it strips commas and merges IDs together.
    ids = [r.strip() for r in run_ids.split(",")
           if r.strip() and _re.match(r'^[A-Za-z0-9_-]+$', r.strip())]
    if not ids:
        return jsonify(error="No run IDs provided"), 400

    all_warnings = []
    seen_wids = set()
    total_manual = total_high = total_medium = total_low = total_cached = 0

    for run_id in ids:
        run_dir = OUTPUT_DIR / run_id
        if not run_dir.exists():
            continue

        result_file = run_dir / "evaluated_fixes.json"
        if not result_file.exists():
            result_file = run_dir / "fix_suggestions.json"
        if not result_file.exists():
            continue

        try:
            data = json.loads(result_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        results_list = data.get("results", [])

        # Merge source_context from enriched_warnings
        enriched_path = run_dir / "enriched_warnings.json"
        if enriched_path.exists():
            try:
                enriched_data = json.loads(enriched_path.read_text(encoding="utf-8"))
                enriched_by_id = {str(w.get("warning_id")): w for w in enriched_data.get("warnings", [])}
                for r in results_list:
                    wid = str(r.get("warning_id", ""))
                    ew = enriched_by_id.get(wid)
                    if ew:
                        r["source_context"] = ew.get("source_context", {})
                        for field in ("file_path", "line_start", "line_end", "message",
                                      "severity", "rule_id", "function_name",
                                      "checker_name", "category"):
                            if field not in r and ew.get(field):
                                r[field] = ew[field]
            except Exception:
                pass

        for r in results_list:
            wid = str(r.get("warning_id", ""))
            if wid in seen_wids:
                continue
            seen_wids.add(wid)
            # Tag each warning with its originating run_id for commit/audit actions
            r["_run_id"] = run_id
            all_warnings.append(r)

            ev = r.get("evaluation") or r.get("evaluator_result") or {}
            conf = str(ev.get("overall_confidence", r.get("overall_confidence", ""))).lower()
            if conf == "high":     total_high   += 1
            elif conf == "medium": total_medium += 1
            else:                  total_low    += 1
            if ev.get("needs_manual_review") or ev.get("manual_review_required"):
                total_manual += 1
            if r.get("_from_cache"):
                total_cached += 1

    summary = {
        "total":  len(all_warnings),
        "high":   total_high,
        "medium": total_medium,
        "low":    total_low,
        "manual": total_manual,
        "cached": total_cached,
    }

    return jsonify({
        "run_id":   run_ids,
        "status":   "done",
        "summary":  summary,
        "warnings": all_warnings,
        "merged":   True,
        "run_ids":  ids,
    })


# ---------------------------------------------------------------------------
# Route — list all completed runs
# ---------------------------------------------------------------------------
@app.route("/api/runs")
def list_runs():
    runs = []
    if not OUTPUT_DIR.exists():
        return jsonify(runs=[])
    for d in sorted(OUTPUT_DIR.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        result_file = d / "evaluated_fixes.json"
        if not result_file.exists():
            result_file = d / "fix_suggestions.json"
        if result_file.exists():
            try:
                data         = json.loads(result_file.read_text(encoding="utf-8"))
                results_list = data.get("results", [])
                total  = len(results_list)
                manual = sum(
                    1 for r in results_list
                    if (r.get("evaluation") or r.get("evaluator_result") or {}).get("needs_manual_review")
                )
                runs.append({
                    "run_id": d.name,
                    "total":  total,
                    "manual": manual,
                    "file":   result_file.name,
                    "mtime":  result_file.stat().st_mtime,
                })
            except Exception:
                pass
    return jsonify(runs=runs)


# ---------------------------------------------------------------------------
# Route — get result for a run (reads from saved JSON file)
# ---------------------------------------------------------------------------
@app.route("/api/result/<run_id>")
def get_result(run_id):
    run_id  = secure_filename(run_id)
    run_dir = OUTPUT_DIR / run_id

    if not run_dir.exists():
        job = next((j for j in JOBS.values() if j.get("run_id") == run_id), None)
        if job:
            return jsonify(error="Pipeline still running", status=job["status"]), 202
        return jsonify(error="Run not found"), 404

    # Prefer evaluated_fixes.json, fall back to fix_suggestions.json
    result_file = run_dir / "evaluated_fixes.json"
    if not result_file.exists():
        result_file = run_dir / "fix_suggestions.json"
    if not result_file.exists():
        job = next((j for j in JOBS.values() if j.get("run_id") == run_id), None)
        if job and job["status"] == "running":
            return jsonify(error="Pipeline still running", status="running"), 202
        return jsonify(error="Results not ready yet", status="pending"), 202

    try:
        data = json.loads(result_file.read_text(encoding="utf-8"))
    except Exception as e:
        return jsonify(error=f"Failed to read results: {e}"), 500

    results_list = data.get("results", [])

    # Merge source_context + raw warning fields from enriched_warnings.json
    # (fix_suggestions.json does not carry source code — it lives in enriched)
    enriched_path = run_dir / "enriched_warnings.json"
    if enriched_path.exists():
        try:
            enriched_data = json.loads(enriched_path.read_text(encoding="utf-8"))
            enriched_by_id = {
                str(w.get("warning_id")): w
                for w in enriched_data.get("warnings", [])
            }
            for r in results_list:
                wid = str(r.get("warning_id", ""))
                ew  = enriched_by_id.get(wid)
                if ew:
                    # Attach source_context so the UI can show violated code
                    r["source_context"] = ew.get("source_context", {})
                    # Attach raw warning fields (file, line, message, severity)
                    for field in ("file_path", "line_start", "line_end",
                                  "message", "severity", "rule_id",
                                  "function_name", "checker_name",
                                  "category"):   # category = "MISRA-R (Required)" etc. for filter
                        if field not in r and ew.get(field):
                            r[field] = ew[field]
        except Exception:
            pass  # enriched merge is best-effort

    # Build summary
    high = medium = low = manual = cached = 0
    for r in results_list:
        ev   = r.get("evaluation") or r.get("evaluator_result") or {}
        conf = str(ev.get("overall_confidence", r.get("overall_confidence", ""))).lower()
        if conf == "high":     high   += 1
        elif conf == "medium": medium += 1
        else:                  low    += 1
        if ev.get("needs_manual_review") or ev.get("manual_review_required"):
            manual += 1
        if r.get("_from_cache"):
            cached += 1

    summary = {
        "total":  len(results_list),
        "high":   high,
        "medium": medium,
        "low":    low,
        "manual": manual,
        "cached": cached,
    }

    return jsonify({
        "run_id":   run_id,
        "status":   "done",
        "summary":  summary,
        "warnings": results_list,
        "out_dir":  str(run_dir),
    })


# ---------------------------------------------------------------------------
# Route — commit fix (returns patched code as downloadable file)
# ---------------------------------------------------------------------------
@app.route("/api/commit", methods=["POST"])
def commit_fix():
    body       = request.get_json(force=True) or {}
    warning_id = str(body.get("warning_id", "unknown"))
    run_id     = str(body.get("run_id", ""))
    patched    = body.get("patched_code", "")

    if not patched or patched.strip() == "[fix code not available]":
        return jsonify(error="No patched code to commit"), 400

    commit_dir = PROJECT_ROOT / "data" / "commits"
    commit_dir.mkdir(parents=True, exist_ok=True)

    # ── Try to merge patch into the full original source file ──
    full_patched = None
    original_filename = None
    src_file_path = None
    patch_line_start = None   # 1-indexed line number where the fix was applied
    patch_line_count_val = 0  # how many lines were actually changed

    if run_id:
        try:
            run_dir = OUTPUT_DIR / secure_filename(run_id)
            enriched_path = run_dir / "enriched_warnings.json"
            if enriched_path.exists():
                enriched = json.loads(enriched_path.read_text(encoding="utf-8"))
                warnings_list = enriched.get("warnings", [])
                w = next((x for x in warnings_list if str(x.get("warning_id")) == warning_id), None)
                if w:
                    rel_file   = w.get("file_path", "")
                    line_start = int(w.get("line_start") or 0)
                    line_end   = int(w.get("line_end") or line_start)
                    sc         = w.get("source_context", {})
                    ctx_start  = int(sc.get("context_start_line", line_start) if isinstance(sc, dict) else line_start)
                    ctx_end    = int(sc.get("context_end_line",   line_end)   if isinstance(sc, dict) else line_end)
                    fname_only = Path(rel_file).name if rel_file else ""

                    # Search candidate directories for the source file (most specific first)
                    search_roots = []
                    # 1) Exact job dir for THIS run — run_id format is "20240101_120000_<job_id>"
                    #    The job_id is the last segment after the final underscore.
                    exact_job_id = run_id.split("_")[-1] if run_id else ""
                    if exact_job_id and UPLOAD_DIR.exists():
                        exact_job_dir = UPLOAD_DIR / exact_job_id
                        if exact_job_dir.exists():
                            search_roots.append(exact_job_dir / "source_code")
                            search_roots.append(exact_job_dir)
                    # 2) All other web_uploads dirs (newest first — fallback)
                    if UPLOAD_DIR.exists():
                        for d in sorted(UPLOAD_DIR.iterdir(), reverse=True):
                            if d.is_dir() and d.name != exact_job_id:
                                search_roots.append(d / "source_code")
                                search_roots.append(d)
                    # 3) Legacy _upload_tmp dirs
                    _tmp = PROJECT_ROOT / "data" / "_upload_tmp"
                    if _tmp.exists():
                        for d in sorted(_tmp.iterdir(), reverse=True):
                            if d.is_dir():
                                search_roots.append(d / "source")
                                search_roots.append(d)

                    if fname_only:
                        for root in search_roots:
                            candidate = root / fname_only
                            if candidate.exists():
                                src_file_path = candidate
                                original_filename = fname_only
                                break

                    if src_file_path:
                        orig_lines = src_file_path.read_text(encoding="utf-8", errors="replace").splitlines()
                        import re as _re2

                        # ── Helper: preserve original line indentation ──────────────
                        def _apply_indent(orig_ln, new_code):
                            indent = _re2.match(r"^(\s*)", orig_ln).group(1)
                            return indent + new_code.lstrip()

                        # ── Helper: clean prose-style patched_code ──────────────────
                        # LLM sometimes returns "replace X; with Y;" instead of code.
                        # Extract the last C statement (after "with ") as the fix.
                        def _clean_patched(raw):
                            # "replace printf(...); with printf(...);"  → "printf(...);"
                            m_with = _re2.search(r"\bwith\s+(.*)", raw, _re2.IGNORECASE | _re2.DOTALL)
                            if m_with:
                                candidate = m_with.group(1).strip()
                                # If it still has multiple statements, take the last
                                stmts = [s.strip() for s in _re2.split(r";", candidate) if s.strip()]
                                return (stmts[-1] + ";") if stmts else raw
                            # If multiple semicolons, the last statement is the fix
                            stmts = [s.strip() for s in _re2.split(r";", raw) if s.strip()]
                            return (stmts[-1] + ";") if len(stmts) > 1 else raw

                        # ── Helper: structural + token score ───────────────────────
                        # Uses ALL tokens (including C type keywords) for matching,
                        # plus a structural bonus when both patch and source line are
                        # the same syntactic form (declaration vs assignment vs call).
                        def _score_line(src_ln, patch_code):
                            # Token overlap — ALL identifiers, including uint8_t/uint16_t etc.
                            all_patch_toks = set(_re2.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", patch_code))
                            all_src_toks   = set(_re2.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", src_ln))
                            token_score = len(all_patch_toks & all_src_toks)

                            # Structural bonus (+2): both lines are the SAME syntactic category
                            # declaration:  "type var;"   or  "type var = expr;"
                            # assignment:   "var = expr;"
                            # call:         "func(...);"
                            _DECL  = _re2.compile(r"^\s*[a-zA-Z_]\w*(?:\s*\*)?\s+[a-zA-Z_]\w*\s*(?:=|;)")
                            _ASGN  = _re2.compile(r"^\s*[a-zA-Z_]\w*\s*(?:\[.*?\])?\s*=")
                            _CALL  = _re2.compile(r"^\s*[a-zA-Z_]\w*\s*\(")
                            def _kind(s):
                                s = s.strip()
                                if _DECL.match(s): return "decl"
                                if _ASGN.match(s): return "asgn"
                                if _CALL.match(s): return "call"
                                return "other"
                            struct_bonus = 2 if _kind(patch_code) == _kind(src_ln) else 0

                            return token_score + struct_bonus

                        # ── Parse patched_code lines ────────────────────────────────
                        # The LLM may emit:
                        #   A) "28      small = (uint8_t)total + 300;"  ← explicit line number
                        #   B) "uint16_t small;"                        ← bare code, no number
                        #   C) "replace printf(...); with printf(...);" ← English prose
                        patch_map  = {}   # { 1-indexed line number: new code }
                        bare_lines = []   # code strings stripped of any line-number prefix
                        for ln in patched.splitlines():
                            m = _re2.match(r"^\s*(\d+)\s+(.*)", ln)
                            if m:
                                lnum = int(m.group(1))
                                code = m.group(2)
                                patch_map[lnum] = code
                                bare_lines.append(code)
                            else:
                                bare_lines.append(ln)

                        # ── STRATEGY A: SURGICAL (LLM gave explicit line numbers) ───
                        # Replace only those exact numbered lines, everything else stays.
                        if patch_map:
                            merged = list(orig_lines)
                            for lnum, new_code in patch_map.items():
                                idx = lnum - 1
                                if 0 <= idx < len(merged):
                                    merged[idx] = _apply_indent(merged[idx], new_code)
                            patch_line_start    = min(patch_map.keys())
                            patch_line_count_val = len(patch_map)
                            app.logger.info(f"[commit] SURGICAL: replaced lines {sorted(patch_map.keys())}")

                        # ── STRATEGY B: FUZZY (no line numbers — 1-3 line fix) ──────
                        # Clean prose ("replace X with Y"), then score every line in the
                        # context window using token overlap + structural form bonus.
                        # The highest-scoring line is the violated line to replace.
                        elif len(bare_lines) <= 3:
                            raw_patch  = "\n".join(bare_lines)
                            clean_code = _clean_patched(raw_patch)

                            # Score every non-blank line inside the context window
                            ctx_range = orig_lines[max(0, ctx_start - 1): ctx_end]
                            best_score, best_idx = 0, None
                            for rel_i, src_ln in enumerate(ctx_range):
                                if not src_ln.strip():
                                    continue
                                score = _score_line(src_ln, clean_code)
                                if score > best_score:
                                    best_score, best_idx = score, rel_i

                            if best_idx is not None and best_score > 0:
                                abs_idx = (ctx_start - 1) + best_idx
                                merged  = list(orig_lines)
                                merged[abs_idx] = _apply_indent(orig_lines[abs_idx], clean_code)
                                patch_line_start    = abs_idx + 1
                                patch_line_count_val = 1
                                app.logger.info(
                                    f"[commit] FUZZY: matched line {patch_line_start} "
                                    f"score={best_score} patch={repr(clean_code[:60])}"
                                )
                            else:
                                # No confident match — fall back to warning line_start
                                abs_idx = max(0, (line_start or ctx_start) - 1)
                                merged  = list(orig_lines)
                                merged[abs_idx] = _apply_indent(orig_lines[abs_idx], clean_code)
                                patch_line_start    = abs_idx + 1
                                patch_line_count_val = 1
                                app.logger.warning(
                                    f"[commit] FUZZY fallback (no match): "
                                    f"replaced line {patch_line_start}"
                                )

                        # ── STRATEGY C: BLOCK REPLACE (LLM returned the full fixed block) ─
                        # bare_lines > 3 means the LLM gave the whole context rewritten.
                        # Replace the context window with the bare lines verbatim.
                        else:
                            before = orig_lines[: max(0, ctx_start - 1)]
                            after  = orig_lines[ctx_end:]
                            merged = before + bare_lines + after
                            patch_line_start    = ctx_start
                            patch_line_count_val = len(bare_lines)
                            app.logger.info(f"[commit] BLOCK REPLACE mode: lines {ctx_start}-{ctx_end}")

                        full_patched = "\n".join(merged)
        except Exception as merge_err:
            app.logger.warning(f"Patch merge failed (will save snippet only): {merge_err}")

    # Fall back to saving the snippet alone
    content_to_save = full_patched if full_patched else patched
    is_full_file = full_patched is not None

    safe_wid = secure_filename(warning_id)
    base_name = original_filename or f"warning_{safe_wid}"
    stem = Path(base_name).stem
    fname = f"patched_{stem}_{uuid.uuid4().hex[:6]}.c"
    out_path = commit_dir / fname
    out_path.write_text(content_to_save, encoding="utf-8")

    # Save backup of original source file for potential revert
    if src_file_path and src_file_path.exists():
        try:
            backup_path = commit_dir / f"orig_{safe_wid}_{src_file_path.stem}.bak"
            if not backup_path.exists():
                shutil.copy2(str(src_file_path), str(backup_path))
        except Exception:
            pass

    return jsonify({
        "status":            "ok",
        "warning_id":        warning_id,
        "download_url":      f"/api/download/{fname}",
        "filename":          fname,
        "patched_code":      content_to_save,
        "is_full_file":      is_full_file,
        "original_file":     original_filename or "",
        "audit_updated":     False,
        "audit_path":        str(AUDIT_EXCEL),
        "patch_line_start":  patch_line_start,
        "patch_line_count":  patch_line_count_val if is_full_file else len((patched or "").splitlines()),
        "run_id":            run_id,
    })


# ---------------------------------------------------------------------------
# Route — download patched file
# ---------------------------------------------------------------------------
@app.route("/api/download/<filename>")
def download_file(filename):
    filename  = secure_filename(filename)
    file_path = PROJECT_ROOT / "data" / "commits" / filename
    if not file_path.exists():
        return jsonify(error="File not found"), 404
    return send_file(str(file_path), as_attachment=True, download_name=filename)


# ---------------------------------------------------------------------------
# Route — Save patched .c file to Output_excel_after_run/patched_files/
# ---------------------------------------------------------------------------
@app.route("/api/save_patched_c", methods=["POST"])
def save_patched_c():
    body       = request.get_json(force=True) or {}
    filename   = secure_filename(str(body.get("filename", "patched.c")))
    warning_id = str(body.get("warning_id", ""))
    # Ensure filename ends with .c
    if not filename.lower().endswith(".c"):
        filename = filename + ".c"
    src_name = secure_filename(str(body.get("src_filename", filename)))
    commit_dir = PROJECT_ROOT / "data" / "commits"
    # Find the committed patched file
    src_path = commit_dir / filename
    if not src_path.exists():
        # Try to find by warning_id pattern
        candidates = list(commit_dir.glob(f"patched_*_{warning_id[:8]}*.c")) if warning_id else []
        if not candidates:
            candidates = list(commit_dir.glob("patched_*.c"))
        if candidates:
            src_path = max(candidates, key=lambda p: p.stat().st_mtime)
        else:
            return jsonify(error="Patched file not found"), 404
    out_dir = PROJECT_ROOT / "Output_excel_after_run" / "patched_files"
    out_dir.mkdir(parents=True, exist_ok=True)
    # Save with original source filename (e.g. control.c) not the patched_* name
    dest_name = src_name if src_name.lower().endswith(".c") else (src_name + ".c")
    dest_path = out_dir / dest_name
    import shutil as _sh
    _sh.copy2(str(src_path), str(dest_path))
    return jsonify({"status": "ok", "saved_to": str(dest_path), "filename": dest_name})


# ---------------------------------------------------------------------------
# Route — Get committed patch for a warning (so Results page can show full
#         patched file even after navigation from homepage side panel)
# ---------------------------------------------------------------------------
@app.route("/api/committed/<warning_id>")
def get_committed(warning_id):
    """Return the most recently committed patched file for a given warning_id."""
    safe_wid   = secure_filename(str(warning_id))
    commit_dir = PROJECT_ROOT / "data" / "commits"
    if not commit_dir.exists():
        return jsonify(committed=False), 200

    # Find all patched_*.c files whose stem ends with the warning_id (fragile but
    # the only link we have — filenames are patched_<stem>_<hex>.c and the warning
    # id is stored only in the backup name orig_<wid>_<stem>.bak).
    # Use backup file to identify which patched file belongs to this wid.
    backups = list(commit_dir.glob(f"orig_{safe_wid}_*.bak"))
    if not backups:
        return jsonify(committed=False), 200

    # Find the most recent patched file that was written after the latest backup
    latest_backup = max(backups, key=lambda p: p.stat().st_mtime)
    backup_stem   = latest_backup.stem[len(f"orig_{safe_wid}_"):]  # e.g. "main"
    # patched files matching this source stem
    candidates = list(commit_dir.glob(f"patched_{backup_stem}_*.c"))
    if not candidates:
        # Try broader match
        candidates = list(commit_dir.glob("patched_*.c"))
    if not candidates:
        return jsonify(committed=False), 200

    latest_patch = max(candidates, key=lambda p: p.stat().st_mtime)
    try:
        patched_code = latest_patch.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return jsonify(committed=False), 200

    return jsonify({
        "committed":      True,
        "patched_code":   patched_code,
        "filename":       latest_patch.name,
        "download_url":   f"/api/download/{latest_patch.name}",
        "original_file":  backup_stem + ".c",
    })


# ---------------------------------------------------------------------------
# Route — Save audit Excel (manually triggered from Review Report tab)
# ---------------------------------------------------------------------------
@app.route("/api/save_audit", methods=["POST"])
def save_audit():
    body             = request.get_json(force=True) or {}
    warning_id       = str(body.get("warning_id", "unknown"))
    run_id           = str(body.get("run_id", ""))
    all_fixes        = body.get("all_fixes", [])
    chosen_fix_index = body.get("chosen_fix_index")
    chosen_fix_code  = body.get("chosen_fix_code", "")
    fixed_code_full  = body.get("fixed_code_full", "")
    user_edited_code = body.get("user_edited_code", "")
    is_no_change     = bool(body.get("is_no_change", False))
    was_user_edited  = bool(body.get("was_user_edited", False))

    # Build violated_code from enriched warnings
    violated_code = ""
    file_name     = body.get("file_name", "")   # sent directly from JS as fallback
    if run_id:
        try:
            rdir = OUTPUT_DIR / secure_filename(run_id)
            ep   = rdir / "enriched_warnings.json"
            if ep.exists():
                import json as _jx
                ed = _jx.loads(ep.read_text(encoding="utf-8"))
                for wx in ed.get("warnings", []):
                    if str(wx.get("warning_id")) == str(warning_id):
                        sc = wx.get("source_context", {})
                        violated_code = sc.get("context_text", "") if isinstance(sc, dict) else str(sc)
                        fp = wx.get("file_path", "")
                        file_name = Path(fp).name if fp else ""
                        break
        except Exception:
            pass

    ok = _update_audit_excel(
        warning_id=warning_id,
        run_id=run_id,
        file_name=file_name,
        violated_code=violated_code,
        all_fixes=all_fixes,
        chosen_fix_index=chosen_fix_index,
        chosen_fix_code=chosen_fix_code,
        fixed_code_full=fixed_code_full,
        user_edited_code=user_edited_code,
        is_no_change=is_no_change,
        was_user_edited=was_user_edited,
    )
    if ok:
        return jsonify({"status": "ok", "audit_path": str(AUDIT_EXCEL)})
    return jsonify({"status": "error", "message": "Failed to update audit Excel"}), 500


# ---------------------------------------------------------------------------
# Audit Excel — two-sheet design:
#   Sheet 1 "Warning Details"  : one row per warning number
#   Sheet 2 "File Summary"     : one row per source file, aggregating all warnings
# ---------------------------------------------------------------------------
SOURCE_EXCEL = (PROJECT_ROOT / "data" / "input" / "warning_reports" / "mock_warning_report.xlsx")

# Columns appended after the dynamic Fix N columns on Sheet 1
_DETAIL_EXTRA = [
    "Chosen Fix",
    "Chosen Fix Code",
    "Violated Source Code",
    "Fixed Code (Full File)",
    "User Edited & Committed",
    "Audit Status",
    "Run ID",
    "Timestamp",
]

# Fixed columns on Sheet 2 (File Summary)
_SUMMARY_COLS = [
    "Source File",
    "Total Warnings",
    "Warning Numbers",
    "Rules Violated",
    "Warnings Detail",
    "Full Fixed Source File",
    "Fix Summary",
    "Last Updated",
]

# Stale column names from the old schema — if present, we rebuild the workbook
_STALE_COLS = {"Violated Code", "Fixed Code", "Status"}


def _load_or_init_workbook():
    """
    Load the audit workbook, rebuilding from scratch if it has the old stale schema.
    Always returns (wb, ws_detail, ws_summary).
    """
    import openpyxl
    from openpyxl import load_workbook, Workbook
    import shutil as _shutil

    def _fresh_wb():
        """Create a brand-new workbook seeded from source Excel."""
        wb = Workbook()
        ws1 = wb.active
        ws1.title = "Warning Details"
        ws2 = wb.create_sheet("File Summary")

        # Seed Warning Details headers from source Excel columns
        base_headers = ["Warning Number", "Category", "Rule", "Message", "File", "Function"]
        if SOURCE_EXCEL.exists():
            try:
                src_wb = load_workbook(str(SOURCE_EXCEL), read_only=True)
                src_ws = src_wb.active
                src_headers = [str(c.value).strip() for c in src_ws[1] if c.value]
                if src_headers:
                    base_headers = src_headers
                src_wb.close()
            except Exception:
                pass

        for i, h in enumerate(base_headers, 1):
            ws1.cell(row=1, column=i, value=h)

        # Seed Warning Details rows from source Excel data
        if SOURCE_EXCEL.exists():
            try:
                src_wb2 = load_workbook(str(SOURCE_EXCEL), read_only=True)
                src_ws2 = src_wb2.active
                for row in src_ws2.iter_rows(min_row=2, values_only=True):
                    if any(v is not None for v in row):
                        ws1.append(list(row))
                src_wb2.close()
            except Exception:
                pass

        # File Summary headers
        for i, h in enumerate(_SUMMARY_COLS, 1):
            ws2.cell(row=1, column=i, value=h)

        return wb, ws1, ws2

    if AUDIT_EXCEL.exists():
        try:
            wb = load_workbook(str(AUDIT_EXCEL))
            ws1 = wb["Warning Details"] if "Warning Details" in wb.sheetnames else wb.active
            # Check for stale schema
            existing_headers = {str(c.value).strip() for c in ws1[1] if c.value}
            if existing_headers & _STALE_COLS:
                app.logger.info("Audit Excel has stale schema — rebuilding from source")
                try:
                    wb.close()
                except Exception:
                    pass
                # Try to delete — on Windows the file may be open in Excel
                try:
                    AUDIT_EXCEL.unlink()
                except PermissionError:
                    # File locked by Excel — write to a new path and replace
                    app.logger.warning("audit_report.xlsx is locked — will overwrite on next save")
                    AUDIT_EXCEL.unlink(missing_ok=True) if hasattr(Path, 'unlink') else None
                wb, ws1, ws2 = _fresh_wb()
            else:
                ws2 = wb["File Summary"] if "File Summary" in wb.sheetnames else wb.create_sheet("File Summary")
                if ws2.max_row < 1 or ws2.cell(1, 1).value != "Source File":
                    for i, h in enumerate(_SUMMARY_COLS, 1):
                        ws2.cell(row=1, column=i, value=h)
        except Exception as _e:
            app.logger.warning(f"Could not load audit Excel ({_e}) — rebuilding fresh")
            try:
                AUDIT_EXCEL.unlink()
            except Exception:
                pass
            wb, ws1, ws2 = _fresh_wb()
            wb, ws1, ws2 = _fresh_wb()
    else:
        wb, ws1, ws2 = _fresh_wb()

    return wb, ws1, ws2


def _update_audit_excel(
    warning_id: str,
    run_id: str,
    file_name: str,
    violated_code: str,
    all_fixes: list,
    chosen_fix_index,
    chosen_fix_code: str,
    fixed_code_full: str,
    user_edited_code: str,
    is_no_change: bool,
    was_user_edited: bool,
) -> bool:
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    import json as _json
    import datetime

    HDR_FONT  = Font(bold=True, color="FFFFFF", name="Arial", size=10)
    HDR_FILL  = PatternFill("solid", start_color="1E3A5F")
    HDR_ALIGN = Alignment(wrap_text=True, vertical="center", horizontal="center")
    CELL_FONT = Font(name="Arial", size=9)
    MONO_FONT = Font(name="Courier New", size=8)

    def _sh(cell):
        cell.font = HDR_FONT; cell.fill = HDR_FILL; cell.alignment = HDR_ALIGN

    try:
        wb, ws1, ws2 = _load_or_init_workbook()

        # ── SHEET 1: Warning Details ──────────────────────────────────────────

        # Read current headers
        headers = [str(c.value).strip() if c.value is not None else "" for c in ws1[1]]

        def col_idx(name):
            try:    return headers.index(name) + 1
            except: return None

        def ensure_col(name, before_idx=None):
            if name in headers:
                return headers.index(name) + 1
            if before_idx and 1 <= before_idx <= len(headers) + 1:
                ws1.insert_cols(before_idx)
                cell = ws1.cell(row=1, column=before_idx, value=name)
                _sh(cell)
                headers.insert(before_idx - 1, name)
                return before_idx
            new_col = len(headers) + 1
            cell = ws1.cell(row=1, column=new_col, value=name)
            _sh(cell)
            headers.append(name)
            return new_col

        # Style existing header cells (idempotent)
        for col_num in range(1, len(headers) + 1):
            c = ws1.cell(row=1, column=col_num)
            if not c.font or not c.font.bold:
                _sh(c)

        # Determine max fix count needed (across new payload + existing headers)
        max_fix_new = max((f.get("index", 0) for f in all_fixes), default=0)
        existing_max = max(
            (int(h[4:].strip()) for h in headers if h.startswith("Fix ") and h[4:].strip().isdigit()),
            default=0,
        )
        max_fix = max(max_fix_new, existing_max)

        # Ensure Fix N columns, inserted BEFORE the first fixed-extra column
        for fix_num in range(1, max_fix + 1):
            col_name = f"Fix {fix_num}"
            if col_name not in headers:
                fp = next((headers.index(fe) + 1 for fe in _DETAIL_EXTRA if fe in headers), None)
                ensure_col(col_name, before_idx=fp)

        # Ensure fixed extra columns at far right
        for fe in _DETAIL_EXTRA:
            ensure_col(fe)

        # Find existing row for this warning_id (upsert)
        wid_col    = col_idx("Warning Number")
        target_row = None
        if wid_col:
            for row in ws1.iter_rows(min_row=2):
                cv = row[wid_col - 1].value
                if cv is not None and str(cv).strip() == str(warning_id).strip():
                    target_row = row[0].row
                    break
        if target_row is None:
            target_row = ws1.max_row + 1

        # Pull enriched metadata
        ew = {}
        try:
            if run_id:
                ep = OUTPUT_DIR / secure_filename(run_id) / "enriched_warnings.json"
                if ep.exists():
                    ed = _json.loads(ep.read_text(encoding="utf-8"))
                    for w in ed.get("warnings", []):
                        if str(w.get("warning_id")) == str(warning_id):
                            ew = w
                            break
        except Exception:
            pass

        def wc1(col_name, value, mono=False, bg=None, bold=False):
            ci = col_idx(col_name)
            if not ci:
                return
            cell = ws1.cell(row=target_row, column=ci, value=value)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.font = Font(name="Courier New" if mono else "Arial",
                             size=8 if mono else 9, bold=bold)
            if bg:
                cell.fill = PatternFill("solid", start_color=bg)

        # Write base columns (only if blank or we have enriched data)
        base = {
            "Warning Number": warning_id,
            "Category":       ew.get("category") or ew.get("severity") or "",
            "Rule":           ew.get("rule_id") or "",
            "Message":        ew.get("message") or "",
            "File":           ew.get("file_path") or file_name or "",
            "Function":       ew.get("function_name") or "",
        }
        for col_name, value in base.items():
            ci = col_idx(col_name)
            if not ci:
                continue
            existing = ws1.cell(row=target_row, column=ci).value
            if not existing or (value and str(value) != str(existing)):
                wc1(col_name, value)

        # Write dynamic Fix columns
        fix_by_index = {f.get("index"): f for f in all_fixes}
        for fix_num in range(1, max_fix + 1):
            fix = fix_by_index.get(fix_num)
            if fix:
                fix_text = f"[{fix.get('title', 'Fix ' + str(fix_num))}]\n{fix.get('code', '')}"
                ci = col_idx(f"Fix {fix_num}")
                if ci:
                    cell = ws1.cell(row=target_row, column=ci, value=fix_text)
                    cell.alignment = Alignment(wrap_text=True, vertical="top")
                    cell.font = MONO_FONT
                    cell.fill = PatternFill("solid", start_color="EFF6FF")

        # Audit status
        if is_no_change:
            audit_status = "No Change Applied"; chosen_lbl = "No Change Applied"; sbg = "FFF9C4"
        elif was_user_edited:
            audit_status = "User Edited & Committed"; chosen_lbl = "User Edited"; sbg = "FFF3E0"
        elif chosen_fix_index:
            audit_status = f"Fix {chosen_fix_index} Committed"; chosen_lbl = f"Fix {chosen_fix_index}"; sbg = "E8F5E9"
        else:
            audit_status = "Pending"; chosen_lbl = "Pending"; sbg = "F3F4F6"

        wc1("Chosen Fix",              chosen_lbl)
        wc1("Chosen Fix Code",         chosen_fix_code,   mono=True)
        wc1("Violated Source Code",    violated_code,     mono=True, bg="FFF5F5")
        wc1("Fixed Code (Full File)",  fixed_code_full,   mono=True, bg="F0FDF4")
        wc1("User Edited & Committed", user_edited_code,  mono=True,
            bg="FFF3E0" if user_edited_code else None)
        wc1("Audit Status",            audit_status,      bg=sbg, bold=True)
        wc1("Run ID",                  run_id)
        wc1("Timestamp",               datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        ws1.row_dimensions[target_row].height = 100
        ws1.row_dimensions[1].height = 32

        for col_num in range(1, len(headers) + 1):
            letter = get_column_letter(col_num)
            hdr    = headers[col_num - 1]
            if any(k in hdr for k in ["Fix", "Code", "Violated", "Edited", "Full"]):
                ws1.column_dimensions[letter].width = 55
            else:
                ws1.column_dimensions[letter].width = max(len(hdr) + 4, 16)

        ws1.freeze_panes = "A2"

        # ── SHEET 2: File Summary ─────────────────────────────────────────────
        # Collect all data from Sheet 1 grouped by source file

        # Resolve column indices on Sheet 1
        h1 = [str(c.value).strip() if c.value else "" for c in ws1[1]]

        def ci1(name):
            try: return h1.index(name) + 1
            except: return None

        file_col   = ci1("File")
        wnum_col   = ci1("Warning Number")
        rule_col   = ci1("Rule")
        msg_col    = ci1("Message")
        viol_col   = ci1("Violated Source Code")
        fixed_col  = ci1("Fixed Code (Full File)")
        status_col = ci1("Audit Status")
        chosen_col = ci1("Chosen Fix")
        func_col   = ci1("Function")

        # Group rows by source file
        from collections import defaultdict
        file_groups = defaultdict(list)
        for row_num in range(2, ws1.max_row + 1):
            fn_raw = ws1.cell(row_num, file_col).value if file_col else None
            if not fn_raw or str(fn_raw).strip() == "":
                continue
            fn = Path(str(fn_raw)).name if fn_raw else ""
            if not fn:
                continue
            file_groups[fn].append(row_num)

        # Read File Summary sheet headers
        h2 = [str(c.value).strip() if c.value else "" for c in ws2[1]]

        def ensure_sum_col(name):
            if name not in h2:
                nc = len(h2) + 1
                cell = ws2.cell(row=1, column=nc, value=name)
                _sh(cell)
                h2.append(name)
            return h2.index(name) + 1

        for sc_name in _SUMMARY_COLS:
            ensure_sum_col(sc_name)

        # Style File Summary headers
        for col_num in range(1, len(h2) + 1):
            c = ws2.cell(row=1, column=col_num)
            if not c.font or not c.font.bold:
                _sh(c)

        def ci2(name):
            try: return h2.index(name) + 1
            except: return None

        # Find or create File Summary row for each source file
        sf_col = ci2("Source File")
        for fn, row_nums in file_groups.items():
            # Find existing summary row for this file
            sum_row = None
            if sf_col:
                for r in range(2, ws2.max_row + 1):
                    if str(ws2.cell(r, sf_col).value or "").strip() == fn:
                        sum_row = r
                        break
            if sum_row is None:
                sum_row = ws2.max_row + 1

            # Gather data from all warning rows for this file
            warn_nums   = []
            rules       = []
            warn_detail = []
            full_fixed  = ""  # latest non-empty full-file patch for this file
            fix_summary = []

            for rn in row_nums:
                wn = ws1.cell(rn, wnum_col).value if wnum_col else ""
                rl = ws1.cell(rn, rule_col).value if rule_col else ""
                mg = ws1.cell(rn, msg_col).value if msg_col else ""
                fn2 = ws1.cell(rn, func_col).value if func_col else ""
                ff = ws1.cell(rn, fixed_col).value if fixed_col else ""
                st = ws1.cell(rn, status_col).value if status_col else ""
                ch = ws1.cell(rn, chosen_col).value if chosen_col else ""

                if wn is not None:
                    warn_nums.append(str(wn))
                if rl:
                    rules.append(str(rl))
                # Prefer the most recent non-empty full file content
                if ff and str(ff).strip():
                    full_fixed = str(ff)
                detail_line = f"#{wn} [{rl}] {mg}"
                if fn2:
                    detail_line += f" (in {fn2})"
                warn_detail.append(detail_line)
                if st and st != "Pending":
                    fix_summary.append(f"#{wn}: {ch} — {st}")

            def wc2(col_name, value, mono=False, bg=None, bold=False):
                ci = ci2(col_name)
                if not ci: return
                cell = ws2.cell(row=sum_row, column=ci, value=value)
                cell.alignment = Alignment(wrap_text=True, vertical="top")
                cell.font = Font(name="Courier New" if mono else "Arial",
                                 size=8 if mono else 9, bold=bold)
                if bg:
                    cell.fill = PatternFill("solid", start_color=bg)

            wc2("Source File",            fn, bold=True)
            wc2("Total Warnings",         len(warn_nums))
            wc2("Warning Numbers",        ", ".join(warn_nums))
            wc2("Rules Violated",         "\n".join(sorted(set(rules))))
            wc2("Warnings Detail",        "\n".join(warn_detail))
            wc2("Full Fixed Source File", full_fixed, mono=True, bg="F0FDF4")
            wc2("Fix Summary",            "\n".join(fix_summary) if fix_summary else "Pending")
            wc2("Last Updated",
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            ws2.row_dimensions[sum_row].height = max(80, len(row_nums) * 30)

        ws2.row_dimensions[1].height = 32
        ws2.freeze_panes = "A2"

        # Auto-size File Summary columns
        for col_num in range(1, len(h2) + 1):
            letter = get_column_letter(col_num)
            hdr    = h2[col_num - 1]
            if any(k in hdr for k in ["Fixed", "Detail", "Summary"]):
                ws2.column_dimensions[letter].width = 70
            elif "File" in hdr:
                ws2.column_dimensions[letter].width = 25
            else:
                ws2.column_dimensions[letter].width = max(len(hdr) + 4, 18)

        # ── Fill empty audit cells with "-" for un-run warnings ──────────────
        # Audit columns start after the base source columns (Warning Number..Function)
        # Any row that has a Warning Number but empty audit cells gets "-"
        audit_col_start = None
        for _ci, _ch in enumerate(headers, 1):
            if _ch in ("Fix 1", "Chosen Fix"):
                audit_col_start = _ci
                break
        if audit_col_start and wid_col:
            dash_font = Font(name="Arial", size=9, color="999999")
            dash_align = Alignment(horizontal="center", vertical="center")
            for _r in range(2, ws1.max_row + 1):
                _wid_val = ws1.cell(_r, wid_col).value
                if _wid_val is None:
                    continue
                for _c in range(audit_col_start, len(headers) + 1):
                    _cell = ws1.cell(_r, _c)
                    if _cell.value is None or str(_cell.value).strip() == "":
                        _cell.value = "-"
                        _cell.font = dash_font
                        _cell.alignment = dash_align

        # ── Save ─────────────────────────────────────────────────────────────
        wb.save(str(AUDIT_EXCEL))
        app.logger.info(f"Audit Excel saved -> {AUDIT_EXCEL} (warning {warning_id})")
        return True

    except Exception as exc:
        import traceback
        app.logger.error(
            f"Audit Excel FAILED for warning {warning_id}: {exc}\n{traceback.format_exc()}"
        )
        return False


# ---------------------------------------------------------------------------
# Route — Export HTML Audit Report (self-contained, viewable in browser)
# Generates the two-tab audit report (File Summary + Warning Details)
# from actual run data: evaluated_fixes.json + enriched_warnings.json +
# audit_report.xlsx (for committed status / chosen fix / timestamps).
# ---------------------------------------------------------------------------
@app.route("/api/export_html", methods=["POST"])
def export_html():
    body    = request.get_json(force=True) or {}
    run_ids = body.get("run_ids", [])
    if not run_ids:
        return jsonify(error="No run_ids provided"), 400

    import json as _json
    import datetime
    import html as _html
    from collections import defaultdict as _ddict
    from pathlib import Path as _Path

    def esc(v):
        return _html.escape(str(v or ""), quote=True)

    # ── 1. Load all warnings from every run ─────────────────────────────────
    all_warnings = []
    for rid in run_ids:
        try:
            rdir = OUTPUT_DIR / secure_filename(rid)

            enriched_lookup = {}
            ew_file = rdir / "enriched_warnings.json"
            if ew_file.exists():
                ew_data = _json.loads(ew_file.read_text(encoding="utf-8"))
                for ew in ew_data.get("warnings", ew_data.get("results", [])):
                    enriched_lookup[str(ew.get("warning_id", ""))] = ew

            ef = rdir / "evaluated_fixes.json"
            if not ef.exists():
                ef = rdir / "fix_suggestions.json"
            if ef.exists():
                data  = _json.loads(ef.read_text(encoding="utf-8"))
                items = data.get("results", data.get("warnings", []))
                for w in items:
                    wid = str(w.get("warning_id", ""))
                    if wid in enriched_lookup:
                        en = enriched_lookup[wid]
                        w.setdefault("file_path",      en.get("file_path", ""))
                        w.setdefault("rule_id",        en.get("rule_id", ""))
                        w.setdefault("message",        en.get("message", ""))
                        w.setdefault("function_name",  en.get("function_name", ""))
                        w.setdefault("source_context", en.get("source_context", ""))
                        w.setdefault("category",       en.get("category", ""))
                    if not w.get("rule_id"):
                        gid = w.get("guideline_id", "")
                        w["rule_id"] = gid.replace("Rule ", "").strip() if gid else ""
                    if not w.get("message"):
                        w["message"] = w.get("guideline_title", "")
                    w["_run_id"] = rid
                    all_warnings.append(w)
        except Exception:
            pass

    if not all_warnings:
        return jsonify(error="No warnings found"), 404

    # ── 2. Load audit status from audit_report.xlsx ─────────────────────────
    audit_map = {}   # warning_id (str) -> dict with status, chosen_fix, timestamp, fix_code
    try:
        if AUDIT_EXCEL.exists():
            import openpyxl as _opx
            _wb  = _opx.load_workbook(str(AUDIT_EXCEL), read_only=True)
            _ws  = _wb["Warning Details"] if "Warning Details" in _wb.sheetnames else _wb.active
            _hdrs = [str(c.value).strip() if c.value else "" for c in _ws[1]]
            def _ci(name):
                try: return _hdrs.index(name)
                except: return None
            _wnum_ci   = _ci("Warning Number")
            _status_ci = _ci("Audit Status")
            _chosen_ci = _ci("Chosen Fix")
            _code_ci   = _ci("Chosen Fix Code")
            _ts_ci     = _ci("Timestamp")
            _viol_ci   = _ci("Violated Source Code")
            for _row in _ws.iter_rows(min_row=2, values_only=True):
                if _wnum_ci is None or _row[_wnum_ci] is None:
                    continue
                _wid = str(_row[_wnum_ci]).strip()
                audit_map[_wid] = {
                    "status":     str(_row[_status_ci] or "").strip() if _status_ci is not None else "",
                    "chosen_fix": str(_row[_chosen_ci] or "").strip() if _chosen_ci is not None else "",
                    "fix_code":   str(_row[_code_ci]   or "").strip() if _code_ci   is not None else "",
                    "timestamp":  str(_row[_ts_ci]     or "").strip() if _ts_ci     is not None else "",
                    "viol_code":  str(_row[_viol_ci]   or "").strip() if _viol_ci   is not None else "",
                }
            _wb.close()
    except Exception:
        pass

    # ── 3. Group by source file ─────────────────────────────────────────────
    by_file = _ddict(list)
    for w in all_warnings:
        fn = _Path(w.get("file_path", "") or "").name or "unknown"
        by_file[fn].append(w)

    ts    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    total = len(all_warnings)

    # Count committed / pending
    committed_count = 0
    fixes_applied   = 0
    for w in all_warnings:
        wid = str(w.get("warning_id", ""))
        a   = audit_map.get(wid, {})
        st  = a.get("status", "")
        if "Committed" in st or "Edited" in st:
            committed_count += 1
        if st and st not in ("Pending", "-", ""):
            fixes_applied += 1

    pending_count = total - committed_count

    # Category counts
    cat_counts = {"R": 0, "M": 0, "A": 0}
    for w in all_warnings:
        cat_raw = str(w.get("category", "") or "").upper()
        if "MISRA-M" in cat_raw or "(MANDATORY)" in cat_raw:
            cat_counts["M"] += 1
        elif "MISRA-A" in cat_raw or "(ADVISORY)" in cat_raw:
            cat_counts["A"] += 1
        else:
            cat_counts["R"] += 1

    # ── 4. Build FILE SUMMARY tab HTML ─────────────────────────────────────
    def _audit_tag_summary(warnings_in_file):
        """Build the fix-summary-line for a file card."""
        lines = []
        for w in warnings_in_file:
            wid = str(w.get("warning_id", ""))
            a   = audit_map.get(wid, {})
            st  = a.get("status", "")
            ch  = a.get("chosen_fix", "")
            if "Committed" in st or "Edited" in st:
                lines.append(f"✅ #{wid}: {esc(ch)}")
        if lines:
            return " &nbsp;·&nbsp; ".join(lines)
        return "Status: No fixes applied"

    summary_cards = ""
    for fname, warnings in by_file.items():
        rules = sorted({str(w.get("rule_id", "") or "").strip() for w in warnings if w.get("rule_id")})
        rule_chips = "".join(f'<span class="rule-chip">Rule {esc(r)}</span>' for r in rules)
        warn_minis = ""
        for w in warnings:
            wid  = str(w.get("warning_id", ""))
            rule = str(w.get("rule_id", "") or "")
            msg  = str(w.get("message", "") or "")
            func = str(w.get("function_name", "") or "")
            warn_minis += (
                f'<strong>#{wid}</strong> [Rule {esc(rule)}] {esc(msg)}'
                + (f' <em>({esc(func)})</em>' if func else "")
                + "<br>"
            )
        fix_summary_line = _audit_tag_summary(warnings)
        n = len(warnings)
        summary_cards += f"""
    <div class="file-card">
      <div class="file-card-hdr">
        <div class="file-icon-wrap">📄</div>
        <div class="file-card-name">{esc(fname)}</div>
        <span class="warn-count-badge">{n} warning{"s" if n != 1 else ""}</span>
      </div>
      <div class="file-card-body">
        <div class="rule-list">{rule_chips}</div>
        <div class="warn-mini">{warn_minis}</div>
        <div class="fix-summary-line">{fix_summary_line}</div>
      </div>
    </div>"""

    # ── 5. Build WARNING DETAILS tab HTML ───────────────────────────────────
    def _cat_class(cat_raw):
        c = str(cat_raw).upper()
        if "MISRA-M" in c or "MANDATORY" in c: return "mand"
        if "MISRA-A" in c or "ADVISORY"  in c: return "adv"
        return "req"

    def _cat_label(cat_raw):
        c = str(cat_raw).upper()
        if "MISRA-M" in c or "MANDATORY" in c: return "MISRA-M (Mandatory)"
        if "MISRA-A" in c or "ADVISORY"  in c: return "MISRA-A (Advisory)"
        return "MISRA-R (Required)"

    def _audit_tag_html(status):
        if "Committed" in status or "Edited" in status:
            return f'<span class="audit-tag committed">✅ Committed</span>'
        if status and status not in ("Pending", "-", ""):
            return f'<span class="audit-tag edited">⚠ {esc(status)}</span>'
        return '<span class="audit-tag none">Pending</span>'

    def code_block(text, cls=""):
        if not text or not str(text).strip() or str(text).strip() == "-":
            return ""
        return f'<div class="code-block {cls}"><pre>{esc(str(text))}</pre></div>'

    # Build file filter <option> list
    file_options = "".join(f'<option>{esc(fn)}</option>' for fn in sorted(by_file.keys()))

    detail_sections = ""
    for fname, warnings in by_file.items():
        n = len(warnings)
        cards_html = ""
        for w in warnings:
            wid     = str(w.get("warning_id", ""))
            rule    = str(w.get("rule_id", "") or "")
            msg     = str(w.get("message", "") or "")
            func    = str(w.get("function_name", "") or "")
            cat_raw = str(w.get("category", "") or "")
            cat_cls = _cat_class(cat_raw)
            cat_lbl = _cat_label(cat_raw)

            a        = audit_map.get(wid, {})
            status   = a.get("status", "Pending") or "Pending"
            chosen   = a.get("chosen_fix", "") or ""
            fix_code = a.get("fix_code", "") or ""
            ts_val   = a.get("timestamp", "") or ""
            viol     = a.get("viol_code", "") or ""

            audit_tag = _audit_tag_html(status)

            # Source context from enriched data
            sc       = w.get("source_context", "") or ""
            src_text = sc.get("context_text", "") if isinstance(sc, dict) else str(sc)
            if not src_text and viol:
                src_text = viol

            # Fix suggestions
            fixes     = w.get("ranked_fixes", w.get("fix_suggestions", w.get("fixes", []))) or []
            fixes_html = ""
            for fi, f in enumerate(fixes, 1):
                pc    = f.get("patched_code", "") or f.get("corrected_code", "") or ""
                title = f.get("title", f"Fix {fi}")
                fixes_html += f"""
              <div style="margin-bottom:12px;">
                <div class="fix-label">✅ {esc(title)}</div>
                {code_block(pc, "fixed")}
              </div>"""

            # Committed fix code block (from audit Excel)
            committed_section = ""
            if ("Committed" in status or "Edited" in status) and fix_code:
                committed_section = f"""
            <div class="section">
              <div class="section-title">🔧 Fix Applied</div>
              <div class="fix-label">✅ {esc(chosen)}</div>
              {code_block(fix_code, "fixed")}
            </div>"""

            # Info grid extra rows
            extra_info = ""
            if ts_val:
                extra_info += f'<div class="info-item"><div class="label">Timestamp</div><div class="value">{esc(ts_val)}</div></div>'
            if chosen:
                extra_info += f'<div class="info-item"><div class="label">Chosen Fix</div><div class="value">{esc(chosen)}</div></div>'

            audit_status_color = ' style="color:#166534"' if ("Committed" in status or "Edited" in status) else ""

            search_text = f'{wid} rule {rule} {msg} {func} {cat_lbl}'.lower()

            cards_html += f"""
    <div class="warn-card" data-cat="{esc(cat_lbl)}" data-file="{esc(fname)}" data-text="{esc(search_text)}">
      <div class="warn-hdr">
        <span class="wid">#{wid}</span>
        <span class="rule-pill {cat_cls}">Rule {esc(rule)}</span>
        <span class="wmsg">{esc(msg)}</span>
        {f'<span class="func-tag">{esc(func)}</span>' if func else ''}
        {audit_tag}
        <span class="chevron">▼</span>
      </div>
      <div class="warn-body">
        <div class="info-grid">
          <div class="info-item"><div class="label">Category</div><div class="value">{esc(cat_lbl)}</div></div>
          <div class="info-item"><div class="label">File</div><div class="value">{esc(fname)}</div></div>
          <div class="info-item"><div class="label">Function</div><div class="value">{esc(func) if func else "—"}</div></div>
          <div class="info-item"><div class="label">Audit Status</div><div class="value"{audit_status_color}>{esc(status)}</div></div>
          {extra_info}
        </div>
        {f'<div class="section" style="margin-top:14px"><div class="section-title">🔴 Violated Code</div>{code_block(src_text, "violated")}</div>' if src_text else ''}
        {committed_section}
        {f'<div class="section"><div class="section-title">🔧 Fix Suggestions</div>{fixes_html}</div>' if fixes_html else ''}
        {f'<div class="section" style="margin-top:14px"><div class="section-title">ℹ️ Details</div><p class="no-data">No fix suggestions available for this warning.</p></div>' if not fixes_html and not committed_section else ''}
      </div>
    </div>"""

        detail_sections += f"""
  <div class="file-section" data-file="{esc(fname)}">
    <div class="file-hdr">
      <div class="file-hdr-icon">📄</div>
      <span class="file-name">{esc(fname)}</span>
      <span class="file-badge">{n} warning{"s" if n != 1 else ""}</span>
    </div>
    {cards_html}
  </div>"""

    # ── 6. Assemble full HTML ────────────────────────────────────────────────
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MISRA Compliance AI \u2014 Audit Report</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:#f3f4f6;color:#1f2937;min-height:100vh}}
.header{{background:linear-gradient(135deg,#1e3a5f,#1e40af);padding:32px 40px;border-bottom:2px solid #1e3a5f}}
.header-top{{display:flex;align-items:center;gap:14px}}
.logo{{width:42px;height:42px;background:linear-gradient(135deg,#3b82f6,#1d4ed8);border-radius:10px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:20px;font-weight:900;flex-shrink:0}}
.header h1{{font-size:24px;font-weight:800;color:#fff;letter-spacing:-.02em}}
.header h1 span{{color:#93c5fd}}
.header .sub{{color:#bfdbfe;font-size:13px;margin-top:6px}}
.badge-row{{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap}}
.badge{{background:rgba(255,255,255,.15);color:#e0f2fe;font-size:11px;font-weight:600;padding:4px 12px;border-radius:20px;border:1px solid rgba(255,255,255,.2)}}
.badge.green{{background:rgba(34,197,94,.2);color:#bbf7d0;border-color:rgba(34,197,94,.3)}}
.stats{{display:flex;gap:14px;margin-top:22px;flex-wrap:wrap}}
.stat{{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);border-radius:10px;padding:12px 20px;text-align:center;min-width:100px}}
.stat .n{{font-size:26px;font-weight:800;color:#fff}}
.stat .l{{font-size:10px;color:#bfdbfe;text-transform:uppercase;letter-spacing:.06em;margin-top:2px}}
.tabs{{background:#fff;border-bottom:1px solid #e5e7eb;display:flex;gap:0;padding:0 40px}}
.tab{{padding:14px 20px;font-size:13px;font-weight:600;color:#6b7280;cursor:pointer;border-bottom:2px solid transparent;transition:all .2s}}
.tab.active{{color:#1d4ed8;border-bottom-color:#1d4ed8}}
.tab:hover{{color:#374151}}
.content{{max-width:1280px;margin:0 auto;padding:28px 24px}}
.summary-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px;margin-bottom:28px}}
.file-card{{background:#fff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.05)}}
.file-card-hdr{{display:flex;align-items:center;gap:10px;padding:14px 18px;background:#f9fafb;border-bottom:1px solid #e5e7eb}}
.file-icon-wrap{{width:34px;height:34px;background:#dbeafe;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0}}
.file-card-name{{font-weight:700;font-size:13px;color:#111827;flex:1}}
.warn-count-badge{{background:#dbeafe;color:#1d4ed8;font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px}}
.file-card-body{{padding:14px 18px}}
.rule-list{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}}
.rule-chip{{background:#f3f4f6;color:#374151;font-size:11px;font-weight:600;padding:2px 9px;border-radius:6px;border:1px solid #e5e7eb;font-family:monospace}}
.warn-mini{{font-size:12px;color:#6b7280;line-height:1.7}}
.warn-mini strong{{color:#374151}}
.fix-summary-line{{margin-top:10px;padding-top:10px;border-top:1px solid #f3f4f6;font-size:12px;color:#6b7280}}
#tab-details{{display:none}}
.filter-bar{{display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap;align-items:center}}
.filter-bar input{{flex:1;min-width:200px;padding:8px 14px;border:1px solid #e5e7eb;border-radius:8px;font-size:13px;outline:none;background:#fff}}
.filter-bar input:focus{{border-color:#3b82f6;box-shadow:0 0 0 3px rgba(59,130,246,.1)}}
.filter-bar select{{padding:8px 12px;border:1px solid #e5e7eb;border-radius:8px;font-size:13px;background:#fff;outline:none;color:#374151;cursor:pointer}}
.file-section{{margin-bottom:32px}}
.file-hdr{{display:flex;align-items:center;gap:10px;background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:12px 18px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.04)}}
.file-hdr-icon{{width:32px;height:32px;background:#eff6ff;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:15px}}
.file-name{{font-weight:800;font-size:13px;color:#111827;flex:1}}
.file-badge{{background:#dbeafe;color:#1d4ed8;font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px}}
.warn-card{{background:#fff;border:1px solid #e5e7eb;border-radius:12px;margin-bottom:10px;overflow:hidden;transition:border-color .2s,box-shadow .2s;box-shadow:0 1px 3px rgba(0,0,0,.04)}}
.warn-card.open{{border-color:#3b82f6;box-shadow:0 4px 14px rgba(59,130,246,.1)}}
.warn-hdr{{display:flex;align-items:center;gap:10px;padding:13px 18px;background:#fafafa;flex-wrap:wrap;cursor:pointer;user-select:none}}
.warn-hdr:hover{{background:#f3f4f6}}
.wid{{font-family:monospace;font-size:12px;font-weight:700;background:#f3f4f6;color:#111827;padding:2px 9px;border-radius:6px;border:1px solid #e5e7eb;flex-shrink:0}}
.rule-pill{{font-size:10px;font-weight:700;padding:2px 9px;border-radius:20px;border:1px solid;flex-shrink:0}}
.rule-pill.req{{background:#eff6ff;color:#1d4ed8;border-color:#bfdbfe}}
.rule-pill.mand{{background:#fff7ed;color:#c2410c;border-color:#fed7aa}}
.rule-pill.adv{{background:#f0fdf4;color:#15803d;border-color:#bbf7d0}}
.wmsg{{color:#374151;font-size:13px;flex:1}}
.func-tag{{color:#9ca3af;font-size:11px;background:#f9fafb;padding:2px 8px;border-radius:4px;border:1px solid #f0f0f0;flex-shrink:0}}
.audit-tag{{font-size:10px;font-weight:700;padding:2px 9px;border-radius:20px;flex-shrink:0}}
.audit-tag.committed{{background:#dcfce7;color:#166534;border:1px solid #bbf7d0}}
.audit-tag.edited{{background:#fef9c3;color:#854d0e;border:1px solid #fde68a}}
.audit-tag.none{{background:#f3f4f6;color:#9ca3af;border:1px solid #e5e7eb}}
.chevron{{margin-left:auto;color:#9ca3af;transition:transform .2s;flex-shrink:0;font-size:14px}}
.warn-card.open .chevron{{transform:rotate(180deg)}}
.warn-body{{padding:18px;display:none;border-top:1px solid #e5e7eb;background:#fff}}
.warn-card.open .warn-body{{display:block}}
.section{{margin-bottom:16px}}
.section-title{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#9ca3af;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #f3f4f6;display:flex;align-items:center;gap:6px}}
.info-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px}}
.info-item{{background:#f9fafb;padding:10px 14px;border-radius:8px;border:1px solid #f0f0f0}}
.info-item .label{{font-size:10px;color:#9ca3af;font-weight:600;text-transform:uppercase;letter-spacing:.05em}}
.info-item .value{{font-size:13px;color:#111827;font-weight:600;margin-top:3px}}
.code-block{{background:#1e293b;border-radius:8px;overflow:auto;font-family:'Cascadia Code',Consolas,monospace;font-size:12px;max-height:280px;border:1px solid #e2e8f0;margin-top:6px;color:#e2e8f0}}
.code-block.violated{{border-left:3px solid #ef4444}}
.code-block.fixed{{border-left:3px solid #22c55e}}
.code-block pre{{padding:12px 16px;white-space:pre-wrap}}
.fix-label{{font-size:11px;font-weight:700;color:#16a34a;margin-bottom:6px;text-transform:uppercase;letter-spacing:.04em;display:flex;align-items:center;gap:5px}}
.no-data{{font-size:13px;color:#9ca3af;font-style:italic}}
.stats-bar{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px;margin-bottom:24px}}
.stat-card{{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:16px 20px;box-shadow:0 1px 3px rgba(0,0,0,.04)}}
.stat-card .n{{font-size:28px;font-weight:800;color:#1d4ed8}}
.stat-card .n.orange{{color:#d97706}}
.stat-card .n.green{{color:#16a34a}}
.stat-card .n.red{{color:#dc2626}}
.stat-card .l{{font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;margin-top:3px}}
@media(max-width:640px){{.header{{padding:20px}}.tabs{{padding:0 16px}}.content{{padding:16px 12px}}}}
</style>
</head>
<body>

<div class="header">
  <div class="header-top">
    <div class="logo">M</div>
    <div>
      <h1>MISRA <span>Compliance AI</span></h1>
      <div class="sub">Audit Report &nbsp;&middot;&nbsp; Generated {ts} &nbsp;&middot;&nbsp; SRM Technologies</div>
    </div>
  </div>
  <div class="badge-row">
    <span class="badge">MISRA-C 2012</span>
    <span class="badge green">&#x25CF; Audit Complete</span>
    <span class="badge">Polyspace Compatible</span>
    <span class="badge">QAC Compatible</span>
  </div>
  <div class="stats">
    <div class="stat"><div class="n">{total}</div><div class="l">Total Warnings</div></div>
    <div class="stat"><div class="n">{len(by_file)}</div><div class="l">Source Files</div></div>
    <div class="stat"><div class="n">{fixes_applied}</div><div class="l">Fixes Applied</div></div>
    <div class="stat"><div class="n">{committed_count}</div><div class="l">Committed</div></div>
    <div class="stat"><div class="n">{pending_count}</div><div class="l">Pending</div></div>
  </div>
</div>

<div class="tabs">
  <div class="tab active" onclick="switchTab('summary',this)">&#128202; File Summary</div>
  <div class="tab" onclick="switchTab('details',this)">&#9888;&#65039; Warning Details</div>
</div>

<div class="content">

<div id="tab-summary">
  <div class="stats-bar">
    <div class="stat-card"><div class="n">{total}</div><div class="l">Total Warnings</div></div>
    <div class="stat-card"><div class="n red">{cat_counts["R"]}</div><div class="l">Required (R)</div></div>
    <div class="stat-card"><div class="n orange">{cat_counts["M"]}</div><div class="l">Mandatory (M)</div></div>
    <div class="stat-card"><div class="n">{cat_counts["A"]}</div><div class="l">Advisory (A)</div></div>
    <div class="stat-card"><div class="n green">{fixes_applied}</div><div class="l">Fixes Applied</div></div>
    <div class="stat-card"><div class="n green">{committed_count}</div><div class="l">Committed</div></div>
  </div>
  <div class="summary-grid">{summary_cards}</div>
</div>

<div id="tab-details" style="display:none">
  <div class="filter-bar">
    <input type="text" id="searchInput" placeholder="&#128269; Search warnings, rules, functions..." oninput="filterWarnings()">
    <select id="fileFilter" onchange="filterWarnings()">
      <option value="">All Files</option>
      {file_options}
    </select>
    <select id="catFilter" onchange="filterWarnings()">
      <option value="">All Categories</option>
      <option>MISRA-R (Required)</option>
      <option>MISRA-M (Mandatory)</option>
      <option>MISRA-A (Advisory)</option>
    </select>
  </div>
  {detail_sections}
</div>

</div>

<script>
function switchTab(name, el) {{
  document.getElementById('tab-summary').style.display = name === 'summary' ? 'block' : 'none';
  document.getElementById('tab-details').style.display = name === 'details' ? 'block' : 'none';
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
}}
document.querySelectorAll('.warn-hdr').forEach(h => {{
  h.addEventListener('click', () => h.parentElement.classList.toggle('open'));
}});
function filterWarnings() {{
  const s = document.getElementById('searchInput').value.toLowerCase();
  const f = document.getElementById('fileFilter').value;
  const c = document.getElementById('catFilter').value;
  document.querySelectorAll('.warn-card').forEach(card => {{
    const text = card.dataset.text || '';
    const file = card.dataset.file || '';
    const cat  = card.dataset.cat  || '';
    const show = (!s || text.includes(s)) && (!f || file === f) && (!c || cat === c);
    card.style.display = show ? '' : 'none';
  }});
  document.querySelectorAll('.file-section').forEach(sec => {{
    const visible = [...sec.querySelectorAll('.warn-card')].some(c => c.style.display !== 'none');
    sec.style.display = visible ? '' : 'none';
  }});
}}
</script>
</body>
</html>"""

    out_dir   = PROJECT_ROOT / "Output_excel_after_run"
    out_dir.mkdir(parents=True, exist_ok=True)
    html_file = out_dir / "misra_report.html"
    html_file.write_text(html_content, encoding="utf-8")
    return jsonify({"status": "ok", "url": "/view_html_report"})


@app.route("/view_html_report")
def view_html_report():
    html_file = PROJECT_ROOT / "Output_excel_after_run" / "misra_report.html"
    if not html_file.exists():
        return "HTML report not generated yet.", 404
    return send_file(str(html_file), mimetype="text/html")


# Helper — apply rule config filter to uploaded Excel before analysis
# ---------------------------------------------------------------------------
def _filter_excel_by_rules(src_excel: Path, rule_selected: list,
                             rule_overrides: dict) -> Path:
    """Keep only rows whose Rule matches a selected rule_id.
    Returns path to (possibly filtered) Excel file."""
    if not rule_selected:
        return src_excel   # nothing selected → run all

    import openpyxl
    wb = openpyxl.load_workbook(str(src_excel))
    ws = wb.active
    headers = [str(c.value).strip().lower() if c.value else "" for c in ws[1]]

    # Find the Rule column
    rule_col = next((i for i, h in enumerate(headers)
                     if "rule" in h), None)
    if rule_col is None:
        return src_excel  # can't filter — pass through

    # ── FIX: normalise both sides so "Rule 10.3" matches selected id "10.3" ──
    # Build a set of normalised selected IDs for robust matching
    def _normalise_rule_id(raw: str) -> str:
        """Strip leading 'Rule ' / 'rule ' prefix and whitespace."""
        return _re.sub(r"(?i)^rule\s*", "", str(raw)).strip()

    selected_set = set(_normalise_rule_id(r) for r in rule_selected)

    # Collect rows to keep (skip header)
    keep_rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        raw = str(row[rule_col] or "").strip()
        # Normalise "Rule 10.3" → "10.3"
        normalised = _normalise_rule_id(raw)
        if normalised in selected_set:
            keep_rows.append(row)

    # ── FIX: guard against empty filter result — return original if nothing matched ──
    # This prevents sending a 0-row Excel to the orchestrator, which would cause
    # the pipeline to parse 0 warnings and the UI to show "All 0 records complete".
    if not keep_rows:
        app.logger.warning(
            f"[filter] No rows matched selected rules {sorted(selected_set)} — "
            f"running unfiltered to avoid 0-record pipeline."
        )
        return src_excel

    # Build filtered workbook
    from openpyxl import Workbook
    wb2 = Workbook()
    ws2 = wb2.active
    ws2.title = ws.title or "Filtered"
    ws2.append([c.value for c in ws[1]])   # header
    for row in keep_rows:
        # Apply override: patch Category column if override exists
        row = list(row)
        cat_col = next((i for i, h in enumerate(headers)
                        if "category" in h), None)
        if cat_col is not None:
            raw_rule = str(row[rule_col] or "")
            norm = _normalise_rule_id(raw_rule)
            ov = rule_overrides.get(norm)
            if ov:
                label = {"M": "MISRA-M (Mandatory)",
                         "R": "MISRA-R (Required)",
                         "A": "MISRA-A (Advisory)"}.get(ov, row[cat_col])
                row[cat_col] = label
        ws2.append(row)

    filtered_path = src_excel.parent / ("filtered_" + src_excel.name)
    wb2.save(str(filtered_path))
    return filtered_path


# ---------------------------------------------------------------------------
# Helper — filter Excel rows to only those referencing the requested source files
# ---------------------------------------------------------------------------
def _filter_excel_by_filenames(excel_path: Path, run_filenames: list) -> Path:
    """Keep only Excel rows whose File column (basename) matches one of the
    requested filenames.  Returns the original path if filtering is impossible
    or produces an empty result (fail-safe pass-through)."""
    if not run_filenames:
        return excel_path

    import openpyxl
    wb = openpyxl.load_workbook(str(excel_path))
    ws = wb.active
    headers = [str(c.value).strip().lower() if c.value else "" for c in ws[1]]

    # Find the File column
    file_col = next((i for i, h in enumerate(headers) if "file" in h), None)
    if file_col is None:
        return excel_path  # can't filter — pass through

    # Normalise requested names to basenames (case-insensitive)
    from pathlib import Path as _Path
    requested = set(_Path(f).name.lower() for f in run_filenames)

    keep_rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        cell_val = str(row[file_col] or "").strip()
        # Compare basename only, case-insensitive
        cell_base = _Path(cell_val).name.lower() if cell_val else ""
        if cell_base in requested:
            keep_rows.append(row)

    if not keep_rows:
        # No rows match — pass through unfiltered so the pipeline doesn't see 0 records
        app.logger.warning(
            f"[filter_files] No Excel rows matched filenames {run_filenames} — running unfiltered"
        )
        return excel_path

    # Build filtered workbook
    from openpyxl import Workbook
    wb2 = Workbook()
    ws2 = wb2.active
    ws2.title = ws.title or "Filtered"
    ws2.append([c.value for c in ws[1]])   # header
    for row in keep_rows:
        ws2.append(list(row))

    filtered_path = excel_path.parent / ("byfile_" + excel_path.name)
    wb2.save(str(filtered_path))
    app.logger.info(
        f"[filter_files] Kept {len(keep_rows)} rows for {run_filenames} → {filtered_path.name}"
    )
    return filtered_path


# ---------------------------------------------------------------------------
# API — Excel MISRA config load / save
# ---------------------------------------------------------------------------
@app.route("/api/config/load", methods=["GET"])
def load_config():
    """Load MISRA rule config from the locked original (or working copy if it exists).
    On first run: copies locked original → WORKING_SPEC.
    On subsequent runs: reads WORKING_SPEC (preserves previous overrides).
    Original is NEVER written to.
    """
    try:
        # Ensure working copy exists
        if not WORKING_SPEC.exists():
            if not ORIGINAL_SPEC.exists():
                return jsonify({"error":
                    f"Original file not found: {ORIGINAL_SPEC}\n"
                    "Place user_specification.xlsx in:\n"
                    f"  {PROJECT_ROOT / 'data'}"}), 404
            shutil.copy2(str(ORIGINAL_SPEC), str(WORKING_SPEC))
            app.logger.info(f"[config/load] Created working copy: {WORKING_SPEC}")
        else:
            app.logger.info(f"[config/load] Reading working copy: {WORKING_SPEC}")

        file_path = WORKING_SPEC
        df = pd.read_excel(str(file_path), engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        df = df.fillna("")

        RULE_COL     = "MISRA Rule"
        CAT_COL      = "MISRA Category"
        USER_CAT_COL = "User Category"

        missing = [c for c in [RULE_COL, CAT_COL] if c not in df.columns]
        if missing:
            return jsonify({
                "error": f"Expected columns not found: {missing}. Found: {list(df.columns)}"
            }), 400

        rows = []
        for i, row in df.iterrows():
            rule_raw = str(row.get(RULE_COL, "")).strip()
            cat_raw  = str(row.get(CAT_COL,  "")).strip()
            user_cat = str(row.get(USER_CAT_COL, "")).strip() if USER_CAT_COL in df.columns else ""

            if not rule_raw:
                continue

            rule_display = rule_raw
            m = _re.match(r"Rule[-_](.+)", rule_raw, _re.I)
            if m:
                rule_display = m.group(1).strip()
            else:
                m2 = _re.match(r"Dir[-_](.+)", rule_raw, _re.I)
                if m2:
                    rule_display = "Dir " + m2.group(1).strip()

            cat_display = {"MISRA-M": "Mandatory", "MISRA-R": "Required",
                           "MISRA-A": "Advisory"}.get(cat_raw, cat_raw)

            warn_nos = str(row.get("Warning Message Nos.", "")).strip() \
                if "Warning Message Nos." in df.columns else ""

            rows.append({
                "row_index":              int(i),
                "rule_list":              rule_display,
                "misra_category":         cat_display,
                "misra_category_display": cat_display,
                "user_category":          _normalize_user_category(user_cat),
                "warning_message_nos":    warn_nos,
            })

        if not rows:
            return jsonify({"error": "No valid data rows found in Excel"}), 400

        token = uuid.uuid4().hex
        _CONFIG_FILES[token] = WORKING_SPEC

        return jsonify({"token": token, "rows": rows, "count": len(rows)})

    except Exception:
        import traceback
        print("GET /api/config/load ERROR:\n", traceback.format_exc())
        return jsonify({"error": "Internal server error loading config"}), 500


@app.route("/api/config/save", methods=["POST"])
def api_config_save():
    """Save user category selections back to the user_specification Excel."""
    data    = request.get_json(silent=True) or {}
    token   = _safe_text(data.get("token", ""))
    updates = data.get("updates", [])

    if not token:
        return jsonify(error="Missing config token."), 400

    # Always write to the single working copy — original untouched
    if not WORKING_SPEC.exists():
        return jsonify(error="Working copy not found. Please open the modal first."), 404

    try:
        df = _read_excel_df(WORKING_SPEC)
        df.columns = [str(c).strip() for c in df.columns]

        USER_CAT_COL = "User Category"
        if USER_CAT_COL not in df.columns:
            df[USER_CAT_COL] = "-"

        for item in updates:
            try:
                idx      = int(item.get("row_index"))
                user_cat = _normalize_user_category(item.get("user_category", ""))
                if idx in df.index:
                    df.at[idx, USER_CAT_COL] = user_cat if user_cat else "-"
            except Exception:
                continue

        df.to_excel(str(WORKING_SPEC), index=False, engine="openpyxl")
        app.logger.info(f"[config/save] Overrides saved → {WORKING_SPEC}")

        rows = _excel_rows_from_df(df)

    except Exception as exc:
        return jsonify(error=f"Could not save Excel: {exc}"), 400

    return jsonify(status="updated", token=token, rows=rows,
                   saved_file=WORKING_SPEC.name,
                   saved_path=str(WORKING_SPEC))


# ---------------------------------------------------------------------------
# Route — save uploads once (called when user selects files, before any run)
# ---------------------------------------------------------------------------
@app.route("/api/save_uploads", methods=["POST"])
def save_uploads():
    if "warning_report" not in request.files:
        return jsonify(error="No warning report uploaded"), 400
    excel_file = request.files["warning_report"]
    if Path(excel_file.filename).suffix.lower() not in ALLOWED_EXCEL:
        return jsonify(error="Warning report must be .xlsx or .xls"), 400

    c_files = request.files.getlist("source_files")
    if not c_files or all(f.filename == "" for f in c_files):
        return jsonify(error="No C source files uploaded"), 400

    upload_session_id = str(uuid.uuid4())[:8]
    job_dir = UPLOAD_DIR / upload_session_id
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

    return jsonify(
        upload_session_id=upload_session_id,
        excel_filename=secure_filename(excel_file.filename),
        c_files=saved_c,
    )


# ---------------------------------------------------------------------------
# Route — start analysis (saves uploads, launches orchestrator subprocess)
# ---------------------------------------------------------------------------
@app.route("/api/analyse", methods=["POST"])
def start_analysis():
    try:
        batch_size = max(1, min(15, int(request.form.get("batch_size", DEFAULT_BATCH_SIZE))))
    except (TypeError, ValueError):
        batch_size = DEFAULT_BATCH_SIZE

    upload_session_id = request.form.get("upload_session_id", "").strip()

    if upload_session_id:
        # ── Fast path: files already saved by /api/save_uploads ──
        session_dir = UPLOAD_DIR / secure_filename(upload_session_id)
        src_dir = session_dir / "source_code"
        if not session_dir.exists():
            return jsonify(error="Upload session not found — please re-upload your files"), 400

        # Find the excel file in the session dir.
        # IMPORTANT: always prefer the ORIGINAL uploaded file (no byfile_/filtered_ prefix).
        # On Windows, iterdir() may return byfile_mock_warning_report.xlsx before
        # mock_warning_report.xlsx — using a stale byfile_ as excel_path causes
        # _filter_excel_by_filenames to produce byfile_byfile_... and the orchestrator
        # gets served 0 rows from the stale file (root cause of the uninit_read.c bug).
        all_excels = [p for p in session_dir.iterdir()
                      if p.suffix.lower() in ALLOWED_EXCEL]
        if not all_excels:
            return jsonify(error="Warning report not found in upload session"), 400
        # Prefer originals: files NOT starting with byfile_ or filtered_
        original_excels = [p for p in all_excels
                           if not p.name.startswith("byfile_")
                           and not p.name.startswith("filtered_")]
        excel_path = original_excels[0] if original_excels else all_excels[0]

        # Determine which .c files to run (subset or all)
        run_files = request.form.getlist("run_filenames")
        if run_files:
            saved_c = [secure_filename(n) for n in run_files
                       if (src_dir / secure_filename(n)).exists()]
        else:
            saved_c = [p.name for p in src_dir.iterdir()
                       if p.suffix.lower() in ALLOWED_C]

        if not saved_c:
            return jsonify(error="No matching source files found in upload session"), 400

        # Create a new job_id/run_id
        # Bug 1 fix: if only specific files were requested, copy them to a temp dir
        # so the orchestrator only processes those files and not the entire src_dir
        job_id = str(uuid.uuid4())[:8]
        run_id = time.strftime("%Y%m%d_%H%M%S") + "_" + job_id
        if run_files and len(saved_c) < len([p for p in src_dir.iterdir() if p.suffix.lower() in ALLOWED_C]):
            # Create a temp source dir containing only the requested files
            import tempfile as _tmpmod
            tmp_src_dir = Path(_tmpmod.mkdtemp(prefix="misra_run_"))
            for _fn in saved_c:
                _src_file = src_dir / _fn
                if _src_file.exists():
                    import shutil as _shutil
                    _shutil.copy2(str(_src_file), str(tmp_src_dir / _fn))
            src_dir = tmp_src_dir

    else:
        # ── Standard path: fresh file upload ──
        if "warning_report" not in request.files:
            return jsonify(error="No warning report uploaded"), 400
        excel_file = request.files["warning_report"]
        if Path(excel_file.filename).suffix.lower() not in ALLOWED_EXCEL:
            return jsonify(error="Warning report must be .xlsx or .xls"), 400

        c_files = request.files.getlist("source_files")
        if not c_files or all(f.filename == "" for f in c_files):
            return jsonify(error="No C source files uploaded"), 400

        job_id  = str(uuid.uuid4())[:8]
        run_id  = time.strftime("%Y%m%d_%H%M%S") + "_" + job_id
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

        run_files = []  # fresh upload always runs all files
    import json as _json
    try:
        rule_selected  = _json.loads(request.form.get("rule_selected", "[]"))
        rule_overrides = _json.loads(request.form.get("rule_overrides", "{}"))
    except Exception:
        rule_selected  = []
        rule_overrides = {}

    # Optional: resume from a previous run so Phase 7 cache hits skip re-generation.
    # SAFETY: only honour resume when NOT running a specific-file subset — using it
    # for a different file causes the orchestrator to re-emit cached wids from the
    # previous run, which then get mapped to the new run_id → "Record not found".
    resume_run_id = ""  # disabled per-file-run; kept as empty to preserve CLI compat

    # Filter rows to only those referencing the requested source files FIRST
    # (applied to the original excel_path to avoid double-prefix "byfile_byfile_" bug).
    # If we applied rule filter first and then filename filter, the filename filter
    # would create "byfile_filtered_..." while the orchestrator path still pointed to
    # the old stale "byfile_mock_warning_report.xlsx" from a previous run.
    if run_files:
        byfile_excel = _filter_excel_by_filenames(excel_path, run_files)
    else:
        byfile_excel = excel_path
    # Then apply rule config filter on top of the filename-filtered result
    filtered_excel = _filter_excel_by_rules(byfile_excel, rule_selected, rule_overrides)
    warnings_filtered = len(rule_selected) > 0
    filtered_count = 0
    if warnings_filtered and filtered_excel != excel_path:
        import openpyxl as _opx
        _wb = _opx.load_workbook(str(filtered_excel), read_only=True)
        filtered_count = max(0, _wb.active.max_row - 1)  # exclude header
        _wb.close()

        # ── FIX: abort early if the filter produced 0 rows ──
        # This gives the user a clear error instead of a silent "0 records" run.
        if filtered_count == 0:
            return jsonify(
                error=(
                    "No warnings matched the selected rules. "
                    "Try selecting different rules or clear the rule filter to run all warnings."
                ),
                filtered_count=0,
                warnings_filtered=True,
            ), 400

    q = queue.Queue()
    JOBS[job_id] = {
        "status":     "running",
        "queue":      q,
        "run_id":     run_id,
        "started_at": time.time(),
    }

    t = threading.Thread(
        target=_run_pipeline_subprocess,
        args=(job_id, run_id, str(filtered_excel), str(src_dir), batch_size),
        kwargs={"resume_run_id": resume_run_id},
        daemon=True,
    )
    t.start()

    return jsonify(job_id=job_id, run_id=run_id, c_files=saved_c,
                   batch_size=batch_size, warnings_filtered=warnings_filtered,
                   filtered_count=filtered_count, resumed=bool(resume_run_id))


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
# Background: run orchestrator.py as subprocess, forward stdout as SSE
# ---------------------------------------------------------------------------
def _run_pipeline_subprocess(
    job_id: str,
    run_id: str,
    excel_path: str,
    src_dir: str,
    batch_size: int,
    resume_run_id: str = "",
) -> None:
    job = JOBS[job_id]
    q   = job["queue"]

    def emit(msg: dict) -> None:
        q.put(msg)

    try:
        python_exe   = sys.executable
        orchestrator = str(PROJECT_ROOT / "app" / "pipeline" / "orchestrator.py")

        cmd = [
            python_exe, orchestrator,
            excel_path, src_dir,
            "--run-id", run_id,
        ]
        # If resuming a previous run, tell the orchestrator to skip already-done phases
        if resume_run_id:
            cmd += ["--resume", resume_run_id]

        # Force UTF-8 + unbuffered output from the subprocess.
        # On Windows, Python stdout is block-buffered when writing to a pipe,
        # which means print() output is held in an 8KB buffer and only reaches
        # the server when the buffer fills or the process ends — causing the UI
        # to show nothing for minutes. PYTHONUNBUFFERED=1 forces line-by-line.
        _env = os.environ.copy()
        _env["PYTHONIOENCODING"] = "utf-8"
        _env["PYTHONUTF8"]       = "1"
        _env["PYTHONUNBUFFERED"] = "1"   # ← critical: forces line-buffered stdout on Windows

        # Emit a neutral status — do NOT activate any phase circle yet.
        # The orchestrator's own print() lines will drive the stepper.
        emit({"type": "status", "label": "Pipeline starting…", "detail": ""})

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,           # line-buffered pipe read on the server side
            cwd=str(PROJECT_ROOT),
            env=_env,
        )

        total_warnings = 0
        _last_wid      = ""   # tracks the last warning_id seen for fix(es) lines

        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue

            # Skip evaluation-progress lines — these look like generation lines
            # ("EVAL_PROGRESS [1/1] Evaluating 2883 ...") and must not create cards.
            if line.startswith("EVAL_PROGRESS") or "EVAL_PROGRESS" in line:
                continue

            # Per-record Phase 8 completion — "EVAL_DONE <wid>"
            # Emitted by evaluate_fixes.py after each record is evaluated.
            if line.startswith("EVAL_DONE"):
                parts = line.split()
                eval_wid = parts[1] if len(parts) > 1 else ""
                if eval_wid:
                    emit({"type": "warning_start", "phase": "8",
                          "warning_id": eval_wid,
                          "label": f"Quality check: {eval_wid}"})
                    emit({"type": "warning_done", "phase": "8",
                          "warning_id": eval_wid,
                          "label": f"Check complete: {eval_wid}"})
                continue

            # Always emit as log line
            emit({"type": "log", "detail": line})

            # Phase transitions — match exact orchestrator print() strings
            # e.g. "Phase 6a — Parsing Polyspace report"
            if "Phase 6a" in line:
                emit({"type": "phase_start", "phase": "6a",
                      "label": "Reading file",
                      "detail": "Loading your files", "progress": 5})

            elif "Phase 6b" in line:
                emit({"type": "phase_done", "phase": "6a",
                      "label": "File read complete", "progress": 15})
                emit({"type": "phase_start", "phase": "6b",
                      "label": "Looking up rules",
                      "detail": "Matching rules to warnings", "progress": 16})

            elif "Phase 7" in line:
                emit({"type": "phase_done", "phase": "6b",
                      "label": "Rule lookup complete", "progress": 35})
                emit({"type": "phase_start", "phase": "7",
                      "label": "Fix suggestions",
                      "detail": "Generating fixes with AI", "progress": 31})

            elif "Phase 8" in line:
                emit({"type": "phase_done", "phase": "7",
                      "label": "Fix suggestions complete", "progress": 65})
                emit({"type": "phase_start", "phase": "8",
                      "label": "Quality check",
                      "detail": "Verifying fix quality", "progress": 66})

            # ── FIX: Robust parsed-warning-count extraction ──
            # Original code only matched "Parsed X warnings" with exact word boundary.
            # Orchestrators may print variants like:
            #   "Parsed 16 warnings — High: 4 ..."
            #   "Parsed 16 MISRA warnings"
            #   "16 warnings parsed"
            #   "Found 16 warnings"
            # The regex below handles all these cases.
            _line_lower = line.lower()
            if "warning" in _line_lower and (
                "parsed" in _line_lower
                or "found" in _line_lower
                or "loaded" in _line_lower
                or "read" in _line_lower
            ):
                _m = _re.search(r'(\d+)\s+(?:misra\s+)?warning', line, _re.IGNORECASE)
                if _m:
                    _candidate = int(_m.group(1))
                    if _candidate > 0:
                        total_warnings = _candidate
                emit({"type": "phase_done", "phase": "6a",
                      "label": "Parsing complete",
                      "detail": line.strip(), "progress": 15,
                      "total": total_warnings})

            # Retrieval lines: "  PS002     Rule 10.3     4 rule(s) retrieved"
            if "rule(s) retrieved" in line:
                parts = line.split()
                wid   = parts[0] if parts else ""
                try:
                    n_rules = line.strip().split("rule(s)")[0].strip().split()[-1]
                except Exception:
                    n_rules = "?"
                # warning_start creates the card; warning_done advances it
                emit({"type": "warning_start", "phase": "6b",
                      "label": f"Looking up rules: {wid}",
                      "detail": line.strip(), "progress": 20,
                      "warning_id": wid})
                emit({"type": "warning_done", "phase": "6b",
                      "label": f"Context: {wid} — {n_rules} rule(s)",
                      "detail": line.strip(), "progress": 25,
                      "warning_id": wid})

            # Generation lines: "  [ 1/16] PS002  Rule 10.3 ..."
            if line.strip().startswith("[") and "/" in line and "]" in line:
                try:
                    inner    = line.strip().lstrip("[").split("]", 1)
                    count    = inner[0].strip()
                    rest     = inner[1].strip().split() if len(inner) > 1 else []
                    wid      = rest[0] if rest else ""
                    rule     = rest[1] if len(rest) > 1 else ""
                    cur, tot = count.split("/")
                    cur_i    = int(cur.strip())
                    tot_i    = int(tot.strip())
                    pct      = 31 + int((cur_i / max(1, tot_i)) * 34)
                    _last_wid = wid  # track for fix(es) line matching

                    # ── FIX: also update total_warnings from generation progress ──
                    # If Phase 6a parsing line was missed/different format,
                    # we can still learn the total from "[1/16]" style lines.
                    if total_warnings == 0 and tot_i > 0:
                        total_warnings = tot_i
                        # Re-emit total so the frontend counter updates
                        emit({"type": "total_update", "total": total_warnings})

                    # Emit warning_start so the UI card appears immediately
                    emit({"type": "warning_start", "phase": "7",
                          "label": f"Processing: {wid} ({rule})",
                          "detail": f"{count} of {tot_i} warnings",
                          "progress": pct, "warning_id": wid,
                          "count": cur_i, "total": tot_i, "pct": pct})
                except Exception:
                    pass

            # Fix result line — "  3 fix(es)  254.2s  ✓" — marks warning complete
            if "fix(es)" in line and ("✓" in line or "✗" in line):
                try:
                    emit({"type": "warning_done", "phase": "7",
                          "label": "Fix generated",
                          "detail": line.strip(), "warning_id": _last_wid or ""})
                except Exception:
                    pass

            # Fix result lines: "       3 fix(es)  254.2s"
            if "fix(es)" in line:
                emit({"type": "detail", "detail": line.strip()})

            # Pipeline complete: "Pipeline complete — 955.7s"
            if "Pipeline complete" in line:
                emit({"type": "phase_done", "phase": "8",
                      "label": "Preparing your report",
                      "detail": "Report ready", "progress": 95})

        proc.wait()

        if proc.returncode == 0:
            job["status"] = "done"
            emit({"type": "done", "label": "Analysis complete",
                  "detail": f"Results saved — run ID: {run_id}",
                  "progress": 100, "run_id": run_id,
                  "total": total_warnings})   # ← FIX: include final total in done event
        else:
            job["status"] = "error"
            emit({"type": "error", "label": "Pipeline failed",
                  "detail": f"Process exited with code {proc.returncode}",
                  "progress": 0})

    except Exception as exc:
        import traceback
        job["status"] = "error"
        emit({"type": "error", "label": "Pipeline failed",
              "detail": str(exc), "traceback": traceback.format_exc(),
              "progress": 0})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  MISRA GenAI Web UI  —  Results Viewer")
    print("  http://127.0.0.1:5000")
    print("  Pipeline runs via CLI:")
    print("    python app/pipeline/orchestrator.py <excel> <src_dir> --run-id <id>")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)