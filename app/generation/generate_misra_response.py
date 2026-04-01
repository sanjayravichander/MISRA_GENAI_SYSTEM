from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from llama_cpp import Llama

from app.generation.response_validator import filter_and_validate_response
from app.retrieval.retrieve_rules import retrieve_with_cache
from app.retrieval.cache_service import (
    build_cache_key,
    get_cache_record,
    normalize_retrieval_input,
    store_final_result,
)

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class GenerationConfig:
    model_path: str
    n_ctx: int = 8192
    n_threads: int = 8
    n_gpu_layers: int = 0
    temperature: float = 0.0
    top_p: float = 1.0
    top_k: int = 1
    repeat_penalty: float = 1.0
    seed: int = 42
    max_tokens: int = 4000
    stop: Tuple[str, ...] = ("</json>",)
    prompt_version: str = "misra_generation_v1"


class LocalLlamaRuntime:
    _instance: Optional["LocalLlamaRuntime"] = None
    _instance_signature: Optional[str] = None

    def __init__(self, config: GenerationConfig) -> None:
        model_file = Path(config.model_path)
        if not model_file.exists():
            raise FileNotFoundError(f"Local model file not found: {model_file}")

        self.config = config
        self.llm = Llama(
            model_path=str(model_file),
            n_ctx=config.n_ctx,
            n_threads=config.n_threads,
            n_gpu_layers=config.n_gpu_layers,
            verbose=False,
            seed=config.seed,
        )

    @classmethod
    def get_instance(cls, config: GenerationConfig) -> "LocalLlamaRuntime":
        signature = json.dumps(
            {
                "model_path": config.model_path,
                "n_ctx": config.n_ctx,
                "n_threads": config.n_threads,
                "n_gpu_layers": config.n_gpu_layers,
                "seed": config.seed,
            },
            sort_keys=True,
        )
        if cls._instance is None or cls._instance_signature != signature:
            cls._instance = cls(config)
            cls._instance_signature = signature
        return cls._instance


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _compact_text(value: Any) -> str:
    return re.sub(r"\s+", " ", _safe_text(value)).strip()


