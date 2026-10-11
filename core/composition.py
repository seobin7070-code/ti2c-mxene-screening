"""조성 매핑: 표면 → [xO, xF, xOH].

매핑은 코드가 아니라 data/composition_map.csv 로 관리되어
사용자가 확정 시 코드 수정 없이 보완 가능하다 (요구사항 10.4).
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Composition:
    surface: str
    xO: Optional[float]
    xF: Optional[float]
    xOH: Optional[float]
    confirmed: bool
    arrangement_note: str = ""
    status: str = ""   # computed | planned


def _to_float(s: str) -> Optional[float]:
    s = (s or "").strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _to_bool(s: str) -> bool:
    return (s or "").strip().lower() in {"true", "1", "yes", "y"}


def load_composition_map(path: str) -> dict[str, Composition]:
    """조성 매핑 CSV를 로드한다. 파일이 없으면 빈 매핑을 반환한다."""
    result: dict[str, Composition] = {}
    if not os.path.exists(path):
        return result
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            surface = (row.get("surface") or "").strip()
            if not surface:
                continue
            result[surface] = Composition(
                surface=surface,
                xO=_to_float(row.get("xO", "")),
                xF=_to_float(row.get("xF", "")),
                xOH=_to_float(row.get("xOH", "")),
                confirmed=_to_bool(row.get("confirmed", "")),
                arrangement_note=(row.get("arrangement_note") or "").strip(),
                status=(row.get("status") or "").strip(),
            )
    return result


def is_trainable(comp: Optional[Composition]) -> bool:
    """GPR 학습에 쓸 수 있는 조성인지 판정한다.

    confirmed=True 이고 세 좌표가 모두 존재해야 한다 (요구사항 10.2, 10.3).
    Ti2C_FH처럼 미확정이면 False → 학습 제외.
    """
    if comp is None or not comp.confirmed:
        return False
    return comp.xO is not None and comp.xF is not None and comp.xOH is not None


def vector(comp: Composition) -> Optional[list[float]]:
    """학습 가능한 조성의 [xO, xF, xOH] 벡터. 아니면 None."""
    if not is_trainable(comp):
        return None
    return [comp.xO, comp.xF, comp.xOH]  # type: ignore[list-item]
