#!/usr/bin/env python3
"""
repair_ocr_noise.py — Phase 3.5: targeted OCR repair on review/reject records.

Run AFTER reconstruct_and_normalize, BEFORE validate_guideline_records_v2.

This script applies three deterministic repairs to records that still contain
OCR noise:

  1. CHAR-SPACED COLLAPSE
     "T h e t e c h n i q u e" -> "The technique"
     Algorithm: detect sequences of single letters separated by spaces (4+ chars),
     collapse by removing the inter-character spaces.
     Why: these are entire sentences garbled by PDF column-extraction. The collapsed
     result is always correct because the original text had no spaces between chars.

  2. LIGATURE-SPLIT REPAIR
     "speci fi cation" -> "specification"
     "unde fi ned"     -> "undefined"
     "identi fi er"    -> "identifier"
     "bene fi cial"    -> "beneficial"
     "e ff ect"        -> "effect"
     Algorithm: for each known fi/ff/ffi split pattern, rejoin the fragments.
     Why: PDF ligature extraction fractures fi/ff/ffi glyphs into isolated tokens.

  3. MERGED-WORD SPLIT
     "inwhich" -> "in which"   "octalor" -> "octal or"   "libraryor" -> "library or"
     Algorithm: explicit lookup table of known-bad fused tokens -> correct form.
     Why: PDF extraction drops word boundaries at certain font transitions.

All repairs are:
- Deterministic (same input -> same output always)
- Conservative (only fix patterns with known correct forms)
- Non-destructive of code/example blocks
- CI/CD safe (no network, no randomness)

Usage
-----
  python repair_ocr_noise.py <reconstructed.json> <repaired.json>

Then run:
  python validate_guideline_records_v2.py <repaired.json> <output.json>
"""

from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Text fields to repair (never touch code/example blocks)
# ---------------------------------------------------------------------------

PROSE_FIELDS = ["title", "body_text", "rationale", "amplification", "exception", "see_also"]

# ---------------------------------------------------------------------------
# Repair 1 — Character-spaced collapse
# ---------------------------------------------------------------------------

# Matches 4+ single letters each followed by a space, then a final letter.
# e.g. "T h e t e c h n i q u e" or "p r o g r a m m e r"
CHAR_SPACED_RE = re.compile(r"\b(?:[A-Za-z]\s){4,}[A-Za-z]\b")


def _collapse_char_spaced(text: str) -> str:
    """Remove inter-character spaces from spaced-letter sequences."""
    def _rejoin(m: re.Match) -> str:
        return re.sub(r"\s+", "", m.group(0))
    return CHAR_SPACED_RE.sub(_rejoin, text)


# ---------------------------------------------------------------------------
# Repair 2 — Ligature-split repair
# ---------------------------------------------------------------------------
# Each entry: (search_pattern, replacement)
# Ordered from most specific to least specific to avoid partial-match issues.

