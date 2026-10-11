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


# ── 엔트리 조회 (calc_group 지정 가능) ──────────────────────────
# calc_group 을 지정하면 그 세트 안에서만 찾는다. 서로 다른 calc_group 을
# 섞어서 빼지 않기 위함이다 (데이터 무결성 철칙).
def find_molecule(entries, gas, calc_group=None):
    for e in entries:
        if e.role == "molecule" and e.gas == gas and \
           (calc_group is None or e.calc_group == calc_group):
            return e
    return None


def find_clean(entries, surface, calc_group=None):
    for e in entries:
        if e.role == "clean" and e.surface == surface and \
           (calc_group is None or e.calc_group == calc_group):
            return e
    return None


def find_adsorbed(entries, surface, gas, calc_group=None):
    for e in entries:
        if e.role == "adsorbed" and e.surface == surface and e.gas == gas and \
           (calc_group is None or e.calc_group == calc_group):
            return e
    return None


def surfaces(entries, calc_group=None) -> list[str]:
    seen: list[str] = []
    for e in entries:
        if calc_group is not None and e.calc_group != calc_group:
            continue
        if e.surface and e.surface not in seen:
            seen.append(e.surface)
    return seen


def calc_groups(entries) -> list[str]:
    seen: list[str] = []
    for e in entries:
        if e.calc_group and e.calc_group not in seen:
            seen.append(e.calc_group)
    return seen


def compute_ad_for(entries, surface, gas, calc_group=None) -> AdResult:
    """(표면, 가스) 조합의 E_ad를 계산한다 (PDF 4.1).

    calc_group 을 지정하면 그 세트의 복합체·표면·분자만 쓴다. 지정하지 않으면
    복합체가 속한 세트를 자동으로 따라가(복합체 기준 calc_group) 같은 세트끼리 계산한다.
    """
    ad = find_adsorbed(entries, surface, gas, calc_group)
    # 복합체가 속한 세트를 기준으로 표면·분자도 같은 세트에서 찾는다
    cg = calc_group if calc_group is not None else (ad.calc_group if ad else None)
    return compute_E_ad(
        adsorbed=ad,
        clean=find_clean(entries, surface, cg),
        molecule=find_molecule(entries, gas, cg),
    )


def reaction_flag_for(entries: list[EnergyEntry], surface: str, gas: str) -> str:
    e = find_adsorbed(entries, surface, gas)
    return e.reaction_flag if e else "none"


def all_adsorption_rows(entries) -> list[dict]:
    """등록된 모든 복합체(adsorbed)의 E_ads 를 세트별로 계산해 반환한다.

    각 복합체는 자신이 속한 calc_group 안에서만 계산된다(세트 혼합 금지).
    반환: [{calc_group, surface, gas, E_ads_eV, E_ads_Ry, source_file, ok, reason}]
    """
    rows = []
    for e in entries:
        if e.role != "adsorbed":
            continue
        r = compute_ad_for(entries, e.surface, e.gas, calc_group=e.calc_group)
        rows.append({
            "calc_group": e.calc_group,
            "surface": e.surface,
            "gas": e.gas,
            "E_ads_eV": r.E_ad_eV if r.ok else None,
            "E_ads_Ry": r.E_ad_Ry if r.ok else None,
            "source_file": e.source_file,
            "ok": r.ok,
            "reason": r.reason,
        })
    return rows


def best_calc_group_for_surface(entries, surface: str) -> Optional[str]:
    """표면의 세 가스를 '한 세트 안에서' 가장 많이 계산할 수 있는 calc_group.

    P 지표는 세트를 섞어서 빼면 안 되므로(데이터 무결성 철칙), 표면별로 가스 복합체를
    가장 많이 보유한 단일 세트를 골라 그 안에서만 E_ads·P 를 계산한다.
    동점이면 calc_groups(entries) 등장 순서가 빠른 세트를 쓴다.
    """
    best, best_n = None, -1
    for cg in calc_groups(entries):
        n = sum(1 for g in GASES
                if find_adsorbed(entries, surface, g, calc_group=cg) is not None)
        if n > best_n:
            best, best_n = cg, n
    return best if best_n > 0 else None


