"""CSV 로딩 + 스키마 검증.

에너지 '값'은 오직 이 모듈을 통해 data/energies.csv 에서만 들어온다 (요구사항 1.5, DI-1).
잘못된 행은 전체를 중단시키지 않고 RowError로 수집한다 (요구사항 1.3).
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from typing import Optional

REQUIRED_COLUMNS = [
    "key", "role", "surface", "gas",
    "energy_Ry", "source_file", "calc_group", "status",
]
VALID_ROLES = {"molecule", "clean", "adsorbed"}
VALID_STATUS = {"ok", "pending", "suspect"}


@dataclass(frozen=True)
class EnergyEntry:
    key: str
    role: str
    surface: str
    gas: str
    energy_Ry: float
    source_file: str
    calc_group: str
    status: str


@dataclass(frozen=True)
class RowError:
    row_index: int   # 1-based 데이터 행 번호 (헤더 제외)
    reason: str      # 한국어 사유


@dataclass(frozen=True)
class LoadResult:
    entries: list[EnergyEntry]
    errors: list[RowError]
    file_present: bool


def validate_header(fieldnames: Optional[list[str]]) -> list[str]:
    """필수 컬럼 누락 목록을 반환한다 (요구사항 1.1)."""
    present = set(fieldnames or [])
    return [c for c in REQUIRED_COLUMNS if c not in present]


def _validate_row(idx: int, row: dict) -> tuple[Optional[EnergyEntry], Optional[RowError]]:
    role = (row.get("role") or "").strip()
    status = (row.get("status") or "").strip()
    raw_energy = (row.get("energy_Ry") or "").strip()

    if role not in VALID_ROLES:
        return None, RowError(idx, f"role 값이 유효하지 않음: '{role}' (허용: molecule|clean|adsorbed)")
    if status not in VALID_STATUS:
        return None, RowError(idx, f"status 값이 유효하지 않음: '{status}' (허용: ok|pending|suspect)")
    try:
        energy = float(raw_energy)
    except ValueError:
        return None, RowError(idx, f"energy_Ry를 숫자로 파싱할 수 없음: '{raw_energy}'")

    key = (row.get("key") or "").strip()
    if not key:
        return None, RowError(idx, "key가 비어 있음")

    entry = EnergyEntry(
        key=key,
        role=role,
        surface=(row.get("surface") or "").strip(),
        gas=(row.get("gas") or "").strip(),
        energy_Ry=energy,
        source_file=(row.get("source_file") or "").strip(),
        calc_group=(row.get("calc_group") or "").strip(),
        status=status,
    )
    return entry, None


def parse_rows(fieldnames: Optional[list[str]], rows: list[dict]) -> LoadResult:
    """메모리상 행 리스트를 검증한다 (업로드 CSV 검증에 재사용, 요구사항 6.3)."""
    missing = validate_header(fieldnames)
    if missing:
        return LoadResult(
            entries=[],
            errors=[RowError(0, f"필수 컬럼 누락: {', '.join(missing)}")],
            file_present=True,
        )

    entries: list[EnergyEntry] = []
    errors: list[RowError] = []
    for i, row in enumerate(rows, start=1):
        entry, err = _validate_row(i, row)
        if err is not None:
            errors.append(err)
        else:
            entries.append(entry)  # type: ignore[arg-type]
    return LoadResult(entries=entries, errors=errors, file_present=True)


def load_energies(path: str) -> LoadResult:
    """data/energies.csv를 로드한다. 파일이 없으면 빈 레지스트리를 반환한다 (요구사항 1.4)."""
    if not os.path.exists(path):
        return LoadResult(entries=[], errors=[], file_present=False)
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return parse_rows(reader.fieldnames, rows)


def validate_schema(fieldnames: Optional[list[str]], rows: list[dict]) -> list[RowError]:
    """업로드 CSV 스키마 검증. 오류 리스트가 비어 있으면 반영 가능 (요구사항 6.3)."""
    return parse_rows(fieldnames, rows).errors
