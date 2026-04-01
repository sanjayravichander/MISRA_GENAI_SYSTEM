#!/usr/bin/env python3
"""
evaluate_fixes.py  —  Phase 8: Self-critique evaluator for MISRA fix suggestions.

Runs fully offline via llama-cpp Python bindings (same runtime as Phase 7).
No HTTP server required. No data leaves the process.

For each generated fix suggestion, this module:

  1. Sends the fix + exact MISRA rule text back to the LLM
  2. Asks: does this fix actually resolve the violation per the rule?
  3. Asks: does the fix introduce any NEW MISRA violations?
  4. Asks: is the code_change syntactically valid C?
  5. Assigns a confidence score: High / Medium / Low
  6. If confidence is Low or fix is wrong: generates a corrected fix
  7. Flags low-confidence fixes for manual review in the final report

Why self-critique works
-----------------------
The generation prompt focuses on producing fixes quickly.
The evaluation prompt focuses on a single question: "is this correct?"
The LLM performs better at verification than generation because:
  - It only has to judge one thing at a time
  - The MISRA rule text is explicitly re-provided
  - It has the source code for context

Usage
-----
  from app.pipeline.evaluate_fixes import evaluate_all
  evaluated = evaluate_all(fix_results, enriched_warnings)
"""

from __future__ import annotations

import json
import re
import sys
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path for settings import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from app.config.settings import (
    LOCAL_MODEL_PATH,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS_EVAL,
    MAX_KB_CHARS_EVAL,
    LOW_CONFIDENCE_THRESHOLD,
)
from app.generation.generate_misra_response import GenerationConfig, LocalLlamaRuntime
from app.pipeline.result_cache import ResultCache, CACHE_PATH

# ---------------------------------------------------------------------------
# Evaluator config — reuses same GenerationConfig dataclass as Phase 7
# ---------------------------------------------------------------------------

def _get_eval_config() -> GenerationConfig:
    """Build GenerationConfig for the evaluator."""
    return GenerationConfig(
        model_path=LOCAL_MODEL_PATH,
        n_ctx=8192,
        n_threads=8,
        n_gpu_layers=0,
        temperature=LLM_TEMPERATURE,
        top_p=1.0,
        top_k=1,
        repeat_penalty=1.0,
        seed=42,
        max_tokens=LLM_MAX_TOKENS_EVAL,
        prompt_version="misra_eval_v1",
    )


# ---------------------------------------------------------------------------
# Evaluator system prompt
# ---------------------------------------------------------------------------

EVALUATOR_SYSTEM_PROMPT = """You are a MISRA C 2012 compliance auditor reviewing AI-generated fix suggestions.

For each fix, check all five gates:
Gate 1 — Does AFTER code fully eliminate the flagged violation per the exact rule text?
Gate 2 — Does AFTER code introduce any new MISRA C 2012 violation?
Gate 3 — Is AFTER code real compilable C? (no comments-as-code, no undefined functions, correct types)
Gate 4 — Does the fix avoid introducing overflow, undefined behaviour, or unintended logic changes?
Gate 5 — Does the approach match what the MISRA C 2012 guideline recommends?

Confidence scoring:
- High:   All five gates pass with certainty.
- Medium: Gates 1,3,5 pass; Gate 2 or 4 has one minor assumption about unseen code.
- Low:    Any gate fails — mark is_correct: false and explain in issues_found.

Output ONLY valid JSON. No prose. No markdown outside JSON.

{
  "warning_id": "string",
  "rule_id": "string",
  "overall_confidence": "High|Medium|Low",
  "needs_manual_review": true|false,
  "evaluated_fixes": [
    {
      "rank": 1,
      "is_correct": true|false,
      "confidence": "High|Medium|Low",
      "gates_failed": [],
      "issues_found": [],
      "corrected_code_change": "BEFORE:\n...\nAFTER:\n... (only if is_correct is false, else empty string)"
    }
  ],
  "evaluator_notes": "string — one sentence overall verdict"
}"""


# ---------------------------------------------------------------------------
# Prompt builder for evaluation
# ---------------------------------------------------------------------------

