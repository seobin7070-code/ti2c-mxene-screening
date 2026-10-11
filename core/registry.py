"""레지스트리 유틸: 엔트리 조회, 누락 체크리스트, 지표별 학습 가능 수 산출.

모두 순수 함수로, UI 없이 단위 테스트가 가능하다 (요구사항 6.5, 8.8).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.loader import EnergyEntry
from core.energetics import compute_E_ad, AdResult
from core.metrics import selectivity_P, MetricResult, delta_d
from core.composition import Composition, is_trainable


# ---- 엔트리 조회 ----------------------------------------------------------

def find_molecule(entries: list[EnergyEntry], gas: str) -> Optional[EnergyEntry]:
    for e in entries:
        if e.role == "molecule" and e.gas == gas:
            return e
    return None


def find_clean(entries: list[EnergyEntry], surface: str) -> Optional[EnergyEntry]:
    for e in entries:
        if e.role == "clean" and e.surface == surface:
            return e
    return None


def find_adsorbed(entries: list[EnergyEntry], surface: str, gas: str) -> Optional[EnergyEntry]:
    for e in entries:
        if e.role == "adsorbed" and e.surface == surface and e.gas == gas:
            return e
    return None


def surfaces(entries: list[EnergyEntry]) -> list[str]:
    seen: list[str] = []
    for e in entries:
        if e.surface and e.surface not in seen:
            seen.append(e.surface)
    return seen


def gases(entries: list[EnergyEntry]) -> list[str]:
    seen: list[str] = []
    for e in entries:
        if e.gas and e.gas not in seen:
            seen.append(e.gas)
    return seen


def compute_ad_for(entries: list[EnergyEntry], surface: str, gas: str) -> AdResult:
    """(표면, 가스) 조합의 E_ad를 계산한다 (없는 요소는 None으로 전달)."""
    return compute_E_ad(
        adsorbed=find_adsorbed(entries, surface, gas),
        clean=find_clean(entries, surface),
        molecule=find_molecule(entries, gas),
    )


# ---- 누락 체크리스트 (요구사항 6.4, 6.5) ----------------------------------

@dataclass(frozen=True)
class MissingItem:
    scope: str      # 예: "표면 Ti2CO2 + 가스 CO2" 또는 "전역"
    detail: str     # 무엇이 없는지


def missing_checklist(
    entries: list[EnergyEntry],
    target_gases: Optional[list[str]] = None,
) -> list[MissingItem]:
    """계산에 필요하지만 아직 없는 항목을 집계한다.

    - 각 (표면, 가스) 조합에서 E_ad 계산에 필요한 molecule/clean/adsorbed 누락.
    - 전역: 선택성 지표에 필요하지만 없는 단독 분자(예: H2O).
    """
    items: list[MissingItem] = []
    surf_list = surfaces(entries)

    # 선택성 지표에 필요한 가스 집합 (기본: CO2, H2O, SO2)
    needed_gases = target_gases or ["CO2", "H2O", "SO2"]

    # 전역: 단독 분자 누락
    for g in needed_gases:
        if find_molecule(entries, g) is None:
            items.append(MissingItem("전역", f"{g} 단독 분자 에너지 없음"))

    # 표면×가스: 복합체/clean 누락 (단, 해당 가스의 복합체가 하나라도 있는 경우 위주로)
    for s in surf_list:
        if find_clean(entries, s) is None:
            items.append(MissingItem(f"표면 {s}", "clean 표면 에너지 없음"))
        for g in needed_gases:
            ad = find_adsorbed(entries, s, g)
            if ad is None:
                items.append(MissingItem(f"표면 {s} + 가스 {g}", "복합체(adsorbed) 에너지 없음"))

    return items


# ---- 지표별 학습 가능 수 (요구사항 8.2, 8.8) ------------------------------

# 지표 정의 (지표별 독립 모델 3개)
# - P 지표: target 가스 흡착과 CO2 흡착이 모두 계산되어야 함
# - Δd: geometry(z_before/z_after)로 실제 계산되어야 함
METRIC_TARGET_GAS = {
    "P(CO2/H2O)": "H2O",
    "P(CO2/SO2)": "SO2",
}
DELTA_D_METRIC = "Δd"
ALL_METRICS = ["P(CO2/H2O)", "P(CO2/SO2)", DELTA_D_METRIC]


def trainable_points_for_metric(
    entries: list[EnergyEntry],
    comp_map: dict[str, Composition],
    metric: str,
    geom_map: Optional[dict] = None,
) -> list[tuple[list[float], float]]:
    """해당 지표가 '실제 계산'되고 조성이 확정된 표면들의 (조성벡터, 값) 목록.

    모든 지표 공통 조건:
      1) 표면 조성이 trainable (confirmed + 세 좌표 존재) 해야 한다.
      2) 해당 지표가 그 표면에서 실제로 계산 가능(ok)해야 한다.
    즉 '지표가 계산된 표면'만 센다. 지표가 pending이면 카운트하지 않는다. (요구사항 8.2, 8.6)

    - P 지표: target 가스 흡착 E_ad 와 CO2 흡착 E_ad 가 모두 계산되어야 한다.
    - Δd: geom_map 에 해당 표면의 geometry 가 있어야 계산된다. geom_map 이 없으면 0.
    """
    points: list[tuple[list[float], float]] = []

    # ── Δd 모델 ───────────────────────────────────────────────
    if metric == DELTA_D_METRIC:
        if not geom_map:
            return points  # geometry 데이터 없음 → 유효 데이터 0 (현재 상태)
        for s in surfaces(entries):
            comp = comp_map.get(s)
            if not is_trainable(comp):
                continue
            # Δd는 SO2 케이스 한정
            geom = geom_map.get((s, "SO2"))
            res = delta_d(geom)
            if res.ok:
                points.append(([comp.xO, comp.xF, comp.xOH], res.value))
        return points

    # ── P 지표 모델 ───────────────────────────────────────────
    target_gas = METRIC_TARGET_GAS.get(metric)
    if target_gas is None:
        return points

    for s in surfaces(entries):
        comp = comp_map.get(s)
        if not is_trainable(comp):
            continue
        e_ad_target = compute_ad_for(entries, s, target_gas)
        e_ad_co2 = compute_ad_for(entries, s, "CO2")
        res_p: MetricResult = selectivity_P(metric, e_ad_target, e_ad_co2, target_gas)
        if res_p.ok:
            points.append(([comp.xO, comp.xF, comp.xOH], res_p.value_eV))
    return points


def count_trainable_for_metric(
    entries: list[EnergyEntry],
    comp_map: dict[str, Composition],
    metric: str,
    geom_map: Optional[dict] = None,
) -> int:
    """해당 지표 모델의 '지표가 계산된 표면' 수 (요구사항 8.6, 8.8)."""
    return len(trainable_points_for_metric(entries, comp_map, metric, geom_map))
