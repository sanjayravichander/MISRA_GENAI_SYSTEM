"""
app/web/server.py — SRM Technologies MISRA Compliance Reviewer

Architecture
------------
This server:
  1. Accepts file uploads (warning report + source files) via POST /api/analyse
  2. Launches the pipeline orchestrator as a subprocess
  3. Streams real-time progress back to the browser via SSE GET /api/progress/<job_id>
  4. Lists completed runs and serves result JSON for the results page
  5. Loads Excel configuration, updates User Category, and reuses the saved Excel

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
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from flask import Flask, Response, abort, jsonify, render_template, request, stream_with_context
from flask_cors import CORS
from werkzeug.utils import secure_filename

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
_WEB_DIR = Path(__file__).resolve().parent
_TEMPLATE_DIR = _WEB_DIR / "templates"
_STATIC_DIR = _WEB_DIR / "static"

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
# Upload temp areas
# ---------------------------------------------------------------------------
_UPLOAD_TMP = PROJECT_ROOT / "data" / "_upload_tmp"
_UPLOAD_TMP.mkdir(parents=True, exist_ok=True)

_CONFIG_TMP = _UPLOAD_TMP / "config_files"
_CONFIG_TMP.mkdir(parents=True, exist_ok=True)

# token -> saved Excel path
_CONFIG_FILES: Dict[str, Path] = {}

# ---------------------------------------------------------------------------
# In-memory job registry
# ---------------------------------------------------------------------------
_JOBS: Dict[str, Dict[str, Any]] = {}
_JOBS_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_run_dir(run_id: str) -> Path:
    safe = Path(run_id).name
    run_dir = OUTPUT_DIR / safe
    if not run_dir.is_dir():
        abort(404, description=f"Run '{safe}' not found in {OUTPUT_DIR}")
    return run_dir


def _read_json(path: Path) -> Optional[Union[Dict[str, Any], List[Any]]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


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


def _run_summary(run_id: str, run_dir: Path) -> Dict[str, Any]:
    evaluated = _read_json(run_dir / "evaluated_fixes.json")
    fixes = _read_json(run_dir / "fix_suggestions.json")
    parsed = _read_json(run_dir / "parsed_warnings.json")

    warnings: List[Dict[str, Any]] = []
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

    high = medium = low = manual = 0
    for w in warnings:
        ev = w.get("evaluation") or w.get("evaluator_result") or {}
        conf = str(ev.get("overall_confidence", w.get("confidence", ""))).lower()
        if conf == "high":
            high += 1
        elif conf == "medium":
            medium += 1
        else:
            low += 1
        if ev.get("manual_review_required") or ev.get("flag_for_review"):
            manual += 1

    phases_present: List[str] = []
    for label, fname in [
        ("Parsed", "parsed_warnings.json"),
        ("Enriched", "enriched_warnings.json"),
        ("Fixes", "fix_suggestions.json"),
        ("Evaluated", "evaluated_fixes.json"),
    ]:
        if (run_dir / fname).exists():
            phases_present.append(label)

    try:
        mtime = max(f.stat().st_mtime for f in run_dir.iterdir() if f.is_file())
        completed_at = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
    except Exception:
        completed_at = "—"

    return {
        "run_id": run_id,
        "total": total,
        "high": high,
        "medium": medium,
        "low": low,
        "manual": manual,
        "phases_present": phases_present,
        "completed_at": completed_at,
        "has_results": bool(warnings),
    }


# ---------------------------------------------------------------------------
# Routes — pages
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    runs = []
    if OUTPUT_DIR.is_dir():
        for d in sorted(OUTPUT_DIR.iterdir(), reverse=True):
            if d.is_dir():
                runs.append(_run_summary(d.name, d))
    return render_template("index.html", runs=runs, output_dir=str(OUTPUT_DIR), default_batch=5)


@app.route("/results/<run_id>")
def results(run_id: str):
    _get_run_dir(run_id)
    return render_template("results.html", run_id=run_id)


# ---------------------------------------------------------------------------
# API — run list
# ---------------------------------------------------------------------------
@app.route("/api/runs")
def api_runs():
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
    run_dir = _get_run_dir(run_id)

    evaluated = _read_json(run_dir / "evaluated_fixes.json")
    fixes = _read_json(run_dir / "fix_suggestions.json")
    parsed = _read_json(run_dir / "parsed_warnings.json")

    warnings: List[Dict[str, Any]] = []
    source = "none"
    filter_note = None

    if isinstance(evaluated, list):
        warnings, source = evaluated, "evaluated_fixes"
    elif isinstance(evaluated, dict):
        warnings = evaluated.get("results", evaluated.get("warnings", []))
        filter_note = evaluated.get("misra_filter_note")
        source = "evaluated_fixes"
    elif isinstance(fixes, dict):
        warnings = fixes.get("results", fixes.get("warnings", []))
        filter_note = fixes.get("misra_filter_note")
        source = "fix_suggestions"
    elif isinstance(parsed, list):
        warnings, source = parsed, "parsed_warnings"
    elif isinstance(parsed, dict):
        warnings = parsed.get("warnings", [])
        source = "parsed_warnings"

    enriched_raw = _read_json(run_dir / "enriched_warnings.json")
    parsed_raw = _read_json(run_dir / "parsed_warnings.json")

    def _build_lookup(raw: Any) -> Dict[str, Dict[str, Any]]:
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, dict):
            items = raw.get("warnings", raw.get("results", []))
        else:
            return {}
        return {str(item.get("warning_id", "")): item for item in items if isinstance(item, dict)}

    enriched_lookup = _build_lookup(enriched_raw)
    parsed_lookup = _build_lookup(parsed_raw)

    merged: List[Dict[str, Any]] = []
    for w in warnings:
        wid = str(w.get("warning_id", ""))
        base = parsed_lookup.get(wid, {})
        enr = enriched_lookup.get(wid, {})
        combined = {**base, **enr, **w}
        merged.append(combined)
    warnings = merged

    kb_rule_type: Dict[str, str] = {}
    try:
        from app.config.settings import EXCEL_KB_PATH
        _kb = json.loads(Path(EXCEL_KB_PATH).read_text(encoding="utf-8"))
        _rules = _kb if isinstance(_kb, list) else _kb.get("rules", [])
        if _rules and isinstance(_rules[0], list):
            for k, v in _rules:
                if k == "rules":
                    _rules = v
                    break
        for entry in _rules:
            if isinstance(entry, dict):
                rid = str(entry.get("rule_id", "")).strip()
                rtyp = str(entry.get("rule_type", "")).strip().lower()
                if rid:
                    kb_rule_type[rid] = rtyp
    except Exception:
        pass

    for w in warnings:
        if not w.get("rule_type"):
            rid = str(w.get("rule_id") or "").strip()
            w["rule_type"] = kb_rule_type.get(rid, "")

    total = len(warnings)
    high = medium = low = manual = 0
    for w in warnings:
        ev = w.get("evaluation") or w.get("evaluator_result") or {}
        conf = str(ev.get("overall_confidence", w.get("confidence", ""))).lower()
        if conf == "high":
            high += 1
        elif conf == "medium":
            medium += 1
        else:
            low += 1
        if ev.get("manual_review_required") or ev.get("flag_for_review"):
            manual += 1

    summary = {
        "run_id": run_id,
        "total": total,
        "high": high,
        "medium": medium,
        "low": low,
        "manual": manual,
        "source": source,
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
    FILE_MAP = {
        "parsed": "parsed_warnings.json",
        "enriched": "enriched_warnings.json",
        "fixes": "fix_suggestions.json",
        "evaluated": "evaluated_fixes.json",
    }
    if phase not in FILE_MAP:
        abort(400, description=f"Unknown phase '{phase}'. Valid: {list(FILE_MAP)}")

    run_dir = _get_run_dir(run_id)
    json_path = run_dir / FILE_MAP[phase]
    if not json_path.exists():
        abort(404, description=f"{FILE_MAP[phase]} not found for run '{run_id}'")

    data = _read_json(json_path)
    return jsonify(data)


# ---------------------------------------------------------------------------
# API — Excel config load/save
# ---------------------------------------------------------------------------
from flask import jsonify
import pandas as pd
import os

DATA_FOLDER = r"C:\Users\mohamedafrith.s\Documents\Dev\Projects\MISRA_GENAI_SYSTEM\data"

# Folder where user specification Excel files are saved after Apply Configuration
USER_SPEC_FOLDER = Path(DATA_FOLDER) / "user_specification_excel_folder"
USER_SPEC_FOLDER.mkdir(parents=True, exist_ok=True)


@app.route("/api/config/load", methods=["GET"])
def load_config():
    try:
        if not os.path.exists(DATA_FOLDER):
            return jsonify({"error": f"Data folder not found: {DATA_FOLDER}"}), 500

        # ── Priority: load from previously saved user specification if it exists ──
        # This ensures config persists across server restarts
        _saved = USER_SPEC_FOLDER / "user_specification.xlsx"
        if _saved.exists():
            file_path = _saved
        else:
            files = [f for f in os.listdir(DATA_FOLDER) if f.endswith((".xlsx", ".xls"))]
            if not files:
                return jsonify({"error": "No Excel file found in data folder"}), 404
            file_path = Path(os.path.join(DATA_FOLDER, files[0]))

        df = pd.read_excel(file_path, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        df = df.fillna("")

        # ── Exact column names from your Excel ──────────────────────────
        # SI.No | User Category | MISRA Category | MISRA Rule | Warning Message Nos.
        RULE_COL     = "MISRA Rule"
        CAT_COL      = "MISRA Category"
        USER_CAT_COL = "User Category"

        missing = [c for c in [RULE_COL, CAT_COL] if c not in df.columns]
        if missing:
            return jsonify({
                "error": f"Expected columns not found: {missing}. "
                         f"Found: {list(df.columns)}"
            }), 400

        rows = []
        for i, row in df.iterrows():
            rule_raw  = str(row.get(RULE_COL,     "")).strip()
            cat_raw   = str(row.get(CAT_COL,      "")).strip()
            user_cat  = str(row.get(USER_CAT_COL, "")).strip() if USER_CAT_COL in df.columns else ""

            if not rule_raw:
                continue

            # Clean display: "Rule-9.1" → "9.1",  "Dir-4.14" → "Dir 4.14"
            import re as _re
            rule_display = rule_raw
            m = _re.match(r"Rule[-_](.+)", rule_raw, _re.I)
            if m:
                rule_display = m.group(1).strip()
            else:
                m2 = _re.match(r"Dir[-_](.+)", rule_raw, _re.I)
                if m2:
                    rule_display = "Dir " + m2.group(1).strip()

            # Display: MISRA-M → Mandatory, MISRA-R → Required, MISRA-A → Advisory
            cat_display = {"MISRA-M": "Mandatory",
                           "MISRA-R": "Required",
                           "MISRA-A": "Advisory"}.get(cat_raw, cat_raw)

            # Normalise existing user_category (M / R / A or blank)
            user_cat_norm = _normalize_user_category(user_cat)

            warn_nos  = str(row.get("Warning Message Nos.", "")).strip() if "Warning Message Nos." in df.columns else ""

            rows.append({
                "row_index":            int(i),
                "rule_list":            rule_display,
                "misra_category":       cat_display,
                "misra_category_display": cat_display,
                "user_category":        user_cat_norm,
                "warning_message_nos":  warn_nos,
            })

        if not rows:
            return jsonify({"error": "No valid data rows found in Excel"}), 400

        # Register file so /api/config/save can write back to it
        token = uuid.uuid4().hex
        _CONFIG_FILES[token] = file_path

        return jsonify({"token": token, "rows": rows, "count": len(rows)})

    except Exception as e:
        import traceback
        print("GET load_config ERROR:\n", traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route("/api/config/save", methods=["POST"])
def api_config_save():
    data    = request.get_json(silent=True) or {}
    token   = _safe_text(data.get("token", ""))
    updates = data.get("updates", [])

    if not token:
        return jsonify(error="Missing config token."), 400

    path = _get_config_path(token)
    if not path:
        return jsonify(error="Excel file not found for this session."), 404

    try:
        # Always read from the source (original) file — never write back to it
        df = _read_excel_df(path)
        df.columns = [str(c).strip() for c in df.columns]

        USER_CAT_COL = "User Category"
        if USER_CAT_COL not in df.columns:
            df[USER_CAT_COL] = ""

        for item in updates:
            try:
                idx      = int(item.get("row_index"))
                user_cat = _normalize_user_category(item.get("user_category", ""))
                if idx in df.index:
                    # Store "-" when no checkbox was selected by the user
                    df.at[idx, USER_CAT_COL] = user_cat if user_cat else "-"
            except Exception:
                continue

        # ── Write ONLY to user_specification_excel_folder — original file is never touched ──
        USER_SPEC_FOLDER.mkdir(parents=True, exist_ok=True)
        new_fname = "user_specification.xlsx"
        new_path  = USER_SPEC_FOLDER / new_fname
        df.to_excel(new_path, index=False, engine="openpyxl")

        rows = _excel_rows_from_df(df)

    except Exception as exc:
        return jsonify(error=f"Could not save Excel: {exc}"), 400

    return jsonify(status="updated", token=token, rows=rows, saved_file=new_fname)


# ---------------------------------------------------------------------------
# API — Upload and launch pipeline
# ---------------------------------------------------------------------------
@app.route("/api/analyse", methods=["POST"])
def api_analyse():
    # ✅ AUTO LOAD EXCEL FROM DATA FOLDER
    DATA_EXCEL_PATH = PROJECT_ROOT / "data" / "user_specifi.xlsx"

    if not DATA_EXCEL_PATH.exists():
        return jsonify(error="Excel file not found in data/user_specifi.xlsx"), 400

    source_files = request.files.getlist("source_files")

    if not source_files:
        return jsonify(error="No source files uploaded."), 400

    valid_src = [f for f in source_files if f.filename.lower().endswith((".c", ".h"))]
    if not valid_src:
        return jsonify(error="Please upload at least one .c or .h source file."), 400

    misra_cats = request.form.get("misra_categories", "").strip()

    job_id = uuid.uuid4().hex
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + job_id[:6]

    job_dir = _UPLOAD_TMP / job_id
    src_dir = job_dir / "source"

    job_dir.mkdir(parents=True, exist_ok=True)
    src_dir.mkdir(parents=True, exist_ok=True)

    # ✅ COPY EXCEL FROM DATA FOLDER
    xlsx_path = job_dir / "warning_report.xlsx"
    shutil.copy2(DATA_EXCEL_PATH, xlsx_path)

    # ✅ SAVE SOURCE FILES
    for sf in valid_src:
        sf.save(str(src_dir / sf.filename))

    q: queue.Queue = queue.Queue()

    with _JOBS_LOCK:
        _JOBS[job_id] = {"status": "running", "run_id": run_id, "q": q}

    def _run():
        try:
            _run_pipeline(job_id, run_id, xlsx_path, src_dir, misra_cats, q)
        except Exception as exc:
            q.put({"type": "error", "message": str(exc)})
        finally:
            with _JOBS_LOCK:
                if job_id in _JOBS:
                    _JOBS[job_id]["status"] = "done"

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
    orchestrator = PROJECT_ROOT / "app" / "pipeline" / "orchestrator.py"
    python_exe = sys.executable

    cmd = [
        python_exe, str(orchestrator),
        str(xlsx_path), str(src_dir),
        "--run-id", run_id,
    ]
    if misra_cats:
        cmd += ["--misra-categories", misra_cats]

    PHASE_PATTERNS = [
        (re.compile(r"Phase 6a", re.I), "6a", "Reading your file"),
        (re.compile(r"Phase 6b", re.I), "6b", "Looking up rules"),
        (re.compile(r"Phase 7", re.I), "7", "Creating fix suggestions"),
        (re.compile(r"Phase 8", re.I), "8", "Checking fix quality"),
    ]
    WARNING_RE = re.compile(r"\[(\s*\d+)/(\s*\d+)\]\s+(?:Evaluating\s+)?(\S+)", re.I)

    def _push(obj: Dict[str, Any]):
        q.put(obj)

    _push({"type": "phase_start", "phase": "6a", "detail": "Reading your file…"})

    all_output_lines: List[str] = []

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

    current_phase = "6a"
    total_warnings = 0
    last_wid = None
    COMPLETION_RE = re.compile(r"(confidence=|fix\(es\)|✓|\d+\s+fix)", re.I)

    for line in proc.stdout:
        line = line.rstrip()
        all_output_lines.append(line)
        print(f"  [pipeline] {line}", flush=True)

        if not line:
            continue

        for pattern, phase_id, label in PHASE_PATTERNS:
            if pattern.search(line):
                if phase_id != current_phase:
                    if last_wid:
                        _push({"type": "warning_done", "phase": current_phase, "warning_id": last_wid})
                        last_wid = None
                    _push({"type": "phase_done", "phase": current_phase, "detail": "Done"})
                    _push({"type": "phase_start", "phase": phase_id, "detail": label + "…"})
                    current_phase = phase_id
                break

        m_parsed = re.search(r"Parsed\s+(\d+)\s+warnings", line, re.I)
        if m_parsed:
            total_warnings = int(m_parsed.group(1))
            _push({"type": "detail", "phase": "6a", "detail": f"Found {total_warnings} warning(s) to review"})

        m_warn = WARNING_RE.search(line)
        if m_warn:
            new_wid = m_warn.group(3)
            done_n = int(m_warn.group(1).strip())
            total_w = int(m_warn.group(2).strip())
            if total_w > 0:
                total_warnings = total_w

            if last_wid and last_wid != new_wid:
                _push({"type": "warning_done", "phase": current_phase, "warning_id": last_wid})

            pct = int(done_n / max(total_warnings, 1) * 100)
            _push({
                "type": "warning_start",
                "phase": current_phase,
                "warning_id": new_wid,
                "done": done_n,
                "total": total_warnings,
                "pct": pct,
                "detail": f"Processing {done_n} of {total_warnings}…",
            })
            last_wid = new_wid

        elif last_wid and COMPLETION_RE.search(line) and current_phase in ("7", "8"):
            _push({"type": "warning_done", "phase": current_phase, "warning_id": last_wid})
            last_wid = None

        if re.search(r"Pipeline complete", line, re.I):
            if last_wid:
                _push({"type": "warning_done", "phase": "8", "warning_id": last_wid})
                last_wid = None
            _push({"type": "phase_done", "phase": current_phase, "detail": "Done"})
            _push({"type": "phase_done", "phase": "8", "detail": "Done"})

        if re.match(r"\s*ERROR", line, re.I):
            _push({"type": "detail", "phase": current_phase, "detail": line.strip()})

    proc.wait()

    if proc.returncode == 0:
        _push({"type": "done", "run_id": run_id, "detail": "Your report is ready!"})
    else:
        error_lines = [l for l in all_output_lines if l.strip()]
        key_lines = [l for l in error_lines if re.search(r"error|traceback|exception|not found|importerror|modulenotfound", l, re.I)]
        detail = " | ".join(key_lines[-3:]) if key_lines else " | ".join(error_lines[-5:])
        _push({
            "type": "error",
            "message": f"Pipeline failed (exit code {proc.returncode}). Details: {detail or 'Check the server terminal for full output.'}"
        })


# ---------------------------------------------------------------------------
# API — SSE progress stream
# ---------------------------------------------------------------------------
@app.route("/api/progress/<job_id>")
def api_progress(job_id: str):
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
    if not job:
        return jsonify(error="Job not found"), 404

    q: queue.Queue = job["q"]

    def _generate():
        deadline = time.time() + 5400
        while time.time() < deadline:
            try:
                msg = q.get(timeout=15)
                yield f"data: {json.dumps(msg)}\n\n"
                if msg.get("type") in ("done", "error"):
                    break
            except queue.Empty:
                yield ": heartbeat\n\n"

    return Response(
        stream_with_context(_generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
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