def build_eval_prompt(
    warning: Dict[str, Any],
    fix_result: Dict[str, Any],
) -> str:
    """
    Build the evaluator prompt.
    Provides: original warning + source code + MISRA rule text + fixes to evaluate.
    """
    # Source context
    ctx = warning.get("source_context", {})
    if isinstance(ctx, dict):
        src_text = ctx.get("context_text", "[source not available]")
    else:
        src_text = str(ctx) if ctx else "[source not available]"
    src_lines = src_text.splitlines()[:20]  # cap to keep prompt short
    src_text  = "\n".join(src_lines)

    # MISRA KB context — prioritise rationale and amplification
    kb_chunks = warning.get("misra_context", [])
    kb_parts: List[str] = []
    kb_chars = 0
    max_kb   = min(MAX_KB_CHARS_EVAL, 3000)

    for section_prio in ["rationale", "amplification", "body_text", "exception", "example"]:
        chunk = next(
            (c for c in kb_chunks
             if c.get("section") == section_prio
             and c.get("guideline_id") == warning.get("rule_id")),
            None,
        )
        if not chunk:
            # Also try chunk_type field (Excel KB chunks use chunk_type not section)
            chunk = next(
                (c for c in kb_chunks
                 if c.get("chunk_type") == section_prio
                 and c.get("guideline_id") == warning.get("rule_id")),
                None,
            )
        if not chunk:
            continue
        text   = chunk.get("text", "")
        header = section_prio.replace("_", " ").title()
        entry  = f"[MISRA {chunk.get('guideline_id')} — {header}]\n{text}"
        if kb_chars + len(entry) > max_kb:
            break
        kb_parts.append(entry)
        kb_chars += len(entry)

    # Fallback: if section-based lookup found nothing, use top chunks directly
    if not kb_parts and kb_chunks:
        for chunk in kb_chunks[:3]:
            text  = chunk.get("text", "")
            entry = f"[MISRA {chunk.get('guideline_id', '')} — {chunk.get('chunk_type', '')}]\n{text}"
            if kb_chars + len(entry) > max_kb:
                break
            kb_parts.append(entry)
            kb_chars += len(entry)

    kb_text = "\n\n".join(kb_parts) if kb_parts else "[MISRA context not available]"

    # Format the fixes to evaluate — support both old ranked_fixes and new fix_suggestions schema
    fixes_to_eval = fix_result.get("fix_suggestions", fix_result.get("ranked_fixes", []))
    fixes_text_parts = []
    for fix in fixes_to_eval:
        # New schema: title, why, patched_code, compliance_notes, risk_reduction
        # Old schema: description, code_change, risk_level
        title       = fix.get("title", fix.get("description", ""))
        code        = fix.get("patched_code", fix.get("code_change", ""))
        why         = fix.get("why", "")
        compliance  = fix.get("compliance_notes", "")
        risk        = fix.get("risk_reduction", fix.get("risk_level", ""))
        fixes_text_parts.append(
            f"Fix [{fix.get('rank')}]: {title}\n"
            f"Why: {why}\n"
            f"Patched code: {code}\n"
            f"Compliance: {compliance}\n"
            f"Risk reduction: {risk}"
        )
    fixes_text = "\n\n".join(fixes_text_parts) if fixes_text_parts else "[no fixes to evaluate]"

    # Trim explanation to avoid bloating the prompt
    explanation = str(fix_result.get("explanation", "") or "")[:300]

    return (
        f"Evaluate MISRA fixes. Warning {warning.get('warning_id')} "
        f"Rule {warning.get('rule_id')}: {warning.get('message', '')}\n"
        f"File: {warning.get('file_path', '')} Line {warning.get('line_start', '')}\n\n"
        f"SOURCE (flagged >>>):\n{src_text}\n\n"
        f"MISRA RULE TEXT:\n{kb_text}\n\n"
        f"FIXES TO EVALUATE:\n{fixes_text}\n\n"
        f"EXPLANATION: {explanation}\n\n"
        f"Output ONLY the JSON schema from the system prompt."
    )


# ---------------------------------------------------------------------------
# LLM caller — llama-cpp bindings (fully offline, no HTTP)
# ---------------------------------------------------------------------------

def call_llm_local(
    system_prompt: str,
    user_prompt: str,
    config: Optional[GenerationConfig] = None,
) -> str:
    """
    Call the local Mistral model via llama-cpp Python bindings.
    Reuses the same singleton runtime as Phase 7 — no second model load.
    """
    if config is None:
        config = _get_eval_config()

    runtime = LocalLlamaRuntime.get_instance(config)
    llm     = runtime.llm

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]

    response = llm.create_chat_completion(
        messages=messages,
        temperature=config.temperature,
        top_p=config.top_p,
        top_k=config.top_k,
        repeat_penalty=config.repeat_penalty,
        max_tokens=config.max_tokens,
        seed=config.seed,
    )

    return response["choices"][0]["message"]["content"].strip()


