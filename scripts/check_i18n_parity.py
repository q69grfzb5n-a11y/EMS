#!/usr/bin/env python3
"""Phase 9 i18n completeness gate: every en/<ns>.json locale file must have an
identical set of keys (recursively) as its ar/<ns>.json sibling, and vice
versa. Run from the repo root: `python3 scripts/check_i18n_parity.py`."""

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"


def flatten_keys(obj: Any, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys.add(full_key)
            keys |= flatten_keys(value, full_key)
    return keys


def main() -> int:
    en_files = sorted(FRONTEND_SRC.glob("**/locales/en/*.json"))
    ar_files = sorted(FRONTEND_SRC.glob("**/locales/ar/*.json"))
    if not en_files:
        print(f"No locale files found under {FRONTEND_SRC} — check the path.")
        return 1

    en_by_name = {p.parent.parent.parent / p.name: p for p in en_files}
    ar_by_name = {p.parent.parent.parent / p.name: p for p in ar_files}

    problems: list[str] = []

    for module_key, en_path in en_by_name.items():
        namespace = en_path.stem
        ar_path = ar_by_name.get(module_key)
        if ar_path is None:
            problems.append(f"{namespace}: en/{en_path.name} exists but ar/{en_path.name} is missing")
            continue

        en_keys = flatten_keys(json.loads(en_path.read_text(encoding="utf-8")))
        ar_keys = flatten_keys(json.loads(ar_path.read_text(encoding="utf-8")))

        missing_in_ar = sorted(en_keys - ar_keys)
        missing_in_en = sorted(ar_keys - en_keys)
        if missing_in_ar:
            problems.append(f"{namespace}: keys in en missing from ar: {missing_in_ar}")
        if missing_in_en:
            problems.append(f"{namespace}: keys in ar missing from en: {missing_in_en}")

    for module_key, ar_path in ar_by_name.items():
        if module_key not in en_by_name:
            problems.append(f"{ar_path.stem}: ar/{ar_path.name} exists but en/{ar_path.name} is missing")

    if problems:
        print("i18n key-parity check FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print(f"OK: {len(en_files)} namespaces, en/ar keys match exactly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
