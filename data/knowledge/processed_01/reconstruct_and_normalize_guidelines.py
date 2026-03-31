from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SECTION_HEADER_PATTERNS = {
    "rationale": re.compile(r"^rationale$", re.IGNORECASE),
    "amplification": re.compile(r"^amplifi\s*cation$", re.IGNORECASE),
    "exception": re.compile(r"^exception$", re.IGNORECASE),
    "example": re.compile(r"^example$", re.IGNORECASE),
    "seealso": re.compile(r"^see\s*also$", re.IGNORECASE),
}

SECTION_HEADER_ALIASES = {
    "rationale": ["rationale"],
    "amplification": [
        "amplification",
        "amplifi cation",
        "amplificati on",
        "amplification the",
        "amplifi cation the",
    ],
    "exception": ["exception"],
    "example": ["example"],
    "seealso": ["see also", "seealso"],
}

CATEGORY_RE = re.compile(r"^Category\s+(.+)$", re.IGNORECASE)
APPLIES_TO_RE = re.compile(r"^(?:Applies|Applie\s*s|Appliesto)\s*to?\s+(.+)$", re.IGNORECASE)
ANALYSIS_RE = re.compile(r"^Analysis\s+(.+)$", re.IGNORECASE)
DECIDABLE_RE = re.compile(r"^Decidable$", re.IGNORECASE)
UNDECIDABLE_RE = re.compile(r"^Undecidable$", re.IGNORECASE)
SINGLE_TU_RE = re.compile(r"^Single Translation Unit$", re.IGNORECASE)
SYSTEM_RE = re.compile(r"^System$", re.IGNORECASE)
GUIDELINE_HEADER_RE = re.compile(r"^(Dir|Rule)\s+(\d+\.\d+)\s+(.+)$")
RULE_REF_RE = re.compile(r"\b(?:Dir|Rule)\s+\d+\.\d+\b")
BRACKET_NOTE_RE = re.compile(r"^\[[^\]]+\]$")
BOOK_SECTION_HEADING_RE = re.compile(r"^\d+\.\d+\s+")
PAGE_FURNITURE_RE = re.compile(
    r"(?:MISRA\s*C\s*2012\s*final\.indd|Licensed to:|ISBN|Published by)",
    re.IGNORECASE,
)

CODE_LIKE_RE = re.compile(
    r"(^\s*[{}]$)"
    r"|(^\s*#)"
    r"|(^\s*/\*)"
    r"|(^\s*\*)"
    r"|(^\s*\*/$)"
    r"|(^\s*[A-Za-z_][\w\s\*\[\]]*\([^)]*\)\s*$)"
    r"|(^\s*(if|else|switch|case|for|while|do)\b)"
    r"|(^\s*return\b)"
    r"|(^\s*[A-Za-z_]\w*\s*=\s*.*;$)"
    r"|(^\s*const\s+[A-Za-z_])"
    r"|(^\s*[A-Za-z_]\w*(\s+|\s*\*)+[A-Za-z_]\w*\s*(=\s*.+)?;$)"
    r"|(;(\s*/\*.*\*/)?$)"
)

BULLET_RE = re.compile(r"^\s*(?:•|-|–|—|\*)\s+")
GRAMMAR_RE = re.compile(
    r"^\s*(?:"
    r"[A-Za-z_][A-Za-z0-9_]*\s*::=|"
    r"\|.*|"
    r"\[[^\]]+\]\s*|"
    r"<[^>]+>\s*"
    r")"
)
META_LINE_RE = re.compile(
    r"^(?:Category|Analysis|Applies(?:\s*to)?|C90\s*\[|C99\s*\[)",
    re.IGNORECASE,
)

LIGATURE_CHAR_MAP = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\ufb05": "ft",
    "\ufb06": "st",
}

