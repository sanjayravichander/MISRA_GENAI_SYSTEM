# app/generation/response_validator.py
"""
Generic fix validator — relaxed edition.

Only rejects fixes that are clearly unsafe or non-compilable:
  - Explicit pointer casts  (int*), (void*), (char*)
  - Variable-length array DECLARATIONS (not accesses)
  - extern declaration converted to initialised definition

Does NOT reject new numeric constants or new local variables —
those are required for valid MISRA fixes (Rules 12.2, 17.8, etc.)
and the old stricter checks were causing "No fix suggestions" for
almost every warning.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple


def _safe_text(v: Any) -> str:
    return "" if v is None else str(v).strip()

def _compact_text(v: Any) -> str:
    return re.sub(r"\s+", " ", _safe_text(v)).strip()


def _unsafe_ptr_cast(code: str) -> bool:
    """(int*), (void*), (char*) — always wrong in MISRA context."""
    return bool(re.search(r"\(\s*(?:int|void|char)\s*\*\s*\)", code))


def _vla_decl(code: str) -> bool:
    """int arr[n]; where n is a runtime identifier — VLA declaration only."""
    type_kw = (
        r"(?:int|char|short|long|float|double"
        r"|uint8_t|uint16_t|uint32_t|uint64_t"
        r"|int8_t|int16_t|int32_t|int64_t|size_t|bool)"
    )
    # lowercase identifier as bound = runtime value = VLA
    # uppercase = likely a macro/constant = fine
    return bool(re.search(
        rf"\b{type_kw}\s+[A-Za-z_]\w*\s*\[\s*[a-z_]\w*\s*\](?!\s*=)",
        code,
    ))


def _extern_to_def(orig: str, patch: str) -> bool:
    """extern x;  →  x = 0; changes linkage — genuinely dangerous."""
    if "extern" not in orig:
        return False
    if "extern" in patch:
        return False
    return bool(re.search(r"=\s*[^=]", patch))


def _validate_fix(orig: str, fix: Dict[str, Any]) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    code = _safe_text(fix.get("patched_code"))
    if not code or code in (
        "insufficient evidence from retrieved context",
        "[fix code not available]", "",
    ):
        reasons.append("No patched_code provided.")
        return False, reasons
    if _unsafe_ptr_cast(code):
        reasons.append("Contains unsafe pointer cast (int*, void*, char*).")
    if _vla_decl(code):
        reasons.append("Contains variable-length array declaration.")
    if _extern_to_def(orig, code):
        reasons.append("Converts extern declaration to initialised definition.")
    return len(reasons) == 0, reasons


def filter_and_validate_response(
    result: Dict[str, Any],
    *,
    rule_id: str,
    code_snippet: str,
) -> Dict[str, Any]:
    out = dict(result)
    fixes = out.get("fix_suggestions", [])
    if not isinstance(fixes, list):
        fixes = []

    orig = _compact_text(code_snippet)
    kept: List[Dict[str, Any]] = []
    notes: List[str] = []

    for fix in fixes:
        if not isinstance(fix, dict):
            continue
        ok, reasons = _validate_fix(orig, fix)
        if ok:
            kept.append(fix)
        else:
            title = _safe_text(fix.get("title")) or "Unnamed fix"
            notes.append(f"Rejected '{title}': " + "; ".join(reasons))

    for i, f in enumerate(kept, 1):
        f["rank"] = i

    out["fix_suggestions"] = kept

    tr = out.get("traceability", {})
    if not isinstance(tr, dict):
        tr = {}
    lims = tr.get("limitations", [])
    if not isinstance(lims, list):
        lims = []
    lims.extend(notes)
    if not kept:
        lims.append(
            "All fix suggestions rejected by safety validator "
            "(unsafe pointer casts, VLA declarations, or extern conversion)."
        )
    tr["limitations"] = lims
    out["traceability"] = tr
    return out