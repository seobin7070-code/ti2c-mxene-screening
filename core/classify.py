"""후보 분류 규칙 (PDF 5장).

분류 이름은 PDF 9장 가이드에 따라 '우선 검토 / 추가 계산 권장 / 현재 기준 미충족'만 쓴다.
위에서 아래 순서로 판단하고 먼저 맞는 항목을 적용한다.
계산값(DFT)은 σ=0 으로 둔다.

condition_input 프리셋: P_cond 와 margin m 사용.
wide_range 프리셋: 보정 없이 P 사용, 발표 기준(P<reject_below 미충족, P>prefer_above 우선).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# 분류 라벨 (고정 — 다른 표현 금지)
UNMET = "현재 기준 미충족"
PRIORITY = "우선 검토"
MORE_CALC = "추가 계산 권장"


@dataclass(frozen=True)
class ClassifyInput:
    # P_cond(CO2/H2O) 의 평균/표준편차 (계산값이면 sigma_p=0)
    mu_p_cond: Optional[float]
    sigma_p: float = 0.0
    # Eads(CO2) 평균/표준편차 (낙관적/상한 판정용)
    mu_eads_co2: Optional[float] = None
    sigma_eads_co2: float = 0.0
    # Δd 평균/표준편차 (SO2 한정, 없으면 None)
    mu_dd: Optional[float] = None
    sigma_dd: float = 0.0
    # SO2 reaction_flag
    reaction_flag: str = "none"
    # P 계산에 필요한 데이터가 없으면 사유 목록
    missing: Optional[list] = None


@dataclass(frozen=True)
class ClassifyResult:
    label: str
    reasons: list        # 충족/해당 기준 문구
    needed: list         # 추가 계산 권장 시 필요한 계산 목록


def classify(inp: ClassifyInput, kappa: float, margin_m: float,
             delta_d_max: Optional[float], sigma_max: Optional[float],
             preset: str = "condition_input",
             wide_range: Optional[dict] = None) -> ClassifyResult:
    """PDF 5장 순서대로 분류한다."""
    # 데이터 부족: P 를 계산할 수 없으면 추가 계산 권장 + 필요한 계산 목록
    if inp.mu_p_cond is None:
        needed = inp.missing or ["P 계산에 필요한 데이터 없음"]
        return ClassifyResult(MORE_CALC, ["P 지표 계산 데이터 없음"], list(needed))

    if preset == "wide_range":
        return _classify_wide(inp, wide_range or {})

    return _classify_condition(inp, kappa, margin_m, delta_d_max, sigma_max)


def _classify_condition(inp, kappa, m, dd_max, sig_max) -> ClassifyResult:
    mu, sig = inp.mu_p_cond, inp.sigma_p
    # ── 1) 현재 기준 미충족 (먼저 판단) ──
    unmet_reasons = []
    if mu + kappa * sig < -m:
        unmet_reasons.append(f"P_cond 상한(μ+κσ)이 −m({-m:+.3f}) 미만")
    if inp.mu_eads_co2 is not None and (inp.mu_eads_co2 - kappa * inp.sigma_eads_co2) > 0:
        unmet_reasons.append("낙관적 Eads(CO₂)(μ−κσ)도 양수 — 안정 흡착 아님")
    if inp.reaction_flag and inp.reaction_flag != "none":
        unmet_reasons.append(f"SO₂ 계산 구조 변화 동반(reaction_flag={inp.reaction_flag})")
    if unmet_reasons:
        return ClassifyResult(UNMET, unmet_reasons, [])

    # ── 2) 우선 검토 (아래 모두 만족) ──
    pri_reasons = []
    ok = True
    if mu - kappa * sig > +m:
        pri_reasons.append(f"P_cond 하한(μ−κσ)이 +m({+m:+.3f}) 초과")
    else:
        ok = False
    if inp.mu_eads_co2 is not None:
        if (inp.mu_eads_co2 + kappa * inp.sigma_eads_co2) < 0:
            pri_reasons.append("Eads(CO₂) 상한(μ+κσ) < 0 — 안정 흡착")
        else:
            ok = False
    # Δd_max (설정된 경우만)
    if dd_max is not None:
        if inp.mu_dd is not None and (inp.mu_dd + kappa * inp.sigma_dd) <= dd_max:
            pri_reasons.append(f"Δd 상한 ≤ Δd_max({dd_max})")
        else:
            ok = False
    # σ_max (설정된 경우만)
    if sig_max is not None:
        if sig <= sig_max:
            pri_reasons.append(f"σ(P) ≤ σ_max({sig_max})")
        else:
            ok = False
    if ok and pri_reasons:
        return ClassifyResult(PRIORITY, pri_reasons, [])

    # ── 3) 추가 계산 권장 ──
    return ClassifyResult(MORE_CALC, ["기준선 사이 또는 불확실성이 큼"], [])


def _classify_wide(inp, wide) -> ClassifyResult:
    """wide_range: 보정 없는 P 와 발표 기준값으로 판정 (κσ 미사용, 계산값 기준)."""
    reject = wide.get("reject_below_eV", -0.10)
    prefer = wide.get("prefer_above_eV", 0.25)
    mu = inp.mu_p_cond
    if inp.reaction_flag and inp.reaction_flag != "none":
        return ClassifyResult(UNMET,
                              [f"SO₂ 계산 구조 변화 동반(reaction_flag={inp.reaction_flag})"], [])
    if mu < reject:
        return ClassifyResult(UNMET, [f"P < {reject:+.2f} eV"], [])
    if mu > prefer:
        return ClassifyResult(PRIORITY, [f"P > {prefer:+.2f} eV"], [])
    return ClassifyResult(MORE_CALC, ["기준선 사이"], [])