LIGATURE_REPAIRS: List[Tuple[re.Pattern, str]] = [
    # ffi ligature (most specific — do first)
    (re.compile(r"\be\s+ffi\s+cien(?:cy|t|tly)\b", re.IGNORECASE), lambda m: re.sub(r"\s+", "", m.group(0))),
    (re.compile(r"\bsuf\s+fi\s+x\b",               re.IGNORECASE), "suffix"),
    # ff ligature
    (re.compile(r"\bdi\s+ff\s+er",                  re.IGNORECASE), lambda m: re.sub(r"\s+", "", m.group(0))),
    (re.compile(r"\be\s+ff\s+ect",                  re.IGNORECASE), lambda m: re.sub(r"\s+", "", m.group(0))),
    (re.compile(r"\bo\s+ff\s+set",                  re.IGNORECASE), lambda m: re.sub(r"\s+", "", m.group(0))),
    (re.compile(r"\bo\s+ff\b",                      re.IGNORECASE), lambda m: re.sub(r"\s+", "", m.group(0))),
    (re.compile(r"\ba\s+ff\b",                      re.IGNORECASE), lambda m: re.sub(r"\s+", "", m.group(0))),
    # fi ligature — known-word specific patterns (safest)
    (re.compile(r"\bunde\s+fi\s+ned\b",             re.IGNORECASE), "undefined"),
    (re.compile(r"\bunspeci\s+fi\s+ed\b",           re.IGNORECASE), "unspecified"),
    (re.compile(r"\bspeci\s+fi\s+ed\b",             re.IGNORECASE), "specified"),
    (re.compile(r"\bspeci\s+fi\s+c\b",              re.IGNORECASE), "specific"),
    (re.compile(r"\bspeci\s+fi\s+cation\b",         re.IGNORECASE), "specification"),
    (re.compile(r"\bspeci\s+fi\s+es\b",             re.IGNORECASE), "specifies"),
    (re.compile(r"\bspeci\s+fi\s+er\b",             re.IGNORECASE), "specifier"),
    (re.compile(r"\bidenti\s+fi\s+er",              re.IGNORECASE), "identifier"),
    (re.compile(r"\bidenti\s+fi\s+ca",              re.IGNORECASE), "identifica"),
    (re.compile(r"\bsigni\s+fi\s+cant",             re.IGNORECASE), "significant"),
    (re.compile(r"\bsigni\s+fi\s+c\b",              re.IGNORECASE), "signific"),
    (re.compile(r"\bquali\s+fi\s+",                 re.IGNORECASE), "qualifi"),
    (re.compile(r"\bquali\s+fi\b",                  re.IGNORECASE), "qualify"),
    (re.compile(r"\bjusti\s+fi",                    re.IGNORECASE), "justifi"),
    (re.compile(r"\bmodi\s+fi",                     re.IGNORECASE), "modifi"),
    (re.compile(r"\bde\s+fi\s+n",                   re.IGNORECASE), "defin"),
    (re.compile(r"\bde\s+fi\s+ned\b",               re.IGNORECASE), "defined"),
    (re.compile(r"\bde\s+fi\s+ning\b",              re.IGNORECASE), "defining"),
    (re.compile(r"\bde\s+fi\s+nition\b",            re.IGNORECASE), "definition"),
    (re.compile(r"\bde\s+fi\s+nes\b",               re.IGNORECASE), "defines"),
    (re.compile(r"\bveri\s+fi",                     re.IGNORECASE), "verifi"),
    (re.compile(r"\bclarifyi\s+fi",                 re.IGNORECASE), "clarifyi"),  # edge case
    (re.compile(r"\bcerti\s+fi",                    re.IGNORECASE), "certifi"),
    (re.compile(r"\bclassi\s+fi",                   re.IGNORECASE), "classifi"),
    (re.compile(r"\bnoti\s+fi",                     re.IGNORECASE), "notifi"),
    (re.compile(r"\bampli\s+fi",                    re.IGNORECASE), "amplifi"),
    (re.compile(r"\bampli\s+fi\s+cation\b",         re.IGNORECASE), "amplification"),
    (re.compile(r"\bspeci\s+fi\s+c\b",              re.IGNORECASE), "specific"),
    (re.compile(r"\bbene\s+fi\s+cial\b",            re.IGNORECASE), "beneficial"),
    (re.compile(r"\bsatis\s+fi",                    re.IGNORECASE), "satisfi"),
    (re.compile(r"\bunquali\s+fi",                  re.IGNORECASE), "unqualifi"),
    # fi as word-start (field, first, final)
    (re.compile(r"(?<!\w)fi\s+eld\b",               re.IGNORECASE), "field"),
    (re.compile(r"(?<!\w)fi\s+elds\b",              re.IGNORECASE), "fields"),
    (re.compile(r"(?<!\w)fi\s+rst\b",               re.IGNORECASE), "first"),
    (re.compile(r"(?<!\w)fi\s+nal\b",               re.IGNORECASE), "final"),
    (re.compile(r"(?<!\w)fi\s+xed\b",               re.IGNORECASE), "fixed"),
    (re.compile(r"(?<!\w)fi\s+le\b",                re.IGNORECASE), "file"),
    (re.compile(r"(?<!\w)fi\s+les\b",               re.IGNORECASE), "files"),
]


def _apply_ligature_repairs(text: str) -> str:
    for pattern, replacement in LIGATURE_REPAIRS:
        if callable(replacement):
            text = pattern.sub(replacement, text)
        else:
            text = pattern.sub(replacement, text)
    return text


# ---------------------------------------------------------------------------
# Repair 3 — Merged-word split
# ---------------------------------------------------------------------------
# Explicit lookup: fused_token -> correct_text
# Only include tokens where the correct split is unambiguous.

