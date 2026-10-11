"""스크리닝 통합 경로 (UI 단일 진입점).

조회(엔트리 find)는 registry 재사용, 지표는 selectivity/energetics, 분류는 classify,
보정은 conditions, 좌표는 coords 를 조합한다. UI 는 여기만 호출한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.loader import EnergyEntry
from core.composition import Composition, is_trainable
from core.energetics import AdResult, compute_E_ad
from core.selectivity import selectivity_P, delta_d, PResult, DeltaDResult
from core.conditions import delta as cond_delta
from core.classify import classify, ClassifyInput, ClassifyResult
from core.coords import distance_uv

GASES = ["CO2", "H2O", "SO2"]


# ── 엔트리 조회 ─────────────────────────────────────────────────
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


def compute_ad_for(entries: list[EnergyEntry], surface: str, gas: str) -> AdResult:
    """(표면, 가스) 조합의 E_ad를 계산한다 (PDF 4.1)."""
    return compute_E_ad(
        adsorbed=find_adsorbed(entries, surface, gas),
        clean=find_clean(entries, surface),
        molecule=find_molecule(entries, gas),
    )


def reaction_flag_for(entries: list[EnergyEntry], surface: str, gas: str) -> str:
    e = find_adsorbed(entries, surface, gas)
    return e.reaction_flag if e else "none"


def eads_for_surface(entries: list[EnergyEntry], surface: str) -> dict[str, AdResult]:
    """표면의 세 가스 E_ads 결과."""
    return {g: compute_ad_for(entries, surface, g) for g in GASES}


def p_indices(entries: list[EnergyEntry], surface: str) -> dict[str, PResult]:
    """P(CO2/H2O), P(CO2/SO2) 계산."""
    e = eads_for_surface(entries, surface)
    return {
        "P(CO2/H2O)": selectivity_P("P(CO2/H2O)", e["H2O"], e["CO2"], "H2O"),
        "P(CO2/SO2)": selectivity_P("P(CO2/SO2)", e["SO2"], e["CO2"], "SO2",
                                    reaction_flag=reaction_flag_for(entries, surface, "SO2")),
    }


# ── 조건 보정 ───────────────────────────────────────────────────
@dataclass(frozen=True)
class CondCorrection:
    delta_h2o: Optional[float]
    delta_so2: Optional[float]
    reason_h2o: Optional[str]
    reason_so2: Optional[str]


def condition_correction(p_co2: float, p_h2o: float, p_so2: float) -> CondCorrection:
    """배가스 분율(동일 단위)로 δ_H2O, δ_SO2 계산."""
    dh = cond_delta("H2O", p_h2o, p_co2)
    ds = cond_delta("SO2", p_so2, p_co2)
    return CondCorrection(
        delta_h2o=dh.delta_eV if dh.ok else None,
        delta_so2=ds.delta_eV if ds.ok else None,
        reason_h2o=None if dh.ok else dh.reason,
        reason_so2=None if ds.ok else ds.reason,
    )


# ── 계산된 조성 / 학습 데이터 ───────────────────────────────────
def computed_surfaces(entries, comp_map) -> list[str]:
    """조성 확정 + 어떤 가스든 E_ads 계산값이 하나라도 있는 표면 (지도 계산 마커 대상).

    PDF [7]: 계산 마커 3개(Ti2CO2, Ti2CF2, Ti2C_OF). Ti2CO2는 SO2 복합체만,
    나머지는 CO2 복합체를 가지므로 '가스 무관 계산값 보유'로 판정한다.
    """
    out = []
    for s in surfaces(entries):
        comp = comp_map.get(s)
        if not is_trainable(comp):
            continue
        if any(compute_ad_for(entries, s, g).ok for g in GASES):
            out.append(s)
    return out


_TARGET_GAS = {"Eads_CO2": "CO2", "Eads_H2O": "H2O", "Eads_SO2": "SO2"}


def training_points(entries, comp_map, target: str) -> list:
    """타깃별 학습 데이터: [((xO,xF,xOH), y)].

    Eads_* : 조성 확정 + 해당 가스 E_ads 계산값이 있는 표면.
    Delta_d: geometry 기반(현재 데이터 없음 → 빈 리스트).
    """
    pts = []
    if target == "Delta_d":
        return pts  # geometry 데이터 없음
    gas = _TARGET_GAS.get(target)
    if gas is None:
        return pts
    for s in surfaces(entries):
        comp = comp_map.get(s)
        if not is_trainable(comp):
            continue
        r = compute_ad_for(entries, s, gas)
        if r.ok:
            pts.append(((comp.xO, comp.xF, comp.xOH), r.E_ad_eV))
    return pts


def nearest_computed(entries, comp_map, xO, xF, xOH) -> Optional[dict]:
    """임의 조성에서 가장 가까운 계산 조성과 거리(u,v 평면)."""
    best = None
    for s in computed_surfaces(entries, comp_map):
        c = comp_map[s]
        d = distance_uv((xO, xF, xOH), (c.xO, c.xF, c.xOH))
        if best is None or d < best["distance"]:
            best = {"surface": s, "distance": d,
                    "composition": (c.xO, c.xF, c.xOH)}
    return best


def missing_for_P(entries, surface) -> list[str]:
    """표면에서 P 계산에 필요한데 없는 항목 (예: 'H₂O 복합체 계산 필요')."""
    need = []
    if find_molecule(entries, "H2O") is None or \
       (find_molecule(entries, "H2O") and find_molecule(entries, "H2O").status == "pending"):
        need.append("H₂O 단독 분자 계산(짝 calc_group) 필요")
    if find_adsorbed(entries, surface, "H2O") is None:
        need.append("H₂O 복합체 계산 필요")
    if find_adsorbed(entries, surface, "CO2") is None:
        need.append("CO₂ 복합체 계산 필요")
    return need
