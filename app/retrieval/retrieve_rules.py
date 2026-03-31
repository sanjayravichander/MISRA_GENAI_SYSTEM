from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from app.retrieval.cache_service import (
    normalize_retrieval_input,
    build_cache_key,
    get_cache_record,
    store_retrieval_result,
)


# =============================
# CONFIG
# =============================

@dataclass
class RetrievalConfig:
    qdrant_path: str = "data/knowledge/qdrant_index"
    collection_name: str = "misra_excel_kb"
    embedding_model: str = "BAAI/bge-base-en-v1.5"

    # Reranking boosts (IMPORTANT FOR QUALITY)
    rule_id_exact_boost: float = 0.35
    rule_id_partial_boost: float = 0.15
    rule_core_boost: float = 0.08
    rationale_boost: float = 0.04


# =============================
# CORE ENGINE
# =============================

class RetrievalEngine:
    def __init__(self, config: Optional[RetrievalConfig] = None) -> None:
        self.config = config or RetrievalConfig()

        self.qdrant_path = Path(self.config.qdrant_path)
        self.collection_name = self.config.collection_name
        self.embedding_model_name = self.config.embedding_model

        self.client = QdrantClient(path=str(self.qdrant_path))
        self.embedder = SentenceTransformer(self.embedding_model_name)

    # -----------------------------
    # QUERY BUILDING
    # -----------------------------
    def _build_query(
        self,
        *,
        rule_id: str,
        warning_message: str,
        code_snippet: str,
        checker_name: str = "",
    ) -> str:
        parts = [
            f"Rule ID: {rule_id}" if rule_id else "",
            f"Checker: {checker_name}" if checker_name else "",
            f"Warning: {warning_message}" if warning_message else "",
            f"Code: {code_snippet}" if code_snippet else "",
        ]
        return "\n".join(part for part in parts if part.strip())

    def _embed_query(self, query_text: str) -> List[float]:
        embedding = self.embedder.encode(query_text, normalize_embeddings=True)
        return embedding.tolist()

    # -----------------------------
    # RULE ID NORMALIZATION
    # -----------------------------
    def _normalize_rule_id(self, value: str) -> str:
        text = (value or "").strip().lower()

        checker_match = re.search(r"rule[-_\s]*(\d+)[._-](\d+)", text)
        if checker_match:
            return f"rule{checker_match.group(1)}.{checker_match.group(2)}"

        plain_match = re.search(r"rule\s*(\d+)\.(\d+)", text)
        if plain_match:
            return f"rule{plain_match.group(1)}.{plain_match.group(2)}"

        return re.sub(r"[^a-z0-9.]+", "", text)

    def _extract_major_minor(self, normalized_rule_id: str):
        match = re.match(r"rule(\d+)\.(\d+)", normalized_rule_id)
        if not match:
            return None, None
        return match.group(1), match.group(2)

    # -----------------------------
    # RERANKING (CRITICAL)
    # -----------------------------
    def _compute_rerank_score(
        self,
        *,
        input_rule_id: str,
        candidate_rule_id: str,
        chunk_type: str,
        base_score: float,
    ) -> float:
        reranked = float(base_score)

        normalized_input = self._normalize_rule_id(input_rule_id)
        normalized_candidate = self._normalize_rule_id(candidate_rule_id)

        if normalized_input and normalized_candidate:
            if normalized_input == normalized_candidate:
                reranked += self.config.rule_id_exact_boost
            else:
                input_major, _ = self._extract_major_minor(normalized_input)
                cand_major, _ = self._extract_major_minor(normalized_candidate)

                if input_major and cand_major and input_major == cand_major:
                    reranked += self.config.rule_id_partial_boost

        chunk_type = (chunk_type or "").strip().lower()
        if chunk_type == "rule_core":
            reranked += self.config.rule_core_boost
        elif chunk_type == "rationale":
            reranked += self.config.rationale_boost

        return reranked

    # -----------------------------
    # MAIN RETRIEVE
    # -----------------------------
    def retrieve(
        self,
        *,
        rule_id: str,
        warning_message: str,
        code_snippet: str,
        checker_name: str = "",
        top_k: int = 5,
    ) -> Dict[str, Any]:

        query_text = self._build_query(
            rule_id=rule_id,
            warning_message=warning_message,
            code_snippet=code_snippet,
            checker_name=checker_name,
        )

        query_vector = self._embed_query(query_text)

        initial_limit = max(top_k * 4, 20)

        search_result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=initial_limit,
            with_payload=True,
        )

        matches: List[Dict[str, Any]] = []

        points = getattr(search_result, "points", []) or []

        for point in points:
            payload = point.payload or {}

            base_score = float(point.score)

            reranked_score = self._compute_rerank_score(
                input_rule_id=rule_id,
                candidate_rule_id=payload.get("rule_id", ""),
                chunk_type=payload.get("chunk_type", ""),
                base_score=base_score,
            )

            matches.append(
                {
                    "id": str(payload.get("chunk_id", point.id)),
                    "score": base_score,
                    "reranked_score": reranked_score,
                    "guideline_id": payload.get("rule_id"),
                    "chunk_type": payload.get("chunk_type"),
                    "title": payload.get("rule_statement"),
                    "text": payload.get("text"),
                    "payload": payload,
                }
            )

        matches.sort(
            key=lambda x: (x["reranked_score"], x["score"]),
            reverse=True,
        )

        return {
            "query_text": query_text,
            "matches": matches[:top_k],
        }