SAFE_TOKEN_REPAIRS: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bSeealso\b", re.IGNORECASE), "See also"),
    (re.compile(r"\bAppliesto\b", re.IGNORECASE), "Applies to"),
    (re.compile(r"\bheaderfile\b", re.IGNORECASE), "header file"),
    (re.compile(r"\busageof\b", re.IGNORECASE), "usage of"),
    (re.compile(r"\bshouldbe\b", re.IGNORECASE), "should be"),
    (re.compile(r"\bshallbe\b", re.IGNORECASE), "shall be"),
    (re.compile(r"\bpermittedto\b", re.IGNORECASE), "permitted to"),
    (re.compile(r"\bcompileris\b", re.IGNORECASE), "compiler is"),
    (re.compile(r"\btraceableto\b", re.IGNORECASE), "traceable to"),
    (re.compile(r"\bfunctions?\s+which\b", re.IGNORECASE), lambda m: m.group(0)),
    (re.compile(r"\bapplie\s+s\b", re.IGNORECASE), "Applies"),
    (re.compile(r"\bapplie\s+s\s+to\b", re.IGNORECASE), "Applies to"),
    (re.compile(r"\bappli\s+es\s+to\b", re.IGNORECASE), "Applies to"),
    (re.compile(r"\bamplifi\s*cation\b", re.IGNORECASE), "Amplification"),
    (re.compile(r"\berror\s*flag\b", re.IGNORECASE), "error flag"),
    (re.compile(r"\berror\s+informati\s+on\b", re.IGNORECASE), "error information"),
    (re.compile(r"\bimpleme\s+ntation\b", re.IGNORECASE), "implementation"),
    (re.compile(r"\bguideli\s+ne\b", re.IGNORECASE), "guideline"),
    (re.compile(r"\bcircumst\s+ances\b", re.IGNORECASE), "circumstances"),
    (re.compile(r"\bside\s+eff\s+ects?\b", re.IGNORECASE), "side effects"),
    (re.compile(r"\bside\s+eff\s*ects?\b", re.IGNORECASE), "side effects"),
    (
        re.compile(r"\btyp\s+edefs?\b", re.IGNORECASE),
        lambda m: "typedefs" if m.group(0).lower().endswith("s") else "typedef",
    ),
    (re.compile(r"\bspecific\s*-\s*leng\s*th\b", re.IGNORECASE), "specific-length"),
    (re.compile(r"\bspecific\s*-\s*leng\s*th\s+t\s*y\s*pes\b", re.IGNORECASE), "specific-length types"),
    (re.compile(r"\bspecific-\s*leng\s*th\s+t\s*y\s*pes\b", re.IGNORECASE), "specific-length types"),
    (re.compile(r"\bpack\s+ages\b", re.IGNORECASE), "packages"),
    (re.compile(r"\breso\s+urce\b", re.IGNORECASE), "resource"),
    (re.compile(r"\bO\s+ther\b"), "Other"),
    (re.compile(r"\bF\s+or\b"), "For"),
    (re.compile(r"\bpointertoa\b", re.IGNORECASE), "pointer to a"),
    (re.compile(r"\bfi\s+les\b", re.IGNORECASE), "files"),
    (re.compile(r"\bfi\s+le\b", re.IGNORECASE), "file"),
    (re.compile(r"\bdeall\s+ocation\b", re.IGNORECASE), "deallocation"),
    (re.compile(r"\bdocumente\s+d\b", re.IGNORECASE), "documented"),
    (re.compile(r"\bAssemb\s+ly\b"), "Assembly"),
    (re.compile(r"\bassemb\s+ly\b"), "assembly"),
    (re.compile(r"\bidentifi\s+ers\b", re.IGNORECASE), "identifiers"),
    (re.compile(r"\bidentifi\s+er\b", re.IGNORECASE), "identifier"),
    (re.compile(r"\bdefi\s+nition\b", re.IGNORECASE), "definition"),
    (re.compile(r"\bdefi\s+ned\b", re.IGNORECASE), "defined"),
    (re.compile(r"\bUndefi\s+ned\b", re.IGNORECASE), "Undefined"),
    (re.compile(r"\bunde\s+fined\b", re.IGNORECASE), "undefined"),
    (re.compile(r"\bmodifi\s+ed\b", re.IGNORECASE), "modified"),
    (re.compile(r"\bmodifi\s+cation\b", re.IGNORECASE), "modification"),
    (re.compile(r"\bmodifi\s+cations\b", re.IGNORECASE), "modifications"),
    (re.compile(r"\bspeci\s+fication\b", re.IGNORECASE), "specification"),
    (re.compile(r"\bspecifi\s+ed\b", re.IGNORECASE), "specified"),
    (re.compile(r"\bspecifi\s+c\b", re.IGNORECASE), "specific"),
    (re.compile(r"\bleng\s+th\b", re.IGNORECASE), "length"),
    (re.compile(r"\btyp\s+edef\b", re.IGNORECASE), "typedef"),
    (re.compile(r"\bstructu\s+re\b", re.IGNORECASE), "structure"),
    (re.compile(r"\bencapsul\s+ated\b", re.IGNORECASE), "encapsulated"),
    (re.compile(r"\bencapsul\s+ation\b", re.IGNORECASE), "encapsulation"),
    (re.compile(r"\bfu\s+nctions\b", re.IGNORECASE), "functions"),
    (re.compile(r"\beffi\s+ciency\b", re.IGNORECASE), "efficiency"),
    (re.compile(r"\bbene\s+ficial\b", re.IGNORECASE), "beneficial"),
    (re.compile(r"\bdi\s+ff\s+er\s+ent\b", re.IGNORECASE), "different"),
    (re.compile(r"\bdi\s+ffer\s+ent\b", re.IGNORECASE), "different"),
    (re.compile(r"\be\s+ff\s+ects\b", re.IGNORECASE), "effects"),
    (re.compile(r"\bdiffer\s+ent\b", re.IGNORECASE), "different"),
    (re.compile(r"\bles\s+s\b", re.IGNORECASE), "less"),
    (re.compile(r"\btha\s+t\b", re.IGNORECASE), "that"),
    (re.compile(r"\bpreven\s+t\b", re.IGNORECASE), "prevent"),
    (re.compile(r"\bs\s+hould\b", re.IGNORECASE), "should"),
    (re.compile(r"\bma\s+y\b", re.IGNORECASE), "may"),
    (re.compile(r"\brathe\s+r\b", re.IGNORECASE), "rather"),
    (re.compile(r"\bfl\s+oat\b", re.IGNORECASE), "float"),
    (re.compile(r"\bcomm\s+ent\b", re.IGNORECASE), "comment"),
    (
        re.compile(r"\be\s+ff\s+ects?\b", re.IGNORECASE),
        lambda m: "effects" if m.group(0).lower().endswith("s") else "effect",
    ),
    (re.compile(r"\bimpr\s*/\s*oves\b", re.IGNORECASE), "improves"),
    (re.compile(r"\bth\s*/\s*e\b", re.IGNORECASE), "the"),
    (re.compile(r"\be\s+ff\s+ect\b", re.IGNORECASE), "effect"),
    (re.compile(r"\bover\s+fl\s+ow\b", re.IGNORECASE), "overflow"),
    (re.compile(r"\bunder\s+fl\s+ow\b", re.IGNORECASE), "underflow"),
    (re.compile(r"\bred\s+undant\b", re.IGNORECASE), "redundant"),
    (re.compile(r"\ber\s+ror\b", re.IGNORECASE), "error"),
    (re.compile(r"\bca\s+nleadto\b", re.IGNORECASE), "can lead to"),
    (re.compile(r"\bvi\s+sual\b", re.IGNORECASE), "visual"),
    (re.compile(r"\bno\s+t\b", re.IGNORECASE), "not"),
    (re.compile(r"\bsh\s+all\b", re.IGNORECASE), "shall"),
    (re.compile(r"\bsho\s+uld\b", re.IGNORECASE), "should"),
    (re.compile(r"\bh\s+ave\b", re.IGNORECASE), "have"),
    (re.compile(r"\bi\s+s\b", re.IGNORECASE), "is"),
    (re.compile(r"\ba\s+nd\b", re.IGNORECASE), "and"),
    (re.compile(r"\bth\s+e\b", re.IGNORECASE), "the"),
    (re.compile(r"\bTh\s+e\b"), "The"),
    (re.compile(r"\bTh\s+is\b"), "This"),
    (re.compile(r"\bimpr\s+oves\b", re.IGNORECASE), "improves"),
    (re.compile(r"\bautomot\s+ive\b", re.IGNORECASE), "automotive"),
    (re.compile(r"\bpe\s+rmitted\b", re.IGNORECASE), "permitted"),
    (re.compile(r"\bimpl(?:ementation)?-\s*de\s*fi\s*ned\b", re.IGNORECASE), "implementation-defined"),
    (re.compile(r"\brun\s*-\s*time\b", re.IGNORECASE), "run-time"),
    (re.compile(r"\btimingor\b", re.IGNORECASE), "timing or"),
    (re.compile(r"\bemulatoror\b", re.IGNORECASE), "emulator or"),
    (re.compile(r"\binquestion\b", re.IGNORECASE), "in question"),
    (re.compile(r"\binturn\b", re.IGNORECASE), "in turn"),
    (re.compile(r"\binorder\b", re.IGNORECASE), "in order"),
    (re.compile(r"\binplace\b", re.IGNORECASE), "in place"),
    (re.compile(r"\binwhich\b", re.IGNORECASE), "in which"),
    (re.compile(r"\binthis\b", re.IGNORECASE), "in this"),
    (re.compile(r"\binrange\b", re.IGNORECASE), "in range"),
    (re.compile(r"\binunwanted\b", re.IGNORECASE), "in unwanted"),
    (re.compile(r"\boctalor\b", re.IGNORECASE), "octal or"),
    (re.compile(r"\bconstantor\b", re.IGNORECASE), "constant or"),
    (re.compile(r"\bhexadecimalor\b", re.IGNORECASE), "hexadecimal or"),
    (re.compile(r"\bdirectlyor\b", re.IGNORECASE), "directly or"),
    (re.compile(r"\bmultipleor\b", re.IGNORECASE), "multiple or"),
    (re.compile(r"\bundefinedor\b", re.IGNORECASE), "undefined or"),
    (re.compile(r"\bbreakor\b", re.IGNORECASE), "break or"),
]

