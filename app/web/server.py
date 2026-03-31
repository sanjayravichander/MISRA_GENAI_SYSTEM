"""
app/web/server.py  —  SRM Technologies MISRA Compliance Reviewer

Architecture
------------
This server:
  1. Accepts file uploads (warning report + source files) via POST /api/analyse
  2. Launches the pipeline orchestrator as a subprocess
  3. Streams real-time progress back to the browser via SSE  GET /api/progress/<job_id>
  4. Lists completed runs and serves result JSON for the results page

Run from project root:
    python app/web/server.py
Then open http://127.0.0.1:5000
"""

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, abort, request, stream_with_context
from flask_cors import CORS

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from app.config.settings import OUTPUT_DIR
except ImportError:
    OUTPUT_DIR = PROJECT_ROOT / "data" / "output"

OUTPUT_DIR = Path(OUTPUT_DIR)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

# ---------------------------------------------------------------------------
# Upload temp area (cleaned up after each job completes)
# ---------------------------------------------------------------------------
_UPLOAD_TMP = PROJECT_ROOT / "data" / "_upload_tmp"
_UPLOAD_TMP.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# In-memory job registry  { job_id: {"status", "run_id", "q", "thread"} }
# ---------------------------------------------------------------------------
_JOBS: dict = {}
_JOBS_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_run_dir(run_id: str) -> Path:
    """Return the output directory for a run, or abort 404 if it doesn't exist."""
    safe = Path(run_id).name          # strip any path traversal
    run_dir = OUTPUT_DIR / safe
    if not run_dir.is_dir():
        abort(404, description=f"Run '{safe}' not found in {OUTPUT_DIR}")
    return run_dir


def _read_json(path: Path) -> dict | list | None:
    """Read and parse a JSON file; return None if missing or unparseable."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _run_summary(run_id: str, run_dir: Path) -> dict:
    """
    Build a lightweight summary dict for the run-list page from whatever
    output files are present (evaluated_fixes.json is preferred).
    """
    evaluated = _read_json(run_dir / "evaluated_fixes.json")
    fixes      = _read_json(run_dir / "fix_suggestions.json")
    parsed     = _read_json(run_dir / "parsed_warnings.json")

    # Pick the richest available source for warnings
    warnings = []
    if isinstance(evaluated, list):
        warnings = evaluated
    elif isinstance(evaluated, dict):
        warnings = evaluated.get("results", evaluated.get("warnings", []))
    elif isinstance(fixes, dict):
        warnings = fixes.get("results", fixes.get("warnings", []))
    elif isinstance(parsed, list):
        warnings = parsed
    elif isinstance(parsed, dict):
        warnings = parsed.get("warnings", [])

    total = len(warnings)

    # Confidence breakdown
    high = medium = low = manual = 0
    for w in warnings:
        ev   = w.get("evaluation") or w.get("evaluator_result") or {}
        conf = str(ev.get("overall_confidence", w.get("confidence", ""))).lower()
        if conf == "high":     high   += 1
        elif conf == "medium": medium += 1
        else:                  low    += 1
        if ev.get("manual_review_required") or ev.get("flag_for_review"):
            manual += 1

    # Phase presence flags  (tells the UI which chips to show)
    phases_present = []
    for label, fname in [
        ("Parsed",    "parsed_warnings.json"),
        ("Enriched",  "enriched_warnings.json"),
        ("Fixes",     "fix_suggestions.json"),
        ("Evaluated", "evaluated_fixes.json"),
    ]:
        if (run_dir / fname).exists():
            phases_present.append(label)

    # mtime of the most recently written file
    try:
        mtime = max(
            f.stat().st_mtime for f in run_dir.iterdir() if f.is_file()
        )
        import datetime
        completed_at = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
    except Exception:
        completed_at = "—"

    return {
        "run_id":         run_id,
        "total":          total,
        "high":           high,
        "medium":         medium,
        "low":            low,
        "manual":         manual,
        "phases_present": phases_present,
        "completed_at":   completed_at,
        "has_results":    bool(warnings),
    }


# ---------------------------------------------------------------------------
# Routes — pages
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Landing page — lists all completed runs."""
    runs = []
    if OUTPUT_DIR.is_dir():
        for d in sorted(OUTPUT_DIR.iterdir(), reverse=True):
            if d.is_dir():
                runs.append(_run_summary(d.name, d))
    return render_template("index.html", runs=runs, output_dir=str(OUTPUT_DIR))


