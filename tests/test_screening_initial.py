"""현재 데이터(두 세트) 기대 동작.

세트1(대형 슈퍼셀): 복합체 9종 모두 계산(H2O 포함).
세트2(표준 단위셀): 복합체 4종 계산, H2O 없음.
전체 복합체 13종, GPR 4개 비활성, 세트별 조성 매핑.
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


def test_two_calc_groups():
    entries, _ = _load()
    assert set(S.calc_groups(entries)) == {"SET1", "SET2"}


def test_all_adsorption_rows_13_complexes():
    entries, _ = _load()
    rows = S.all_adsorption_rows(entries)
    assert len(rows) == 13          # 세트1 9종 + 세트2 4종
    assert all(r["ok"] for r in rows)
    # 세트별 개수
    assert sum(1 for r in rows if r["calc_group"] == "SET1") == 9
    assert sum(1 for r in rows if r["calc_group"] == "SET2") == 4


def test_set1_has_h2o_set2_does_not():
    entries, _ = _load()
    # 세트1: H2O 흡착 계산 가능
    assert S.compute_ad_for(entries, "Ti2CF2", "H2O", calc_group="SET1").ok
    # 세트2: H2O 단독 분자가 없어 계산 불가
    assert S.compute_ad_for(entries, "Ti2CF2", "H2O", calc_group="SET2").ok is False


def test_set2_P_h2o_no_data():
    entries, _ = _load()
    # 세트2에는 H2O 가 없으므로 P(CO2/H2O) 데이터 없음
    e_h2o = S.compute_ad_for(entries, "Ti2CF2", "H2O", calc_group="SET2")
    e_co2 = S.compute_ad_for(entries, "Ti2CF2", "CO2", calc_group="SET2")
    from core.selectivity import selectivity_P
    p = selectivity_P("P(CO2/H2O)", e_h2o, e_co2, "H2O")
    assert p.ok is False


def test_ti2c_fh_unconfirmed():
    _, comp = _load()
    c = comp["Ti2C_FH"]
    assert c.confirmed is False
    assert c.xO is None


def test_set1_surfaces_unconfirmed_composition():
    _, comp = _load()
    # 세트1 전용 표면은 좌표 미확정(임의로 지어내지 않음)
    for s in ["Ti2C_OF_alt", "Ti2C_FOH_clu"]:
        assert comp[s].xO is None
        assert comp[s].confirmed is False


def test_all_four_gpr_inactive():
    entries, comp = _load()
    st = load_settings(SETTINGS)
    for t in TARGETS:
        m = fit_target(S.training_points(entries, comp, t), t, st.min_train_points)
        assert isinstance(m, GprUnavailable), f"{t} 활성화됨(기대: 비활성)"


def test_settings_defaults():
    st = load_settings(SETTINGS)
    assert st.min_train_points == 7
    assert st.preset == "condition_input"
    assert st.composition_grid == "quarter"


def test_ry_to_ev_constant():
    from core.units import RY_TO_EV
    assert RY_TO_EV == 13.605698