# =============================
# INTERNAL CALL
# =============================

def _retrieve_from_qdrant(**kwargs) -> Dict[str, Any]:
    engine = RetrievalEngine()
    return engine.retrieve(**kwargs)


# =============================
# CACHE LAYER
# =============================

def retrieve_with_cache(
    *,
    rule_id: str,
    warning_message: str,
    code_snippet: str,
    checker_name: str = "",
    top_k: int = 5,
) -> Dict[str, Any]:

    # ✅ Only pass REQUIRED fields to normalization
    normalized_input = normalize_retrieval_input(
        rule_id=rule_id,
        warning_message=warning_message,
        code_snippet=code_snippet,
        checker_name=checker_name,
    )

    cache_key = build_cache_key(normalized_input)

    cache_record = get_cache_record(cache_key)
    if cache_record and cache_record.get("retrieval_result"):
        return {
            "source": "cache",
            "cache_key": cache_key,
            "retrieval_result": cache_record["retrieval_result"],
            "final_result": cache_record.get("final_result"),
        }

    # ✅ Pass top_k ONLY to retrieval layer
    retrieval_result = _retrieve_from_qdrant(
        rule_id=rule_id,
        warning_message=warning_message,
        code_snippet=code_snippet,
        checker_name=checker_name,
        top_k=top_k,
    )

    store_retrieval_result(
        cache_key=cache_key,
        normalized_input=normalized_input,
        retrieval_result=retrieval_result,
    )

    return {
        "source": "retrieval",
        "cache_key": cache_key,
        "retrieval_result": retrieval_result,
        "final_result": None,
    }


# =============================
# 🚨 PUBLIC API (CRITICAL FIX)
# =============================

def retrieve_rules(warning: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Adapter for orchestrator.

    Converts advanced retrieval output into:
    [
        {
            "rule_id": "...",
            "description": "...",
            "guidelines": "...",
            "score": float
        }
    ]
    """

    if not isinstance(warning, dict):
        return []

    result = retrieve_with_cache(
        rule_id=warning.get("rule_id", ""),
        warning_message=warning.get("message", ""),
        code_snippet="",  # future enhancement
        checker_name="",
        top_k=5,
    )

    matches = result.get("retrieval_result", {}).get("matches", [])

    formatted = []

    for m in matches:
        payload = m.get("payload", {})

        formatted.append({
            "rule_id": payload.get("rule_id") or m.get("guideline_id"),
            "description": payload.get("rule_statement") or m.get("title"),
            "guidelines": payload.get("text"),
            "score": m.get("reranked_score", m.get("score", 0.0)),
        })

    return formatted