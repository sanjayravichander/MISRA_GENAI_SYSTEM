"""
result_cache.py  —  SQLite result cache for MISRA GenAI pipeline.

Two cache tables:
  results     — Phase 7 fix generation cache
  eval_cache  — Phase 8 evaluation cache  (NEW)

Phase 7 cache key : SHA-256 of (rule_id + source_context + top-3 KB chunk texts)
Phase 8 cache key : SHA-256 of (rule_id + source_context + fix_fingerprint)
                    where fix_fingerprint = the serialised fix_suggestions/ranked_fixes list

Same warning on re-run = instant result, no LLM call.

Usage
-----
    from app.pipeline.result_cache import ResultCache

    cache = ResultCache()

    # Phase 7
    hit = cache.get(rule_id, source_ctx, chunks)
    if hit is None:
        result = call_llm(...)
        cache.set(rule_id, source_ctx, chunks, result)

    # Phase 8
    hit = cache.get_eval(rule_id, source_ctx, fix_result)
    if hit is None:
        eval_result = call_eval_llm(...)
        cache.set_eval(rule_id, source_ctx, fix_result, eval_result)
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from app.config.settings import CACHE_PATH
except ImportError:
    CACHE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "cache" / "results_cache.db"


# ---------------------------------------------------------------------------
# Fingerprint helpers
# ---------------------------------------------------------------------------

def _fingerprint(rule_id: str, source_context: str, kb_chunks: List[str]) -> str:
    """Stable SHA-256 key for a (rule, source, kb) triple — Phase 7."""
    top3 = "||".join(kb_chunks[:3])
    raw = f"{rule_id.strip()}|||{source_context.strip()}|||{top3}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _eval_fingerprint(rule_id: str, source_context: str, fix_result: Dict[str, Any]) -> str:
    """
    Stable SHA-256 key for a Phase 8 evaluation.
    Key ingredients: rule_id + source_context + the actual fixes being evaluated.
    We serialise the fix list (ranked_fixes or fix_suggestions) deterministically.
    """
    fix_key = "fix_suggestions" if "fix_suggestions" in fix_result else "ranked_fixes"
    fixes   = fix_result.get(fix_key, [])

    # Only include the fields that determine what the evaluator sees —
    # stripping runtime/cache metadata so the key stays stable across runs.
    stable_fixes = []
    for f in fixes:
        stable_fixes.append({
            "rank":         f.get("rank"),
            "title":        f.get("title", f.get("description", f.get("fix_title", ""))),
            "code":         f.get("patched_code", f.get("code_change", f.get("code", ""))),
            "why":          f.get("why", ""),
            "compliance":   f.get("compliance_notes", ""),
        })

    raw = (
        f"{rule_id.strip()}|||"
        f"{source_context.strip()}|||"
        f"{json.dumps(stable_fixes, sort_keys=True, ensure_ascii=False)}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Cache class
# ---------------------------------------------------------------------------

class ResultCache:
    """Thread-safe SQLite-backed result cache for Phase 7 and Phase 8."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = Path(db_path or CACHE_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        # Phase 7 table (unchanged)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS results (
                fingerprint TEXT PRIMARY KEY,
                rule_id     TEXT,
                result_json TEXT NOT NULL,
                created_at  REAL NOT NULL
            )
        """)
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rule ON results(rule_id)"
        )

        # Phase 8 eval table — ensure it has the correct schema
        # Check existing columns first
        existing_cols = {
            row[1] for row in
            self._conn.execute("PRAGMA table_info(eval_cache)").fetchall()
        }

        if not existing_cols:
            # Table doesn't exist yet — create fresh with correct schema
            self._conn.execute("""
                CREATE TABLE eval_cache (
                    fingerprint TEXT PRIMARY KEY,
                    rule_id     TEXT,
                    result_json TEXT NOT NULL,
                    created_at  REAL NOT NULL
                )
            """)
        elif "created_at" not in existing_cols:
            # Old table exists with typo column — rebuild it
            self._conn.execute("ALTER TABLE eval_cache RENAME TO eval_cache_old")
            self._conn.execute("""
                CREATE TABLE eval_cache (
                    fingerprint TEXT PRIMARY KEY,
                    rule_id     TEXT,
                    result_json TEXT NOT NULL,
                    created_at  REAL NOT NULL
                )
            """)
            # Migrate old rows — map created_ecraft (or whatever old name) to created_at
            old_cols = {
                row[1] for row in
                self._conn.execute("PRAGMA table_info(eval_cache_old)").fetchall()
            }
            old_ts_col = "created_ecraft" if "created_ecraft" in old_cols else (
                next((c for c in old_cols if "creat" in c.lower()), None)
            )
            if old_ts_col:
                self._conn.execute(f"""
                    INSERT OR IGNORE INTO eval_cache
                        (fingerprint, rule_id, result_json, created_at)
                    SELECT fingerprint, rule_id, result_json, {old_ts_col}
                    FROM eval_cache_old
                """)
            self._conn.execute("DROP TABLE eval_cache_old")

        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_eval_rule ON eval_cache(rule_id)"
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Phase 7 — fix generation cache
    # ------------------------------------------------------------------

    def get(
        self,
        rule_id: str,
        source_context: str,
        kb_chunks: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Return cached Phase 7 result dict, or None on cache miss."""
        fp  = _fingerprint(rule_id, source_context, kb_chunks)
        row = self._conn.execute(
            "SELECT result_json FROM results WHERE fingerprint = ?", (fp,)
        ).fetchone()
        if row is None:
            return None
        try:
            result = json.loads(row[0])
            result["_from_cache"] = True
            return result
        except json.JSONDecodeError:
            return None

    def set(
        self,
        rule_id: str,
        source_context: str,
        kb_chunks: List[str],
        result: Dict[str, Any],
    ) -> None:
        """Store Phase 7 result in cache (upsert)."""
        fp = _fingerprint(rule_id, source_context, kb_chunks)
        to_store = {k: v for k, v in result.items() if k != "_from_cache"}
        self._conn.execute(
            """
            INSERT INTO results (fingerprint, rule_id, result_json, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(fingerprint) DO UPDATE SET
                result_json = excluded.result_json,
                created_at  = excluded.created_at
            """,
            (fp, rule_id, json.dumps(to_store, ensure_ascii=False), time.time()),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Phase 8 — evaluation cache
    # ------------------------------------------------------------------

    def get_eval(
        self,
        rule_id: str,
        source_context: str,
        fix_result: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Return cached Phase 8 evaluation result, or None on cache miss.
        fix_result is the Phase 7 output dict (used to build the cache key).
        """
        fp  = _eval_fingerprint(rule_id, source_context, fix_result)
        row = self._conn.execute(
            "SELECT result_json FROM eval_cache WHERE fingerprint = ?", (fp,)
        ).fetchone()
        if row is None:
            return None
        try:
            result = json.loads(row[0])
            result["_eval_from_cache"] = True
            return result
        except json.JSONDecodeError:
            return None

    def set_eval(
        self,
        rule_id: str,
        source_context: str,
        fix_result: Dict[str, Any],
        eval_result: Dict[str, Any],
    ) -> None:
        """Store Phase 8 evaluation result in cache (upsert)."""
        fp       = _eval_fingerprint(rule_id, source_context, fix_result)
        to_store = {k: v for k, v in eval_result.items() if k != "_eval_from_cache"}
        self._conn.execute(
            """
            INSERT INTO eval_cache (fingerprint, rule_id, result_json, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(fingerprint) DO UPDATE SET
                result_json = excluded.result_json,
                created_at  = excluded.created_at
            """,
            (fp, rule_id, json.dumps(to_store, ensure_ascii=False), time.time()),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Stats / maintenance
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """Return basic cache statistics for both tables."""
        r7 = self._conn.execute(
            "SELECT COUNT(*), COUNT(DISTINCT rule_id) FROM results"
        ).fetchone()
        r8 = self._conn.execute(
            "SELECT COUNT(*), COUNT(DISTINCT rule_id) FROM eval_cache"
        ).fetchone()
        return {
            "total_entries":          r7[0],
            "distinct_rules":         r7[1],
            "eval_total_entries":     r8[0],
            "eval_distinct_rules":    r8[1],
        }

    def clear(self) -> int:
        """Wipe all cached entries from both tables. Returns total deleted."""
        n7 = self._conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
        n8 = self._conn.execute("SELECT COUNT(*) FROM eval_cache").fetchone()[0]
        self._conn.execute("DELETE FROM results")
        self._conn.execute("DELETE FROM eval_cache")
        self._conn.commit()
        return n7 + n8

    def close(self) -> None:
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    cache = ResultCache()
    s = cache.stats()
    print(f"Cache at: {cache.db_path}")
    print(f"  Phase 7 entries        : {s['total_entries']}")
    print(f"  Phase 7 distinct rules : {s['distinct_rules']}")
    print(f"  Phase 8 entries        : {s['eval_total_entries']}")
    print(f"  Phase 8 distinct rules : {s['eval_distinct_rules']}")