MERGED_SPLITS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\bshallbe\b",           re.IGNORECASE), "shall be"),
    (re.compile(r"\bshouldbe\b",          re.IGNORECASE), "should be"),
    (re.compile(r"\bmaynot\b",            re.IGNORECASE), "may not"),
    (re.compile(r"\bdoesnot\b",           re.IGNORECASE), "does not"),
    (re.compile(r"\bappliesto\b",         re.IGNORECASE), "applies to"),
    (re.compile(r"\bpermittedto\b",       re.IGNORECASE), "permitted to"),
    (re.compile(r"\btraceableto\b",       re.IGNORECASE), "traceable to"),
    (re.compile(r"\busageof\b",           re.IGNORECASE), "usage of"),
    (re.compile(r"\btimingor\b",          re.IGNORECASE), "timing or"),
    (re.compile(r"\bemulatoror\b",        re.IGNORECASE), "emulator or"),
    (re.compile(r"\binquestion\b",        re.IGNORECASE), "in question"),
    (re.compile(r"\binplace\b",           re.IGNORECASE), "in place"),
    (re.compile(r"\binrange\b",           re.IGNORECASE), "in range"),
    (re.compile(r"\binorder\b",           re.IGNORECASE), "in order"),
    (re.compile(r"\binwhich\b",           re.IGNORECASE), "in which"),
    (re.compile(r"\binthis\b",            re.IGNORECASE), "in this"),
    (re.compile(r"\boctalor\b",           re.IGNORECASE), "octal or"),
    (re.compile(r"\bhexadecimalor\b",     re.IGNORECASE), "hexadecimal or"),
    (re.compile(r"\bconstantor\b",        re.IGNORECASE), "constant or"),
    (re.compile(r"\blibraryor\b",         re.IGNORECASE), "library or"),
    (re.compile(r"\bfunctionor\b",        re.IGNORECASE), "function or"),
    (re.compile(r"\bargumentor\b",        re.IGNORECASE), "argument or"),
    (re.compile(r"\bvalueor\b",           re.IGNORECASE), "value or"),
    (re.compile(r"\btypeor\b",            re.IGNORECASE), "type or"),
    (re.compile(r"\bpointeror\b",         re.IGNORECASE), "pointer or"),
    (re.compile(r"\bexpressionor\b",      re.IGNORECASE), "expression or"),
    (re.compile(r"\bvariableor\b",        re.IGNORECASE), "variable or"),
    (re.compile(r"\bstatementor\b",       re.IGNORECASE), "statement or"),
    (re.compile(r"\boperatoror\b",        re.IGNORECASE), "operator or"),
    (re.compile(r"\bmacroor\b",           re.IGNORECASE), "macro or"),
    (re.compile(r"\bobjector\b",          re.IGNORECASE), "object or"),
    (re.compile(r"\busedin\b",            re.IGNORECASE), "used in"),
    # inturn: only fix when NOT part of "internal", "internet" etc.
    (re.compile(r"\binturn\b(?!al|et|ed|er|ing|s\b)", re.IGNORECASE), "in turn"),

    # ── in-prefix fusions ──────────────────────────────────────────────────
    # All confirmed OCR artifacts: space dropped between "in" and next word.
    (re.compile(r"\bInmost\b"),                           "In most"),
    (re.compile(r"\binmost\b"),                           "in most"),
    (re.compile(r"\bInmany\b"),                           "In many"),
    (re.compile(r"\binmany\b"),                           "in many"),
    (re.compile(r"\bInsome\b"),                           "In some"),
    (re.compile(r"\binsome\b"),                           "in some"),
    (re.compile(r"\binall\b",    re.IGNORECASE),          "in all"),
    (re.compile(r"\binboth\b",   re.IGNORECASE),          "in both"),
    (re.compile(r"\bInsuch\b"),                           "In such"),
    (re.compile(r"\binsuch\b"),                           "in such"),
    (re.compile(r"\bInparticular\b"),                     "In particular"),
    (re.compile(r"\binparticular\b"),                     "in particular"),
    (re.compile(r"\bInaddition\b"),                       "In addition"),
    (re.compile(r"\binaddition\b"),                       "in addition"),
    (re.compile(r"\binreturn\b",      re.IGNORECASE),     "in return"),
    (re.compile(r"\bincombination\b", re.IGNORECASE),     "in combination"),
    (re.compile(r"\bintype\b",        re.IGNORECASE),     "in type"),
    (re.compile(r"\binunwanted\b",    re.IGNORECASE),     "in unwanted"),
    (re.compile(r"\bindesign\b",      re.IGNORECASE),     "in design"),
    (re.compile(r"\binarithmetic\b",  re.IGNORECASE),     "in arithmetic"),

    # ── other missed compound fusions ─────────────────────────────────────
    (re.compile(r"\bbuilt-inrun-time\b", re.IGNORECASE),  "built-in run-time"),
    (re.compile(r"\bzeroor\b",           re.IGNORECASE),  "zero or"),
    (re.compile(r"\bl\s+imited\b",       re.IGNORECASE),  "limited"),
    (re.compile(r"\bconfl\s+ict\b",      re.IGNORECASE),  "conflict"),
    (re.compile(r"\bstanda\s+rds\b",     re.IGNORECASE),  "standards"),
]


