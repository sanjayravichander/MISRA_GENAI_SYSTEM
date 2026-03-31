from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_KB_PATH = PROJECT_ROOT / "data" / "knowledge" / "excel_kb" / "misra_excel_kb.json"
OVERRIDES_PATH = PROJECT_ROOT / "data" / "knowledge" / "excel_kb" / "authoritative_overrides.json"
OUTPUT_KB_PATH = PROJECT_ROOT / "data" / "knowledge" / "excel_kb" / "misra_excel_kb.corrected.json"


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_rules_container(kb_data: Any) -> List[Dict[str, Any]]:
    if isinstance(kb_data, dict):
        if "rules" in kb_data and isinstance(kb_data["rules"], list):
            return kb_data["rules"]
        if "guidelines" in kb_data and isinstance(kb_data["guidelines"], list):
            return kb_data["guidelines"]

    if isinstance(kb_data, list):
        return kb_data

    raise TypeError("Unsupported KB JSON structure. Expected {'rules': [...]}, {'guidelines': [...]}, or [...].")


def normalize_text(value: Any) -> str:
    return str(value).strip()


def extract_numeric_rule_id(value: Any) -> Optional[str]:
    text = normalize_text(value)
    if not text:
        return None

    match = re.search(r"(\d+\.\d+)", text)
    if match:
        return match.group(1)

    return None


def candidate_ids(rule: Dict[str, Any]) -> List[str]:
    fields_to_check = [
        "short_id",
        "guideline_id",
        "rule_id",
        "id",
        "title",
        "name",
    ]

    ids: List[str] = []

    for field in fields_to_check:
        value = rule.get(field)
        if value is None:
            continue

        text = normalize_text(value)
        if text:
            ids.append(text)

        numeric = extract_numeric_rule_id(value)
        if numeric:
            ids.append(numeric)

    unique_ids: List[str] = []
    seen = set()
    for item in ids:
        if item not in seen:
            seen.add(item)
            unique_ids.append(item)

    return unique_ids


def find_matching_rule(rule: Dict[str, Any], target_override_id: str) -> bool:
    target = normalize_text(target_override_id)
    if not target:
        return False

    for cid in candidate_ids(rule):
        numeric_id = extract_numeric_rule_id(cid)
        if numeric_id == target:
            return True

    return False

def apply_overrides(kb_data: Any, overrides: Dict[str, Dict[str, str]]) -> Tuple[Any, List[str]]:
    rules = get_rules_container(kb_data)

    updated_rule_ids: List[str] = []
    missing_override_targets: List[str] = []

    for override_id, override_payload in overrides.items():
        matched = False

        for idx, rule in enumerate(rules, start=1):
            if not find_matching_rule(rule, override_id):
                continue

            print(f"[DEBUG] Match found for override {override_id} in record #{idx}")
            print(f"        candidate_ids={candidate_ids(rule)}")

            if "rule_statement" in override_payload:
                new_statement = normalize_text(override_payload.get("rule_statement", ""))
                if not new_statement:
                    raise ValueError(f"Override for rule {override_id} has empty rule_statement.")
                rule["rule_statement"] = new_statement

            if "description" in override_payload:
                new_description = normalize_text(override_payload.get("description", ""))
                if not new_description:
                    raise ValueError(f"Override for rule {override_id} has empty description.")
                rule["description"] = new_description

            print(f"[DEBUG] Applied override for {override_id}")
            if "rule_statement" in override_payload:
                print("        updated rule_statement")
            if "description" in override_payload:
                print("        updated description")

            rule["source_of_truth"] = "authoritative_override"
            updated_rule_ids.append(override_id)
            matched = True
            break

        if not matched:
            print(f"[DEBUG] No match found for override {override_id}")
            print("[DEBUG] Showing first 15 KB records candidate IDs:")
            for idx, rule in enumerate(rules[:15], start=1):
                print(f"        record #{idx}: {candidate_ids(rule)}")
            missing_override_targets.append(override_id)

    if isinstance(kb_data, dict):
        kb_data.setdefault("metadata", {})
        kb_data["metadata"]["override_applied_count"] = len(updated_rule_ids)
        kb_data["metadata"]["override_applied_ids"] = sorted(updated_rule_ids)

    return kb_data, missing_override_targets


def main() -> int:
    try:
        print(f"[INFO] Loading KB: {INPUT_KB_PATH}")
        kb_data = load_json(INPUT_KB_PATH)

        print(f"[INFO] Loading overrides: {OVERRIDES_PATH}")
        overrides = load_json(OVERRIDES_PATH)

        if not isinstance(overrides, dict):
            raise TypeError("authoritative_overrides.json must be a JSON object/dict.")

        rules = get_rules_container(kb_data)
        print(f"[INFO] Loaded {len(rules)} KB records")

        corrected_kb, missing_override_targets = apply_overrides(kb_data, overrides)

        if missing_override_targets:
            print("[ERROR] These override IDs were not found in KB:")
            print("       " + ", ".join(sorted(missing_override_targets)))
            return 1

        print(f"[INFO] Writing corrected KB: {OUTPUT_KB_PATH}")
        save_json(OUTPUT_KB_PATH, corrected_kb)

        print("[SUCCESS] Corrected KB saved.")
        print(f"[SUCCESS] Overrides applied: {len(corrected_kb.get('metadata', {}).get('override_applied_ids', [])) if isinstance(corrected_kb, dict) else 'done'}")
        return 0

    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())