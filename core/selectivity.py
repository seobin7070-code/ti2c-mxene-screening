"""CO₂ 선호도 P 지표 (PDF 4.2) 와 Δd (PDF 4.3).

P(CO₂/H₂O) = Eads(H₂O) − Eads(CO₂)
P(CO₂/SO₂) = Eads(SO₂) − Eads(CO₂)   ← 참고용, 분류에 쓰지 않음
두 가스의 Eads 가 모두 양수이면 'two_gas_unstable' 플래그를 세운다(우선 검토 제외).
SO₂ 계산 reaction_flag ≠ none 이면 'structure_change' 플래그(분류 미사용).
Δd = |(z_T − z_ref)_after − (z_T − z_ref)_before|  (SO₂ 계산 한정)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.energetics import AdResult


@dataclass(frozen=True)
class PResult:
    label: str                 # "P(CO2/H2O)" | "P(CO2/SO2)"
    ok: bool                   # True면 value 유효
    value_eV: Optional[float]
    reason: Optional[str]      # 계산 불가 사유
    two_gas_unstable: bool = False   # 두 가스 Eads 모두 양수
    structure_change: bool = False   # SO2 reaction_flag ≠ none
    calc_group: Optional[str] = None


def selectivity_P(label: str, e_ad_target: Optional[AdResult],
                  e_ad_co2: Optional[AdResult], target_name: str,
                  reaction_flag: str = "none") -> PResult:
    """P = Eads(target) − Eads(CO₂). 데이터·calc_group 검사."""
    if e_ad_co2 is None or not e_ad_co2.ok:
        return PResult(label, False, None, "CO₂ 흡착 에너지 계산 데이터 없음")
    if e_ad_target is None or not e_ad_target.ok:
        return PResult(label, False, None, f"{target_name} 계산 데이터 없음")
    if e_ad_target.calc_group != e_ad_co2.calc_group:
        return PResult(label, False, None,
                       f"calc_group 불일치: {target_name}={e_ad_target.calc_group}, "
                       f"CO₂={e_ad_co2.calc_group}")

    value = e_ad_target.E_ad_eV - e_ad_co2.E_ad_eV
    two_unstable = (e_ad_target.E_ad_eV > 0) and (e_ad_co2.E_ad_eV > 0)
    struct = (target_name == "SO2" and reaction_flag not in ("", "none"))
    return PResult(label, True, value, None,
                   two_gas_unstable=two_unstable, structure_change=struct,
                   calc_group=e_ad_target.calc_group)


@dataclass(frozen=True)
class DeltaDResult:
    ok: bool
    value_A: Optional[float]
    reason: Optional[str]


def delta_d(z_T_before: Optional[float], z_T_after: Optional[float],
            z_ref_before: Optional[float], z_ref_after: Optional[float]) -> DeltaDResult:
    """Δd = |(z_T − z_ref)_after − (z_T − z_ref)_before| (SO₂ 한정)."""
    vals = [z_T_before, z_T_after, z_ref_before, z_ref_after]
    if any(v is None for v in vals):
        return DeltaDResult(False, None, "geometry(z 좌표) 데이터 없음")
    before = z_T_before - z_ref_before
    after = z_T_after - z_ref_after
    return DeltaDResult(True, abs(after - before), None)