INLINE_FRAGMENT_FIXES: List[Tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\b([A-Za-z]{1,3})\s*/\s*([A-Za-z]{1,8})\b"),
        lambda m: m.group(1) + m.group(2),
    ),
    (
        re.compile(r"\b([A-Za-z]{1,4})\s*-\s*([A-Za-z]{1,10})\b"),
        lambda m: f"{m.group(1)}-{m.group(2)}"
        if len(m.group(1)) > 2 and len(m.group(2)) > 2
        else m.group(0),
    ),
]

SPLIT_LINE_JOIN_RE = re.compile(r"^[A-Za-z]{1,4}$")


@dataclass
class ReconstructedGuideline:
    guideline_type: str
    guideline_id: str
    short_id: str
    title: str
    title_line: str
    page_start: Optional[int]
    page_end: Optional[int]
    document_page_start: Optional[str]
    document_page_end: Optional[str]
    category: str
    applies_to: List[str]
    analysis_decidability: str
    analysis_scope: str
    bracket_notes: List[str]
    rationale: str
    amplification: str
    exception: str
    example: str
    see_also: List[str]
    body_text: str
    normalized_text: str
    raw_text: str
    raw_lines: List[str]
    normalized_lines: List[str]
    repair_notes: List[str] = field(default_factory=list)
    ocr_issue_count: int = 0
    needs_manual_review: bool = False


