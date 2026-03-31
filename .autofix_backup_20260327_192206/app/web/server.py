"""
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
