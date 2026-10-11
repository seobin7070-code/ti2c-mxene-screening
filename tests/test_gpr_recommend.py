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


def test_ternary_on_quarter_grid():
    """삼원 대표 조성은 2×2 셀에서 가능한 1/4-격자 점이어야 한다 (명세 3.1·10).

    (1/3,1/3,1/3)은 2×2 셀에서 만들 수 없고 격자 밖이라, 대표 삼원은 (0.5,0.25,0.25).
    """
    from core.grid import quarter_grid
    _, comp = _load()
    c = comp["Ti2C_ternary"]
    assert (c.xO, c.xF, c.xOH) == (0.5, 0.25, 0.25)
    assert (c.xO, c.xF, c.xOH) in quarter_grid(), "삼원 좌표가 1/4-격자에 없음"


def test_app_imports_get_grid():
    """역방향 추천 페이지가 쓰는 get_grid 가 app 네임스페이스에 로드되어야 한다.

    예전엔 app.py 가 core.grid.get_grid 를 import 하지 않아, 추천 모드에서
    NameError: name 'get_grid' is not defined 로 페이지가 크래시했다.
    """
    import importlib
    app = importlib.import_module("app")
    assert hasattr(app, "get_grid"), "app.py 에 get_grid 미로드(역방향 추천 크래시)"
    assert len(app.get_grid("quarter")) == 15


# ── 요구사항 2: 통합 학습 데이터가 충분(현재 25점, 활성 threshold=3) ──
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


# ── (B) Pareto 역방향 추천 (명세 6.2) ───────────────────────────
def test_pareto_front_dominance():
    """P_cond 하한은 클수록, Δd 상한은 작을수록 좋음. 지배당하는 점은 제외."""
    cands = [
        {"composition": (1, 0, 0), "p_cond_lower": 0.20, "dd_upper": 0.5, "sigma": 0.1},
        {"composition": (0, 1, 0), "p_cond_lower": 0.10, "dd_upper": 0.9, "sigma": 0.2},  # 지배당함
        {"composition": (0, 0, 1), "p_cond_lower": 0.15, "dd_upper": 0.3, "sigma": 0.3},
    ]
    front = G.pareto_front(cands)
    comps = {c["composition"] for c in front}
    assert (1, 0, 0) in comps          # p 최고 + dd 중간 → 비지배
    assert (0, 0, 1) in comps          # dd 최저 → 비지배
    assert (0, 1, 0) not in comps      # 두 축 모두 열세 → 지배당함


def test_pareto_front_ignores_dd_when_none():
    """Δd 가 모두 None 이면 P_cond 하한만으로 비교한다."""
    cands = [
        {"composition": (1, 0, 0), "p_cond_lower": 0.20, "dd_upper": None, "sigma": 0.1},
        {"composition": (0, 1, 0), "p_cond_lower": 0.10, "dd_upper": None, "sigma": 0.2},
    ]
    front = G.pareto_front(cands)
    assert {c["composition"] for c in front} == {(1, 0, 0)}  # p 더 큰 쪽만


def test_recommend_pareto_sorts_by_sigma():
    """비지배 후보를 σ 오름차순으로 정렬해 반환한다."""
    cands = [
        {"composition": (1, 0, 0), "p_cond_lower": 0.20, "dd_upper": None, "sigma": 0.30},
        {"composition": (0, 0, 1), "p_cond_lower": 0.20, "dd_upper": None, "sigma": 0.10},
    ]
    recs = G.recommend_pareto(cands, top=5)
    # 두 점 모두 p_cond_lower 동일 → 둘 다 비지배 → σ 오름차순
    assert [r["sigma"] for r in recs] == [0.10, 0.30]


def test_recommend_pareto_empty():
    assert G.recommend_pareto([], top=5) == []


# ── (D) 다음 계산 후보 (명세 7) ─────────────────────────────────
def test_computed_grid_points_excluded():
    """computed_grid_points 는 계산된 조성 좌표 집합을 돌려주고, 격자 후보에서 제외된다."""
    entries, comp = _load()
    pts = S.computed_grid_points(entries, comp)
    assert (1.0, 0.0, 0.0) in pts and (0.5, 0.25, 0.25) in pts   # 계산된 조성
    # 미계산 격자점은 포함되지 않음
    assert (0.25, 0.0, 0.75) not in pts
