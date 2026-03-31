#!/usr/bin/env python3
"""
orchestrator.py  —  Pipeline orchestrator: runs Phases 6a → 6b → 7 → 8.

This is the single entry point for a complete analysis run.
It replaces running 4 separate scripts manually.

What it does
------------
  Phase 6a  parse_polyspace   : reads Excel report + C source files
  Phase 6b  retrieve          : fetches MISRA KB context per warning
  Phase 7   generate_fixes    : calls Mistral to generate ranked fixes
  Phase 8   evaluate_fixes    : calls Mistral again to self-critique fixes

Each phase writes its output to a run-specific folder under data/output/<run_id>/
so multiple runs never overwrite each other.

Run ID
------
Generated from timestamp: YYYYMMDD_HHMMSS
Optionally pass --run-id <name> for a human-readable label.

Resume
------
Pass --resume <run_id> to skip phases that already completed for that run.
Checks for output file existence — if present, skips that phase.

Usage
-----
  python orchestrator.py <excel_report.xlsx> <source_dir>
  python orchestrator.py <excel_report.xlsx> <source_dir> --run-id my_analysis
  python orchestrator.py <excel_report.xlsx> <source_dir> --resume 20240323_143000
  python orchestrator.py <excel_report.xlsx> <source_dir> --skip-eval
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.config.settings import (
    FAISS_INDEX_DIR, OUTPUT_DIR, AUDIT_DIR,
    LLAMA_HOST, LLAMA_PORT,
)


# ---------------------------------------------------------------------------
# Phase runners — each calls its module's main logic directly
# ---------------------------------------------------------------------------

def phase_6a_parse(
    xlsx_path: Path,
    source_dir: Path,
    out_path: Path,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    """Parse Polyspace Excel report and extract source context."""
    if verbose:
        print(f"\n{'─'*60}")
        print(f"Phase 6a — Parsing Polyspace report")
        print(f"  Excel  : {xlsx_path}")
        print(f"  Sources: {source_dir}")

    from app.ingestion.parse_polyspace import parse_report
    warnings = parse_report(xlsx_path, source_dir)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"warning_count": len(warnings), "warnings": warnings},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    if verbose:
        sev = {}
        for w in warnings:
            s = w.get("severity", "Unknown")
            sev[s] = sev.get(s, 0) + 1
        print(f"  Parsed {len(warnings)} warnings — {sev}")
    return warnings


def phase_6b_retrieve(
    warnings: List[Dict[str, Any]],
    out_path: Path,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    """Retrieve MISRA KB context for each warning."""
    if verbose:
        print(f"\n{'─'*60}")
        print(f"Phase 6b — Retrieving MISRA context")
        print(f"  FAISS index: {FAISS_INDEX_DIR}")

    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer
    from app.knowledge.retrieve import load_index, retrieve_for_warning

    index, chunks, by_rule = load_index(FAISS_INDEX_DIR)
    if verbose:
        print(f"  {index.ntotal} vectors loaded")

    model = SentenceTransformer("all-MiniLM-L6-v2")

    enriched = []
    for w in warnings:
        retrieved = retrieve_for_warning(w, index, chunks, by_rule, model)
        enriched.append({**w, "misra_context": retrieved})
        if verbose:
            exact = sum(1 for r in retrieved if r.get("retrieval_method") == "exact_rule_match")
            sem   = sum(1 for r in retrieved if r.get("retrieval_method") == "semantic")
            print(f"  {w['warning_id']}  {w.get('rule_id',''):12s}  "
                  f"{exact} exact + {sem} semantic")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"warning_count": len(enriched), "warnings": enriched},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return enriched


def phase_7_generate(
    enriched: List[Dict[str, Any]],
    out_path: Path,
    host: str = LLAMA_HOST,
    port: int = LLAMA_PORT,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    """Generate fix suggestions via Mistral."""
    if verbose:
        print(f"\n{'─'*60}")
        print(f"Phase 7 — Generating fix suggestions")
        print(f"  LLM: http://{host}:{port}")
        print(f"  Warnings: {len(enriched)}")

    from app.pipeline.generate_fixes import build_prompt, call_llm, parse_llm_response, SYSTEM_PROMPT

    results = []
    # Load existing if resuming (file may be partially written)
    existing_ids = set()
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            for r in existing.get("results", []):
                if not r.get("parse_error"):
                    results.append(r)
                    existing_ids.add(r["warning_id"])
            if verbose and existing_ids:
                print(f"  Resuming: {len(existing_ids)} already done")
        except Exception:
            pass

    for i, w in enumerate(enriched, 1):
        wid = w.get("warning_id", f"W{i}")
        if wid in existing_ids:
            if verbose:
                print(f"  [{i:2d}/{len(enriched)}] {wid} — skipped (done)")
            continue

        if verbose:
            print(f"  [{i:2d}/{len(enriched)}] {wid}  {w.get('rule_id',''):12s}  "
                  f"{w.get('severity',''):6s}  {w.get('file_path','')}:{w.get('line_start','')}")

        t0     = time.time()
        prompt = build_prompt(w)
        try:
            raw    = call_llm(host, port, SYSTEM_PROMPT, prompt)
            result = parse_llm_response(raw, wid, w.get("rule_id", ""))
            # Retry once on parse error
            if result.get("parse_error"):
                retry = prompt + "\n\nIMPORTANT: Output ONLY the JSON object starting with { and ending with }."
                raw2   = call_llm(host, port, SYSTEM_PROMPT, retry)
                result2 = parse_llm_response(raw2, wid, w.get("rule_id", ""))
                if not result2.get("parse_error"):
                    result = result2
        except TimeoutError:
            result = {"warning_id": wid, "rule_id": w.get("rule_id",""),
                      "ranked_fixes": [], "parse_error": True,
                      "explanation": "Timed out"}
        except Exception as e:
            result = {"warning_id": wid, "rule_id": w.get("rule_id",""),
                      "ranked_fixes": [], "parse_error": True,
                      "explanation": str(e)}

        elapsed = time.time() - t0
        fixes   = len(result.get("ranked_fixes", []))
        status  = "✓" if not result.get("parse_error") else "✗"
        if verbose:
            print(f"       {fixes} fix(es)  {elapsed:.1f}s  {status}")

        results.append(result)
        # Save after every warning
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps({"warning_count": len(results), "results": results},
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return results


def phase_8_evaluate(
    fix_results: List[Dict[str, Any]],
    enriched: List[Dict[str, Any]],
    out_path: Path,
    host: str = LLAMA_HOST,
    port: int = LLAMA_PORT,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    """Self-critique evaluation of generated fixes."""
    if verbose:
        print(f"\n{'─'*60}")
        print(f"Phase 8 — Evaluating fix suggestions (self-critique)")

    from app.pipeline.evaluate_fixes import evaluate_all

    evaluated = evaluate_all(
        fix_results, enriched,
        host=host, port=port,
        verbose=verbose,
        out_path=out_path,
    )

    # Summary
    high   = sum(1 for r in evaluated if r.get("overall_confidence") == "High")
    medium = sum(1 for r in evaluated if r.get("overall_confidence") == "Medium")
    low    = sum(1 for r in evaluated if r.get("overall_confidence") == "Low")
    review = sum(1 for r in evaluated if r.get("needs_manual_review"))
    fixed  = sum(1 for r in evaluated
                 for f in r.get("ranked_fixes", []) if f.get("was_corrected"))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({
            "warning_count": len(evaluated),
            "confidence_high": high, "confidence_medium": medium,
            "confidence_low": low, "needs_manual_review": review,
            "fixes_corrected": fixed, "results": evaluated,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if verbose:
        print(f"\n  Confidence: High={high} Medium={medium} Low={low}")
        print(f"  Manual review flagged: {review}")
        print(f"  Fixes auto-corrected : {fixed}")

    return evaluated


# ---------------------------------------------------------------------------
# Server health check
# ---------------------------------------------------------------------------

def check_server(host: str, port: int) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://{host}:{port}/health", timeout=5
        ) as resp:
            body = json.loads(resp.read().decode())
            return body.get("status") == "ok"
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Audit logger
# ---------------------------------------------------------------------------

def write_audit(run_id: str, run_dir: Path, meta: Dict[str, Any]) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    audit_path = AUDIT_DIR / f"{run_id}_audit.json"
    audit_path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="MISRA GenAI pipeline orchestrator (Phases 6a–8)"
    )
    parser.add_argument("excel_report", type=Path,
                        help="Polyspace Excel warning report (.xlsx)")
    parser.add_argument("source_dir",   type=Path,
                        help="Directory containing the C source files")
    parser.add_argument("--run-id",     default=None,
                        help="Human-readable run ID (default: timestamp)")
    parser.add_argument("--resume",     default=None, metavar="RUN_ID",
                        help="Resume an existing run by ID")
    parser.add_argument("--skip-eval",  action="store_true",
                        help="Skip Phase 8 (evaluation) — faster but less accurate")
    parser.add_argument("--host",       default=LLAMA_HOST)
    parser.add_argument("--port",       type=int, default=LLAMA_PORT)
    args = parser.parse_args()

    # Resolve run ID
    run_id  = args.resume or args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = OUTPUT_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"{'='*60}")
    print(f"MISRA GenAI Analysis Pipeline")
    print(f"Run ID : {run_id}")
    print(f"Output : {run_dir}")
    print(f"{'='*60}")

    # Validate inputs
    if not args.excel_report.exists():
        print(f"ERROR: Excel report not found: {args.excel_report}")
        return 1
    if not args.source_dir.exists():
        print(f"ERROR: Source directory not found: {args.source_dir}")
        return 1
    if not FAISS_INDEX_DIR.exists():
        print(f"ERROR: FAISS index not found at {FAISS_INDEX_DIR}")
        print(f"  Run build_index.py first.")
        return 1

    # Check LLM server
    print(f"\nChecking llama-server at http://{args.host}:{args.port} ...")
    if not check_server(args.host, args.port):
        print(f"ERROR: llama-server not reachable.")
        print(f"  Start it with:")
        print(f"  llama-server.exe -m <model.gguf> --host {args.host} --port {args.port} --ctx-size 4096 --threads 4")
        return 1
    print("  Server healthy ✓")

    t_start = time.time()
    audit   = {
        "run_id": run_id,
        "excel_report": str(args.excel_report),
        "source_dir": str(args.source_dir),
        "started_at": datetime.now().isoformat(),
        "phases": {},
    }

    # Output file paths for this run
    parsed_path   = run_dir / "parsed_warnings.json"
    enriched_path = run_dir / "enriched_warnings.json"
    fixes_path    = run_dir / "fix_suggestions.json"
    eval_path     = run_dir / "evaluated_fixes.json"

    # Phase 6a
    t0 = time.time()
    if args.resume and parsed_path.exists():
        print(f"\nPhase 6a — Skipped (resuming, file exists)")
        warnings = json.loads(parsed_path.read_text(encoding="utf-8"))["warnings"]
    else:
        warnings = phase_6a_parse(args.excel_report, args.source_dir, parsed_path)
    audit["phases"]["6a"] = {"duration_s": round(time.time()-t0, 1),
                              "warnings": len(warnings)}

    # Phase 6b
    t0 = time.time()
    if args.resume and enriched_path.exists():
        print(f"\nPhase 6b — Skipped (resuming, file exists)")
        enriched = json.loads(enriched_path.read_text(encoding="utf-8"))["warnings"]
    else:
        enriched = phase_6b_retrieve(warnings, enriched_path)
    audit["phases"]["6b"] = {"duration_s": round(time.time()-t0, 1)}

    # Phase 7
    t0 = time.time()
    fix_results = phase_7_generate(
        enriched, fixes_path, host=args.host, port=args.port
    )
    audit["phases"]["7"] = {
        "duration_s": round(time.time()-t0, 1),
        "fixes_generated": len(fix_results),
        "parse_errors": sum(1 for r in fix_results if r.get("parse_error")),
    }

    # Phase 8
    if not args.skip_eval:
        t0 = time.time()
        evaluated = phase_8_evaluate(
            fix_results, enriched, eval_path, host=args.host, port=args.port
        )
        audit["phases"]["8"] = {
            "duration_s": round(time.time()-t0, 1),
            "needs_manual_review": sum(1 for r in evaluated
                                       if r.get("needs_manual_review")),
            "fixes_corrected": sum(1 for r in evaluated
                                   for f in r.get("ranked_fixes", [])
                                   if f.get("was_corrected")),
        }
        final_results = evaluated
        final_path    = eval_path
    else:
        final_results = fix_results
        final_path    = fixes_path

    # Write audit
    total_time = round(time.time() - t_start, 1)
    audit["completed_at"]  = datetime.now().isoformat()
    audit["total_duration_s"] = total_time
    audit["final_output"]  = str(final_path)
    write_audit(run_id, run_dir, audit)

    print(f"\n{'='*60}")
    print(f"Pipeline complete — {total_time}s")
    print(f"  Warnings analysed : {len(warnings)}")
    print(f"  Output directory  : {run_dir}")
    print(f"  Final results     : {final_path.name}")
    print(f"  Audit log         : {AUDIT_DIR / (run_id + '_audit.json')}")
    print(f"{'='*60}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())