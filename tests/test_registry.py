"""core.registry / core.composition 단위 테스트 (요구사항 6.4, 6.5, 8.6, 8.8, 10)."""

import os

from core.loader import load_energies
from core.composition import load_composition_map, is_trainable, Composition
from core.registry import (
    missing_checklist, count_trainable_for_metric,
    find_molecule, compute_ad_for, ALL_METRICS,
    trainable_points_for_metric,
)
from core.metrics import GeometryRow

HERE = os.path.dirname(__file__)
ENERGIES = os.path.join(HERE, "..", "data", "energies.csv")
COMP = os.path.join(HERE, "..", "data", "composition_map.csv")


def load():
    entries = load_energies(ENERGIES).entries
    comp = load_composition_map(COMP)
    return entries, comp


# ---- composition ----------------------------------------------------------

def test_is_trainable_confirmed_full():
    c = Composition("Ti2CO2", 1.0, 0.0, 0.0, True)
    assert is_trainable(c) is True


def test_is_trainable_unconfirmed_excluded():
    # Ti2C_FH: 미확정 + 공란 → 학습 제외 (요구사항 10.2, 10.3)
    _, comp = load()
    assert is_trainable(comp["Ti2C_FH"]) is False


def test_composition_map_initial_values():
    _, comp = load()
    assert comp["Ti2CO2"].xO == 1.0 and comp["Ti2CO2"].xF == 0.0
    assert comp["Ti2C_OF"].xO == 0.5 and comp["Ti2C_OF"].xF == 0.5
    assert comp["Ti2C_FH"].confirmed is False


# ---- 누락 체크리스트 (요구사항 6.4) ----------------------------------------

def test_h2o_molecule_flagged_missing_globally():
    entries, _ = load()
    items = missing_checklist(entries)
    globals_ = [i for i in items if i.scope == "전역"]
    assert any("H2O 단독 분자" in i.detail for i in globals_)
    # CO2, SO2 단독은 있으므로 전역 누락에 없어야 함
    assert not any("CO2 단독 분자" in i.detail for i in globals_)
    assert not any("SO2 단독 분자" in i.detail for i in globals_)


def test_missing_adsorbed_combos_flagged():
    entries, _ = load()
    items = missing_checklist(entries)
    # 예: SO2 복합체는 Ti2CO2에만 존재 → Ti2CF2+SO2 복합체 누락이 잡혀야 함
    assert any("Ti2CF2 + 가스 SO2" in i.scope for i in items)


# ---- 지표별 학습 가능 수 (요구사항 8.6) ------------------------------------

def test_all_three_metric_counts_are_zero_on_initial_data():
    """현재 데이터에서 세 지표(P 2종 + Δd) 유효 학습 데이터가 모두 0이어야 한다.

    - P(CO2/H2O): H2O 단독 없음 → 모든 표면 pending → 0
    - P(CO2/SO2): SO2 흡착은 Ti2CO2에만, CO2 흡착은 그 표면에 없음 → 교집합 0
    - Δd: geometry 데이터 없음(또는 미전달) → 0
    """
    entries, comp = load()
    assert count_trainable_for_metric(entries, comp, "P(CO2/H2O)") == 0
    assert count_trainable_for_metric(entries, comp, "P(CO2/SO2)") == 0
    # Δd: geom_map 미전달 → 0
    assert count_trainable_for_metric(entries, comp, "Δd") == 0
    # geom_map을 빈 dict로 줘도 0
    assert count_trainable_for_metric(entries, comp, "Δd", {}) == 0
    # 세 지표 전부 7 미만
    for m in ALL_METRICS:
        assert count_trainable_for_metric(entries, comp, m) < 7


def test_delta_d_counts_only_surfaces_with_geometry():
    """Δd는 geometry가 있고 Δd가 계산된(조성 확정) 표면만 센다."""
    entries, comp = load()
    # Ti2CO2는 조성 확정(1,0,0). 이 표면에 SO2 geometry 를 주면 Δd 1개가 되어야 함.
    geom = {("Ti2CO2", "SO2"): GeometryRow(
        "Ti2CO2", "SO2", z_before=2.10, z_after=2.37,
        source_file="geom.out", calc_group="G")}
    assert count_trainable_for_metric(entries, comp, "Δd", geom) == 1
    pts = trainable_points_for_metric(entries, comp, "Δd", geom)
    assert pts[0][0] == [1.0, 0.0, 0.0]  # 조성 벡터
    assert abs(pts[0][1] - 0.27) < 1e-9  # Δd 값

    # 조성 미확정 표면(Ti2C_FH)에 geometry 를 줘도 세지 않는다.
    geom2 = {("Ti2C_FH", "SO2"): GeometryRow(
        "Ti2C_FH", "SO2", 2.0, 2.3, "g.out", "G")}
    assert count_trainable_for_metric(entries, comp, "Δd", geom2) == 0


def test_initial_adsorption_energies_computable():
    entries, _ = load()
    # 초기 데이터로 네 흡착 에너지가 계산 가능해야 함
    for surf, gas in [("Ti2CO2", "SO2"), ("Ti2CF2", "CO2"),
                      ("Ti2C_FH", "CO2"), ("Ti2C_OF", "CO2")]:
        r = compute_ad_for(entries, surf, gas)
        assert r.ok is True, f"{gas}@{surf} 계산 실패: {r.reason}"


def test_h2o_adsorption_pending():
    entries, _ = load()
    # H2O 단독/복합체 없음 → H2O 흡착 pending
    r = compute_ad_for(entries, "Ti2CO2", "H2O")
    assert r.ok is False
    assert find_molecule(entries, "H2O") is None