def eads_for_surface(entries: list[EnergyEntry], surface: str,
                     calc_group: Optional[str] = None) -> dict[str, AdResult]:
    """표면의 세 가스 E_ads 결과. calc_group 미지정 시 가스를 가장 많이 보유한 단일 세트에서 계산."""
    cg = calc_group if calc_group is not None else best_calc_group_for_surface(entries, surface)
    return {g: compute_ad_for(entries, surface, g, calc_group=cg) for g in GASES}


def p_indices(entries: list[EnergyEntry], surface: str,
              calc_group: Optional[str] = None) -> dict[str, PResult]:
    """P(CO2/H2O), P(CO2/SO2) 계산. 세 가스를 동일 세트 안에서만 계산해 세트 혼합을 막는다."""
    cg = calc_group if calc_group is not None else best_calc_group_for_surface(entries, surface)
    e = eads_for_surface(entries, surface, calc_group=cg)
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


def training_points_multiset(entries, comp_map, target: str) -> list:
    """세트 통합 학습 데이터: [((xO,xF,xOH), calc_group, y)].

    각 (표면, 세트) 조합에서 '같은 세트 안에서만' E_ads 를 계산한다(세트 혼합 금지).
    조성이 확정된 표면만 포함한다. 서로 다른 세트는 섞어서 빼지 않고, 세트 지표를
    별도 차원으로 넘겨 모델이 구분해 학습하게 한다.
    """
    pts = []
    if target == "Delta_d":
        return pts  # geometry 데이터 없음
    gas = _TARGET_GAS.get(target)
    if gas is None:
        return pts
    for cg in calc_groups(entries):
        for s in surfaces(entries, calc_group=cg):
            comp = comp_map.get(s)
            if not is_trainable(comp):
                continue
            r = compute_ad_for(entries, s, gas, calc_group=cg)
            if r.ok:
                pts.append(((comp.xO, comp.xF, comp.xOH), cg, r.E_ad_eV))
    return pts


def training_points_unified(entries, comp_map) -> list:
    """통합 학습 데이터: [((xO,xF,xOH), calc_group, gas, y)].

    조성 확정 표면의 모든 (세트, 가스) E_ads 계산값을 세트 안에서만 계산해 모은다.
    가스를 입력 차원으로 넣어 하나의 GPR 로 학습(가스별로 나누지 않아 7개 이상 확보).
    """
    pts = []
    for cg in calc_groups(entries):
        for s in surfaces(entries, calc_group=cg):
            comp = comp_map.get(s)
            if not is_trainable(comp):
                continue
            for g in GASES:
                r = compute_ad_for(entries, s, g, calc_group=cg)
                if r.ok:
                    pts.append(((comp.xO, comp.xF, comp.xOH), cg, g, r.E_ad_eV))
    return pts


def confirmed_surface_markers(entries, comp_map) -> list[dict]:
    """조성 확정 표면을 세트별로 모아 지도 마커 데이터로 반환한다.

    같은 표면이 여러 세트에 있으면 세트별로 각각 마커를 만든다.
    반환: [{surface, calc_group, xO, xF, xOH, eads:{gas:eV}}]
    """
    out = []
    for cg in calc_groups(entries):
        for s in surfaces(entries, calc_group=cg):
            comp = comp_map.get(s)
            if not is_trainable(comp):
                continue
            eads = {}
            for g in GASES:
                r = compute_ad_for(entries, s, g, calc_group=cg)
                if r.ok:
                    eads[g] = r.E_ad_eV
            out.append({"surface": s, "calc_group": cg,
                        "xO": comp.xO, "xF": comp.xF, "xOH": comp.xOH, "eads": eads})
    return out


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
