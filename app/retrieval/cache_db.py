from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path("data/cache/retrieval_cache.sqlite3")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _get_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def ensure_cache_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS retrieval_cache (
            cache_key TEXT PRIMARY KEY,
            normalized_input_json TEXT NOT NULL,
            retrieval_result_json TEXT,
            final_result_json TEXT,
            generation_signature TEXT,
            generation_model TEXT,
            prompt_version TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    columns = _get_columns(conn, "retrieval_cache")

    migrations = {
        "retrieval_result_json": "ALTER TABLE retrieval_cache ADD COLUMN retrieval_result_json TEXT",
        "final_result_json": "ALTER TABLE retrieval_cache ADD COLUMN final_result_json TEXT",
        "generation_signature": "ALTER TABLE retrieval_cache ADD COLUMN generation_signature TEXT",
        "generation_model": "ALTER TABLE retrieval_cache ADD COLUMN generation_model TEXT",
        "prompt_version": "ALTER TABLE retrieval_cache ADD COLUMN prompt_version TEXT",
        "created_at": "ALTER TABLE retrieval_cache ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "ALTER TABLE retrieval_cache ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP",
    }

    for column_name, ddl in migrations.items():
        if column_name not in columns:
            conn.execute(ddl)

    conn.commit()