class GuidelineSectionReconstructor:
    def __init__(self, segments_path: Path) -> None:
        self.segments_path = segments_path
        with segments_path.open("r", encoding="utf-8") as handle:
            self.payload = json.load(handle)

    def reconstruct(self) -> Dict[str, Any]:
        items = self.payload.get("segments") or self.payload.get("guidelines") or []
        records = [self._reconstruct_single(item) for item in items]
        return {
            "source_segments": str(self.segments_path),
            "guideline_count": len(records),
            "guidelines": [asdict(record) for record in records],
        }

    def _reconstruct_single(self, item: Dict[str, Any]) -> ReconstructedGuideline:
        raw_lines = list(item.get("raw_lines") or self._split_lines(item.get("raw_text", "")))
        normalized_lines = self._normalize_guideline_lines(raw_lines)

        title_line = normalized_lines[0] if normalized_lines else ""
        m = GUIDELINE_HEADER_RE.match(title_line)
        guideline_type, short_id, title = (
            item.get("guideline_type", ""),
            item.get("short_id", ""),
            item.get("title", ""),
        )
        if m:
            guideline_type, short_id, title = m.group(1), m.group(2), m.group(3).strip()
        guideline_id = f"{guideline_type} {short_id}".strip()

        title, trailing_notes = self._extract_inline_bracket_notes(title)
        bracket_notes: List[str] = list(trailing_notes)

        title, consumed_count = self._promote_multiline_title(title, normalized_lines[1:])
        working_lines = normalized_lines[1 + consumed_count :]

        category = ""
        applies_to: List[str] = []
        analysis_decidability = ""
        analysis_scope = ""
        body_buffer: List[str] = []
        sections = {"rationale": [], "amplification": [], "exception": [], "example": [], "seealso": []}
        current_section: Optional[str] = None

        for line in working_lines:
            if not line:
                continue
            if PAGE_FURNITURE_RE.search(line):
                continue
            if BRACKET_NOTE_RE.match(line):
                bracket_notes.append(line)
                continue
            if BOOK_SECTION_HEADING_RE.match(line):
                break

            category_match = CATEGORY_RE.match(line)
            if category_match:
                category = category_match.group(1).strip()
                continue

            analysis_match = ANALYSIS_RE.match(line)
            if analysis_match:
                analysis_decidability, analysis_scope = self._parse_analysis_line(
                    analysis_match.group(1).strip()
                )
                continue

            applies_match = APPLIES_TO_RE.match(line)
            if applies_match:
                applies_to = self._parse_applies_to(applies_match.group(1).strip())
                continue

            section_key, remainder = self._detect_section_header_with_remainder(line)
            if section_key is not None:
                current_section = section_key
                if remainder:
                    sections[current_section].append(remainder)
                continue

            if current_section:
                sections[current_section].append(line)
            else:
                body_buffer.append(line)

        rationale = self._collapse_mixed_section(sections["rationale"])
        amplification = self._collapse_mixed_section(sections["amplification"])
        exception = self._collapse_mixed_section(sections["exception"])
        example = self._collapse_mixed_section(sections["example"], prefer_code=True)
        see_also = self._extract_rule_refs(sections["seealso"])
        body_text = self._collapse_mixed_section(body_buffer)

        title, body_text, rationale, amplification, exception, example, applies_to, post_notes = (
            self._postprocess_fields(
                title=title,
                body_text=body_text,
                rationale=rationale,
                amplification=amplification,
                exception=exception,
                example=example,
                applies_to=applies_to,
                bracket_notes=bracket_notes,
            )
        )

        normalized_text = self._build_normalized_text(
            title=title,
            bracket_notes=bracket_notes,
            category=category,
            applies_to=applies_to,
            analysis_decidability=analysis_decidability,
            analysis_scope=analysis_scope,
            body_text=body_text,
            rationale=rationale,
            amplification=amplification,
            exception=exception,
            example=example,
            see_also=see_also,
        )
        repair_notes, ocr_issue_count = self._collect_quality_notes(
            title=title,
            body_text=body_text,
            rationale=rationale,
            amplification=amplification,
            exception=exception,
            example=example,
            normalized_text=normalized_text,
        )
        repair_notes = post_notes + repair_notes

        return ReconstructedGuideline(
            guideline_type=guideline_type,
            guideline_id=guideline_id,
            short_id=short_id,
            title=title,
            title_line=title_line,
            page_start=item.get("page_start"),
            page_end=item.get("page_end"),
            document_page_start=item.get("document_page_start"),
            document_page_end=item.get("document_page_end"),
            category=category,
            applies_to=applies_to,
            analysis_decidability=analysis_decidability,
            analysis_scope=analysis_scope,
            bracket_notes=bracket_notes,
            rationale=rationale,
            amplification=amplification,
            exception=exception,
            example=example,
            see_also=see_also,
            body_text=body_text,
            normalized_text=normalized_text,
            raw_text=item.get("raw_text", ""),
            raw_lines=raw_lines,
            normalized_lines=normalized_lines,
            repair_notes=repair_notes,
            ocr_issue_count=ocr_issue_count,
            needs_manual_review=ocr_issue_count > 0,
        )

    def _normalize_guideline_lines(self, raw_lines: Iterable[str]) -> List[str]:
        lines = [self._normalize_line(line) for line in raw_lines]
        expanded: List[str] = []
        for line in lines:
            expanded.extend(self._split_embedded_headers(line))
        lines = self._join_fragment_lines(expanded)
        lines = self._merge_wrapped_lines(lines)
        lines = [self._final_cleanup(line) for line in lines]
        return [line for line in lines if line]

    def _normalize_line(self, line: str) -> str:
        line = unicodedata.normalize("NFKC", line)
        for src, dst in LIGATURE_CHAR_MAP.items():
            line = line.replace(src, dst)
        line = (
            line.replace("\u2013", "-")
            .replace("\u2014", "-")
            .replace("\u2018", "'")
            .replace("\u2019", "'")
            .replace("\u201c", '"')
            .replace("\u201d", '"')
        )
        line = line.replace("\xa0", " ")
        line = re.sub(r"\s+", " ", line).strip()
        for pattern, replacement in SAFE_TOKEN_REPAIRS:
            line = pattern.sub(replacement, line)
        for pattern, replacement in INLINE_FRAGMENT_FIXES:
            line = pattern.sub(replacement, line)
        line = self._repair_small_internal_splits(line)
        line = self._repair_fused_known_phrases(line)
        return line.strip()

    def _repair_small_internal_splits(self, line: str) -> str:
        changed = True
        while changed:
            original = line
            line = re.sub(r"\b([A-Za-z]{3,})\s+([A-Za-z]{1,2})\b", self._join_if_safe_suffix, line)
            line = re.sub(r"\b([A-Za-z]{1,2})\s+([A-Za-z]{3,})\b", self._join_if_safe_prefix, line)
            changed = line != original
        return line

    def _join_if_safe_suffix(self, match: re.Match[str]) -> str:
        left, right = match.group(1), match.group(2)
        pair = f"{left} {right}".lower()
        if pair in {
            "shall be",
            "should be",
            "may be",
            "to a",
            "to the",
            "of a",
            "of the",
            "in a",
            "in the",
            "is a",
            "is the",
        }:
            return match.group(0)
        if right.lower() in {"d", "s", "er", "ed", "ly", "es", "al", "or", "ty", "re", "nt"}:
            return left + right
        return match.group(0)

    def _join_if_safe_prefix(self, match: re.Match[str]) -> str:
        left, right = match.group(1), match.group(2)
        pair = f"{left} {right}".lower()
        if pair in {"be used", "to a", "to the", "of a", "of the", "in a", "in the"}:
            return match.group(0)
        if left.lower() in {"un", "re", "de", "pre", "co", "in", "im", "non"}:
            return left + right
        return match.group(0)

    def _repair_fused_known_phrases(self, line: str) -> str:
        replacements = {
            "headerfile": "header file",
            "sourcefiles": "source files",
            "compileris": "compiler is",
            "permittedto": "permitted to",
            "traceableto": "traceable to",
            "usageof": "usage of",
            "pointertoa": "pointer to a",
            "ca nleadto": "can lead to",
            "timingor": "timing or",
            "emulatoror": "emulator or",
            "inquestion": "in question",
            "inturn": "in turn",
            "inorder": "in order",
            "inplace": "in place",
            "inwhich": "in which",
            "inthis": "in this",
            "octalor": "octal or",
            "constantor": "constant or",
            "hexadecimalor": "hexadecimal or",
            "directlyor": "directly or",
            "multipleor": "multiple or",
            "undefinedor": "undefined or",
            "breakor": "break or",
        }
        out = line
        for bad, good in replacements.items():
            out = re.sub(re.escape(bad), good, out, flags=re.IGNORECASE)
        return out

    def _split_embedded_headers(self, line: str) -> List[str]:
        if not line:
            return [line]
        patterns = [
            r"\bCategory\s+",
            r"\bAnalysis\s+",
            r"\bRationale\b",
            r"\bAmplifi\s*cation\b",
            r"\bException\b",
            r"\bExample\b",
            r"\bSee\s*also\b",
        ]
        parts = [line]
        for pattern in patterns:
            new_parts: List[str] = []
            for part in parts:
                indices = [m.start() for m in re.finditer(pattern, part, flags=re.IGNORECASE)]
                if not indices or indices[0] == 0:
                    new_parts.append(part)
                    continue
                cursor = 0
                for idx in indices:
                    new_parts.append(part[cursor:idx].strip())
                    cursor = idx
                new_parts.append(part[cursor:].strip())
            parts = [p for p in new_parts if p]
        return parts

    def _join_fragment_lines(self, lines: List[str]) -> List[str]:
        result: List[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if result and SPLIT_LINE_JOIN_RE.match(line) and not CODE_LIKE_RE.search(line):
                result[-1] = f"{result[-1]} {line}".strip()
                i += 1
                continue
            if i + 1 < len(lines) and SPLIT_LINE_JOIN_RE.match(line) and SPLIT_LINE_JOIN_RE.match(lines[i + 1]):
                joined = f"{line} {lines[i + 1]}".strip()
                if result:
                    result[-1] = f"{result[-1]} {joined}".strip()
                else:
                    result.append(joined)
                i += 2
                continue
            if i + 1 < len(lines) and SPLIT_LINE_JOIN_RE.match(line) and not CODE_LIKE_RE.search(lines[i + 1]):
                result.append(f"{line} {lines[i + 1]}".strip())
                i += 2
                continue
            result.append(line)
            i += 1
        return result

    def _classify_line(self, line: str) -> str:
        if not line.strip():
            return "blank"
        if PAGE_FURNITURE_RE.search(line):
            return "meta"
        if META_LINE_RE.match(line):
            return "meta"
        if self._detect_section_header(line) is not None:
            return "section_header"
        if BRACKET_NOTE_RE.match(line):
            return "meta"
        if BULLET_RE.match(line):
            return "bullet"
        if GRAMMAR_RE.match(line):
            return "grammar"
        if CODE_LIKE_RE.search(line):
            return "code"
        return "text"

    def _merge_wrapped_lines(self, lines: List[str]) -> List[str]:
        merged: List[str] = []
        for line in lines:
            if not merged:
                merged.append(line)
                continue

            prev = merged[-1]
            prev_kind = self._classify_line(prev)
            curr_kind = self._classify_line(line)

            if self._should_merge_lines(prev, line, prev_kind, curr_kind):
                merged[-1] = self._merge_two_lines(prev, line, prev_kind, curr_kind)
            else:
                merged.append(line)
        return merged

    def _should_merge_lines(
        self,
        prev: str,
        current: str,
        prev_kind: str,
        curr_kind: str,
    ) -> bool:
        if not prev or not current:
            return False

        if prev_kind in {"meta", "section_header"} or curr_kind in {"meta", "section_header"}:
            return False

        if prev_kind in {"code", "grammar"} or curr_kind in {"code", "grammar"}:
            return False

        if prev_kind == "bullet" or curr_kind == "bullet":
            return False

        if GUIDELINE_HEADER_RE.match(current):
            return False
        if BOOK_SECTION_HEADING_RE.match(current):
            return False

        if prev.endswith("-"):
            return True

        if re.search(r"[,:(]$", prev):
            return True

        if current[:1].islower() and not prev.endswith((".", ";", "?", "!", ":")):
            return True

        if len(current.split()) <= 3 and not prev.endswith((".", ";", "?", "!")):
            return True

        return False

    def _merge_two_lines(
        self,
        prev: str,
        current: str,
        prev_kind: str,
        curr_kind: str,
    ) -> str:
        if prev.endswith("-"):
            return prev[:-1] + current.lstrip()

        return f"{prev.rstrip()} {current.lstrip()}".strip()

    def _final_cleanup(self, line: str) -> str:
        line = re.sub(r"\s+", " ", line).strip()
        for pattern, replacement in SAFE_TOKEN_REPAIRS:
            line = pattern.sub(replacement, line)
        line = self._repair_fused_known_phrases(line)
        line = self._repair_small_internal_splits(line)
        return line

    def _extract_inline_bracket_notes(self, text: str) -> Tuple[str, List[str]]:
        notes: List[str] = []
        while True:
            m = re.search(r"\s+(C(?:90|99)\s*\[[^\]]+\]|\[[^\]]+\])$", text)
            if not m:
                break
            notes.insert(0, m.group(1).strip())
            text = text[: m.start()].strip()
        return text.strip(), notes

    def _promote_multiline_title(self, title: str, lines: List[str]) -> Tuple[str, int]:
        consumed = 0
        title_words = len(title.split())
        while consumed < len(lines):
            line = lines[consumed]
            if not line or CATEGORY_RE.match(line) or ANALYSIS_RE.match(line) or APPLIES_TO_RE.match(line):
                break
            if self._detect_section_header(line) is not None or BRACKET_NOTE_RE.match(line) or BOOK_SECTION_HEADING_RE.match(line):
                break
            if CODE_LIKE_RE.search(line):
                break
            if title_words >= 18:
                break
            if line.endswith((".", ";", ":")) and len(line.split()) > 10:
                break
            title = f"{title} {line}".strip()
            title_words = len(title.split())
            consumed += 1
            if title.endswith((".", ";")):
                break
        title, _ = self._extract_inline_bracket_notes(title)
        return title, consumed

    def _detect_section_header(self, line: str) -> Optional[str]:
        normalized = re.sub(r"\s+", " ", line.strip())
        for key, aliases in SECTION_HEADER_ALIASES.items():
            for alias in aliases:
                if normalized.lower() == alias.lower():
                    return key
        return None

    def _detect_section_header_with_remainder(self, line: str) -> Tuple[Optional[str], str]:
        normalized = re.sub(r"\s+", " ", line.strip())
        for key, aliases in SECTION_HEADER_ALIASES.items():
            for alias in aliases:
                pattern = re.compile(rf"^{re.escape(alias)}\b\s*(.*)$", re.IGNORECASE)
                m = pattern.match(normalized)
                if m:
                    return key, m.group(1).strip()
        return None, ""

    def _parse_analysis_line(self, text: str) -> Tuple[str, str]:
        parts = [part.strip() for part in text.split(",") if part.strip()]
        decidability = ""
        scope = ""
        for part in parts:
            if DECIDABLE_RE.match(part) or UNDECIDABLE_RE.match(part):
                decidability = part
            elif SINGLE_TU_RE.match(part) or SYSTEM_RE.match(part):
                scope = part
        return decidability, scope

    def _parse_applies_to(self, text: str) -> List[str]:
        values = [value.strip() for value in re.split(r"\s*,\s*", text) if value.strip()]
        clean: List[str] = []
        for value in values:
            if value.lower() in {"c90", "c99"}:
                clean.append(value.upper())
            elif value and len(clean) < 2:
                clean.append(value)
        return clean

    def _collapse_mixed_section(self, lines: List[str], prefer_code: bool = False) -> str:
        if not lines:
            return ""

        chunks: List[str] = []
        current: List[str] = []
        current_kind: Optional[str] = None

        for line in lines:
            line_kind = self._classify_line(line)

            if prefer_code and line_kind in {"code", "grammar", "bullet"}:
                normalized_kind = line_kind
            else:
                normalized_kind = "text" if line_kind not in {"code", "grammar", "bullet"} else line_kind

            if current_kind is None:
                current_kind = normalized_kind
                current = [line]
                continue

            if normalized_kind != current_kind:
                chunks.append(self._collapse_lines(current, kind=current_kind))
                current = [line]
                current_kind = normalized_kind
            else:
                current.append(line)

        if current:
            chunks.append(self._collapse_lines(current, kind=current_kind or "text"))

        return "\n\n".join(chunk for chunk in chunks if chunk.strip()).strip()

    def _collapse_lines(self, lines: List[str], kind: str = "text") -> str:
        if kind in {"code", "grammar", "bullet"}:
            return "\n".join(line.rstrip() for line in lines if line.strip())

        out: List[str] = []
        for line in lines:
            if out and self._should_merge_lines(
                out[-1],
                line,
                self._classify_line(out[-1]),
                self._classify_line(line),
            ):
                out[-1] = self._merge_two_lines(
                    out[-1],
                    line,
                    self._classify_line(out[-1]),
                    self._classify_line(line),
                )
            else:
                out.append(line)

        return "\n\n".join(line.strip() for line in out if line.strip())

    def _move_embedded_header_text(self, body_text: str, target_text: str, header_name: str) -> Tuple[str, str]:
        if not body_text:
            return body_text, target_text
        pattern = re.compile(rf"\b{header_name}\b\s*(.*)$", re.IGNORECASE | re.DOTALL)
        m = pattern.search(body_text)
        if not m:
            return body_text, target_text
        before = body_text[:m.start()].strip()
        after = m.group(1).strip()
        combined = after if not target_text else f"{after}\n\n{target_text}"
        return before, combined.strip()

    def _extract_rule_refs(self, lines: List[str]) -> List[str]:
        refs: List[str] = []
        for line in lines:
            for ref in RULE_REF_RE.findall(line):
                if ref not in refs:
                    refs.append(ref)
        return refs

    def _collect_quality_notes(self, **fields: str) -> Tuple[List[str], int]:
        notes: List[str] = []
        issue_count = 0
        suspicious = [
            r"\b[A-Za-z]{24,}\b",
            r"\b(?:th e|i s|a nd|e ff ect|effi ciency|identifi er|identifi ers|structu re|typ edef|applie s to|amplifi cation)\b",
            r"\b(?:ca nleadto|documente d|deall ocation|encapsul ated|fu nctions|impleme ntation|informati on|specifi c- leng th t y pes|effi ciency|structu re|preven t|les s|tha t)\b",
            r"\b(?:timingor|emulatoror|inquestion|inturn|inorder|directlyor|breakor|multipleor|undefinedor)\b",
        ]
        for field_name, text in fields.items():
            if not text:
                continue
            local_hits = 0
            for pat in suspicious:
                local_hits += len(re.findall(pat, text, flags=re.IGNORECASE))
            if local_hits:
                notes.append(f"ocr_residue:{field_name}:{local_hits}")
                issue_count += local_hits
        return notes, issue_count

    def _postprocess_fields(
        self,
        title: str,
        body_text: str,
        rationale: str,
        amplification: str,
        exception: str,
        example: str,
        applies_to: List[str],
        bracket_notes: List[str],
    ) -> Tuple[str, str, str, str, str, str, List[str], List[str]]:
        notes: List[str] = []

        body_lines = [ln.strip() for ln in body_text.splitlines()] if body_text else []
        while body_lines and re.fullmatch(r"C(?:90|99)\s*\[[^\]]+\]", body_lines[0]):
            bracket_notes.append(body_lines.pop(0))
            notes.append("moved_body_bracket_note")
        body_text = "\n".join(body_lines).strip()

        if body_text:
            m = re.match(
                r"^(?:Applies|Applie\s*s|Appliesto)\s*to?\s+(.+?)(?:\s+Amplification\b|\s+Rationale\b|\s+Exception\b|\s+Example\b|$)",
                body_text,
                re.IGNORECASE | re.DOTALL,
            )
            if m:
                candidate = self._parse_applies_to(self._final_cleanup(m.group(1).strip()))
                if candidate:
                    applies_to = candidate
                    notes.append("extracted_embedded_applies_to")
                    body_text = body_text[m.end(1) :].strip()
                    body_text = re.sub(
                        r"^(?:\s*(?:Amplification|Rationale|Exception|Example)\b)",
                        lambda mm: mm.group(0).strip(),
                        body_text,
                        flags=re.IGNORECASE,
                    )

        title, body_text, promoted = self._promote_title_from_body(title, body_text)
        if promoted:
            notes.append("promoted_title_continuation")

        body_text, amplification, moved = self._move_embedded_header_text_fuzzy(
            body_text, amplification, "amplification"
        )
        if moved:
            notes.append("moved_embedded_amplification")
        body_text, rationale, moved = self._move_embedded_header_text_fuzzy(
            body_text, rationale, "rationale"
        )
        if moved:
            notes.append("moved_embedded_rationale")
        body_text, exception, moved = self._move_embedded_header_text_fuzzy(
            body_text, exception, "exception"
        )
        if moved:
            notes.append("moved_embedded_exception")
        body_text, example, moved = self._move_embedded_header_text_fuzzy(
            body_text, example, "example"
        )
        if moved:
            notes.append("moved_embedded_example")

        body_text = self._final_cleanup(body_text)
        rationale = self._final_cleanup(rationale)
        amplification = self._final_cleanup(amplification)
        exception = self._final_cleanup(exception)
        example = self._final_cleanup(example) if example else example
        title = self._final_cleanup(title)

        return title, body_text, rationale, amplification, exception, example, applies_to, notes

    def _promote_title_from_body(self, title: str, body_text: str) -> Tuple[str, str, bool]:
        if not body_text:
            return title, body_text, False

        weak_tail = {
            "a",
            "an",
            "the",
            "to",
            "of",
            "on",
            "in",
            "within",
            "order",
            "header",
            "resource",
            "operations",
        }
        lines = [ln for ln in body_text.splitlines() if ln.strip()]
        if not lines:
            return title, body_text, False

        first = lines[0].strip()
        lead = first
        m = re.search(r"\b(Amplification|Rationale|Exception|Example)\b", first, flags=re.IGNORECASE)
        if m and m.start() > 0:
            lead = first[: m.start()].strip()
            remainder = first[m.start() :].strip()
        else:
            remainder = ""

        should_promote = (
            title.split()[-1].lower() in weak_tail
            or (lead and lead[:1].islower())
            or len(title.split()) < 8
        )
        if not should_promote or not lead:
            return title, body_text, False
        if len(lead.split()) > 12:
            return title, body_text, False
        if lead.endswith((".", ";")) and len(lead.split()) > 6:
            return title, body_text, False

        new_title = f"{title} {lead}".strip()
        new_lines = lines[:]
        if remainder:
            new_lines[0] = remainder
        else:
            new_lines = new_lines[1:]
        return new_title, "\n".join(new_lines).strip(), True

    def _move_embedded_header_text_fuzzy(
        self,
        body_text: str,
        target_text: str,
        header_name: str,
    ) -> Tuple[str, str, bool]:
        if not body_text:
            return body_text, target_text, False

        alias_map = {
            "amplification": r"Amplifi\s*cation|Amplification",
            "rationale": r"Rationale",
            "exception": r"Exception",
            "example": r"Example",
        }
        header_re = alias_map.get(header_name, re.escape(header_name))
        pattern = re.compile(rf"\b(?:{header_re})\b\s*(.*)$", re.IGNORECASE | re.DOTALL)
        m = pattern.search(body_text)
        if not m:
            return body_text, target_text, False

        before = body_text[: m.start()].strip()
        after = m.group(1).strip()

        if not after:
            return before, target_text, True

        combined = after if not target_text else f"{after}\n\n{target_text}"
        return before, combined.strip(), True

    def _build_normalized_text(
        self,
        title: str,
        bracket_notes: List[str],
        category: str,
        applies_to: List[str],
        analysis_decidability: str,
        analysis_scope: str,
        body_text: str,
        rationale: str,
        amplification: str,
        exception: str,
        example: str,
        see_also: List[str],
    ) -> str:
        parts: List[str] = [title]
        if bracket_notes:
            parts.append("\n".join(bracket_notes))
        if category:
            parts.append(f"Category: {category}")
        if applies_to:
            parts.append(f"Applies to: {', '.join(applies_to)}")
        analysis_parts = [part for part in [analysis_decidability, analysis_scope] if part]
        if analysis_parts:
            parts.append(f"Analysis: {', '.join(analysis_parts)}")
        if body_text:
            parts.append(body_text)
        if rationale:
            parts.append(f"Rationale\n{rationale}")
        if amplification:
            parts.append(f"Amplification\n{amplification}")
        if exception:
            parts.append(f"Exception\n{exception}")
        if example:
            parts.append(f"Example\n{example}")
        if see_also:
            parts.append(f"See also\n{', '.join(see_also)}")
        return "\n\n".join(part.strip() for part in parts if part and part.strip())

    def _split_lines(self, text: str) -> List[str]:
        return [line.rstrip() for line in text.splitlines()]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reconstruct and normalize MISRA guideline sections from segmented records."
    )
    parser.add_argument("segments_path", type=Path, help="Path to misra_segments.json")
    parser.add_argument(
        "output_path",
        type=Path,
        help="Path to output reconstructed_and_normalized_guidelines.json",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    reconstructor = GuidelineSectionReconstructor(args.segments_path)
    payload = reconstructor.reconstruct()
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    with args.output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()