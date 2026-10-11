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


def test_ti2c_fh_confirmed_coords():
    # Ti2C_FH: H→OH 환산 가정으로 F:OH 50:50 좌표 부여 (확정)
    _, comp = _load()
    c = comp["Ti2C_FH"]
    assert c.confirmed is True
    assert (c.xO, c.xF, c.xOH) == (0.0, 0.5, 0.5)


def test_set1_surfaces_have_assigned_coords():
    _, comp = _load()
    # 세트1 전용 표면에 요구된 조성 좌표가 부여됨 (Descriptor)
    of = comp["Ti2C_OF_alt"]
    assert (of.xO, of.xF, of.xOH) == (0.5, 0.5, 0.0) and of.confirmed is True
    foh = comp["Ti2C_FOH_clu"]
    assert (foh.xO, foh.xF, foh.xOH) == (0.0, 0.5, 0.5) and foh.confirmed is True


def test_unified_gpr_active_with_threshold():
    """세트 통합(가스 차원 포함) 학습 데이터가 threshold 이상이면 통합 GPR이 활성화된다."""
    from core.gpr_model import fit_unified, UnifiedModel
    entries, comp = _load()
    st = load_settings(SETTINGS)
    pts = S.training_points_unified(entries, comp)
    assert len(pts) >= st.min_train_points, \
        f"통합 학습 데이터 {len(pts)}개 (<{st.min_train_points})"
    m = fit_unified(pts, st.min_train_points)
    assert isinstance(m, UnifiedModel)
    # 학습점 예측이 실제 계산값에 근접
    mu, _ = m.predict((0.0, 1.0, 0.0), "SET1", "CO2")
    r = S.compute_ad_for(entries, "Ti2CF2", "CO2", calc_group="SET1")
    assert abs(mu - r.E_ad_eV) < 0.02


def test_settings_defaults():
    st = load_settings(SETTINGS)
    assert st.min_train_points == 3
    assert st.preset == "condition_input"
    assert st.composition_grid == "quarter"


def test_ry_to_ev_constant():
    from core.units import RY_TO_EV
    assert RY_TO_EV == 13.605698