# ---------------------------------------------------------------------------
# Legacy HTTP caller — kept for backward compatibility, logs a warning
# ---------------------------------------------------------------------------

def call_llm(host: str, port: int, system_prompt: str, user_prompt: str) -> str:
    """
    Legacy HTTP caller — now delegates to call_llm_local.
    Kept so server.py Phase 8 imports don't break.
    host and port parameters are ignored.
    """
    return call_llm_local(system_prompt, user_prompt)


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------

def _repair_json(text: str) -> str:
    """Best-effort repair of truncated/slightly-broken LLM JSON."""
    text = re.sub(r",\s*([}\]])", r"\1", text)
    depth_sq = text.count("[") - text.count("]")
    depth_cu = text.count("{") - text.count("}")
    stripped = re.sub(r'\\\\.', '', text)
    if stripped.count('"') % 2 == 1:
        text += '"'
    text += "]" * max(0, depth_sq)
    text += "}" * max(0, depth_cu)
    return text


def parse_eval_response(
    raw: str,
    warning_id: str,
    rule_id: str,
) -> Dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    cleaned = re.sub(r"```\s*$",          "", cleaned, flags=re.MULTILINE).strip()

    start = cleaned.find("{")
    end   = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        return _eval_fallback(warning_id, rule_id, "No JSON found")

    candidate = cleaned[start:end]

    try:
        result = json.loads(candidate)
    except json.JSONDecodeError:
        try:
            result = json.loads(_repair_json(candidate))
        except json.JSONDecodeError as e:
            conf_match   = re.search(r'"overall_confidence"\s*:\s*"(High|Medium|Low)"', candidate)
            review_match = re.search(r'"needs_manual_review"\s*:\s*(true|false)', candidate)
            notes_match  = re.search(r'"evaluator_notes"\s*:\s*"([^"]{0,300})', candidate)
            if conf_match:
                return {
                    "warning_id":          warning_id,
                    "rule_id":             rule_id,
                    "overall_confidence":  conf_match.group(1),
                    "needs_manual_review": review_match.group(1) == "true" if review_match else False,
                    "evaluated_fixes":     [],
                    "evaluator_notes":     notes_match.group(1) + "…" if notes_match else "Partial parse",
                    "eval_partial_parse":  True,
                }
            return _eval_fallback(warning_id, rule_id, str(e))

    result.setdefault("warning_id",         warning_id)
    result.setdefault("rule_id",            rule_id)
    result.setdefault("overall_confidence", "Medium")
    result.setdefault("needs_manual_review", False)
    result.setdefault("evaluated_fixes",    [])
    result.setdefault("evaluator_notes",    "")
    return result


def _eval_fallback(warning_id: str, rule_id: str, error: str) -> Dict[str, Any]:
    return {
        "warning_id":         warning_id,
        "rule_id":            rule_id,
        "overall_confidence": "Low",
        "needs_manual_review": True,
        "evaluated_fixes":    [],
        "evaluator_notes":    f"Evaluator error: {error}",
        "eval_parse_error":   True,
    }


# ---------------------------------------------------------------------------
# Merge: apply evaluation results back onto the original fix result
# ---------------------------------------------------------------------------

