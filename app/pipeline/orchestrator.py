#!/usr/bin/env python3
"""
orchestrator.py  —  Pipeline orchestrator: runs Phases 6a → 6b → 7 → 8.

Single entry point for a complete analysis run.

Phase 6a  parse_polyspace         : reads Excel report + C source files
Phase 6b  retrieve_rules          : Qdrant + BGE retrieval + postprocessing
Phase 7   generate_misra_response : llama-cpp generation + generic validation
Phase 8   evaluate_fixes          : self-critique evaluator

Usage
-----
  python orchestrator.py <excel_report.xlsx> <source_dir>
  python orchestrator.py <excel_report.xlsx> <source_dir> --run-id my_run
  python orchestrator.py <excel_report.xlsx> <source_dir> --resume 20240323_143000
  python orchestrator.py <excel_report.xlsx> <source_dir> --skip-eval
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# ── Force line-buffered stdout so server.py receives print() output immediately
# rather than waiting for the 8KB pipe buffer to fill (critical on Windows).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

from app.config.settings import (
    OUTPUT_DIR, AUDIT_DIR,
    LOCAL_MODEL_PATH,
    LLM_N_CTX,        # auto-detected from available RAM at startup
    LLM_N_THREADS,    # auto-detected from CPU cores at startup
    LLM_N_GPU_LAYERS, # auto-detected: 33 if CUDA GPU found, else 0
    LLM_MAX_TOKENS,
)


# ---------------------------------------------------------------------------
# Phase 6a — Parse Polyspace report
# ---------------------------------------------------------------------------

def phase_6a_parse(
    xlsx_path: Path,
    source_dir: Path,
    out_path: Path,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    if verbose:
        print(f"\n{'─'*60}", flush=True)
        print(f"Phase 6a — Parsing Polyspace report", flush=True)
        print(f"  Excel  : {xlsx_path}", flush=True)
        print(f"  Sources: {source_dir}", flush=True)

    from app.ingestion.parse_polyspace import parse_report
    warnings = parse_report(xlsx_path, source_dir)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"warning_count": len(warnings), "warnings": warnings},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    if verbose:
        sev: Dict[str, int] = {}
        for w in warnings:
            s = w.get("severity", "Unknown")
            sev[s] = sev.get(s, 0) + 1
        print(f"  Parsed {len(warnings)} warnings — {sev}", flush=True)
    return warnings


# ---------------------------------------------------------------------------
# Phase 6b — Qdrant retrieval + postprocessing
# ---------------------------------------------------------------------------

def phase_6b_retrieve(
    warnings: List[Dict[str, Any]],
    out_path: Path,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    if verbose:
        print(f"\n{'─'*60}", flush=True)
        print(f"Phase 6b — Retrieving MISRA context (Qdrant + BGE)", flush=True)

    from app.retrieval.retrieve_rules import retrieve_rules
    from app.retrieval.retrieval_postprocessor import postprocess_retrieved_rules

    enriched: List[Dict[str, Any]] = []

    for w in warnings:
        try:
            retrieved   = retrieve_rules(w)
            clean_rules = postprocess_retrieved_rules(retrieved)
        except Exception as exc:
            clean_rules = []
            if verbose:
                print(f"  ERROR retrieving {w.get('warning_id')}: {exc}", flush=True)

        enriched.append({**w, "misra_context": clean_rules})

        if verbose:
            print(
                f"  {w.get('warning_id','?'):8s}  "
                f"{w.get('rule_id',''):12s}  "
                f"{len(clean_rules)} rule(s) retrieved"
            , flush=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"warning_count": len(enriched), "warnings": enriched},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return enriched


# ---------------------------------------------------------------------------
# Phase 7 — Generation via llama-cpp + generic validation
# ---------------------------------------------------------------------------

def phase_7_generate(
    enriched: List[Dict[str, Any]],
    out_path: Path,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    if verbose:
        print(f"\n{'─'*60}", flush=True)
        print(f"Phase 7 — Generating fix suggestions (llama-cpp)", flush=True)
        print(f"  Model : {LOCAL_MODEL_PATH}", flush=True)
        print(f"  Warnings: {len(enriched)}", flush=True)

    from app.generation.generate_misra_response import (
        GenerationConfig,
        generate_misra_response,
    )

    config = GenerationConfig(
        model_path    = LOCAL_MODEL_PATH,
        n_ctx         = LLM_N_CTX,          # auto-detected from RAM at startup
        n_threads     = LLM_N_THREADS,      # auto-detected from CPU cores at startup
        n_gpu_layers  = LLM_N_GPU_LAYERS,   # auto-detected: 33 if CUDA GPU, else 0
        temperature   = 0.0,
        top_p         = 1.0,
        top_k         = 1,
        repeat_penalty= 1.0,
        seed          = 42,
        max_tokens    = LLM_MAX_TOKENS,     # 3500 tokens — enough for full MISRA response
        prompt_version= "misra_generation_v1",
    )

    results: List[Dict[str, Any]] = []

    # Resume: load already-completed results
    existing_ids: set = set()
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            for r in existing.get("results", []):
                if not r.get("parse_error"):
                    results.append(r)
                    existing_ids.add(r.get("warning_id"))
            if verbose and existing_ids:
                print(f"  Resuming: {len(existing_ids)} already done", flush=True)
        except Exception:
            pass

    for i, w in enumerate(enriched, 1):
        wid = w.get("warning_id", f"W{i}")

        if wid in existing_ids:
            if verbose:
                print(f"  [{i:2d}/{len(enriched)}] {wid} — skipped (done)", flush=True)
            continue

        if verbose:
            print(
                f"  [{i:2d}/{len(enriched)}] {wid}  "
                f"{w.get('rule_id',''):12s}  "
                f"{w.get('severity',''):6s}  "
                f"{w.get('file_path','')}:{w.get('line_start','')}"
            , flush=True)

        t0 = time.time()
        try:
            bundle = generate_misra_response(
                rule_id=w.get("rule_id", ""),
                warning_message=w.get("message", ""),
                code_snippet=w.get("source_context", {}).get("context_text", ""),
                checker_name=w.get("checker_name", ""),
                config=config,
                top_k=5,
            )
            result            = bundle.get("result", {})
            result["warning_id"] = wid
            result["source"]     = bundle.get("source", "generation")
            # Mark cache hits so the UI/summary can show them
            if bundle.get("source") == "final_cache":
                result["_from_cache"] = True

        except Exception as exc:
            result = {
                "warning_id":    wid,
                "rule_id":       w.get("rule_id", ""),
                "fix_suggestions": [],
                "parse_error":   True,
                "explanation":   {"summary": str(exc)},
            }

        elapsed = time.time() - t0
        n_fixes = len(result.get("fix_suggestions", []))
        status  = "✓" if not result.get("parse_error") else "✗"

        cached_tag = " [cache]" if result.get("_from_cache") else ""
        if verbose:
            print(f"       {n_fixes} fix(es)  {elapsed:.1f}s  {status}{cached_tag}", flush=True)

        results.append(result)

        # Save incrementally so nothing is lost on crash/timeout
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps({"warning_count": len(results), "results": results},
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return results


# ---------------------------------------------------------------------------
# Phase 8 — Self-critique evaluator
# ---------------------------------------------------------------------------

def phase_8_evaluate(
    fix_results: List[Dict[str, Any]],
    enriched: List[Dict[str, Any]],
    out_path: Path,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    if verbose:
        print(f"\n{'─'*60}", flush=True)
        print(f"Phase 8 — Evaluating fix suggestions (self-critique)", flush=True)

    from app.pipeline.evaluate_fixes import evaluate_all

    evaluated = evaluate_all(
        fix_results, enriched,
        verbose=verbose,
        out_path=out_path,
    )

    high   = sum(1 for r in evaluated if r.get("overall_confidence") == "High")
    medium = sum(1 for r in evaluated if r.get("overall_confidence") == "Medium")
    low    = sum(1 for r in evaluated if r.get("overall_confidence") == "Low")
    review = sum(1 for r in evaluated if r.get("needs_manual_review"))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({
            "warning_count": len(evaluated),
            "confidence_high": high, "confidence_medium": medium,
            "confidence_low": low,  "needs_manual_review": review,
            "results": evaluated,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if verbose:
        print(f"\n  Confidence: High={high} Medium={medium} Low={low}", flush=True)
        print(f"  Manual review flagged: {review}", flush=True)

    return evaluated


# ---------------------------------------------------------------------------
# Audit logger
# ---------------------------------------------------------------------------

def write_audit(run_id: str, meta: Dict[str, Any]) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    (AUDIT_DIR / f"{run_id}_audit.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="MISRA Compliance pipeline orchestrator (Phases 6a–8)"
    )
    parser.add_argument("excel_report", type=Path)
    parser.add_argument("source_dir",   type=Path)
    parser.add_argument("--run-id",     default=None)
    parser.add_argument("--resume",     default=None, metavar="RUN_ID")
    parser.add_argument("--skip-eval",  action="store_true")
    # --misra-categories kept for CLI compatibility but ignored — filtering
    # is now done client-side on the results page using the KB rule_type field
    parser.add_argument("--misra-categories", default=None, metavar="CATS",
                        help="(ignored — filtering is done on the results page)")
    args = parser.parse_args()

    run_id  = args.resume or args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = OUTPUT_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"{'='*60}", flush=True)
    print(f"SRM Technologies — MISRA Compliance Analysis", flush=True)
    print(f"Run ID : {run_id}", flush=True)
    print(f"Output : {run_dir}", flush=True)
    print(f"{'='*60}", flush=True)

    if not args.excel_report.exists():
        print(f"ERROR: Warning report not found: {args.excel_report}", flush=True)
        return 1
    if not args.source_dir.exists():
        print(f"ERROR: Source directory not found: {args.source_dir}", flush=True)
        return 1

    # Validate Qdrant index exists
    from app.config.settings import QDRANT_INDEX_DIR
    if not QDRANT_INDEX_DIR.exists():
        print(f"ERROR: Knowledge index not found at {QDRANT_INDEX_DIR}", flush=True)
        print(f"  Please run scripts/build_qdrant_index.py first.", flush=True)
        return 1

    t_start = time.time()
    audit: Dict[str, Any] = {
        "run_id":       run_id,
        "excel_report": str(args.excel_report),
        "source_dir":   str(args.source_dir),
        "started_at":   datetime.now().isoformat(),
        "phases": {},
    }

    parsed_path   = run_dir / "parsed_warnings.json"
    enriched_path = run_dir / "enriched_warnings.json"
    fixes_path    = run_dir / "fix_suggestions.json"
    eval_path     = run_dir / "evaluated_fixes.json"

    # Phase 6a
    t0 = time.time()
    if args.resume and parsed_path.exists():
        print(f"\nPhase 6a — Skipped (resuming)", flush=True)
        warnings = json.loads(parsed_path.read_text(encoding="utf-8"))["warnings"]
    else:
        warnings = phase_6a_parse(args.excel_report, args.source_dir, parsed_path)
    audit["phases"]["6a"] = {"duration_s": round(time.time()-t0, 1), "warnings": len(warnings)}

    # Phase 6b
    t0 = time.time()
    if args.resume and enriched_path.exists():
        print(f"\nPhase 6b — Skipped (resuming)", flush=True)
        enriched = json.loads(enriched_path.read_text(encoding="utf-8"))["warnings"]
    else:
        enriched = phase_6b_retrieve(warnings, enriched_path)
    audit["phases"]["6b"] = {"duration_s": round(time.time()-t0, 1)}

    # Phase 7
    t0 = time.time()
    fix_results = phase_7_generate(enriched, fixes_path)
    audit["phases"]["7"] = {
        "duration_s":      round(time.time()-t0, 1),
        "fixes_generated": len(fix_results),
        "parse_errors":    sum(1 for r in fix_results if r.get("parse_error")),
    }

    # Phase 8
    if not args.skip_eval:
        t0 = time.time()
        evaluated = phase_8_evaluate(fix_results, enriched, eval_path)
        audit["phases"]["8"] = {"duration_s": round(time.time()-t0, 1)}
        final_results = evaluated
        final_path    = eval_path
    else:
        final_results = fix_results
        final_path    = fixes_path

    total_time = round(time.time() - t_start, 1)
    audit["completed_at"]    = datetime.now().isoformat()
    audit["total_duration_s"] = total_time
    audit["final_output"]    = str(final_path)
    write_audit(run_id, audit)

    print(f"\n{'='*60}", flush=True)
    print(f"Pipeline complete — {total_time}s", flush=True)
    print(f"  Warnings analysed : {len(warnings)}", flush=True)
    print(f"  Output directory  : {run_dir}", flush=True)
    print(f"  Final results     : {final_path.name}", flush=True)
    print(f"{'='*60}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())