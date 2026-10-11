"""통합 검증: 초기 데이터(calc_group=A)의 기대 동작 (요구사항 12.4, 13.2, 13.3).

- core가 Streamlit 임포트 없이 실행됨을 보장한다 (이 파일은 streamlit을 import하지 않음).
- 사용자가 제시한 흡착 에너지 기대값과 일치하는지 확인한다.
- H2O 관련 항목과 모든 P 지수는 pending이어야 한다.
- 지표별 GPR 모델은 모두 7개 미만 → 비활성이어야 한다.
"""

import math
import os
import sys

from core.loader import load_energies
from core.composition import load_composition_map
from core.registry import (
    compute_ad_for, count_trainable_for_metric, find_molecule,
)
from core.metrics import selectivity_P, delta_d, load_geometry
from core.gpr import fit_metric_model, GprUnavailable

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data")

EXPECTED = {
    ("Ti2CO2", "SO2"): (-0.06568, -0.894),
    ("Ti2CF2", "CO2"): (-0.03848, -0.524),
    ("Ti2C_FH", "CO2"): (-0.02948, -0.401),
    ("Ti2C_OF", "CO2"): (-0.04614, -0.628),
}


def load():
    entries = load_energies(os.path.join(DATA, "energies.csv")).entries
    comp = load_composition_map(os.path.join(DATA, "composition_map.csv"))
    return entries, comp


def test_core_has_no_streamlit_dependency():
    # 깨끗한 서브프로세스에서 core.* 전체를 임포트해도 streamlit이 로드되지 않아야 한다.
    import subprocess
    project_root = os.path.abspath(os.path.join(HERE, ".."))
    code = (
        "import sys;"
        "import core.units, core.loader, core.energetics, core.metrics,"
        " core.composition, core.registry, core.gpr, core.quality;"
        "assert 'streamlit' not in sys.modules, 'core가 streamlit에 의존함';"
        "print('core-only OK')"
    )
    res = subprocess.run(
        [sys.executable, "-c", code],
        cwd=project_root, capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stderr
    assert "core-only OK" in res.stdout


def test_expected_adsorption_energies():
    entries, _ = load()
    for (surf, gas), (exp_ry, exp_ev) in EXPECTED.items():
        r = compute_ad_for(entries, surf, gas)
        assert r.ok is True, f"{gas}@{surf} 계산 실패: {r.reason}"
        assert math.isclose(r.E_ad_Ry, exp_ry, abs_tol=1e-4), \
            f"{gas}@{surf} Ry: {r.E_ad_Ry} != {exp_ry}"
        assert math.isclose(r.E_ad_eV, exp_ev, abs_tol=2e-3), \
            f"{gas}@{surf} eV: {r.E_ad_eV} != {exp_ev}"
        assert r.suspect is False


def test_h2o_items_pending():
    entries, _ = load()
    # H2O 단독 분자 없음
    assert find_molecule(entries, "H2O") is None
    # H2O 흡착 pending
    r = compute_ad_for(entries, "Ti2CO2", "H2O")
    assert r.ok is False


def test_all_P_indices_pending():
    entries, _ = load()
    for surf in ["Ti2CO2", "Ti2CF2", "Ti2C_FH", "Ti2C_OF"]:
        e_co2 = compute_ad_for(entries, surf, "CO2")
        e_h2o = compute_ad_for(entries, surf, "H2O")
        e_so2 = compute_ad_for(entries, surf, "SO2")
        # P(CO2/H2O)는 H2O 없음 → 반드시 pending
        p_h2o = selectivity_P("P(CO2/H2O)", e_h2o, e_co2, "H2O")
        assert p_h2o.ok is False, f"{surf}: P(CO2/H2O)가 pending이 아님"
        # P(CO2/SO2)도 표면별로 둘 다 계산되는 경우가 없어 pending
        p_so2 = selectivity_P("P(CO2/SO2)", e_so2, e_co2, "SO2")
        assert p_so2.ok is False, f"{surf}: P(CO2/SO2)가 pending이 아님"


def test_delta_d_pending():
    geom = load_geometry(os.path.join(DATA, "geometry.csv"))
    assert geom == {}  # geometry 값 없음
    r = delta_d(geom.get(("Ti2CO2", "SO2")))
    assert r.ok is False


def test_tab_b_models_all_inactive():
    entries, comp = load()
    for metric in ["P(CO2/H2O)", "P(CO2/SO2)"]:
        n = count_trainable_for_metric(entries, comp, metric)
        assert n < 7
        model = fit_metric_model(
            __import__("core.registry", fromlist=["trainable_points_for_metric"])
            .trainable_points_for_metric(entries, comp, metric),
            metric,
        )
        assert isinstance(model, GprUnavailable)
