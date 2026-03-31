import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.pipeline.phase1_ingest import build_phase1_records


def main():
    records = build_phase1_records(
        warning_reports_path="data/input/warning_reports",
        source_code_path="data/input/source_code",
        rules_json_path="data/knowledge/processed/rules_structured.json",
        snippet_context=4,
    )

    print(f"Total enriched records: {len(records)}")
    print(json.dumps(records[:2], indent=2, default=str))


if __name__ == "__main__":
    main()