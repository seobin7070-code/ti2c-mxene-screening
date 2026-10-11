"""잠금 해제 로드맵 규칙 (core — 순수 로직, 결정적).

각 지표 모델(P(CO2/H2O), P(CO2/SO2), Δd)에 대해 현재 유효 표면 수/7을 집계하고,
'해당 표면이 그 지표를 계산하기 위해 부족한 기록 수'가 적은 순으로 다음 후보를 나열한다.
동점은 표면 이름 알파벳순(결정적). 가상 데이터를 만들지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.loader import EnergyEntry
from core.composition import Composition, is_trainable
from core.registry import (
    surfaces, find_clean, find_molecule, find_adsorbed,
    count_trainable_for_metric, METRIC_TARGET_GAS, DELTA_D_METRIC,
)

RULE_TEXT = (
    "각 표면이 해당 지표를 계산하는 데 '부족한 기록 수'(필요하지만 없는 clean/molecule/"
    "complex/조성확정/geometry 항목 수)를 세어, 부족 수가 적은 순으로 정렬합니다. "
    "동점은 표면 이름 알파벳순입니다. 부족 수 0에 가까운 표면이 '다음 1건'으로 해금에 가장 가깝습니다."
)


@dataclass
class RoadmapItem:
    surface: str
    missing_count: int
    missing_detail: str


def _missing_for_P(entries, comp_map, surface, target_gas) -> tuple[int, list[str]]:
    """P 지표를 그 표면에서 계산하는 데 부족한 기록 수와 상세."""
    need = []
    # 조성 확정
    if not is_trainable(comp_map.get(surface)):
        need.append("조성 확정")
    # CO2 복합체·단독, target 복합체·단독, clean
    if find_clean(entries, surface) is None:
        need.append("clean 표면")
    if find_molecule(entries, "CO2") is None:
        need.append("CO2 단독")
    if find_molecule(entries, target_gas) is None:
        need.append(f"{target_gas} 단독")
    if find_adsorbed(entries, surface, "CO2") is None:
        need.append("CO2 복합체")
    if find_adsorbed(entries, surface, target_gas) is None:
        need.append(f"{target_gas} 복합체")
    return len(need), need


def _missing_for_dd(entries, comp_map, surface, geom_map) -> tuple[int, list[str]]:
    need = []
    if not is_trainable(comp_map.get(surface)):
        need.append("조성 확정")
    if not geom_map or (surface, "SO2") not in geom_map:
        need.append("SO2 geometry(z_before/z_after)")
    return len(need), need


def metric_roadmap(entries: list[EnergyEntry], comp_map: dict, metric: str,
                   geom_map: dict | None = None) -> list[RoadmapItem]:
    """지표별 로드맵 항목을 부족 수 오름차순(동점 표면명)으로 반환한다."""
    geom_map = geom_map or {}
    items = []
    for s in surfaces(entries):
        if metric == DELTA_D_METRIC:
            cnt, detail = _missing_for_dd(entries, comp_map, s, geom_map)
        else:
            target = METRIC_TARGET_GAS.get(metric)
            if target is None:
                continue
            cnt, detail = _missing_for_P(entries, comp_map, s, target)
        if cnt == 0:
            continue  # 이미 계산됨 → 로드맵에 올리지 않음
        items.append(RoadmapItem(s, cnt, ", ".join(detail)))
    # 부족 수 적은 순, 동점은 표면명 알파벳순 (결정적)
    items.sort(key=lambda it: (it.missing_count, it.surface))
    return items


def roadmap_overview(entries: list[EnergyEntry], comp_map: dict,
                     metric_labels: dict, need: int, geom_map: dict | None = None) -> list[dict]:
    """세 지표의 현재 수/필요, 그리고 다음 후보 목록을 반환한다."""
    from core.registry import ALL_METRICS
    out = []
    for m in ALL_METRICS:
        current = count_trainable_for_metric(entries, comp_map, m, geom_map)
        items = metric_roadmap(entries, comp_map, m, geom_map)
        out.append({
            "metric": m, "label": metric_labels.get(m, m),
            "current": current, "need": need,
            "items": items,
        })
    return out