def merge_evaluation(
    fix_result: Dict[str, Any],
    eval_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge evaluation into the fix result.
    Supports both old schema (ranked_fixes) and new schema (fix_suggestions).
    """
    merged = deepcopy(fix_result)
    merged["evaluation"]          = eval_result
    merged["overall_confidence"]  = eval_result.get("overall_confidence", "Medium")
    merged["needs_manual_review"] = eval_result.get("needs_manual_review", False)
    merged["evaluator_notes"]     = eval_result.get("evaluator_notes", "")

    eval_fixes_by_rank = {
        ef.get("rank"): ef
        for ef in eval_result.get("evaluated_fixes", [])
    }

    # Support both fix_suggestions (new) and ranked_fixes (old)
    fix_key = "fix_suggestions" if "fix_suggestions" in merged else "ranked_fixes"
    updated_fixes = []

    for fix in merged.get(fix_key, []):
        rank    = fix.get("rank")
        ef      = eval_fixes_by_rank.get(rank, {})
        updated = deepcopy(fix)

        # Audit trail
        updated["original_patched_code"] = fix.get("patched_code", fix.get("code_change", ""))
        updated["original_title"]        = fix.get("title", fix.get("description", ""))
        updated["confidence"]            = ef.get("confidence", "Medium")
        updated["is_correct"]            = ef.get("is_correct", True)
        updated["issues_found"]          = ef.get("issues_found", [])

        # Apply correction if evaluator found issues
        corrected_code = ef.get("corrected_code_change", "").strip()
        if corrected_code:
            if fix_key == "fix_suggestions":
                updated["patched_code"] = corrected_code
            else:
                updated["code_change"]  = corrected_code
            updated["was_corrected"] = True

        updated_fixes.append(updated)

    # Re-sort: High confidence first, then Medium, then Low
    confidence_order = {"High": 0, "Medium": 1, "Low": 2}
    updated_fixes.sort(key=lambda f: (
        confidence_order.get(f.get("confidence", "Medium"), 1),
        f.get("rank", 99),
    ))
    for i, f in enumerate(updated_fixes, 1):
        f["rank"] = i

    merged[fix_key] = updated_fixes
    return merged


# ---------------------------------------------------------------------------
# Incremental save helper
# ---------------------------------------------------------------------------

def _save_incremental(evaluated: List[Dict[str, Any]], out_path: Path) -> None:
    try:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(
                {"warning_count": len(evaluated), "results": evaluated},
                indent=2, ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"  [WARNING] Incremental save failed: {e}")


# ---------------------------------------------------------------------------
# Main evaluation function
# ---------------------------------------------------------------------------

def evaluate_all(
    fix_results: List[Dict[str, Any]],
    enriched_warnings: List[Dict[str, Any]],
    host: str = "127.0.0.1",   # ignored — kept for API compatibility
    port: int = 8080,           # ignored — kept for API compatibility
    verbose: bool = True,
    out_path: Optional[Path] = None,
    config: Optional[GenerationConfig] = None,
    cache_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Run evaluation for all fix results using llama-cpp (fully offline).

    Phase 8 results are cached in SQLite (eval_cache table).
    On re-runs with identical warnings + fixes, evaluation is instant.

    Parameters
    ----------
    fix_results       : output of generate_misra_response (list of result dicts)
    enriched_warnings : output of retrieve_rules (list of warning dicts with misra_context)
    host, port        : ignored — kept for backward compatibility only
    verbose           : print progress
    out_path          : if provided, write results incrementally after each warning
    config            : GenerationConfig — if None, uses default eval config
    cache_path        : path to SQLite cache DB — if None, uses default CACHE_PATH
    """
    if config is None:
        config = _get_eval_config()

    warn_by_id = {w["warning_id"]: w for w in enriched_warnings}
    evaluated: List[Dict[str, Any]] = []

    cache = ResultCache(cache_path or CACHE_PATH)

    for i, fix_result in enumerate(fix_results, 1):
        wid  = fix_result.get("warning_id", f"W{i}")
        rule = fix_result.get("rule_id", "")

        # Skip parse errors
        if fix_result.get("parse_error"):
            if verbose:
                print(f"  [{i:2d}] {wid} {rule:12s} — SKIPPED (generation parse error)")
            evaluated.append({**fix_result, "evaluation_skipped": True,
                               "needs_manual_review": True})
            continue

        # Skip if no fixes
        fix_key = "fix_suggestions" if "fix_suggestions" in fix_result else "ranked_fixes"
        if not fix_result.get(fix_key):
            if verbose:
                print(f"  [{i:2d}] {wid} {rule:12s} — SKIPPED (no fixes to evaluate)")
            evaluated.append({**fix_result, "evaluation_skipped": True,
                               "needs_manual_review": True})
            continue

        warning = warn_by_id.get(wid)
        if not warning:
            if verbose:
                print(f"  [{i:2d}] {wid} {rule:12s} — SKIPPED (warning not found)")
            evaluated.append({**fix_result, "evaluation_skipped": True})
            continue

        # ── Source context string (used as part of cache key) ──────────
        ctx = warning.get("source_context", {})
        if isinstance(ctx, dict):
            source_ctx = ctx.get("context_text", "")
        else:
            source_ctx = str(ctx) if ctx else ""

        # ── Phase 8 cache check ────────────────────────────────────────
        cached_eval = cache.get_eval(rule, source_ctx, fix_result)
        if cached_eval is not None:
            merged = merge_evaluation(fix_result, cached_eval)
            merged["_eval_from_cache"] = True
            if verbose:
                conf   = merged.get("overall_confidence", "?")
                review = "⚠ REVIEW" if merged.get("needs_manual_review") else "✓"
                print(f"  [{i:2d}/{len(fix_results)}] {wid}  {rule:12s}"
                      f"  [EVAL CACHE] confidence={conf}  {review}")
                print(f"EVAL_DONE {wid}", flush=True)   # signals UI: phase 8 complete for this record
            evaluated.append(merged)
            if out_path is not None:
                _save_incremental(evaluated, out_path)
            continue

        # ── LLM evaluation call ────────────────────────────────────────
        if verbose:
            print(f"EVAL_PROGRESS [{i:2d}/{len(fix_results)}] Evaluating {wid}  {rule:12s} ...")

        t0 = time.time()
        try:
            prompt      = build_eval_prompt(warning, fix_result)
            raw         = call_llm_local(EVALUATOR_SYSTEM_PROMPT, prompt, config)
            eval_result = parse_eval_response(raw, wid, rule)

            # Store in cache before merging (cache pure eval, not merged result)
            if not eval_result.get("eval_parse_error"):
                cache.set_eval(rule, source_ctx, fix_result, eval_result)

            merged    = merge_evaluation(fix_result, eval_result)
            elapsed   = time.time() - t0
            conf      = merged.get("overall_confidence", "?")
            review    = "⚠ REVIEW" if merged.get("needs_manual_review") else "✓"
            fix_key2  = "fix_suggestions" if "fix_suggestions" in merged else "ranked_fixes"
            corrected = sum(1 for f in merged.get(fix_key2, []) if f.get("was_corrected"))

            if verbose:
                print(f"       confidence={conf}  corrected={corrected} fix(es)"
                      f"  {elapsed:.1f}s  {review}")
                print(f"EVAL_DONE {wid}", flush=True)   # signals UI: phase 8 complete for this record

            evaluated.append(merged)

            if out_path is not None:
                _save_incremental(evaluated, out_path)

        except Exception as e:
            if verbose:
                print(f"       ERROR: {e}")
                print(f"EVAL_DONE {wid}", flush=True)   # signal even on error so UI advances
            evaluated.append({**fix_result, "needs_manual_review": True,
                               "evaluator_notes": f"Evaluator error: {e}"})
            if out_path is not None:
                _save_incremental(evaluated, out_path)

    cache.close()
    return evaluated


# ---------------------------------------------------------------------------
# CLI entry point (for standalone testing)
# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: python evaluate_fixes.py"
              " <fix_suggestions.json> <enriched_warnings.json> <output.json>")
        return 2

    fix_path      = Path(sys.argv[1])
    enriched_path = Path(sys.argv[2])
    out_path      = Path(sys.argv[3])

    fix_data      = json.loads(fix_path.read_text(encoding="utf-8"))
    enriched_data = json.loads(enriched_path.read_text(encoding="utf-8"))

    fix_results       = fix_data.get("results", fix_data.get("warnings", []))
    enriched_warnings = enriched_data.get("warnings", [])

    print(f"Evaluating {len(fix_results)} fix results ...")
    evaluated = evaluate_all(fix_results, enriched_warnings)

    total     = len(evaluated)
    high      = sum(1 for r in evaluated if r.get("overall_confidence") == "High")
    medium    = sum(1 for r in evaluated if r.get("overall_confidence") == "Medium")
    low       = sum(1 for r in evaluated if r.get("overall_confidence") == "Low")
    review    = sum(1 for r in evaluated if r.get("needs_manual_review"))
    fix_key   = "fix_suggestions" if any("fix_suggestions" in r for r in evaluated) else "ranked_fixes"
    corrected = sum(1 for r in evaluated
                    for f in r.get(fix_key, []) if f.get("was_corrected"))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({
            "warning_count":      total,
            "confidence_high":    high,
            "confidence_medium":  medium,
            "confidence_low":     low,
            "needs_manual_review": review,
            "fixes_corrected":    corrected,
            "results":            evaluated,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nEvaluation complete:")
    print(f"  High confidence  : {high}")
    print(f"  Medium confidence: {medium}")
    print(f"  Low confidence   : {low}")
    print(f"  Manual review    : {review}")
    print(f"  Fixes corrected  : {corrected}")
    print(f"  Output: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())