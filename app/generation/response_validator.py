# app/generation/response_validator.py
"""
Generic fix validator.

Checks ALL fix suggestions for universal unsafe patterns:
  - invented numeric constants
  - new symbols not in original code
  - variable-length arrays
  - pointer casts to/from void* or int*
  - declaration converted to definition with initialiser

No rule-specific branches. Every rule gets the same generic safety checks.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _compact_text(value: Any) -> str:
    return re.sub(r"\s+", " ", _safe_text(value)).strip()


# ---------------------------------------------------------------------------
# Generic unsafe-pattern detectors
# ---------------------------------------------------------------------------

def _contains_unsafe_pointer_cast(code: str) -> bool:
    """
    Detects (int*), (void*), (char*) style pointer casts that the LLM tends
    to hallucinate when it does not have enough KB context.
    """
    return bool(re.search(r"\(\s*(int|void|char|uint\w*|int\w*)\s*\*\s*\)", code))


def _contains_magic_number(original_code: str, patched_code: str) -> bool:
    """
    Detects numeric literals in the patch that do NOT appear in the original.
    Example: original has no '10' → patch adds arr[10] → magic number.
    Allows 0 and 1 — these are almost always safe constants.
    """
    original_nums = set(re.findall(r"\b\d+\b", original_code))
    patch_nums    = set(re.findall(r"\b\d+\b", patched_code))
    invented      = patch_nums - original_nums - {"0", "1"}
    return len(invented) > 0


def _contains_vla_pattern(code: str) -> bool:
    """
    Detects variable-length array declarations like: int arr[n];
    where the bound is an identifier, not a literal or macro.
    """
    return bool(re.search(r"\[\s*[A-Za-z_][A-Za-z0-9_]*\s*\]", code))


def _introduces_new_symbol(original_code: str, patched_code: str) -> bool:
    """
    Detects new typed variable declarations in the patch that
    do not appear in the original snippet.
    Only flags actual declarations (int x, uint8_t y etc.), not uses.
    """
    original_tokens = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", original_code))
    patched_decl_tokens = set(re.findall(
        r"\b(?:int|char|short|long|float|double|uint\d+_t|int\d+_t)\s+([A-Za-z_][A-Za-z0-9_]*)",
        patched_code,
    ))
    unseen = [tok for tok in patched_decl_tokens if tok not in original_tokens]
    return len(unseen) > 0


def _converts_decl_to_definition(original_code: str, patched_code: str) -> bool:
    """
    Catches cases where the patch turns an extern declaration into an
    initialised definition, e.g.  extern int x;  →  int x = 0;
    This is only flagged when the original contained 'extern' and the
    patch adds an initialiser (= ...) without 'extern'.
    """
    if "extern" not in original_code:
        return False
    if "extern" in patched_code:
        return False   # kept extern, fine
    # patch removed extern AND added an initialiser
    return bool(re.search(r"=\s*[^=]", patched_code))


# ---------------------------------------------------------------------------
# Per-fix validator  (generic — no rule_id checks)
# ---------------------------------------------------------------------------

def _validate_single_fix(
    original_code: str,
    fix: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    """
    Run all generic safety checks on one fix suggestion.
    Returns (keep: bool, rejection_reasons: List[str]).
    """
    reasons: List[str] = []
    patched_code = _safe_text(fix.get("patched_code"))

    if not patched_code or patched_code == "insufficient evidence from retrieved context":
        reasons.append("No patched_code provided.")
        return False, reasons

    if _contains_unsafe_pointer_cast(patched_code):
        reasons.append("Patch contains unsafe pointer cast (int*, void*, char*).")

    if _contains_magic_number(original_code, patched_code):
        reasons.append(
            "Patch introduces numeric constant not present in original code. "
            "Cannot verify this value is correct without additional context."
        )

    if _contains_vla_pattern(patched_code):
        reasons.append("Patch introduces variable-length array (MISRA Rule 18.8 violation).")

    if _introduces_new_symbol(original_code, patched_code):
        reasons.append(
            "Patch declares new variable(s) not present in original snippet. "
            "Cannot verify these are safe to introduce."
        )

    if _converts_decl_to_definition(original_code, patched_code):
        reasons.append(
            "Patch removes 'extern' and adds initialiser, "
            "converting a declaration into a definition without evidence this is safe."
        )

    return len(reasons) == 0, reasons


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def filter_and_validate_response(
    result: Dict[str, Any],
    *,
    rule_id: str,
    code_snippet: str,
) -> Dict[str, Any]:
    """
    Validate all fix suggestions in the LLM response.
    Applies generic safety checks to every fix regardless of rule_id.
    Updates rankings after filtering.
    Appends rejection notes to traceability.limitations.
    """
    validated = dict(result)
    fixes = validated.get("fix_suggestions", [])
    if not isinstance(fixes, list):
        fixes = []

    original_code = _compact_text(code_snippet)

    filtered: List[Dict[str, Any]] = []
    validator_notes: List[str] = []

    for fix in fixes:
        if not isinstance(fix, dict):
            continue

        keep, reasons = _validate_single_fix(original_code, fix)

        if keep:
            filtered.append(fix)
        else:
            title = _safe_text(fix.get("title")) or "Unnamed fix"
            validator_notes.append(
                f"Rejected '{title}': " + "; ".join(reasons)
            )

    # Re-number ranks after filtering
    for i, fix in enumerate(filtered, start=1):
        fix["rank"] = i

    validated["fix_suggestions"] = filtered

    # Write rejection notes into traceability
    traceability = validated.get("traceability", {})
    if not isinstance(traceability, dict):
        traceability = {}

    limitations = traceability.get("limitations", [])
    if not isinstance(limitations, list):
        limitations = []

    limitations.extend(validator_notes)

    if not filtered:
        limitations.append(
            "All generated fix suggestions were rejected by the generic safety validator. "
            "The LLM output contained unsafe patterns (magic numbers, pointer casts, "
            "new symbols, or VLAs). Review the raw LLM output manually."
        )

    traceability["limitations"] = limitations
    validated["traceability"] = traceability

    return validated