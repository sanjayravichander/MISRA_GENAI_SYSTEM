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
    raw = json.dumps(
        {
            "model_path": config.model_path,
            "prompt_version": config.prompt_version,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "top_k": config.top_k,
            "repeat_penalty": config.repeat_penalty,
            "seed": config.seed,
            "max_tokens": config.max_tokens,
        },
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _extract_json_block(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Model output does not contain a valid JSON object. Raw output: {text}")
    return text[start:end + 1]


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
You are an offline MISRA C:2012 analysis engine.

Rules:
1. Use ONLY the provided warning details, source code snippet, and retrieved MISRA knowledge context.
2. Do NOT invent MISRA rule text, rationale, exceptions, or examples.
3. If evidence is missing, say "insufficient evidence from retrieved context".
4. Output STRICT JSON only.
5. Do not output markdown.
6. Fix suggestions must be conservative and standards-aligned.
7. Never claim certainty if the retrieved evidence is weak or inconsistent.
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

    return f"""
Produce one STRICT JSON object matching this schema exactly:

{json.dumps(schema, indent=2)}

Input warning:
{json.dumps(warning_input, indent=2)}

Retrieved MISRA context:
{json.dumps(prompt_context, indent=2)[:6000]}

Instructions:
- guideline_id must align to the strongest retrieved guideline when supported by evidence.
- guideline_title must come only from retrieved context if available.
- Generate as many ranked fix_suggestions as the retrieved MISRA context justifies. If the rule has multiple recommended remediation approaches in the context, provide one fix per approach. If only one clear fix exists, provide one. Do not invent fixes beyond what the retrieved context supports.
- If exact patch code is uncertain, provide the safest local patch.
- Prefer the smallest compliant patch.
- Do not convert a declaration into a definition unless the retrieved context explicitly requires it.
- Do not introduce new symbols unless strictly necessary.
- Do not propose variable-length arrays.
- If the warning text and retrieved rule meaning appear inconsistent, mention that in traceability.limitations.
- Return JSON only.
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
    parsed = json.loads(json_text)
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