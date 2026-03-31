#!/usr/bin/env python3
"""
validate_excel_kb.py

Cheap validation pass for the canonical MISRA Excel KB JSON.
Use this BEFORE expensive LLM runs.

What it checks
--------------
- rule_count matches actual record count
- duplicate rule_ids
- invalid/missing rule_type
- missing rule_statement / description / violated_code
- suspiciously short rule statements
- OCR / metadata leakage patterns
- known historically problematic rules (7.2, 7.3, 8.11, 20.2, 21.11)

Usage
-----
python validate_excel_kb.py
python validate_excel_kb.py --kb data/knowledge/excel_kb/misra_excel_kb.json
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from pathlib import Path

DEFAULT_KB = Path(r"C:\Users\sanjay.ravichander\misra_genai_system\misra_genai_system\data\knowledge\excel_kb\misra_excel_kb.json")
VALID_RULE_TYPES = {"Required", "Mandatory", "Advisory"}

KNOWN_EXPECTED_SNIPPETS = {
    "Rule 7.2": ["u", "U", "suffix"],
    "Rule 7.3": ["lowercase", "l", "suffix"],
    "Rule 8.11": ["external", "array", "size"],
    "Rule 20.2": ["header", "include", "character"],
    "Rule 21.11": ["tgmath.h"],
}

OCR_PATTERNS = [
    r"Mandato\s+ry",
    r"Manda\s+tory",
    r"Adviso\s+ry",
    r"\bAn\s*alysis\b",
    r"Undecidable",
    r"System Rational",
    r"\bta\s+g\b",
    r"\bma\s+cro\b",
    r"\bshal\s+l\b",
    r"\bessentia\s+l\b",
]

def looks_suspiciously_short(text: str) -> bool:
    text = text.strip()
    if not text:
        return True
    word_count = len(re.findall(r"\w+", text))
    return word_count < 4

def load_kb(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rules = data.get("rules", [])
    declared_count = data.get("rule_count")
    if declared_count is not None and declared_count != len(rules):
        print(f"[WARN] rule_count={declared_count}, actual_rules={len(rules)}")
    return rules

def validate_rules(rules: list[dict]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    ids = [r.get("rule_id", "") for r in rules]
    duplicates = [rid for rid, count in Counter(ids).items() if rid and count > 1]
    for rid in duplicates:
        errors.append(f"{rid}: duplicate rule_id")

    for i, rec in enumerate(rules, start=1):
        rid = rec.get("rule_id", f"<row {i}>")
        rule_type = (rec.get("rule_type") or "").strip()
        statement = (rec.get("rule_statement") or "").strip()
        description = (rec.get("description") or "").strip()
        violated_code = (rec.get("violated_code") or "").strip()

        if not rid:
            errors.append(f"row {i}: missing rule_id")
        elif not re.fullmatch(r"Rule \d+\.\d+", rid):
            errors.append(f"{rid}: malformed rule_id")

        if rule_type not in VALID_RULE_TYPES:
            errors.append(f"{rid}: invalid rule_type '{rule_type}'")

        if not statement:
            errors.append(f"{rid}: missing rule_statement")
        elif looks_suspiciously_short(statement):
            warnings.append(f"{rid}: suspiciously short rule_statement -> {statement!r}")

        if not description:
            errors.append(f"{rid}: missing description")
        elif len(description) < 15:
            warnings.append(f"{rid}: very short description -> {description!r}")

        if not violated_code:
            errors.append(f"{rid}: missing violated_code")
        elif len(violated_code) < 8:
            warnings.append(f"{rid}: very short violated_code")

        combined = " ".join([statement, description, violated_code])
        for pat in OCR_PATTERNS:
            if re.search(pat, combined, flags=re.IGNORECASE):
                warnings.append(f"{rid}: possible OCR/metadata artifact matched /{pat}/")
                break

        if rid in KNOWN_EXPECTED_SNIPPETS:
            haystack = f"{statement} {description}".lower()
            missing = [s for s in KNOWN_EXPECTED_SNIPPETS[rid] if s.lower() not in haystack]
            if missing:
                warnings.append(
                    f"{rid}: missing expected keywords {missing} "
                    f"(statement={statement!r}; description={description!r})"
                )

    return errors, warnings

def main() -> int:
    parser = argparse.ArgumentParser(description="Validate MISRA Excel KB JSON")
    parser.add_argument("--kb", type=Path, default=DEFAULT_KB, help="Path to misra_excel_kb.json")
    args = parser.parse_args()

    # FORCE PATH (temporary debug override)
    args.kb = Path(r"C:\Users\sanjay.ravichander\misra_genai_system\misra_genai_system\data\knowledge\excel_kb\misra_excel_kb.json")

    print("_HERE =", _HERE)
    print("PROJECT_ROOT =", PROJECT_ROOT)
    print(f"Validating KB: {args.kb}")

    if not args.kb.exists():
        print(f"[ERROR] KB not found: {args.kb}")
        return 1

    rules = load_kb(args.kb)
    print(f"Loaded {len(rules)} rules")

    errors, warnings = validate_rules(rules)

    print("\n" + "=" * 72)
    print(f"Validation Summary")
    print("=" * 72)
    print(f"Rules checked : {len(rules)}")
    print(f"Errors        : {len(errors)}")
    print(f"Warnings      : {len(warnings)}")

    if errors:
        print("\n[ERRORS]")
        for msg in errors:
            print(f"  - {msg}")

    if warnings:
        print("\n[WARNINGS]")
        for msg in warnings:
            print(f"  - {msg}")

    if not errors and not warnings:
        print("\nAll checks passed.")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
