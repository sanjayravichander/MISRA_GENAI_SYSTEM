from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

GUIDELINE_START_RE = re.compile(r"^(Rule|Dir)\s+(\d+\.\d+)(?:\s+(.*))?$")
CATEGORY_RE = re.compile(r"^Category\b", re.IGNORECASE)
ANALYSIS_RE = re.compile(r"^Analysis\b", re.IGNORECASE)
APPLIES_RE = re.compile(r"^Applies to\b", re.IGNORECASE)
APPENDIX_RE = re.compile(r"^Appendix\s+[A-Z]\s*:", re.IGNORECASE)
NOISE_LINE_RE = re.compile(
    r"^(Section\s+\d+\s*:|Licensed to:|MISRA C 2012 final\.indd|Copy\s+\d+\s+of\s+\d+|\d+\s+Section\s+\d+\s*:)",
    re.IGNORECASE,
)
DATE_LINE_RE = re.compile(r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\.\s+Copy\s+\d+\s+of\s+\d+", re.IGNORECASE)


@dataclass
class GuidelineSegment:
    guideline_type: str
    guideline_id: str
    short_id: str
    title_line: str
    page_start: int
    page_end: int
    document_page_start: Optional[str]
    document_page_end: Optional[str]
    raw_text: str
    raw_lines: List[str] = field(default_factory=list)


class GuidelineSegmenter:
    def __init__(self, pages_payload: Dict) -> None:
        self.pages_payload = pages_payload
        self.pages = pages_payload["pages"]

    def segment(self) -> List[GuidelineSegment]:
        active: Optional[GuidelineSegment] = None
        segments: List[GuidelineSegment] = []

        for page in self.pages:
            if not (page.get("is_rules_section") or page.get("is_directives_section")):
                continue
            if page.get("is_appendix"):
                continue

            lines = self._normalized_page_lines(page)
            previous_non_empty = ""
            for index, line in enumerate(lines):
                if self._is_guideline_start(lines=lines, index=index, previous_non_empty=previous_non_empty):
                    start_match = GUIDELINE_START_RE.match(line)
                    assert start_match is not None
                    if active is not None:
                        segments.append(self._finalize(active))
                    guideline_type = start_match.group(1)
                    short_id = start_match.group(2)
                    active = GuidelineSegment(
                        guideline_type=guideline_type,
                        guideline_id=f"{guideline_type} {short_id}",
                        short_id=short_id,
                        title_line=line,
                        page_start=page["pdf_page_number"],
                        page_end=page["pdf_page_number"],
                        document_page_start=page.get("document_page_label"),
                        document_page_end=page.get("document_page_label"),
                        raw_text="",
                        raw_lines=[line],
                    )
                    previous_non_empty = line
                    continue

                if active is None:
                    if line:
                        previous_non_empty = line
                    continue

                if self._should_ignore_line(line):
                    continue

                active.raw_lines.append(line)
                active.page_end = page["pdf_page_number"]
                active.document_page_end = page.get("document_page_label")
                if line:
                    previous_non_empty = line

        if active is not None:
            segments.append(self._finalize(active))

        return segments

    def _normalized_page_lines(self, page: Dict) -> List[str]:
        text = page.get("cleaned_text", "")
        lines = [line.strip() for line in text.splitlines()]
        normalized: List[str] = []
        previous_blank = False
        for line in lines:
            if not line:
                if not previous_blank:
                    normalized.append("")
                previous_blank = True
                continue
            previous_blank = False
            normalized.append(line)
        return normalized

    def _is_guideline_start(self, lines: List[str], index: int, previous_non_empty: str) -> bool:
        line = lines[index]
        match = GUIDELINE_START_RE.match(line)
        if not match:
            return False

        remainder = (match.group(3) or "").strip()
        if remainder.startswith(",") or remainder.startswith(";"):
            return False
        if previous_non_empty.lower().startswith("see also"):
            return False
        if previous_non_empty.lower().startswith("example"):
            # Examples often contain standalone rule references.
            return False

        lookahead = [candidate for candidate in lines[index + 1 : index + 8] if candidate.strip()]
        if not lookahead:
            return False
        if any(DATE_LINE_RE.match(candidate) for candidate in lookahead[:2]):
            return False

        # Canonical guideline blocks should declare category or analysis/applies very near the header.
        if not any(
            CATEGORY_RE.match(candidate) or ANALYSIS_RE.match(candidate) or APPLIES_RE.match(candidate)
            for candidate in lookahead
        ):
            return False

        return True

    def _should_ignore_line(self, line: str) -> bool:
        if not line:
            return False
        if NOISE_LINE_RE.match(line):
            return True
        if APPENDIX_RE.match(line):
            return True
        if DATE_LINE_RE.match(line):
            return True
        return False

    def _finalize(self, segment: GuidelineSegment) -> GuidelineSegment:
        while segment.raw_lines and not segment.raw_lines[-1].strip():
            segment.raw_lines.pop()
        segment.raw_text = "\n".join(segment.raw_lines).strip()
        return segment


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Segment directives/rules from extracted MISRA pages.")
    parser.add_argument("pages_json", type=Path, help="JSON created by extract_pdf_pages.py")
    parser.add_argument("output_json", type=Path, help="Output JSON for guideline segments")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    with args.pages_json.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    segmenter = GuidelineSegmenter(payload)
    segments = segmenter.segment()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "source_pdf": payload.get("source_pdf"),
        "segment_count": len(segments),
        "guidelines": [asdict(segment) for segment in segments],
    }
    with args.output_json.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
