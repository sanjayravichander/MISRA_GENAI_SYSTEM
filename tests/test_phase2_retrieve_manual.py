"""
Manual test for Phase 2 retrieval pipeline.

Runs the Phase 2 builder using the actual Phase 1 JSON file and prints:
- number of records
- first retrieval record
- key field checks
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline.phase2_retrieve import (
    build_phase2_retrieval,
    load_json,
)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    input_path = project_root / "data" / "output" / "phase1_ingest.json"

    phase1_data = load_json(input_path)

    if not isinstance(phase1_data, list):
        raise ValueError("phase1_ingest.json must contain a list.")

    phase2_data = build_phase2_retrieval(phase1_data)

    print(f"Loaded Phase 1 records: {len(phase1_data)}")
    print(f"Built Phase 2 retrieval records: {len(phase2_data)}")

    if not phase2_data:
        print("No Phase 2 records generated.")
        return

    first_record = phase2_data[0]

    print("\nFirst Phase 2 retrieval record:")
    print(json.dumps(first_record, indent=2, ensure_ascii=False))

    expected_keys = [
        "warning_id",
        "rule_id",
        "severity",
        "message",
        "file_name",
        "line_number",
        "function_name",
        "checker_name",
        "code_snippet",
        "guideline_id",
        "category",
        "rule_text",
    ]

    print("\nField presence check:")
    for key in expected_keys:
        print(f"{key}: {'YES' if key in first_record else 'NO'}")


if __name__ == "__main__":
    main()