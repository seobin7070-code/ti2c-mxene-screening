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
# 선택 컬럼 (비어 있어도 됨)
OPTIONAL_COLUMNS = [
    "converged", "setup_hash", "min_distance_after", "reaction_flag",
    "qc_note", "cell", "arrangement_note",
]
VALID_ROLES = {"molecule", "clean", "adsorbed"}
VALID_STATUS = {"ok", "pending", "suspect"}
VALID_REACTION_FLAGS = {"none", "H2O_dissociated", "SO2_dissociated", "termination_lost"}


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
    # 선택 필드 (없으면 빈 문자열/None)
    converged: str = ""
    setup_hash: str = ""
    min_distance_after: Optional[float] = None
    reaction_flag: str = "none"
    qc_note: str = ""
    cell: str = ""
    arrangement_note: str = ""


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

    # 선택 컬럼 파싱 (비어 있어도 됨)
    rflag = (row.get("reaction_flag") or "none").strip() or "none"
    if rflag not in VALID_REACTION_FLAGS:
        return None, RowError(
            idx, f"reaction_flag 값이 유효하지 않음: '{rflag}'")
    mind_raw = (row.get("min_distance_after") or "").strip()
    try:
        min_distance_after = float(mind_raw) if mind_raw else None
    except ValueError:
        return None, RowError(idx, f"min_distance_after를 숫자로 파싱할 수 없음: '{mind_raw}'")

    entry = EnergyEntry(
        key=key,
        role=role,
        surface=(row.get("surface") or "").strip(),
        gas=(row.get("gas") or "").strip(),
        energy_Ry=energy,
        source_file=(row.get("source_file") or "").strip(),
        calc_group=(row.get("calc_group") or "").strip(),
        status=status,
        converged=(row.get("converged") or "").strip(),
        setup_hash=(row.get("setup_hash") or "").strip(),
        min_distance_after=min_distance_after,
        reaction_flag=rflag,
        qc_note=(row.get("qc_note") or "").strip(),
        cell=(row.get("cell") or "").strip(),
        arrangement_note=(row.get("arrangement_note") or "").strip(),
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
    # source_file → 처음 등록된 energy_Ry (같은 파일명에 다른 값 등록 거부)
    seen_source: dict[str, float] = {}
    for i, row in enumerate(rows, start=1):
        entry, err = _validate_row(i, row)
        if err is not None:
            errors.append(err)
            continue
        # 같은 source_file 에 서로 다른 energy_Ry 가 오면 등록 거부
        if entry.source_file:
            prev = seen_source.get(entry.source_file)
            if prev is not None and prev != entry.energy_Ry:
                errors.append(RowError(
                    i, f"같은 source_file('{entry.source_file}')에 다른 energy_Ry 등록 거부: "
                       f"기존 {prev} ≠ 신규 {entry.energy_Ry}"))
                continue
            seen_source[entry.source_file] = entry.energy_Ry
        entries.append(entry)
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
