"""배가스 조건 보정 δ (PDF 4.4).

DFT 값은 0 K·한 분자 조건이라 배가스 조건과 무관하다. 사용자가 입력한 온도·분율은
P 에 더하는 보정값 δ 로만 들어간다.

  P_cond(CO2/H2O) = P(CO2/H2O) + δ_H2O
  δ_H2O = T·[S°(H2O) − S°(CO2)] − kT·ln(p_H2O / p_CO2)
  P_cond(CO2/SO2) = P(CO2/SO2) + δ_SO2
  δ_SO2 = T·[S°(SO2) − S°(CO2)] − kT·ln(p_SO2 / p_CO2)

분율은 비(p_i/p_CO2)로만 쓰이므로 단위(mol% 또는 ppm)는 일관되기만 하면 된다.
가정: 이상기체, 저피복, 흡착 엔트로피 무시, 영점 에너지 무시 (1차 근사).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

T_K = 298.15                       # 온도 (MVP 고정)
KT_EV = 0.02569                    # kT (eV)
JMOL_PER_EV = 96485.0              # J/mol → eV 환산
S_STD = {                          # 표준 엔트로피 S° (298.15 K, J/mol·K)
    "CO2": 213.8, "H2O": 188.8, "SO2": 248.2,
}

NOTE = "온도·분압 1차 보정"
NOTE_HINT = "조건 입력은 후보 순위가 아니라 분류 기준선을 옮깁니다."


def t_delta_s_eV(gas: str) -> float:
    """T·[S°(gas) − S°(CO2)] 를 eV로 반환."""
    return T_K * (S_STD[gas] - S_STD["CO2"]) / JMOL_PER_EV


@dataclass(frozen=True)
class CorrectionResult:
    ok: bool
    delta_eV: Optional[float]
    reason: Optional[str]


def delta(gas: str, p_gas: float, p_co2: float) -> CorrectionResult:
    """δ_gas = T·ΔS° − kT·ln(p_gas/p_CO2). 분율이 0/음수면 계산 거부(사유 반환)."""
    if gas not in ("H2O", "SO2"):
        return CorrectionResult(False, None, f"지원하지 않는 가스: {gas}")
    if p_co2 is None or p_gas is None:
        return CorrectionResult(False, None, "분율 입력 없음")
    if p_co2 <= 0 or p_gas <= 0:
        return CorrectionResult(False, None, "분율은 0보다 커야 함 (로그비 계산 불가)")
    d = t_delta_s_eV(gas) - KT_EV * math.log(p_gas / p_co2)
    return CorrectionResult(True, d, None)


def ppm_to_molpct(ppm: float) -> float:
    """ppm → mol% (500 ppm = 0.05 mol%). 비로만 쓰이므로 단위 통일용."""
    return ppm / 10000.0
