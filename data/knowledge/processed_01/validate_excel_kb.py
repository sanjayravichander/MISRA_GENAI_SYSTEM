from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


DEFAULT_KB_PATH = (
    Path(__file__).resolve().parents[1]
    / "excel_kb"
    / "misra_excel_kb.corrected.json"
)

MIN_RULE_STATEMENT_LENGTH = 10

EXPECTED_RULE_PREFIXES = {
    "7.2": 'A "u" or "U" suffix',
    "7.3": 'The lowercase character "l"',
    "8.11": "When an array with external linkage",
    "20.2": "The ', \" or \\ characters",
    "21.11": "The standard header file <tgmath.h>",
}


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"KB file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_rules_container(kb_data: Any) -> List[Dict[str, Any]]:
    if isinstance(kb_data, dict) and "rules" in kb_data:
        if not isinstance(kb_data["rules"], list):
            raise TypeError("'rules' key exists but is not a list.")
        return kb_data["rules"]

    if isinstance(kb_data, list):
        return kb_data

    raise TypeError("Unsupported KB JSON structure. Expected {'rules': [...]} or [...].")


def extract_short_id(rule_id: str) -> str:
    if not rule_id:
        return ""
    match = re.search(r"(\d+\.\d+)", str(rule_id))
    return match.group(1) if match else ""


def validate_rule(rule: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    rule_id = str(rule.get("rule_id", "")).strip()
    rule_type = str(rule.get("rule_type", "")).strip()
    rule_statement = str(rule.get("rule_statement", "")).strip()
    description = str(rule.get("description", "")).strip()
    violated_code = str(rule.get("violated_code", "")).strip()

    short_id = extract_short_id(rule_id)

    if not rule_id:
        errors.append("Missing rule_id.")

    if not short_id:
        errors.append(f"Invalid or missing numeric rule id in rule_id: '{rule_id}'")

    if not rule_type:
        errors.append(f"Rule {rule_id or '[unknown]'}: Missing rule_type.")
    elif rule_type not in {"Mandatory", "Required", "Advisory"}:
        warnings.append(f"Rule {rule_id}: Unexpected rule_type '{rule_type}'")

    if not rule_statement:
        errors.append(f"Rule {rule_id or '[unknown]'}: Empty rule_statement.")
    elif len(rule_statement) < MIN_RULE_STATEMENT_LENGTH:
        errors.append(
            f"Rule {rule_id}: suspiciously short rule_statement -> '{rule_statement}'"
        )

    if not description:
        warnings.append(f"Rule {rule_id}: Missing description.")

    if not violated_code:
        warnings.append(f"Rule {rule_id}: Missing violated_code example.")

    if rule_statement:
        lowered = rule_statement.lower()
        modal_keywords = ["shall", "should", "required", "mandatory", "advisory"]

        if not any(word in lowered for word in modal_keywords):
            warnings.append(
                f"Rule {rule_id}: missing expected normative wording"
            )

    if short_id in EXPECTED_RULE_PREFIXES:
        expected_prefix = EXPECTED_RULE_PREFIXES[short_id]
        if not rule_statement.startswith(expected_prefix):
            errors.append(
                f"Rule {rule_id}: authoritative prefix mismatch. "
                f"Expected prefix: '{expected_prefix}' | Actual: '{rule_statement}'"
            )

    # Optional consistency check:
    # description should usually mention the rule statement meaningfully
    if description and rule_statement and short_id in {"7.2", "7.3", "8.11", "20.2", "21.11"}:
        description_l = description.lower()
        rule_statement_l = rule_statement.lower()

        semantic_checks = {
            "7.2": ["unsigned", "suffix"],
            "7.3": ["lowercase", "literal"],
            "8.11": ["array", "external linkage", "size"],
            "20.2": ["header", "file", "name"],
            "21.11": ["tgmath.h"],
        }

        expected_terms = semantic_checks.get(short_id, [])
        missing_terms = [term for term in expected_terms if term not in description_l]

        if missing_terms:
            warnings.append(
                f"Rule {rule_id}: description may be stale relative to corrected rule_statement. "
                f"Missing expected terms: {missing_terms}"
            )

    return errors, warnings


def validate_all_rules(rules: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    all_errors: List[str] = []
    all_warnings: List[str] = []

    seen_rule_ids = set()

    for rule in rules:
        rule_id = str(rule.get("rule_id", "")).strip()

        if rule_id:
            if rule_id in seen_rule_ids:
                all_errors.append(f"Duplicate rule_id found: {rule_id}")
            else:
                seen_rule_ids.add(rule_id)

        errors, warnings = validate_rule(rule)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    return all_errors, all_warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate MISRA Excel KB JSON.")
    parser.add_argument(
        "--kb",
        type=str,
        default=str(DEFAULT_KB_PATH),
        help="Path to KB JSON file",
    )
    args = parser.parse_args()

    kb_path = Path(args.kb).resolve()

    try:
        print(f"Validating KB: {kb_path}")
        kb_data = load_json(kb_path)
        rules = get_rules_container(kb_data)

        print(f"Loaded {len(rules)} rules")

        errors, warnings = validate_all_rules(rules)

        print("\n" + "=" * 72)
        print("Validation Summary")
        print("=" * 72)
        print(f"Rules checked : {len(rules)}")
        print(f"Errors        : {len(errors)}")
        print(f"Warnings      : {len(warnings)}")

        if errors:
            print("\n[ERRORS]")
            for item in errors:
                print(f"  - {item}")

        if warnings:
            print("\n[WARNINGS]")
            for item in warnings:
                print(f"  - {item}")

        if errors:
            print("\n[RESULT] VALIDATION FAILED")
            return 1

        print("\n[RESULT] VALIDATION PASSED")
        return 0

    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())