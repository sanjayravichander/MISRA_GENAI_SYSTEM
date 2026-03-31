from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class SourceInventory:
    root_dir: Path
    folders: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    files_by_extension: dict[str, list[str]] = field(default_factory=dict)


class SourceFolderScanner:
    """
    Scans a source root directory and collects:
    - all subfolders
    - all files
    - files grouped by extension
    """

    def __init__(
        self,
        source_root: str | Path,
        include_extensions: Iterable[str] | None = None,
    ) -> None:
        self.source_root = Path(source_root).resolve()
        self.include_extensions = (
            {ext.lower() for ext in include_extensions}
            if include_extensions is not None
            else None
        )

    def scan(self) -> SourceInventory:
        if not self.source_root.exists():
            raise FileNotFoundError(f"Source root does not exist: {self.source_root}")

        if not self.source_root.is_dir():
            raise NotADirectoryError(f"Source root is not a directory: {self.source_root}")

        inventory = SourceInventory(root_dir=self.source_root)

        for path in sorted(self.source_root.rglob("*")):
            relative_path = path.relative_to(self.source_root).as_posix()

            if path.is_dir():
                inventory.folders.append(relative_path)
                continue

            if path.is_file():
                extension = path.suffix.lower()

                if self.include_extensions is not None and extension not in self.include_extensions:
                    continue

                inventory.files.append(relative_path)
                inventory.files_by_extension.setdefault(
                    extension or "<no_extension>", []
                ).append(relative_path)

        return inventory


def build_file_index(inventory: SourceInventory) -> dict[str, str]:
    """
    Builds a lookup index for files.

    Example:
    {
        "src/main.c": "/abs/path/src/main.c",
        "main.c": "/abs/path/src/main.c",
        "include/common.h": "/abs/path/include/common.h",
        "common.h": "/abs/path/include/common.h",
    }
    """
    index: dict[str, str] = {}

    for relative_file in inventory.files:
        absolute_path = str((inventory.root_dir / relative_file).resolve())

        # Full relative path
        index[relative_file] = absolute_path

        # Filename only
        filename = Path(relative_file).name
        index[filename] = absolute_path

    return index


def print_inventory(inventory: SourceInventory) -> None:
    print(f"\nSource Root: {inventory.root_dir}\n")

    print("Folders:")
    if inventory.folders:
        for folder in inventory.folders:
            print(f"  - {folder}")
    else:
        print("  (no folders found)")

    print("\nFiles:")
    if inventory.files:
        for file_name in inventory.files:
            print(f"  - {file_name}")
    else:
        print("  (no files found)")

    print("\nFiles By Extension:")
    if inventory.files_by_extension:
        for ext, files in sorted(inventory.files_by_extension.items()):
            print(f"  {ext}:")
            for file_name in files:
                print(f"    - {file_name}")
    else:
        print("  (no matching files found)")


def print_file_index(file_index: dict[str, str]) -> None:
    print("\nFile Index:")
    if file_index:
        for key, value in sorted(file_index.items()):
            print(f"  {key} -> {value}")
    else:
        print("  (file index is empty)")


def main() -> None:
    # Change this path to your project source folder
    source_root = "data/input/source_code"

    # Keep only C/C header files. Set to None to include all files.
    include_extensions = [".c", ".h"]

    scanner = SourceFolderScanner(
        source_root=source_root,
        include_extensions=include_extensions,
    )

    inventory = scanner.scan()
    file_index = build_file_index(inventory)

    print_inventory(inventory)
    print_file_index(file_index)


if __name__ == "__main__":
    main()