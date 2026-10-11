"""흡착 에너지 계산 + calc_group 일치 검사 + suspect 판정 (핵심 로직).

설계 원칙: 계산 '거부'도 예외가 아니라 일급 결과값(AdResult)으로 반환한다.
UI가 try/except로 과학적 판단을 내리지 않도록 하기 위함이다 (DI-2, DI-3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.loader import EnergyEntry
from core.units import ry_to_ev

# suspect 임계값 (eV) — 요구사항 4.1
SUSPECT_LOW_EV = -3.0
SUSPECT_HIGH_EV = 0.5


@dataclass(frozen=True)
class AdResult:
    ok: bool
    E_ad_eV: Optional[float]
    E_ad_Ry: Optional[float]
    components: dict          # 세 에너지 값 + source_file + calc_group (요구사항 3.5, DI-4)
    calc_group: Optional[str]
    suspect: bool
    reason: Optional[str]     # 실패/거부 사유 (한국어)


def is_suspect(e_ad_ev: float) -> bool:
    """E_ad(eV)가 물리적으로 비현실적 범위인지 판정한다 (요구사항 4.1)."""
    return e_ad_ev < SUSPECT_LOW_EV or e_ad_ev > SUSPECT_HIGH_EV


def _component(entry: Optional[EnergyEntry]) -> Optional[dict]:
    if entry is None:
        return None
    return {
        "energy_Ry": entry.energy_Ry,
        "source_file": entry.source_file,
        "calc_group": entry.calc_group,
        "key": entry.key,
    }


def compute_E_ad(
    adsorbed: Optional[EnergyEntry],
    clean: Optional[EnergyEntry],
    molecule: Optional[EnergyEntry],
) -> AdResult:
    """E_ad = E_adsorbed − (E_clean + E_molecule).

    세 값이 모두 존재하고 calc_group이 동일할 때만 계산한다 (요구사항 3.1~3.5, DI-6).
    """
    # 1) 값 존재 검사 — 하나라도 없으면 거부 (요구사항 3.3, DI-2)
    missing = []
    if adsorbed is None:
        missing.append("복합체(adsorbed) 에너지 없음")
    if clean is None:
        missing.append("clean 표면 에너지 없음")
    if molecule is None:
        missing.append("단독 분자(molecule) 에너지 없음")
    if missing:
        return AdResult(
            ok=False, E_ad_eV=None, E_ad_Ry=None,
            components={
                "E_adsorbed": _component(adsorbed),
                "E_clean": _component(clean),
                "E_molecule": _component(molecule),
            },
            calc_group=None, suspect=False,
            reason="; ".join(missing),
        )

    # 2) calc_group 일치 검사 (요구사항 3.4, DI-6)
    groups = {adsorbed.calc_group, clean.calc_group, molecule.calc_group}
    if len(groups) != 1:
        return AdResult(
            ok=False, E_ad_eV=None, E_ad_Ry=None,
            components={
                "E_adsorbed": _component(adsorbed),
                "E_clean": _component(clean),
                "E_molecule": _component(molecule),
            },
            calc_group=None, suspect=False,
            reason=(
                "calc_group 불일치: "
                f"adsorbed={adsorbed.calc_group}, "
                f"clean={clean.calc_group}, "
                f"molecule={molecule.calc_group}"
            ),
        )

    # 3) 계산
    e_ad_ry = adsorbed.energy_Ry - (clean.energy_Ry + molecule.energy_Ry)
    e_ad_ev = ry_to_ev(e_ad_ry)
    calc_group = adsorbed.calc_group

    return AdResult(
        ok=True,
        E_ad_eV=e_ad_ev,
        E_ad_Ry=e_ad_ry,
        components={
            "E_adsorbed": _component(adsorbed),
            "E_clean": _component(clean),
            "E_molecule": _component(molecule),
        },
        calc_group=calc_group,
        suspect=is_suspect(e_ad_ev),   # 값은 유지하되 경고 부여 (요구사항 4.2)
        reason=None,
    )