@app.route("/results/<run_id>")
def results(run_id: str):
    """Results viewer for a specific completed run."""
    _get_run_dir(run_id)           # 404 if missing
    return render_template("results.html", run_id=run_id)


# ---------------------------------------------------------------------------
# API — run list
# ---------------------------------------------------------------------------
@app.route("/api/runs")
def api_runs():
    """Return JSON list of all available runs with summary stats."""
    runs = []
    if OUTPUT_DIR.is_dir():
        for d in sorted(OUTPUT_DIR.iterdir(), reverse=True):
            if d.is_dir():
                runs.append(_run_summary(d.name, d))
    return jsonify(runs=runs, output_dir=str(OUTPUT_DIR))


# ---------------------------------------------------------------------------
# API — run data
# ---------------------------------------------------------------------------
@app.route("/api/result/<run_id>")
def api_result(run_id: str):
    """
    Return the full result payload for a run.

    Priority for warnings data:
      1. evaluated_fixes.json  (richest — has evaluation block)
      2. fix_suggestions.json  (has fixes but no evaluation)
      3. parsed_warnings.json  (raw parse only)
    """
    run_dir = _get_run_dir(run_id)

    evaluated = _read_json(run_dir / "evaluated_fixes.json")
    fixes      = _read_json(run_dir / "fix_suggestions.json")
    parsed     = _read_json(run_dir / "parsed_warnings.json")

    # Normalise warnings list
    warnings = []
    source   = "none"
    filter_note = None
    if isinstance(evaluated, list):
        warnings, source = evaluated, "evaluated_fixes"
    elif isinstance(evaluated, dict):
        warnings = evaluated.get("results", evaluated.get("warnings", []))
        filter_note = evaluated.get("misra_filter_note")
        source   = "evaluated_fixes"
    elif isinstance(fixes, dict):
        warnings = fixes.get("results", fixes.get("warnings", []))
        filter_note = fixes.get("misra_filter_note")
        source   = "fix_suggestions"
    elif isinstance(parsed, list):
        warnings, source = parsed, "parsed_warnings"
    elif isinstance(parsed, dict):
        warnings = parsed.get("warnings", [])
        source   = "parsed_warnings"

    # Merge source_context + original warning fields from enriched/parsed
    # (fix_suggestions and evaluated_fixes don't carry source_context)
    enriched_raw = _read_json(run_dir / "enriched_warnings.json")
    parsed_raw   = _read_json(run_dir / "parsed_warnings.json")

    def _build_lookup(raw):
        """Build warning_id → warning dict from a raw JSON blob."""
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, dict):
            items = raw.get("warnings", raw.get("results", []))
        else:
            return {}
        return {str(item.get("warning_id", "")): item for item in items if isinstance(item, dict)}

    enriched_lookup = _build_lookup(enriched_raw)
    parsed_lookup   = _build_lookup(parsed_raw)

    merged = []
    for w in warnings:
        wid  = str(w.get("warning_id", ""))
        base = parsed_lookup.get(wid, {})
        enr  = enriched_lookup.get(wid, {})
        # Start from parsed (has source_context), overlay enriched, then overlay result
        combined = {**base, **enr, **w}
        merged.append(combined)
    warnings = merged

    # ── Build KB rule_id → rule_type lookup ──────────────────────────────
    kb_rule_type: dict = {}
    try:
        from app.config.settings import EXCEL_KB_PATH
        _kb = json.loads(Path(EXCEL_KB_PATH).read_text(encoding="utf-8"))
        _rules = _kb if isinstance(_kb, list) else _kb.get("rules", [])
        if _rules and isinstance(_rules[0], list):   # list-of-pairs format
            for k, v in _rules:
                if k == "rules":
                    _rules = v
                    break
        for entry in _rules:
            if isinstance(entry, dict):
                rid  = str(entry.get("rule_id", "")).strip()
                rtyp = str(entry.get("rule_type", "")).strip().lower()
                if rid:
                    kb_rule_type[rid] = rtyp
    except Exception:
        pass   # KB unavailable — rule_type will be blank

    # Attach rule_type to every warning so the UI can filter by it
    for w in warnings:
        if not w.get("rule_type"):
            rid = str(w.get("rule_id") or "").strip()
            w["rule_type"] = kb_rule_type.get(rid, "")

    # Build summary from the warnings list
    total = len(warnings)
    high = medium = low = manual = 0
    for w in warnings:
        ev   = w.get("evaluation") or w.get("evaluator_result") or {}
        conf = str(ev.get("overall_confidence", w.get("confidence", ""))).lower()
        if conf == "high":     high   += 1
        elif conf == "medium": medium += 1
        else:                  low    += 1
        if ev.get("manual_review_required") or ev.get("flag_for_review"):
            manual += 1

    summary = {
        "run_id":  run_id,
        "total":   total,
        "high":    high,
        "medium":  medium,
        "low":     low,
        "manual":  manual,
        "source":  source,
        "out_dir": str(run_dir),
    }

    return jsonify(
        run_id=run_id,
        status="done",
        summary=summary,
        warnings=warnings,
        misra_filter_note=filter_note,
        out_dir=str(run_dir),
    )


