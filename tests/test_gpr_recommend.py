"""GPR 통합 모델·역방향 추천·조성 좌표 부여 테스트 (요구사항 1~3)."""

import os

from core.loader import load_energies
from core.composition import load_composition_map
from core import screening as S
from core import gpr_model as G
from core.grid import quarter_grid
from core.settings import load_settings

HERE = os.path.dirname(__file__)
ENERGIES = os.path.join(HERE, "..", "data", "energies.csv")
COMP = os.path.join(HERE, "..", "data", "composition_map.csv")
SETTINGS = os.path.join(HERE, "..", "config", "settings.json")


def _load():
    return load_energies(ENERGIES).entries, load_composition_map(COMP)


# ── 요구사항 1: 조성 좌표(Descriptor) 부여 ──────────────────────
def test_descriptor_coordinates():
    _, comp = _load()
    # [F, O, OH] → 플랫폼 (xO, xF, xOH)
    expect = {
        "Ti2CF2": (0.0, 1.0, 0.0),
        "Ti2CO2": (1.0, 0.0, 0.0),
        "Ti2C_OF_alt": (0.5, 0.5, 0.0),
        "Ti2C_FOH_clu": (0.0, 0.5, 0.5),
    }
    for s, (xo, xf, xoh) in expect.items():
        c = comp[s]
        assert (c.xO, c.xF, c.xOH) == (xo, xf, xoh), f"{s} 좌표 불일치"
        assert c.confirmed is True


# ── 요구사항 2: 통합 학습 데이터가 충분(현재 13점, 활성 threshold=3) ──
def test_unified_training_enough():
    entries, comp = _load()
    pts = S.training_points_unified(entries, comp)
    assert len(pts) >= 7
    # SET1·SET2 모두 포함(통합)
    cgs = {p[1] for p in pts}
    assert "SET1" in cgs and "SET2" in cgs


def test_unified_model_active_and_accurate():
    entries, comp = _load()
    st = load_settings(SETTINGS)
    m = G.fit_unified(S.training_points_unified(entries, comp), st.min_train_points)
    assert isinstance(m, G.UnifiedModel)
    # 세 학습점 예측이 실제값에 근접(세트 내 계산값과 비교)
    for g in ["CO2", "H2O", "SO2"]:
        mu, _ = m.predict((0.0, 1.0, 0.0), "SET1", g)
        r = S.compute_ad_for(entries, "Ti2CF2", g, calc_group="SET1")
        assert abs(mu - r.E_ad_eV) < 0.03, f"{g} 예측 오차 큼"


def test_sets_not_mixed_in_prediction():
    """같은 조성이라도 세트 기준에 따라 예측 스케일이 다르다(세트 혼합 없음)."""
    entries, comp = _load()
    st = load_settings(SETTINGS)
    m = G.fit_unified(S.training_points_unified(entries, comp), st.min_train_points)
    co2_set1, _ = m.predict((0.0, 1.0, 0.0), "SET1", "CO2")   # ≈ -0.015
    co2_set2, _ = m.predict((0.0, 1.0, 0.0), "SET2", "CO2")   # ≈ -0.523
    assert abs(co2_set1 - co2_set2) > 0.1


# ── 요구사항 3: 역방향 추천 ─────────────────────────────────────
def test_recommend_returns_sorted_candidates():
    entries, comp = _load()
    st = load_settings(SETTINGS)
    m = G.fit_unified(S.training_points_unified(entries, comp), st.min_train_points)
    recs = G.recommend_unified(m, quarter_grid(), "SET1",
                               {"CO2": -0.02, "SO2": -0.07}, top=5)
    assert len(recs) == 5
    scores = [r["score"] for r in recs]
    assert scores == sorted(scores)           # 거리 오름차순
    # 각 후보에 예측 포함
    assert "CO2" in recs[0]["predictions"] and "SO2" in recs[0]["predictions"]


def test_recommend_empty_without_targets():
    entries, comp = _load()
    st = load_settings(SETTINGS)
    m = G.fit_unified(S.training_points_unified(entries, comp), st.min_train_points)
    assert G.recommend_unified(m, quarter_grid(), "SET1", {}, top=5) == []


# ── 조성 지도 마커: 두 세트 확정 표면 ──────────────────────────
def test_map_markers_both_sets():
    entries, comp = _load()
    mks = S.confirmed_surface_markers(entries, comp)
    cgs = {m["calc_group"] for m in mks}
    assert "SET1" in cgs and "SET2" in cgs
    # SET1 확정 표면 3개(Ti2CF2, Ti2C_OF_alt, Ti2C_FOH_clu)
    set1 = {m["surface"] for m in mks if m["calc_group"] == "SET1"}
    assert {"Ti2CF2", "Ti2C_OF_alt", "Ti2C_FOH_clu"} <= set1