def _apply_merged_splits(text: str) -> str:
    for pattern, replacement in MERGED_SPLITS:
        text = pattern.sub(replacement, text)
    return text


# ---------------------------------------------------------------------------
# Post-repair normalisation
# ---------------------------------------------------------------------------

def _normalise_spaces(text: str) -> str:
    """Collapse multiple spaces, clean up around punctuation."""
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" +\n", "\n", text)
    text = re.sub(r"\n +", "\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Full repair pipeline for a single text value
# ---------------------------------------------------------------------------

def repair_text(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        return text
    text = _collapse_char_spaced(text)
    text = _apply_ligature_repairs(text)
    text = _apply_merged_splits(text)
    text = _normalise_spaces(text)
    return text


# ---------------------------------------------------------------------------
# Rebuild normalized_text from repaired fields
# ---------------------------------------------------------------------------

SECTION_ORDER = [
    ("title",         None),
    ("body_text",     None),
    ("applies_to",    "Applies to"),
    ("rationale",     "Rationale"),
    ("amplification", "Amplification"),
    ("exception",     "Exception"),
    ("example",       "Example"),
    ("see_also",      "See also"),
]


def rebuild_normalized(record: Dict[str, Any]) -> str:
    parts: List[str] = []
    title = str(record.get("title") or "").strip()
    if title:
        parts.append(title)
    for field, header in SECTION_ORDER[1:]:
        value = str(record.get(field) or "").strip()
        if not value:
            continue
        if header:
            parts.append(f"{header}: {value}")
        else:
            parts.append(value)
    return "\n\n".join(parts).strip()


# ---------------------------------------------------------------------------
# Record-level repair
# ---------------------------------------------------------------------------

def repair_record(record: Dict[str, Any]) -> Dict[str, Any]:
    rec = deepcopy(record)
    changed = False
    for field in PROSE_FIELDS:
        original = rec.get(field)
        if not isinstance(original, str) or not original:
            continue
        repaired = repair_text(original)
        if repaired != original:
            rec[field] = repaired
            changed = True
    if changed:
        rec["normalized_text"] = rebuild_normalized(rec)
        notes: List[str] = list(rec.get("quality_notes") or [])
        if "ocr_repair_applied" not in notes:
            notes.append("ocr_repair_applied")
        rec["quality_notes"] = notes
    return rec


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: str, payload: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def get_records(payload: Any) -> Tuple[List[Dict[str, Any]], str | None]:
    if isinstance(payload, dict):
        if isinstance(payload.get("guidelines"), list):
            return payload["guidelines"], "guidelines"
        if isinstance(payload.get("segments"), list):
            return payload["segments"], "segments"
    if isinstance(payload, list):
        return payload, None
    raise ValueError("Unsupported JSON payload shape.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: python repair_ocr_noise.py <reconstructed.json> <repaired.json>",
            file=sys.stderr,
        )
        return 2

    input_path, output_path = sys.argv[1], sys.argv[2]
    payload = load_json(input_path)
    records, key = get_records(payload)

    repaired_records: List[Dict[str, Any]] = []
    changed_count = 0
    for rec in records:
        repaired = repair_record(rec)
        if json.dumps(repaired, sort_keys=True) != json.dumps(rec, sort_keys=True):
            changed_count += 1
        repaired_records.append(repaired)

    if key is None:
        out_payload: Any = repaired_records
    else:
        out_payload = deepcopy(payload)
        out_payload[key] = repaired_records
        out_payload["guideline_count"] = len(repaired_records)
        out_payload["ocr_repair_source"] = input_path

    dump_json(output_path, out_payload)
    print(f"OCR repair complete: {changed_count}/{len(records)} records modified -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())