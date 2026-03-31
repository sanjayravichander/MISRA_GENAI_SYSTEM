#!/usr/bin/env python3
"""
parse_polyspace_report.py  —  Phase 6a: Parse Polyspace Excel warning report.

Reads the Excel report and produces a structured JSON list of warnings,
each enriched with the surrounding source code context (±10 lines around
the flagged line).

Input columns expected
----------------------
  Tool Name | Warning ID | Category | Checker Name | Rule ID | Severity
  Message   | File Path  | Line Start | Line End | Function Name

Output
------
  A JSON file: list of warning objects, each with:
    - all Excel fields
    - source_context: the flagged lines + ±10 surrounding lines
    - severity_rank:  High=3, Medium=2, Low=1  (for sorting)

Usage
-----
  python parse_polyspace_report.py <report.xlsx> <source_dir> <output.json>

  source_dir: directory containing the .c files referenced in File Path column
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import openpyxl

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CONTEXT_LINES = 10       # lines before and after the flagged line to include
SEVERITY_RANK  = {"High": 3, "Medium": 2, "Low": 1}

EXPECTED_COLUMNS = {
    "Tool Name", "Warning ID", "Category", "Checker Name",
    "Rule ID", "Severity", "Message", "File Path",
    "Line Start", "Line End", "Function Name",
}


# ---------------------------------------------------------------------------
# Source context extractor
# ---------------------------------------------------------------------------

def extract_source_context(
    source_dir: Path,
    file_path: str,
    line_start: Optional[int],
    line_end: Optional[int],
    context: int = CONTEXT_LINES,
) -> Dict[str, Any]:
    """
    Load the source file and extract the flagged region with surrounding context.
    Returns a dict with the context text and exact line numbers shown.
    """
    # Try the filename directly under source_dir (handles both bare names and paths)
    candidates = [
        source_dir / file_path,
        source_dir / Path(file_path).name,
    ]
    src_file = next((p for p in candidates if p.exists()), None)

    if src_file is None:
        return {
            "file": file_path,
            "found": False,
            "context_text": f"[Source file not found: {file_path}]",
            "context_start_line": None,
            "context_end_line": None,
            "flagged_lines": [],
        }

    all_lines = src_file.read_text(encoding="utf-8", errors="replace").splitlines()
    total = len(all_lines)

    ls = int(line_start) if line_start else 1
    le = int(line_end)   if line_end   else ls

    ctx_start = max(1, ls - context)
    ctx_end   = min(total, le + context)

    numbered_lines = []
    for i in range(ctx_start - 1, ctx_end):
        lineno = i + 1
        marker = ">>>" if ls <= lineno <= le else "   "
        numbered_lines.append(f"{marker} {lineno:4d}  {all_lines[i]}")

    return {
        "file": str(src_file.name),
        "found": True,
        "context_text": "\n".join(numbered_lines),
        "context_start_line": ctx_start,
        "context_end_line": ctx_end,
        "flagged_lines": list(range(ls, le + 1)),
    }


# ---------------------------------------------------------------------------
# Excel parser
# ---------------------------------------------------------------------------

def parse_report(xlsx_path: Path, source_dir: Path) -> List[Dict[str, Any]]:
    wb = openpyxl.load_workbook(str(xlsx_path), read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise ValueError("Excel sheet is empty.")

    headers = [str(h).strip() if h is not None else "" for h in rows[0]]

    missing = EXPECTED_COLUMNS - set(headers)
    if missing:
        raise ValueError(f"Missing columns in Excel report: {missing}")

    idx = {h: i for i, h in enumerate(headers)}

    def get(row, col):
        i = idx.get(col)
        return row[i] if i is not None and i < len(row) else None

    warnings: List[Dict[str, Any]] = []
    for row in rows[1:]:
        if not any(row):   # skip blank rows
            continue

        rule_id    = str(get(row, "Rule ID") or "").strip()
        severity   = str(get(row, "Severity") or "Medium").strip()
        file_path  = str(get(row, "File Path") or "").strip()
        line_start = get(row, "Line Start")
        line_end   = get(row, "Line End")

        source_ctx = extract_source_context(
            source_dir, file_path, line_start, line_end
        )

        warnings.append({
            "warning_id":    str(get(row, "Warning ID") or "").strip(),
            "tool_name":     str(get(row, "Tool Name")  or "").strip(),
            "category":      str(get(row, "Category")   or "").strip(),
            "checker_name":  str(get(row, "Checker Name") or "").strip(),
            "rule_id":       rule_id,
            "severity":      severity,
            "severity_rank": SEVERITY_RANK.get(severity, 1),
            "message":       str(get(row, "Message") or "").strip(),
            "file_path":     file_path,
            "line_start":    int(line_start) if line_start else None,
            "line_end":      int(line_end)   if line_end   else None,
            "function_name": str(get(row, "Function Name") or "").strip(),
            "source_context": source_ctx,
        })

    # Sort by severity descending (High first), then by file+line
    warnings.sort(key=lambda w: (
        -w["severity_rank"],
        w["file_path"],
        w["line_start"] or 0,
    ))

    return warnings


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: python parse_polyspace_report.py <report.xlsx> <source_dir> <output.json>")
        return 2

    xlsx_path  = Path(sys.argv[1])
    source_dir = Path(sys.argv[2])
    out_path   = Path(sys.argv[3])

    print(f"Parsing {xlsx_path} ...")
    warnings = parse_report(xlsx_path, source_dir)
    print(f"  Parsed {len(warnings)} warnings")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"warning_count": len(warnings), "warnings": warnings},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  Output: {out_path}")

    # Quick summary
    from collections import Counter
    sev = Counter(w["severity"] for w in warnings)
    rules = Counter(w["rule_id"] for w in warnings)
    print(f"\nSeverity breakdown: {dict(sev)}")
    print(f"Unique rules: {len(rules)}  — {sorted(rules.keys())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())