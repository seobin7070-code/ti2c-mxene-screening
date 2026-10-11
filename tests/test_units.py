"""core.units 단위 테스트 (요구사항 2.1, 2.3, 12.1)."""

import math

from core.units import RY_TO_EV, ry_to_ev, ev_to_ry


def test_conversion_constant_is_exact():
    # 요구사항 2.1: 정확히 1 Ry = 13.6057 eV
    assert RY_TO_EV == 13.6057


def test_ry_to_ev_known_value():
    assert math.isclose(ry_to_ev(1.0), 13.6057, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(ry_to_ev(-0.06568), -0.06568 * 13.6057, abs_tol=1e-12)


def test_roundtrip_ry_ev_ry():
    for x in (-105.27217923, -0.03848, 0.0, 1.2345):
        assert math.isclose(ev_to_ry(ry_to_ev(x)), x, rel_tol=1e-12)


def test_ev_to_ry_inverse_of_ry_to_ev():
    assert math.isclose(ev_to_ry(13.6057), 1.0, rel_tol=1e-12)