@app.route("/api/result/<run_id>/raw/<phase>")
def api_raw_phase(run_id: str, phase: str):
    """
    Serve a raw phase JSON file for inspection.
    phase must be one of: parsed, enriched, fixes, evaluated
    """
    FILE_MAP = {
        "parsed":    "parsed_warnings.json",
        "enriched":  "enriched_warnings.json",
        "fixes":     "fix_suggestions.json",
        "evaluated": "evaluated_fixes.json",
    }
    if phase not in FILE_MAP:
        abort(400, description=f"Unknown phase '{phase}'. Valid: {list(FILE_MAP)}")

    run_dir  = _get_run_dir(run_id)
    json_path = run_dir / FILE_MAP[phase]
    if not json_path.exists():
        abort(404, description=f"{FILE_MAP[phase]} not found for run '{run_id}'")

    data = _read_json(json_path)
    return jsonify(data)


# ---------------------------------------------------------------------------
# API — Upload and launch pipeline
# ---------------------------------------------------------------------------

@app.route("/api/analyse", methods=["POST"])
def api_analyse():
    """
    Accepts:
      warning_report  : .xlsx file
      source_files    : one or more .c / .h files
      misra_categories: comma-separated e.g. "mandatory,required"  (optional)
      batch_size      : integer  (optional, ignored — kept for UI compat)

    Saves uploads to a temp folder, spawns the orchestrator subprocess,
    and returns { job_id } immediately so the UI can start polling SSE.
    """
    # ── validate inputs ──
    if "warning_report" not in request.files:
        return jsonify(error="No warning report uploaded."), 400
    if "source_files" not in request.files:
        return jsonify(error="No source files uploaded."), 400

    excel_file   = request.files["warning_report"]
    source_files = request.files.getlist("source_files")

    if not excel_file.filename.lower().endswith((".xlsx", ".xls")):
        return jsonify(error="Warning report must be an .xlsx file."), 400

    valid_src = [f for f in source_files if f.filename.lower().endswith((".c", ".h"))]
    if not valid_src:
        return jsonify(error="Please upload at least one .c or .h source file."), 400

    misra_cats = request.form.get("misra_categories", "").strip()  # kept for future use

    # ── create a unique job id and temp workspace ──
    job_id  = uuid.uuid4().hex
    run_id  = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + job_id[:6]
    job_dir = _UPLOAD_TMP / job_id
    src_dir = job_dir / "source"
    job_dir.mkdir(parents=True, exist_ok=True)
    src_dir.mkdir(parents=True, exist_ok=True)

    # ── save files ──
    xlsx_path = job_dir / excel_file.filename
    excel_file.save(str(xlsx_path))
    for sf in valid_src:
        sf.save(str(src_dir / sf.filename))

    # ── register job ──
    q: queue.Queue = queue.Queue()
    with _JOBS_LOCK:
        _JOBS[job_id] = {"status": "running", "run_id": run_id, "q": q}

    # ── spawn background thread that runs the pipeline ──
    def _run():
        try:
            _run_pipeline(job_id, run_id, xlsx_path, src_dir, misra_cats, q)
        except Exception as exc:
            q.put({"type": "error", "message": str(exc)})
        finally:
            with _JOBS_LOCK:
                if job_id in _JOBS:
                    _JOBS[job_id]["status"] = "done"
            # clean up temp files after a short delay
            def _cleanup():
                time.sleep(30)
                shutil.rmtree(job_dir, ignore_errors=True)
            threading.Thread(target=_cleanup, daemon=True).start()

    t = threading.Thread(target=_run, daemon=True)
    with _JOBS_LOCK:
        _JOBS[job_id]["thread"] = t
    t.start()

    return jsonify(job_id=job_id, run_id=run_id)


