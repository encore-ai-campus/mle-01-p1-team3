"""하나 이상의 CSV 입력을 찾고 공통 스키마로 읽는다."""

from __future__ import annotations

import csv
import glob
from pathlib import Path
from typing import Sequence

REQUIRED_COLUMNS = frozenset({"url", "title", "content"})
OPTIONAL_COLUMNS = ("category", "author", "created_at", "views", "likes")


class InputSchemaError(ValueError):
    """입력 CSV에 필수 컬럼이 없을 때 발생한다."""


def discover_input_files(patterns: Sequence[str | Path]) -> list[Path]:
    """리터럴 경로와 glob을 인자 순서대로 해석하고 중복을 제거한다."""
    discovered: list[Path] = []
    seen: set[Path] = set()

    for raw_pattern in patterns:
        pattern = str(raw_pattern)
        literal = Path(pattern)
        matches = (
            [literal]
            if literal.is_file()
            else [Path(value) for value in sorted(glob.glob(pattern))]
        )

        if not matches:
            raise FileNotFoundError(f"입력 CSV를 찾지 못했습니다: {pattern}")

        for match in matches:
            resolved = match.resolve()
            if resolved.suffix.lower() != ".csv":
                raise ValueError(f"CSV 파일만 입력할 수 있습니다: {resolved}")
            if resolved not in seen:
                seen.add(resolved)
                discovered.append(resolved)

    return discovered


def load_csv_rows(paths: Sequence[Path]) -> list[dict[str, object]]:
    """CSV를 읽고 각 행에 원본 파일과 행 번호를 붙인다."""
    rows: list[dict[str, object]] = []

    for path in paths:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            columns = set(reader.fieldnames or ())
            missing = sorted(REQUIRED_COLUMNS - columns)
            if missing:
                raise InputSchemaError(
                    f"{path} 필수 컬럼 누락: {', '.join(missing)}"
                )

            for row_number, row in enumerate(reader, start=2):
                normalized: dict[str, object] = {
                    key: value or ""
                    for key, value in row.items()
                    if key is not None
                }
                for name in OPTIONAL_COLUMNS:
                    normalized.setdefault(name, "")
                normalized["__source_file"] = str(path.resolve())
                normalized["__source_row"] = row_number
                rows.append(normalized)

    return rows
