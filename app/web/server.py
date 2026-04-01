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
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

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
    patched    = body.get("patched_code", "")

    if not patched or patched.strip() == "[fix code not available]":
        return jsonify(error="No patched code to commit"), 400

    commit_dir = PROJECT_ROOT / "data" / "commits"
    commit_dir.mkdir(parents=True, exist_ok=True)

    safe_wid = secure_filename(warning_id)
    fname    = f"patched_{safe_wid}_{uuid.uuid4().hex[:6]}.c"
    out_path = commit_dir / fname

    out_path.write_text(patched, encoding="utf-8")

    return jsonify({
        "status":       "ok",
        "warning_id":   warning_id,
        "download_url": f"/api/download/{fname}",
        "filename":     fname,
        "patched_code": patched,
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
# Route — start analysis (saves uploads, launches orchestrator subprocess)
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

    try:
        batch_size = max(1, min(15, int(request.form.get("batch_size", DEFAULT_BATCH_SIZE))))
    except (TypeError, ValueError):
        batch_size = DEFAULT_BATCH_SIZE

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

    q = queue.Queue()
    JOBS[job_id] = {
        "status":     "running",
        "queue":      q,
        "run_id":     run_id,
        "started_at": time.time(),
    }

    t = threading.Thread(
        target=_run_pipeline_subprocess,
        args=(job_id, run_id, str(excel_path), str(src_dir), batch_size),
        daemon=True,
    )
    t.start()

    return jsonify(job_id=job_id, run_id=run_id, c_files=saved_c, batch_size=batch_size)


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

        # Force UTF-8 output from the subprocess — prevents UnicodeEncodeError
        # on Windows when settings.py or orchestrator prints special characters
        _env = os.environ.copy()
        _env["PYTHONIOENCODING"] = "utf-8"
        _env["PYTHONUTF8"]       = "1"

        emit({"type": "phase_start", "phase": "6a",
              "label": "Starting pipeline", "detail": "Launching analysis engine",
              "progress": 2})

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(PROJECT_ROOT),
            env=_env,
        )

        total_warnings = 0
        _last_wid      = ""   # tracks the last warning_id seen for fix(es) lines

        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue

            # Always emit as log line
            emit({"type": "log", "detail": line})

            # Phase transitions — match exact orchestrator print() strings
            # e.g. "Phase 6a — Parsing Polyspace report"
            if "Phase 6a" in line:
                emit({"type": "phase_start", "phase": "6a",
                      "label": "Parsing warning report",
                      "detail": "Reading Excel + source files", "progress": 5})

            elif "Phase 6b" in line:
                emit({"type": "phase_start", "phase": "6b",
                      "label": "Retrieving MISRA context",
                      "detail": "Querying Qdrant + BGE embeddings", "progress": 16})

            elif "Phase 7" in line:
                emit({"type": "phase_start", "phase": "7",
                      "label": "Generating fix suggestions",
                      "detail": "Mistral-7B processing warnings", "progress": 31})

            elif "Phase 8" in line:
                emit({"type": "phase_start", "phase": "8",
                      "label": "Evaluating fix quality",
                      "detail": "Self-critique pass", "progress": 66})

            # Parsed warning count: "  Parsed 16 warnings — {sev}"
            if "Parsed" in line and "warnings" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "warnings" and i > 0:
                        try:
                            total_warnings = int(parts[i - 1])
                        except ValueError:
                            pass
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
                # Extract warning_id from the last warning_start we saw
                try:
                    # Find the wid from context (we track last_wid below)
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
                      "label": "Pipeline complete",
                      "detail": line.strip(), "progress": 95})

        proc.wait()

        if proc.returncode == 0:
            job["status"] = "done"
            emit({"type": "done", "label": "Analysis complete",
                  "detail": f"Results saved — run ID: {run_id}",
                  "progress": 100, "run_id": run_id})
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