def _run_pipeline(
    job_id: str,
    run_id: str,
    xlsx_path: Path,
    src_dir: Path,
    misra_cats: str,
    q: queue.Queue,
) -> None:
    """
    Runs the orchestrator as a subprocess, parses its stdout line-by-line,
    and pushes SSE-compatible dicts onto the queue.
    """

    orchestrator = PROJECT_ROOT / "app" / "pipeline" / "orchestrator.py"
    python_exe   = sys.executable

    cmd = [
        python_exe, str(orchestrator),
        str(xlsx_path), str(src_dir),
        "--run-id", run_id,
    ]
    if misra_cats:
        cmd += ["--misra-categories", misra_cats]

    # Phase-line patterns → map to frontend phase ids
    PHASE_PATTERNS = [
        (re.compile(r"Phase 6a", re.I),  "6a", "Reading your file"),
        (re.compile(r"Phase 6b", re.I),  "6b", "Looking up rules"),
        (re.compile(r"Phase 7",  re.I),  "7",  "Creating fix suggestions"),
        (re.compile(r"Phase 8",  re.I),  "8",  "Checking fix quality"),
    ]
    WARNING_RE = re.compile(
        r"\[(\s*\d+)/(\s*\d+)\]\s+(?:Evaluating\s+)?(\S+)", re.I
    )  # handles both "[ 1/2] PS008" and "[ 1/2] Evaluating PS008"

    def _push(obj: dict):
        q.put(obj)

    _push({"type": "phase_start", "phase": "6a", "detail": "Reading your file…"})

    # Collect all output lines so we can send full error detail to the UI
    all_output_lines: list[str] = []

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=str(PROJECT_ROOT),
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"},
        )
    except Exception as exc:
        _push({"type": "error", "message": f"Could not start the pipeline: {exc}"})
        return

    current_phase  = "6a"
    total_warnings = 0
    done_warnings  = 0
    last_wid       = None   # track previous warning to mark it Done when next starts
    # Completion markers — lines that confirm the current warning finished
    COMPLETION_RE  = re.compile(
        r"(confidence=|fix\(es\)|✓|\d+\s+fix)", re.I
    )

    for line in proc.stdout:
        line = line.rstrip()
        all_output_lines.append(line)

        # Always print to server terminal for easy debugging
        print(f"  [pipeline] {line}", flush=True)

        if not line:
            continue

        # Detect phase transitions
        for pattern, phase_id, label in PHASE_PATTERNS:
            if pattern.search(line):
                if phase_id != current_phase:
                    # Mark last warning done when phase changes
                    if last_wid:
                        _push({"type": "warning_done", "phase": current_phase,
                               "warning_id": last_wid})
                        last_wid = None
                    _push({"type": "phase_done",  "phase": current_phase, "detail": "Done"})
                    _push({"type": "phase_start", "phase": phase_id, "detail": label + "…"})
                    current_phase = phase_id
                break

        # Detect "Parsed N warnings" from phase 6a
        m_parsed = re.search(r"Parsed\s+(\d+)\s+warnings", line, re.I)
        if m_parsed:
            total_warnings = int(m_parsed.group(1))
            _push({"type": "detail", "phase": "6a",
                   "detail": f"Found {total_warnings} warning(s) to review"})

        # Detect per-warning progress lines:  [ 1/2] PS002  or  [ 1/2] Evaluating PS002
        m_warn = WARNING_RE.search(line)
        if m_warn:
            new_wid   = m_warn.group(3)
            done_n    = int(m_warn.group(1).strip())
            total_w   = int(m_warn.group(2).strip())
            if total_w > 0:
                total_warnings = total_w

            # The previous warning just finished — mark it Done
            if last_wid and last_wid != new_wid:
                _push({"type": "warning_done", "phase": current_phase,
                       "warning_id": last_wid})

            pct = int(done_n / max(total_warnings, 1) * 100)
            _push({
                "type":       "warning_start",
                "phase":      current_phase,
                "warning_id": new_wid,
                "done":       done_n,
                "total":      total_warnings,
                "pct":        pct,
                "detail":     f"Processing {done_n} of {total_warnings}…",
            })
            last_wid      = new_wid
            done_warnings = done_n

        # Detect completion of the current warning (confidence= or fix count line)
        elif last_wid and COMPLETION_RE.search(line) and current_phase in ("7", "8"):
            _push({"type": "warning_done", "phase": current_phase,
                   "warning_id": last_wid})
            last_wid = None

        # Pipeline complete
        if re.search(r"Pipeline complete", line, re.I):
            if last_wid:
                _push({"type": "warning_done", "phase": "8", "warning_id": last_wid})
                last_wid = None
            _push({"type": "phase_done", "phase": current_phase, "detail": "Done"})
            _push({"type": "phase_done", "phase": "8",  "detail": "Done"})

        # Catch explicit ERROR lines early
        if re.match(r"\s*ERROR", line, re.I):
            _push({"type": "detail", "phase": current_phase, "detail": line.strip()})

    proc.wait()

    if proc.returncode == 0:
        _push({"type": "done", "run_id": run_id,
               "detail": "Your report is ready!"})
    else:
        # Find the most useful error lines from the output
        error_lines = [l for l in all_output_lines if l.strip()]
        # Prefer lines with ERROR/Traceback/Exception
        key_lines = [l for l in error_lines if re.search(r"error|traceback|exception|not found|importerror|modulenotfound", l, re.I)]
        detail = " | ".join(key_lines[-3:]) if key_lines else " | ".join(error_lines[-5:])
        _push({"type": "error",
               "message": f"Pipeline failed (exit code {proc.returncode}). "
                          f"Details: {detail or 'Check the server terminal for full output.'}"})


# ---------------------------------------------------------------------------
# API — SSE progress stream
# ---------------------------------------------------------------------------

@app.route("/api/progress/<job_id>")
def api_progress(job_id: str):
    """
    Server-Sent Events stream.  Each event is a JSON object pushed from the
    pipeline thread via the job's queue.
    """
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
    if not job:
        return jsonify(error="Job not found"), 404

    q: queue.Queue = job["q"]

    def _generate():
        # Keep the connection alive for up to 90 minutes
        deadline = time.time() + 5400
        while time.time() < deadline:
            try:
                msg = q.get(timeout=15)
                yield f"data: {json.dumps(msg)}\n\n"
                if msg.get("type") in ("done", "error"):
                    break
            except queue.Empty:
                # heartbeat — keeps the SSE connection open
                yield ": heartbeat\n\n"

    return Response(
        stream_with_context(_generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":  "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  SRM Technologies — MISRA Compliance Reviewer")
    print(f"  Output directory : {OUTPUT_DIR}")
    print(f"  Upload temp      : {_UPLOAD_TMP}")
    print("  http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)