from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from app.retrieval.cache_db import get_connection, ensure_cache_schema


def normalize_retrieval_input(
    *,
    rule_id: str,
    warning_message: str,
    code_snippet: str,
    checker_name: str = "",
) -> Dict[str, str]:
    def clean(value: str) -> str:
        return " ".join((value or "").strip().split())

    return {
        "rule_id": clean(rule_id),
        "warning_message": clean(warning_message),
        "code_snippet": clean(code_snippet),
        "checker_name": clean(checker_name),
    }


def build_cache_key(normalized_input: Dict[str, str]) -> str:
    raw = json.dumps(normalized_input, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cache_record(cache_key: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    ensure_cache_schema(conn)

    row = conn.execute(
        """
        SELECT
            cache_key,
            normalized_input_json,
            retrieval_result_json,
            final_result_json,
            generation_signature,
            generation_model,
            prompt_version,
            created_at,
            updated_at
        FROM retrieval_cache
        WHERE cache_key = ?
        """,
        (cache_key,),
    ).fetchone()

    if row is None:
        return None

    return {
        "cache_key": row["cache_key"],
        "normalized_input": json.loads(row["normalized_input_json"]) if row["normalized_input_json"] else None,
        "retrieval_result": json.loads(row["retrieval_result_json"]) if row["retrieval_result_json"] else None,
        "final_result": json.loads(row["final_result_json"]) if row["final_result_json"] else None,
        "generation_signature": row["generation_signature"],
        "generation_model": row["generation_model"],
        "prompt_version": row["prompt_version"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def store_retrieval_result(
    *,
    cache_key: str,
    normalized_input: Dict[str, str],
    retrieval_result: Dict[str, Any],
) -> None:
    conn = get_connection()
    ensure_cache_schema(conn)

    conn.execute(
        """
        INSERT INTO retrieval_cache (
            cache_key,
            normalized_input_json,
            retrieval_result_json
        )
        VALUES (?, ?, ?)
        ON CONFLICT(cache_key) DO UPDATE SET
            normalized_input_json = excluded.normalized_input_json,
            retrieval_result_json = excluded.retrieval_result_json,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            cache_key,
            json.dumps(normalized_input, ensure_ascii=False, sort_keys=True),
            json.dumps(retrieval_result, ensure_ascii=False),
        ),
    )
    conn.commit()


def store_final_result(
    *,
    cache_key: str,
    final_result: Dict[str, Any],
    generation_signature: str,
    generation_model: str,
    prompt_version: str,
) -> None:
    conn = get_connection()
    ensure_cache_schema(conn)

    conn.execute(
        """
        UPDATE retrieval_cache
        SET
            final_result_json = ?,
            generation_signature = ?,
            generation_model = ?,
            prompt_version = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE cache_key = ?
        """,
        (
            json.dumps(final_result, ensure_ascii=False),
            generation_signature,
            generation_model,
            prompt_version,
            cache_key,
        ),
    )
    conn.commit()