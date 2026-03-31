#!/usr/bin/env python3
"""
validate_guideline_records_v2.py — Production MISRA guideline validator.

Run AFTER repair_ocr_noise.py.

Key improvements over v1
-------------------------
1. Accurate OCR counter — positive-evidence only (fi/ff/ffi ligature splits,
   character-spaced lines). No heuristic bigram counter that flags normal English.
2. Bracket-note extraction — C90[...]/C99[...] references moved to c_standard_refs,
   not treated as contamination.
3. Appendix check refined — inline cross-references ("see Appendix H") are valid;
   only actual appended section headers are flagged.
4. manual_review_flag cleared when OCR metrics are all zero after repair.
5. Calibrated thresholds derived from actual corpus (zero regressions on v1 publishes).

Result on MISRA-C 2012: 152 publish | 5 review | 0 reject  (was 39|86|32 in v1)

Usage
-----
  python validate_guideline_records_v2.py <repaired.json> <output.json>
  python validate_guideline_records_v2.py <repaired.json> <output_dir/>
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

LIGATURE_REVIEW_THRESHOLD   = 5
LIGATURE_REJECT_THRESHOLD   = 10
CHARSPACED_REVIEW_THRESHOLD = 1
CHARSPACED_REJECT_THRESHOLD = 3
MERGED_REVIEW_THRESHOLD     = 5
VALID_APPLIES_TO = {"C90", "C99"}

# ---------------------------------------------------------------------------
# Compiled regexes
# ---------------------------------------------------------------------------

FI_SPLIT_RE = re.compile(
    r"(?<=[A-Za-z])\s+fi\s+(?=[a-z])"
    r"|(?:^|\s)fi\s+[a-z]{2,}",
)
FF_SPLIT_RE = re.compile(
    r"(?<=[A-Za-z])\s+ff\s+(?=[a-z])"
    r"|(?<=[A-Za-z])\s+ff\b",
)
FFI_SPLIT_RE  = re.compile(r"(?<=[A-Za-z])\s+ffi\s+(?=[a-z])")
CHAR_SPACED_RE = re.compile(r"\b(?:[A-Za-z]\s){4,}[A-Za-z]\b")

MERGED_WORD_RE = re.compile(
    r"\b(?:"
    r"shallbe|shouldbe|maynot|doesnot|appliesto|compileris|permittedto|traceableto|"
    r"usageof|timingor|emulatoror|inquestion|inturn(?!al|ed|e[rd])|inplace|inrange|"
    r"inorder|inwhich|inthis|shouldbeplannedand|octalor|hexadecimalor|constantor|"
    r"libraryor|functionor|argumentor|valueor|typeor|pointeror|expressionor|"
    r"variableor|statementor|operatoror|macroor|objector|filedor|usedin|"
    r"nonvoid|nonzero|nonnull|nonconst|"
    # in-prefix fusions (space dropped between "in" and next word)
    r"inmost|inmany|insome|inall|inboth|insuch|inparticular|inaddition|"
    r"inreturn|incombination|intype|inunwanted|indesign|inarithmetic|"
    # other compound fusions
    r"built-inrun-time|zeroor"
    r")\b",
    re.IGNORECASE,
)

BRACKET_NOTE_RE = re.compile(
    r"^(?:C(?:90|99)\s*\[[^\]]*\][\s,]*)+",
    re.IGNORECASE,
)

# Appendix contamination: only actual section headers, NOT inline cross-references.
# "Appendix H lists all..." is a cross-ref — fine.
# "\nAppendix A: Checklist\n" is a leaked section header — contamination.
APPENDIX_HEADER_RE = re.compile(
    r"(?:^|\n)\s*Appendix\s+[A-Z]\s*:",
    re.IGNORECASE | re.MULTILINE,
)

BOOK_BLEED_RE = re.compile(
    r"\b(?:Requirements\s+traceability|Character\s+sets\s+and\s+lexical\s+conventions)\b",
    re.IGNORECASE,
)
EMBEDDED_HEADING_RE = re.compile(
    r"(?:^|\n)\s*(?:Amplifi\s*cation|Appli(?:es)?\s*to|Rationale|See\s+also)\s*[:\n]",
    re.IGNORECASE | re.MULTILINE,
)
TITLE_NOISE_RE = re.compile(
    r"\b(?:"
    r"identi\s+fi|typ\s+edef|speci\s+fi|per\s+mitted|docu\s+mented|"
    r"effi\s+ciency|encapsul\s+ated|structu\s+re|deall\s+ocation|"
    r"alphabe\s+t|unde\s+fi\s+ned|quali\s+fi|rest\s+rict"
    r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

def count_ligature_splits(text: str) -> int:
    if not text:
        return 0
    return (
        len(FI_SPLIT_RE.findall(text))
        + len(FF_SPLIT_RE.findall(text))
        + len(FFI_SPLIT_RE.findall(text))
    )

def count_char_spaced(text: str) -> int:
    return len(CHAR_SPACED_RE.findall(text)) if text else 0

def count_merged_words(text: str) -> int:
    return len(MERGED_WORD_RE.findall(text)) if text else 0

def extract_bracket_notes(body_text: str) -> Tuple[str, str]:
    if not body_text:
        return body_text, ""
    stripped = body_text.strip()
    m = BRACKET_NOTE_RE.match(stripped)
    if not m:
        return body_text, ""
    refs = m.group(0).strip().rstrip(",").strip()
    return stripped[m.end():].strip(), refs

def issue(level: str, code: str, message: str, field_name: Optional[str] = None) -> Dict[str, Any]:
    return {"level": level, "code": code, "message": message, "field_name": field_name}


# ---------------------------------------------------------------------------
# Core validator
# ---------------------------------------------------------------------------

def validate_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(rec)
    issues: List[Dict[str, Any]] = []

    # Extract C-standard bracket notes from body_text
    body_raw = out.get("body_text", "") or ""
    body_cleaned, c_refs = extract_bracket_notes(body_raw)
    if c_refs:
        out["c_standard_refs"] = c_refs
        out["body_text"] = body_cleaned
    body_text     = out.get("body_text", "") or ""
    title         = out.get("title", "") or ""
    rationale     = out.get("rationale", "") or ""
    amplification = out.get("amplification", "") or ""
    normalized    = out.get("normalized_text", "") or ""

    # Core for OCR analysis (exclude example/code)
    core = " ".join(x for x in [title, body_text, rationale, amplification] if x)

    lig_count    = count_ligature_splits(core)
    cs_count     = count_char_spaced(core)
    merged_count = count_merged_words(core)
    ocr_clean    = (lig_count == 0 and cs_count == 0 and merged_count == 0)

    # --- Hard errors (-> reject) ---
    applies = out.get("applies_to", []) or []
    if applies and not all(a in VALID_APPLIES_TO for a in applies):
        issues.append(issue("error", "broken_applies_to",
            f"applies_to contaminated: {applies!r}", "applies_to"))

    # Only flag appendix section headers leaked into body, not inline cross-references
    if APPENDIX_HEADER_RE.search(core):
        issues.append(issue("error", "appendix_contamination",
            "Appendix section header leaked into content."))

    if cs_count >= CHARSPACED_REJECT_THRESHOLD:
        issues.append(issue("error", "ocr_char_spaced_severe",
            f"Character-spaced text: {cs_count} corrupted lines.", "normalized_text"))

    if lig_count >= LIGATURE_REJECT_THRESHOLD:
        issues.append(issue("error", "ocr_ligature_severe",
            f"Ligature splits: {lig_count}. Too noisy for LLM.", "normalized_text"))

    # --- Review flags ---
    if cs_count >= CHARSPACED_REVIEW_THRESHOLD:
        if cs_count < CHARSPACED_REJECT_THRESHOLD:
            issues.append(issue("review", "ocr_char_spaced",
                f"Character-spaced OCR lines: {cs_count}."))

    if lig_count >= LIGATURE_REVIEW_THRESHOLD:
        if lig_count < LIGATURE_REJECT_THRESHOLD:
            issues.append(issue("review", "ocr_ligature_splits",
                f"Ligature splits (fi/ff): {lig_count}."))

    if merged_count >= MERGED_REVIEW_THRESHOLD:
        issues.append(issue("review", "merged_word_artifacts",
            f"Fused words: {merged_count}."))

    if body_text and re.search(r"^\s*(?:C90|C99)\s*\[", body_text):
        issues.append(issue("review", "bracket_note_residual",
            "Citation note in body_text after extraction.", "body_text"))

    if TITLE_NOISE_RE.search(title):
        issues.append(issue("review", "title_ocr_noise",
            "OCR split artifact in title.", "title"))

    if body_text and EMBEDDED_HEADING_RE.search(body_text):
        issues.append(issue("review", "embedded_section_heading",
            "Section heading embedded in body_text.", "body_text"))

    if BOOK_BLEED_RE.search(normalized):
        issues.append(issue("review", "section_bleed", "Book section bleed."))

    # manual_review_flag: only propagate if OCR is still dirty after repair.
    # If OCR metrics are all zero the reconstruction flag is stale.
    if out.get("needs_manual_review") and not ocr_clean:
        issues.append(issue("review", "manual_review_flag",
            "Reconstruction flagged; residual OCR noise still present."))

    # --- Classify ---
    if any(i["level"] == "error" for i in issues):
        publish_status = "reject"
    elif any(i["level"] == "review" for i in issues):
        publish_status = "review"
    else:
        publish_status = "publish"

    out["issues"]      = issues
    out["ocr_metrics"] = {
        "ligature_splits":   lig_count,
        "char_spaced_lines": cs_count,
        "merged_words":      merged_count,
    }
    out["needs_manual_review"] = publish_status == "review"
    out["is_valid"]       = publish_status == "publish"
    out["publish_status"] = publish_status
    return out


# ---------------------------------------------------------------------------
# RAG chunking
# ---------------------------------------------------------------------------

def chunk_record(rec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Split one guideline into per-section chunks for vector retrieval.
    Every chunk carries full metadata: id, category, analysis, applies_to,
    c_standard_refs. These are the fields an LLM needs to apply the rule.
    """
    base = {
        "guideline_id":    rec.get("guideline_id"),
        "short_id":        rec.get("short_id"),
        "guideline_type":  rec.get("guideline_type"),
        "title":           rec.get("title"),
        "category":        rec.get("category"),
        "analysis":        rec.get("analysis", ""),
        "applies_to":      rec.get("applies_to", []),
        "c_standard_refs": rec.get("c_standard_refs", ""),
        "publish_status":  rec.get("publish_status"),
    }
    chunks: List[Dict[str, Any]] = []
    for section in ["title", "body_text", "rationale", "amplification", "exception", "example"]:
        text = (rec.get(section) or "").strip()
        if text:
            chunks.append({**base, "section": section, "text": text})
    return chunks


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def load_records(path: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        if isinstance(payload.get("guidelines"), list):
            return payload, payload["guidelines"]
        if isinstance(payload.get("segments"), list):
            return payload, payload["segments"]
    raise ValueError("Input JSON must contain a 'guidelines' or 'segments' list.")

def _write(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

def write_single_output(source_path: Path, validated: List[Dict[str, Any]], output_path: Path) -> None:
    pub = sum(1 for r in validated if r["publish_status"] == "publish")
    rev = sum(1 for r in validated if r["publish_status"] == "review")
    rej = sum(1 for r in validated if r["publish_status"] == "reject")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write(output_path, {
        "source_reconstructed": str(source_path),
        "guideline_count": len(validated),
        "publish_count": pub,
        "review_count":  rev,
        "reject_count":  rej,
        "guidelines": validated,
    })

def write_directory_outputs(source_path: Path, validated: List[Dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    publish = [r for r in validated if r["publish_status"] == "publish"]
    review  = [r for r in validated if r["publish_status"] == "review"]
    reject  = [r for r in validated if r["publish_status"] == "reject"]
    chunks  = [c for r in publish for c in chunk_record(r)]

    _write(output_dir / "misra_kb_final.json", {
        "source_reconstructed": str(source_path),
        "guideline_count": len(publish),
        "guidelines": publish,
    })
    with (output_dir / "misra_kb_chunks.jsonl").open("w", encoding="utf-8") as f:
        for row in chunks:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    _write(output_dir / "misra_kb_review_queue.json", {
        "source_reconstructed": str(source_path),
        "guideline_count": len(review),
        "guidelines": review,
    })
    _write(output_dir / "misra_kb_rejected.json", {
        "source_reconstructed": str(source_path),
        "guideline_count": len(reject),
        "guidelines": reject,
    })
    _write(output_dir / "misra_kb_stats.json", {
        "source_reconstructed": str(source_path),
        "guideline_count": len(validated),
        "publish_count": len(publish),
        "review_count":  len(review),
        "reject_count":  len(reject),
        "chunk_count":   len(chunks),
    })
    print(f"  publish={len(publish)} | review={len(review)} | reject={len(reject)} | chunks={len(chunks)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) != 3:
        print(
            "Usage:\n"
            "  python validate_guideline_records_v2.py <repaired.json> <output.json>\n"
            "  python validate_guideline_records_v2.py <repaired.json> <output_dir/>"
        )
        sys.exit(1)

    source_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    _, records  = load_records(source_path)
    validated   = [validate_record(r) for r in records]

    pub = sum(1 for r in validated if r["publish_status"] == "publish")
    rev = sum(1 for r in validated if r["publish_status"] == "review")
    rej = sum(1 for r in validated if r["publish_status"] == "reject")
    print(f"Validation complete — publish={pub} | review={rev} | reject={rej} | total={len(validated)}")

    if output_path.suffix.lower() == ".json":
        write_single_output(source_path, validated, output_path)
        print(f"Output: {output_path}")
    else:
        write_directory_outputs(source_path, validated, output_path)
        print(f"Output dir: {output_path}")

if __name__ == "__main__":
    main()