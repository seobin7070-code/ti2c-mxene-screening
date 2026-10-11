"""단위 변환: Rydberg ↔ electron-volt.

변환 상수는 이 모듈에 정의된 단 하나(RY_TO_EV)만 존재한다.
에너지 '값'은 어디에서도 하드코딩하지 않으며 CSV에서만 로드한다.
"""

from __future__ import annotations

# 유일한 변환 상수 (1 Ry = 13.605698 eV)
RY_TO_EV: float = 13.605698


def ry_to_ev(x_ry: float) -> float:
    """Rydberg 값을 eV로 변환한다 (순수 함수)."""
    return x_ry * RY_TO_EV


def ev_to_ry(x_ev: float) -> float:
    """eV 값을 Rydberg로 변환한다 (순수 함수)."""
    return x_ev / RY_TO_EV
