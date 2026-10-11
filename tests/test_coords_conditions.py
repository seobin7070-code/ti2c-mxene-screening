"""좌표 변환(요구 7-(8))과 δ 보정 기준값(요구 7-(5)) 테스트."""

import math

from core.coords import to_uv, to_triangle_xy, is_normalized, distance_uv
from core.conditions import delta, ppm_to_molpct, t_delta_s_eV


# ── 좌표 변환 ───────────────────────────────────────────────────
def test_uv_vertices_distance_sqrt2():
    # 세 꼭짓점 사이 거리가 모두 √2
    O, F, OH = (1, 0, 0), (0, 1, 0), (0, 0, 1)
    assert math.isclose(distance_uv(O, F), math.sqrt(2), abs_tol=1e-9)
    assert math.isclose(distance_uv(F, OH), math.sqrt(2), abs_tol=1e-9)
    assert math.isclose(distance_uv(O, OH), math.sqrt(2), abs_tol=1e-9)


def test_uv_known_values():
    # OF 50:50 → u = (0.5-0)/√2, v = (2*0-0.5-0)/√6
    u, v = to_uv(0, 0.5, 0.5)
    assert math.isclose(u, (0.5 - 0.5) / math.sqrt(2), abs_tol=1e-9)
    assert math.isclose(v, (0 - 0.5 - 0.5) / math.sqrt(6), abs_tol=1e-9)


def test_triangle_xy_vertices():
    assert to_triangle_xy(1, 0, 0) == (0.0, 0.0)          # O 꼭짓점
    assert to_triangle_xy(0, 1, 0) == (1.0, 0.0)          # F 꼭짓점
    x, y = to_triangle_xy(0, 0, 1)                        # OH 꼭짓점
    assert math.isclose(x, 0.5) and math.isclose(y, math.sqrt(3) / 2)


def test_triangle_xy_formula():
    # x = xF + 0.5·xOH, y = (√3/2)·xOH
    x, y = to_triangle_xy(0.5, 0.25, 0.25)
    assert math.isclose(x, 0.25 + 0.5 * 0.25)
    assert math.isclose(y, (math.sqrt(3) / 2) * 0.25)


def test_is_normalized():
    assert is_normalized(0.5, 0.25, 0.25)
    assert not is_normalized(0.5, 0.2, 0.2)   # 합 0.9


# ── δ 보정 (요구 7-(5)) ─────────────────────────────────────────
def test_t_delta_s_known():
    assert math.isclose(t_delta_s_eV("H2O"), -0.077, abs_tol=1e-3)
    assert math.isclose(t_delta_s_eV("SO2"), 0.106, abs_tol=1e-3)


def test_delta_reference_values():
    # CO₂ 12 mol%, H₂O 10 mol%, SO₂ 500 ppm → δ_H2O=−0.073, δ_SO2=+0.247
    p_co2, p_h2o = 12.0, 10.0
    p_so2 = ppm_to_molpct(500)   # 0.05 mol%
    dh = delta("H2O", p_h2o, p_co2)
    ds = delta("SO2", p_so2, p_co2)
    assert dh.ok and ds.ok
    assert math.isclose(dh.delta_eV, -0.073, abs_tol=1e-3)
    assert math.isclose(ds.delta_eV, +0.247, abs_tol=1e-3)


def test_delta_zero_fraction_refused():
    r = delta("H2O", 0.0, 12.0)
    assert r.ok is False and "0보다" in r.reason