def _hash_generation_signature(config: GenerationConfig) -> str:
    # NOTE: max_tokens and n_ctx intentionally excluded — changing the token
    # budget does not change the generation outcome for already-cached results.
    # Including them would bust the cache every time settings are tuned.
    raw = json.dumps(
        {
            "model_path": config.model_path,
            "prompt_version": config.prompt_version,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "top_k": config.top_k,
            "repeat_penalty": config.repeat_penalty,
            "seed": config.seed,
        },
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _extract_json_block(text: str) -> str:
    """Extract and clean a JSON object from raw LLM output.

    Handles common LLM quirks:
    - Markdown code fences (```json ... ```)
    - Trailing commas before } or ]  (common LLM mistake)
    - Truncated output (finds deepest balanced brace)
    - Stray text before/after the JSON object
    """
    # Strip markdown fences
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = re.sub(r"```\s*$", "", text).strip()

    start = text.find("{")
    if start == -1:
        raise ValueError(f"Model output contains no JSON object. Raw: {text[:300]}")

    # Walk forward tracking brace depth to find the balanced closing }
    depth = 0
    end = -1
    in_string = False
    escape_next = False
    for i, ch in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break

    if end == -1:
        # Truncated output — attempt to close all open braces/brackets
        partial = text[start:]
        partial = re.sub(r",\s*$", "", partial.rstrip())  # strip trailing comma
        # Count unclosed braces and brackets
        depth_brace = 0
        depth_bracket = 0
        in_str = False
        esc = False
        for ch in partial:
            if esc: esc = False; continue
            if ch == "\\" and in_str: esc = True; continue
            if ch == '"': in_str = not in_str; continue
            if in_str: continue
            if ch == "{": depth_brace += 1
            elif ch == "}": depth_brace -= 1
            elif ch == "[": depth_bracket += 1
            elif ch == "]": depth_bracket -= 1
        # Close any open strings, brackets, then braces
        closing = ""
        if in_str: closing += '"'
        closing += "]" * max(0, depth_bracket)
        closing += "}" * max(0, depth_brace)
        json_text = partial + closing
    else:
        json_text = text[start:end + 1]

    # Remove trailing commas before } or ] (very common LLM mistake)
    json_text = re.sub(r",\s*([}\]])", r"\1", json_text)
    return json_text


def _chunk_score(chunk: Dict[str, Any]) -> float:
    try:
        return float(chunk.get("reranked_score", chunk.get("score", 0.0)))
    except Exception:
        return 0.0


def _chunk_raw_score(chunk: Dict[str, Any]) -> float:
    try:
        return float(chunk.get("raw_score", chunk.get("score", 0.0)))
    except Exception:
        return 0.0


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _prepare_authoritative_context(retrieval_result: Dict[str, Any]) -> Dict[str, Any]:
    chunks = retrieval_result.get("matches") or retrieval_result.get("results") or []
    if not isinstance(chunks, list):
        chunks = []

    chunks = sorted(chunks, key=_chunk_score, reverse=True)

    top_chunk = chunks[0] if chunks else {}
    top_guideline_id = _safe_text(top_chunk.get("guideline_id"))
    top_score = _chunk_score(top_chunk)
    top_raw_score = _chunk_raw_score(top_chunk)

    grouped: Dict[str, List[Dict[str, Any]]] = {
        "rule_core": [],
        "rationale": [],
        "amplification": [],
        "exception": [],
        "violated_example": [],
        "body_text": [],
        "other": [],
    }

    for chunk in chunks:
        ctype = _safe_text(chunk.get("chunk_type")).lower()
        if ctype in grouped:
            grouped[ctype].append(chunk)
        else:
            grouped["other"].append(chunk)

    def as_prompt_items(chunk_list: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        items = []
        for chunk in chunk_list[:limit]:
            payload = chunk.get("payload", {}) if isinstance(chunk.get("payload"), dict) else {}
            items.append(
                {
                    "chunk_id": _safe_text(chunk.get("id") or payload.get("chunk_id")),
                    "guideline_id": _safe_text(chunk.get("guideline_id") or payload.get("rule_id")),
                    "chunk_type": _safe_text(chunk.get("chunk_type") or payload.get("chunk_type")),
                    "title": _safe_text(chunk.get("title") or payload.get("rule_statement")),
                    "score": round(_chunk_score(chunk), 6),
                    "raw_score": round(_chunk_raw_score(chunk), 6),
                    "text": _safe_text(chunk.get("text") or payload.get("text")),
                }
            )
        return items

    prompt_context = {
        "top_guideline_id": top_guideline_id,
        "top_score": round(top_score, 6),
        "top_raw_score": round(top_raw_score, 6),
        "rule_core": as_prompt_items(grouped["rule_core"], 2),
        "rationale": as_prompt_items(grouped["rationale"], 2),
        "amplification": as_prompt_items(grouped["amplification"], 2),
        "exception": as_prompt_items(grouped["exception"], 2),
        "violated_example": as_prompt_items(grouped["violated_example"], 2),
        "body_text": as_prompt_items(grouped["body_text"], 2),
    }

    trace_chunk_ids = []
    for category in ("rule_core", "rationale", "amplification", "exception", "violated_example", "body_text"):
        for item in prompt_context[category]:
            if item["chunk_id"]:
                trace_chunk_ids.append(item["chunk_id"])

    prompt_context["trace_chunk_ids"] = _dedupe_keep_order(trace_chunk_ids)
    return prompt_context


def _build_system_prompt() -> str:
    return """
You are an offline MISRA C:2012 analysis engine. Your primary job is to produce
at least one valid, compilable fix suggestion for every warning you analyse.

Core rules:
1. Use ONLY the provided warning details, source code snippet, and retrieved MISRA context.
2. Do NOT invent MISRA rule text, rationale, exceptions, or examples.
3. If evidence is missing, say "insufficient evidence from retrieved context".
4. Output STRICT JSON only. No markdown, no prose outside the JSON.
5. Fix suggestions must be conservative, minimal, and MISRA-compliant.
6. You MUST always produce at least one fix_suggestion unless the code snippet
   is completely absent or the warning is not actionable.

Patch quality rules (your patches are validated — follow these exactly):
- Do NOT introduce variable-length arrays. Example of what NOT to do: uint8_t buf[n];
  Array accesses like data[i] are fine — only declarations with non-constant bounds are forbidden.
- Do NOT introduce numeric literals that do not already appear in the original code
  UNLESS the literal is a well-known type-width constant (e.g. 8 for uint8_t, 16 for uint16_t,
  32 for uint32_t) and is directly required by the MISRA rule being fixed.
  For Rule 12.2 (shift range), you MAY use the type-width literal as a bound check.
- Do NOT introduce pointer casts: (int*), (void*), (char*).
- Do NOT remove 'extern' and add an initialiser unless the context explicitly requires it.
- Local helper variables (e.g. a local copy of a parameter) are ALLOWED and encouraged
  for rules like 17.8 where the fix is to avoid modifying the parameter directly.

Fix strategy by rule family:
- Rule 17.x (function params): Use a local copy of the parameter instead of modifying it.
- Rule 10.x / 12.x (shift / type): Add a range guard using the type width as the bound.
- Rule 14.x (control flow): Restructure the branch; do not add new variables.
- Rule 15.x (switch): Add explicit default or break; minimal change only.
- Rule 11.x (pointer): Remove the cast; use the correct type directly.
""".strip()


def _build_user_prompt(warning_input: Dict[str, Any], prompt_context: Dict[str, Any]) -> str:
    schema = {
        "guideline_id": "string",
        "guideline_title": "string",
        "explanation": {
            "summary": "string",
            "rule_basis": "string",
            "code_evidence": "string"
        },
        "fix_suggestions": [
            {
                "rank": 1,
                "title": "string",
                "why": "string",
                "patched_code": "string",
                "compliance_notes": "string",
                "risk_reduction": "string"
            }
        ],
        "risk_analysis": {
            "severity": "Low | Medium | High | Critical | Unknown",
            "why": "string",
            "potential_failures": ["string"],
            "runtime_risk": "string",
            "maintainability_risk": "string"
        },
        "deviation_advice": {
            "deviation_possible": "Yes | No | Conditional | Unknown",
            "recommended_decision": "string",
            "required_justification": "string",
            "review_notes": "string"
        },
        "traceability": {
            "retrieved_chunk_ids": ["string"],
            "retrieval_score_raw": 0.0,
            "retrieval_score_reranked": 0.0,
            "confidence": 0.0,
            "limitations": ["string"]
        }
    }

    import re as _re
    original_nums = set(_re.findall(r"\b\d+\b", warning_input.get("code_snippet", "")))
    original_idents = set(_re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", warning_input.get("code_snippet", "")))

    return f"""
Produce one STRICT JSON object matching this schema exactly:

{json.dumps(schema, indent=2)}

Input warning:
{json.dumps(warning_input, indent=2)}

Retrieved MISRA context:
{json.dumps(prompt_context, indent=2)[:6000]}

=== ORIGINAL CODE TOKEN INVENTORY ===
Numeric literals already in original: {sorted(original_nums)}
Identifiers already in original: {sorted(original_idents)}
(You may use any of these freely in patched_code without triggering validator warnings.)

=== PATCH CONSTRAINTS — READ CAREFULLY ===
Your patched_code will be validated. It will be REJECTED if it:
  1. Contains a VLA declaration: e.g. uint8_t buf[n]; — array accesses like data[i] are FINE.
  2. Introduces a numeric literal NOT in the original list above, UNLESS it is the type-width
     constant strictly required by this rule (e.g. 8 for uint8_t shift bounds in Rule 12.2).
  3. Contains a pointer cast: (int*), (void*), (char*), (uint8_t*).
  4. Converts an extern declaration into a definition.

=== MANDATORY FIX REQUIREMENT ===
You MUST produce at least one fix_suggestion with valid patched_code.
If the only safe fix is adding a comment or const qualifier, do that.
An empty fix_suggestions array is NOT acceptable.

=== INSTRUCTIONS ===
- guideline_id must align to the strongest retrieved guideline when supported by evidence.
- guideline_title must come only from retrieved context if available.
- Generate 1-4 ranked fix_suggestions covering different remediation approaches from the context.
- Prefer the smallest, most local patch that achieves compliance.
- For Rule 17.x: use a local copy variable (it is in the original identifiers list if it exists,
  or use a short name like 'val' which is <= 3 chars and always allowed).
- For Rule 12.x / 10.x shift issues: add a range guard using the type-width constant.
- Do not convert a declaration into a definition unless required.
- If warning and retrieved rule are inconsistent, note it in traceability.limitations.
- Return JSON only. No markdown.
""".strip()


def _validate_and_normalize_output(
    raw_output: Dict[str, Any],
    prompt_context: Dict[str, Any],
    warning_input: Dict[str, Any],
) -> Dict[str, Any]:
    top_guideline_id = _safe_text(prompt_context.get("top_guideline_id"))
    top_score = float(prompt_context.get("top_score", 0.0))
    top_raw_score = float(prompt_context.get("top_raw_score", 0.0))
    trace_ids = prompt_context.get("trace_chunk_ids", [])
    if not isinstance(trace_ids, list):
        trace_ids = []

    result: Dict[str, Any] = {
        "guideline_id": _safe_text(raw_output.get("guideline_id")) or top_guideline_id or _safe_text(warning_input.get("rule_id")),
        "guideline_title": _safe_text(raw_output.get("guideline_title")) or "insufficient evidence from retrieved context",
        "explanation": raw_output.get("explanation") if isinstance(raw_output.get("explanation"), dict) else {},
        "fix_suggestions": raw_output.get("fix_suggestions") if isinstance(raw_output.get("fix_suggestions"), list) else [],
        "risk_analysis": raw_output.get("risk_analysis") if isinstance(raw_output.get("risk_analysis"), dict) else {},
        "deviation_advice": raw_output.get("deviation_advice") if isinstance(raw_output.get("deviation_advice"), dict) else {},
        "traceability": raw_output.get("traceability") if isinstance(raw_output.get("traceability"), dict) else {},
    }

    if top_guideline_id:
        result["guideline_id"] = top_guideline_id

    explanation = result["explanation"]
    result["explanation"] = {
        "summary": _safe_text(explanation.get("summary")) or "insufficient evidence from retrieved context",
        "rule_basis": _safe_text(explanation.get("rule_basis")) or "insufficient evidence from retrieved context",
        "code_evidence": _safe_text(explanation.get("code_evidence")) or _compact_text(warning_input.get("code_snippet")),
    }

    validated_fixes = []
    for item in result["fix_suggestions"]:
        if not isinstance(item, dict):
            continue
        title = _safe_text(item.get("title"))
        if not title:
            continue
        validated_fixes.append(
            {
                "rank": len(validated_fixes) + 1,
                "title": title,
                "why": _safe_text(item.get("why")) or "insufficient evidence from retrieved context",
                "patched_code": _safe_text(item.get("patched_code")) or "insufficient evidence from retrieved context",
                "compliance_notes": _safe_text(item.get("compliance_notes")) or "insufficient evidence from retrieved context",
                "risk_reduction": _safe_text(item.get("risk_reduction")) or "insufficient evidence from retrieved context",
            }
        )

    result["fix_suggestions"] = validated_fixes[:4]

    risk = result["risk_analysis"]
    severity = _safe_text(risk.get("severity")) or "Unknown"
    if severity not in {"Low", "Medium", "High", "Critical", "Unknown"}:
        severity = "Unknown"

    failures = risk.get("potential_failures")
    if not isinstance(failures, list):
        failures = []
    failures = [_safe_text(x) for x in failures if _safe_text(x)]

    result["risk_analysis"] = {
        "severity": severity,
        "why": _safe_text(risk.get("why")) or "insufficient evidence from retrieved context",
        "potential_failures": failures,
        "runtime_risk": _safe_text(risk.get("runtime_risk")) or "insufficient evidence from retrieved context",
        "maintainability_risk": _safe_text(risk.get("maintainability_risk")) or "insufficient evidence from retrieved context",
    }

    deviation = result["deviation_advice"]
    deviation_possible = _safe_text(deviation.get("deviation_possible")) or "Unknown"
    if deviation_possible not in {"Yes", "No", "Conditional", "Unknown"}:
        deviation_possible = "Unknown"

    result["deviation_advice"] = {
        "deviation_possible": deviation_possible,
        "recommended_decision": _safe_text(deviation.get("recommended_decision")) or "insufficient evidence from retrieved context",
        "required_justification": _safe_text(deviation.get("required_justification")) or "insufficient evidence from retrieved context",
        "review_notes": _safe_text(deviation.get("review_notes")) or "insufficient evidence from retrieved context",
    }

    traceability = result["traceability"]
    confidence = traceability.get("confidence", 0.0)
    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.0

    confidence = max(0.0, min(1.0, confidence))
    if top_raw_score > 0:
        confidence = min(confidence, max(0.1, min(0.99, top_raw_score + 0.2)))

    limitations = traceability.get("limitations")
    if not isinstance(limitations, list):
        limitations = []
    limitations = [_safe_text(x) for x in limitations if _safe_text(x)]

    warning_text = _compact_text(warning_input.get("warning_message")).lower()
    rule_title = _compact_text(result["guideline_title"]).lower()

    overlap_tokens = set(re.findall(r"[a-zA-Z_]+", warning_text)) & set(re.findall(r"[a-zA-Z_]+", rule_title))
    meaningful_overlap = {tok for tok in overlap_tokens if len(tok) > 3}

    if warning_text and rule_title and len(meaningful_overlap) < 2:
        limitations.append("Warning text and retrieved rule statement may not fully align.")

    if top_raw_score < 0.50:
        limitations.append("Top raw retrieval score is weak; response should be reviewed.")
    if not result["fix_suggestions"]:
        limitations.append("No reliable fix suggestions could be validated from the generated output.")

    result["traceability"] = {
        "retrieved_chunk_ids": trace_ids,
        "retrieval_score_raw": top_raw_score,
        "retrieval_score_reranked": top_score,
        "confidence": confidence,
        "limitations": _dedupe_keep_order(limitations),
    }

    return result


def _run_generation(
    config: GenerationConfig,
    warning_input: Dict[str, Any],
    prompt_context: Dict[str, Any],
) -> Dict[str, Any]:
    runtime = LocalLlamaRuntime.get_instance(config)

    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(warning_input=warning_input, prompt_context=prompt_context)

    response = runtime.llm.create_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=config.temperature,
        top_p=config.top_p,
        top_k=config.top_k,
        repeat_penalty=config.repeat_penalty,
        seed=config.seed,
        max_tokens=config.max_tokens,
        stop=list(config.stop),
    )

    text = response["choices"][0]["message"]["content"]
    json_text = _extract_json_block(text)
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as exc:
        # Last-resort: aggressively strip any remaining non-JSON chars and retry
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", json_text)  # strip control chars
        cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)  # trailing commas again
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            raise json.JSONDecodeError(
                f"Could not parse LLM JSON after cleanup. Original error: {exc.msg}",
                exc.doc, exc.pos
            ) from exc
    validated = _validate_and_normalize_output(parsed, prompt_context, warning_input)
    return validated


def generate_misra_response(
    *,
    rule_id: str,
    warning_message: str,
    code_snippet: str,
    checker_name: str = "",
    config: GenerationConfig,
    top_k: int = 5,
) -> Dict[str, Any]:
    warning_input = {
        "rule_id": rule_id,
        "warning_message": warning_message,
        "code_snippet": code_snippet,
        "checker_name": checker_name,
    }

    normalized_input = normalize_retrieval_input(
        rule_id=rule_id,
        warning_message=warning_message,
        code_snippet=code_snippet,
        checker_name=checker_name,
    )
    cache_key = build_cache_key(normalized_input)
    generation_signature = _hash_generation_signature(config)

    cache_record = get_cache_record(cache_key)
    if cache_record:
        cached_final_result = cache_record.get("final_result")
        cached_generation_signature = cache_record.get("generation_signature")
        if cached_final_result and cached_generation_signature == generation_signature:
            return {
                "source": "final_cache",
                "cache_key": cache_key,
                "generation_signature": generation_signature,
                "result": cached_final_result,
            }

    retrieval_bundle = retrieve_with_cache(
        rule_id=rule_id,
        warning_message=warning_message,
        code_snippet=code_snippet,
        checker_name=checker_name,
        top_k=top_k,
    )

    retrieval_result = retrieval_bundle.get("retrieval_result") or retrieval_bundle.get("result") or retrieval_bundle
    prompt_context = _prepare_authoritative_context(retrieval_result)

    final_result = _run_generation(
        config=config,
        warning_input=warning_input,
        prompt_context=prompt_context,
    )

    final_result = filter_and_validate_response(
        final_result,
        rule_id=rule_id,
        code_snippet=code_snippet,
    )

    # Retry once if no valid fixes were produced
    if not final_result.get("fix_suggestions"):
        LOGGER.warning(
            "No valid fixes after first generation for %s (%s) — retrying with stricter prompt",
            rule_id, warning_message[:60],
        )
        retry_input = dict(warning_input)
        retry_input["_retry_hint"] = (
            "Previous attempt produced zero valid fixes. "
            "This retry: output patched_code that changes only the flagged line(s). "
            "Do NOT introduce any new variable declarations. "
            "Do NOT use numeric literals not already in the original code. "
            "A minimal comment-only fix or const qualifier is acceptable."
        )
        retry_result = _run_generation(
            config=config,
            warning_input=retry_input,
            prompt_context=prompt_context,
        )
        retry_validated = filter_and_validate_response(
            retry_result,
            rule_id=rule_id,
            code_snippet=code_snippet,
        )
        if retry_validated.get("fix_suggestions"):
            # Merge retry fixes into the main result
            final_result["fix_suggestions"] = retry_validated["fix_suggestions"]
            lims = final_result.get("traceability", {}).get("limitations", [])
            lims.append("Fix suggestions produced on retry attempt.")
            final_result.setdefault("traceability", {})["limitations"] = lims

    store_final_result(
        cache_key=cache_key,
        final_result=final_result,
        generation_signature=generation_signature,
        generation_model=Path(config.model_path).name,
        prompt_version=config.prompt_version,
    )

    return {
        "source": "generation",
        "cache_key": cache_key,
        "generation_signature": generation_signature,
        "result": final_result,
    }