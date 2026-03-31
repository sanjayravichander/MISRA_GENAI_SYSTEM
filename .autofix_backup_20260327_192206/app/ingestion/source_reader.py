# Source code reader
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


SUPPORTED_EXTENSIONS = {".c", ".h", ".cpp", ".hpp"}


@dataclass
class SourceFile:
    file_path: str
    file_name: str
    language: str
    content: str
    lines: List[str]


@dataclass
class CodeSnippet:
    file_path: str
    start_line: int
    end_line: int
    focus_line: int
    snippet_text: str


class SourceReader:
    def __init__(self, source_root: str) -> None:
        self.source_root = Path(source_root)
        self.source_index: Dict[str, SourceFile] = {}

    def discover_source_files(self) -> List[Path]:
        """
        Recursively discover supported source files under source_root.
        """
        if not self.source_root.exists():
            raise FileNotFoundError(f"Source directory not found: {self.source_root}")

        files: List[Path] = []
        for path in self.source_root.rglob("*"):
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(path)

        return sorted(files)

    def _detect_language(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in {".c", ".h"}:
            return "c"
        if suffix in {".cpp", ".hpp"}:
            return "cpp"
        return "unknown"

    def _read_file_safely(self, path: Path) -> str:
        """
        Read file using utf-8 first, then fallback.
        """
        encodings_to_try = ["utf-8", "utf-8-sig", "latin-1"]

        for encoding in encodings_to_try:
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue

        raise UnicodeDecodeError(
            "unknown", b"", 0, 1, f"Unable to decode file: {path}"
        )

    def load_sources(self) -> Dict[str, SourceFile]:
        """
        Load all source files into memory and build an index.
        Key = normalized absolute path string
        """
        discovered_files = self.discover_source_files()
        source_map: Dict[str, SourceFile] = {}

        for file_path in discovered_files:
            content = self._read_file_safely(file_path)
            lines = content.splitlines()

            source_obj = SourceFile(
                file_path=str(file_path.resolve()),
                file_name=file_path.name,
                language=self._detect_language(file_path),
                content=content,
                lines=lines,
            )

            source_map[str(file_path.resolve())] = source_obj

        self.source_index = source_map
        return self.source_index

    def get_lines(self, file_path: str) -> List[str]:
        """
        Return the list of lines for a loaded source file.
        """
        normalized = str(Path(file_path).resolve())
        if normalized not in self.source_index:
            raise KeyError(f"Source file not loaded: {file_path}")

        return self.source_index[normalized].lines

    def extract_snippet(
        self,
        file_path: str,
        line_number: int,
        context: int = 4,
        include_line_numbers: bool = True,
        highlight_focus: bool = True,
    ) -> CodeSnippet:
        """
        Extract a snippet around a warning line.
        line_number is 1-based.
        """
        lines = self.get_lines(file_path)

        if line_number < 1:
            line_number = 1
        if line_number > len(lines):
            line_number = len(lines)

        start_line = max(1, line_number - context)
        end_line = min(len(lines), line_number + context)

        snippet_lines: List[str] = []

        for current_line_num in range(start_line, end_line + 1):
            line_text = lines[current_line_num - 1]

            prefix = ""
            if include_line_numbers:
                prefix = f"{current_line_num:>4}: "

            if highlight_focus and current_line_num == line_number:
                snippet_lines.append(f">>> {prefix}{line_text}")
            else:
                snippet_lines.append(f"    {prefix}{line_text}")

        snippet_text = "\n".join(snippet_lines)

        return CodeSnippet(
            file_path=str(Path(file_path).resolve()),
            start_line=start_line,
            end_line=end_line,
            focus_line=line_number,
            snippet_text=snippet_text,
        )

    def find_file_by_name(self, file_name: str) -> Optional[str]:
        """
        Helps match warning report filenames to actual loaded paths.
        Returns resolved path string if exactly one match exists.
        """
        matches = [
            path
            for path, src in self.source_index.items()
            if src.file_name.lower() == file_name.lower()
        ]

        if len(matches) == 1:
            return matches[0]

        return None