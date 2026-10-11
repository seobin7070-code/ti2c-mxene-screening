"""현재 데이터 기대 동작 (명세 [7] 완료 조건).

E_ads 4건만 계산, H₂O 관련·P 지수 모두 데이터 없음, GPR 4개 모두 비활성,
계산 조성 3개(Ti2CO2, Ti2CF2, Ti2C_OF), Ti2C_FH 미확정.
"""

import os

from core.loader import load_energies
from core.composition import load_composition_map
from core import screening as S
from core.gpr_model import TARGETS, fit_target, GprUnavailable
from core.settings import load_settings

HERE = os.path.dirname(__file__)
ENERGIES = os.path.join(HERE, "..", "data", "energies.csv")
COMP = os.path.join(HERE, "..", "data", "composition_map.csv")
SETTINGS = os.path.join(HERE, "..", "config", "settings.json")


def _load():
    return load_energies(ENERGIES).entries, load_composition_map(COMP)


def test_only_four_eads_computable():
    entries, _ = _load()
    ok_pairs = []
    for s in S.surfaces(entries):
        for g in S.GASES:
            if S.compute_ad_for(entries, s, g).ok:
                ok_pairs.append((s, g))
    assert set(ok_pairs) == {("Ti2CO2", "SO2"), ("Ti2CF2", "CO2"),
                             ("Ti2C_FH", "CO2"), ("Ti2C_OF", "CO2")}


def test_h2o_and_P_all_no_data():
    entries, _ = _load()
    for s in S.surfaces(entries):
        # H2O 흡착 계산 불가
        assert S.compute_ad_for(entries, s, "H2O").ok is False
        p = S.p_indices(entries, s)
        # P(CO2/H2O)는 항상 데이터 없음
        assert p["P(CO2/H2O)"].ok is False


def test_computed_surfaces_three():
    entries, comp = _load()
    assert set(S.computed_surfaces(entries, comp)) == {"Ti2CO2", "Ti2CF2", "Ti2C_OF"}


def test_ti2c_fh_unconfirmed():
    _, comp = _load()
    c = comp["Ti2C_FH"]
    assert c.confirmed is False
    assert c.xO is None and c.xF is None and c.xOH is None


def test_planned_compositions_present():
    _, comp = _load()
    planned = [s for s, c in comp.items() if c.status == "planned" and c.surface != "Ti2C_FH"]
    # 계획 조성 4개 (OH, O:OH, F:OH, 삼원)
    assert len(planned) >= 4


def test_all_four_gpr_inactive():
    entries, comp = _load()
    st = load_settings(SETTINGS)
    for t in TARGETS:
        pts = S.training_points(entries, comp, t)
        m = fit_target(pts, t, st.min_train_points)
        assert isinstance(m, GprUnavailable), f"{t} 모델이 활성화됨(기대: 비활성)"


def test_settings_defaults():
    st = load_settings(SETTINGS)
    assert st.min_train_points == 7
    assert st.preset == "condition_input"
    assert st.composition_grid == "quarter"
    assert st.margin_m_eV == 0.10
