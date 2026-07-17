#!/usr/bin/env python3
"""Fail if any backend/frontend source file exceeds the 1500-line hard cap; warn above 1200."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [ROOT / "backend" / "app", ROOT / "frontend" / "src"]
EXTENSIONS = {".py", ".ts", ".tsx"}
EXCLUDE_DIRS = {"alembic/versions", "node_modules"}
EXCLUDE_SUFFIXES = {"types.gen.ts"}
WARN_AT = 1200
FAIL_AT = 1500


def is_excluded(path: Path) -> bool:
    posix = path.as_posix()
    if any(excl in posix for excl in EXCLUDE_DIRS):
        return True
    return any(posix.endswith(suffix) for suffix in EXCLUDE_SUFFIXES)


def count_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return sum(1 for _ in f)


def main() -> int:
    failures: list[tuple[Path, int]] = []
    warnings: list[tuple[Path, int]] = []

    for target in TARGETS:
        if not target.exists():
            continue
        for path in target.rglob("*"):
            if not path.is_file() or path.suffix not in EXTENSIONS or is_excluded(path):
                continue
            lines = count_lines(path)
            if lines > FAIL_AT:
                failures.append((path, lines))
            elif lines > WARN_AT:
                warnings.append((path, lines))

    for path, lines in warnings:
        print(f"WARN: {path.relative_to(ROOT)} has {lines} lines (warn threshold {WARN_AT})")

    for path, lines in failures:
        print(f"FAIL: {path.relative_to(ROOT)} has {lines} lines (limit {FAIL_AT})")

    if failures:
        print(f"\n{len(failures)} file(s) exceed the {FAIL_AT}-line limit.")
        return 1

    print(f"OK: no file exceeds {FAIL_AT} lines ({len(warnings)} warning(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
