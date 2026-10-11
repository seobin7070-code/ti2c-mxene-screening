"""조성 좌표 변환 (PDF 6.3, 7장).

- GPR 입력 좌표: u = (xF − xOH)/√2, v = (2xO − xF − xOH)/√6
  (세 꼭짓점 사이 거리가 모두 √2 로 같은 정규직교 좌표)
- 삼원 조성 지도 좌표: O 꼭짓점 (0,0), F 꼭짓점 (1,0), OH 꼭짓점 (0.5, √3/2)
  x = xF + 0.5·xOH, y = (√3/2)·xOH
"""

from __future__ import annotations

import math

_SQRT2 = math.sqrt(2.0)
_SQRT6 = math.sqrt(6.0)
_SQRT3_2 = math.sqrt(3.0) / 2.0


def to_uv(xO: float, xF: float, xOH: float) -> tuple[float, float]:
    """조성 (xO,xF,xOH) → GPR 입력 좌표 (u, v)."""
    u = (xF - xOH) / _SQRT2
    v = (2.0 * xO - xF - xOH) / _SQRT6
    return u, v


def to_triangle_xy(xO: float, xF: float, xOH: float) -> tuple[float, float]:
    """조성 → 삼원 지도의 데카르트 좌표 (x, y)."""
    x = xF + 0.5 * xOH
    y = _SQRT3_2 * xOH
    return x, y


def composition_sum(xO: float, xF: float, xOH: float) -> float:
    return xO + xF + xOH


def is_normalized(xO: float, xF: float, xOH: float, tol: float = 1e-6) -> bool:
    """조성 합이 1인지 (tol 이내)."""
    return abs(composition_sum(xO, xF, xOH) - 1.0) <= tol


def distance_uv(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    """두 조성 사이의 (u,v) 평면 거리."""
    ua, va = to_uv(*a)
    ub, vb = to_uv(*b)
    return math.hypot(ua - ub, va - vb)
