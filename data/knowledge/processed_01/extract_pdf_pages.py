from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

from pypdf import PdfReader


LIGATURE_MAP = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\ufb05": "ft",
    "\ufb06": "st",
}

# Common PDF extraction artifacts seen in the uploaded MISRA PDF.
SOFT_JOIN_PATTERNS = [
    (re.compile(r"(?<=\w)\s+ﬁ\s+(?=\w)"), "fi"),
    (re.compile(r"(?<=\w)\s+ﬀ\s+(?=\w)"), "ff"),
    (re.compile(r"(?<=\w)\s+ﬂ\s+(?=\w)"), "fl"),
    (re.compile(r"(?<=\w)\s+ﬃ\s+(?=\w)"), "ffi"),
    (re.compile(r"(?<=\w)\s+ﬄ\s+(?=\w)"), "ffl"),
]

HEADER_FOOTER_PATTERNS = [
    re.compile(r"^MISRA C 2012 final\.indd.*$", re.IGNORECASE),
    re.compile(r"^Licensed to:.*$", re.IGNORECASE),
    re.compile(r"^Copy\s+\d+\s+of\s+\d+.*$", re.IGNORECASE),
    re.compile(r"^Page\s+\d+\s+of\s+\d+.*$", re.IGNORECASE),
]

SECTION_LINE_RE = re.compile(r"^Section\s+\d+\s*:\s*.+$", re.IGNORECASE)
APPENDIX_LINE_RE = re.compile(r"^Appendix\s+[A-Z]\s*:", re.IGNORECASE)
LEADING_PAGE_NUM_RE = re.compile(r"^(\d{1,3})\s+(Section\s+\d+\s*:\s*.+|Appendix\s+[A-Z]\s*:.*)$", re.IGNORECASE)
PURE_PAGE_NUM_RE = re.compile(r"^\d{1,3}$")


@dataclass
class PageRecord:
    pdf_page_index: int
    pdf_page_number: int
    document_page_label: Optional[str]
    section_label: Optional[str]
    cleaned_text: str
    raw_text: str
    extracted_line_count: int
    cleaned_line_count: int
    is_rules_section: bool
    is_directives_section: bool
    is_appendix: bool
    removed_lines: List[str] = field(default_factory=list)


class MisraPdfPageExtractor:
    def __init__(self, pdf_path: Path) -> None:
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")

    def extract_pages(self) -> List[PageRecord]:
        reader = PdfReader(str(self.pdf_path))
        pages: List[PageRecord] = []
        for index, page in enumerate(reader.pages):
            raw_text = page.extract_text() or ""
            pages.append(self._build_page_record(index=index, raw_text=raw_text))
        return pages

    def _build_page_record(self, index: int, raw_text: str) -> PageRecord:
        normalized = self._normalize_text(raw_text)
        raw_lines = [line.rstrip() for line in normalized.splitlines()]
        filtered_lines, removed_lines = self._filter_lines(raw_lines)
        document_page_label, section_label, filtered_lines = self._extract_page_and_section_labels(filtered_lines)
        cleaned_lines = self._clean_lines(filtered_lines)
        cleaned_text = "\n".join(cleaned_lines).strip()
        is_rules = bool(section_label and section_label.lower().startswith("section 8:"))
        is_directives = bool(section_label and section_label.lower().startswith("section 7:"))
        is_appendix = bool(section_label and section_label.lower().startswith("appendix"))
        return PageRecord(
            pdf_page_index=index,
            pdf_page_number=index + 1,
            document_page_label=document_page_label,
            section_label=section_label,
            cleaned_text=cleaned_text,
            raw_text=normalized,
            extracted_line_count=len(raw_lines),
            cleaned_line_count=len(cleaned_lines),
            is_rules_section=is_rules,
            is_directives_section=is_directives,
            is_appendix=is_appendix,
            removed_lines=removed_lines,
        )

    def _normalize_text(self, text: str) -> str:
        text = unicodedata.normalize("NFKC", text or "")
        for ligature, replacement in LIGATURE_MAP.items():
            text = text.replace(ligature, replacement)
        for pattern, replacement in SOFT_JOIN_PATTERNS:
            text = pattern.sub(replacement, text)
        # Normalize non-breaking spaces and tabs.
        text = text.replace("\u00a0", " ").replace("\t", " ")
        # Collapse extreme spacing but keep single newlines for structure.
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"[ ]{2,}", " ", text)
        # Fix common split numeric/header bleed e.g. "158 Section 8: Rules" remains parseable later.
        return text.strip("\n")

    def _filter_lines(self, lines: Iterable[str]) -> tuple[List[str], List[str]]:
        kept: List[str] = []
        removed: List[str] = []
        for line in lines:
            candidate = line.strip()
            if not candidate:
                kept.append("")
                continue
            if any(pattern.match(candidate) for pattern in HEADER_FOOTER_PATTERNS):
                removed.append(candidate)
                continue
            kept.append(candidate)
        return kept, removed

    def _extract_page_and_section_labels(self, lines: List[str]) -> tuple[Optional[str], Optional[str], List[str]]:
        document_page_label: Optional[str] = None
        section_label: Optional[str] = None
        remaining = list(lines)

        # Drop leading blank lines.
        while remaining and not remaining[0].strip():
            remaining.pop(0)

        if remaining:
            first = remaining[0].strip()
            match = LEADING_PAGE_NUM_RE.match(first)
            if match:
                document_page_label = match.group(1)
                section_label = match.group(2)
                remaining.pop(0)
            else:
                if PURE_PAGE_NUM_RE.match(first):
                    document_page_label = first
                    remaining.pop(0)
                    while remaining and not remaining[0].strip():
                        remaining.pop(0)
                if remaining:
                    second = remaining[0].strip()
                    if SECTION_LINE_RE.match(second) or APPENDIX_LINE_RE.match(second):
                        section_label = second
                        remaining.pop(0)

        if section_label is None:
            for probe in remaining[:3]:
                probe = probe.strip()
                if SECTION_LINE_RE.match(probe) or APPENDIX_LINE_RE.match(probe):
                    section_label = probe
                    remaining.remove(probe)
                    break

        return document_page_label, section_label, remaining

    def _clean_lines(self, lines: Iterable[str]) -> List[str]:
        cleaned: List[str] = []
        previous_blank = False
        for line in lines:
            line = line.strip()
            if PURE_PAGE_NUM_RE.match(line):
                continue
            if not line:
                if not previous_blank:
                    cleaned.append("")
                previous_blank = True
                continue
            previous_blank = False
            cleaned.append(line)
        while cleaned and not cleaned[-1]:
            cleaned.pop()
        return cleaned


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract cleaned page text from a MISRA PDF.")
    parser.add_argument("pdf_path", type=Path, help="C:\\Users\\sanjay.ravichander\\misra_genai_system\\misra_genai_system\\data\\knowledge\\processed_01\\Misra-c-2012-guidelines.pdf")
    parser.add_argument("output_path", type=Path, help="misra_genai_system/data/knowledge/processed_01/output_processed_01/extracted_pages.json")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    extractor = MisraPdfPageExtractor(args.pdf_path)
    page_records = extractor.extract_pages()
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_pdf": str(args.pdf_path),
        "page_count": len(page_records),
        "pages": [asdict(record) for record in page_records],
    }
    with args.output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
