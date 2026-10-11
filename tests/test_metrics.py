"""core.metrics 단위 테스트 (요구사항 5)."""

import math

from core.energetics import AdResult
from core.metrics import selectivity_P, delta_d, GeometryRow


def ad(e_ad_ry, ok=True, cg="A"):
    return AdResult(
        ok=ok, E_ad_eV=e_ad_ry * 13.6057 if ok else None,
        E_ad_Ry=e_ad_ry if ok else None,
        components={}, calc_group=cg if ok else None,
        suspect=False, reason=None if ok else "거부",
    )


def test_P_computed_when_both_present():
    r = selectivity_P("P(CO2/SO2)", ad(-0.06568), ad(-0.03848), "SO2")
    assert r.ok is True
    assert math.isclose(r.value_Ry, -0.06568 - (-0.03848), abs_tol=1e-9)
    assert r.calc_group == "A"


def test_P_pending_when_target_missing():
    # H2O 흡착 데이터 없음 → pending (초기 데이터의 기대 동작)
    r = selectivity_P("P(CO2/H2O)", None, ad(-0.03848), "H2O")
    assert r.ok is False
    assert "H2O" in r.reason
    assert r.value_eV is None


def test_P_pending_when_co2_missing():
    r = selectivity_P("P(CO2/SO2)", ad(-0.06568), None, "SO2")
    assert r.ok is False
    assert "CO2" in r.reason


def test_P_pending_on_calc_group_mismatch():
    r = selectivity_P("P(CO2/SO2)", ad(-0.06568, cg="A"), ad(-0.03848, cg="B"), "SO2")
    assert r.ok is False
    assert "calc_group" in r.reason


def test_delta_d_pending_without_geometry():
    r = delta_d(None)
    assert r.ok is False
    assert "geometry" in r.reason.lower()
    assert r.value is None


def test_delta_d_computed_with_geometry():
    g = GeometryRow("Ti2CO2", "SO2", z_before=2.10, z_after=2.37,
                    source_file="geom.out", calc_group="A")
    r = delta_d(g)
    assert r.ok is True
    assert math.isclose(r.value, 0.27, abs_tol=1e-9)
    assert r.calc_group == "A"
