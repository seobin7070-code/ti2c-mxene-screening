"""분류 규칙(요구 7-(6))과 격자(1/4 단위 15점), GPR 비활성(요구 7-(7)) 테스트.

분류 테스트의 합성 입력은 테스트 코드 안에서만 쓰며 data/ 에 넣지 않는다.
"""

from core.classify import (classify, ClassifyInput, UNMET, PRIORITY, MORE_CALC)
from core.grid import quarter_grid, get_grid
from core.gpr_model import fit_target, GprUnavailable, GprModel


KAPPA = 1.0
M = 0.10


def _cls(**kw):
    inp = ClassifyInput(**kw)
    return classify(inp, kappa=KAPPA, margin_m=M,
                    delta_d_max=None, sigma_max=None, preset="condition_input")


# ── 분류 분기 (condition_input) ─────────────────────────────────
def test_priority_branch():
    # P_cond 하한 > +m 이고 Eads(CO2) 상한 < 0 → 우선 검토
    r = _cls(mu_p_cond=0.3, sigma_p=0.0, mu_eads_co2=-0.5, sigma_eads_co2=0.0)
    assert r.label == PRIORITY


def test_unmet_by_low_p():
    # P_cond 상한 < −m → 현재 기준 미충족
    r = _cls(mu_p_cond=-0.3, sigma_p=0.0, mu_eads_co2=-0.5)
    assert r.label == UNMET


def test_unmet_by_positive_eads():
    # 낙관적 Eads(CO2)(μ−κσ)도 양수 → 미충족
    r = _cls(mu_p_cond=0.3, sigma_p=0.0, mu_eads_co2=0.2, sigma_eads_co2=0.0)
    assert r.label == UNMET
    assert any("양수" in x for x in r.reasons)


def test_unmet_by_reaction_flag():
    r = _cls(mu_p_cond=0.3, sigma_p=0.0, mu_eads_co2=-0.5,
             reaction_flag="SO2_dissociated")
    assert r.label == UNMET
    assert any("구조 변화" in x for x in r.reasons)


def test_more_calc_middle():
    # 기준선 사이 (−m ≤ P_cond ≤ +m) → 추가 계산 권장
    r = _cls(mu_p_cond=0.0, sigma_p=0.0, mu_eads_co2=-0.5)
    assert r.label == MORE_CALC


def test_more_calc_when_no_P_data():
    # P 계산 불가 → 추가 계산 권장 + 필요한 계산 목록
    r = _cls(mu_p_cond=None, missing=["H₂O 복합체 계산 필요"])
    assert r.label == MORE_CALC
    assert "H₂O 복합체 계산 필요" in r.needed


def test_wide_range_preset():
    inp = ClassifyInput(mu_p_cond=0.3, sigma_p=0.0)
    r = classify(inp, kappa=1.0, margin_m=0.10, delta_d_max=None, sigma_max=None,
                 preset="wide_range", wide_range={"reject_below_eV": -0.1,
                                                  "prefer_above_eV": 0.25})
    assert r.label == PRIORITY
    inp2 = ClassifyInput(mu_p_cond=-0.2, sigma_p=0.0)
    r2 = classify(inp2, kappa=1.0, margin_m=0.10, delta_d_max=None, sigma_max=None,
                  preset="wide_range", wide_range={"reject_below_eV": -0.1,
                                                   "prefer_above_eV": 0.25})
    assert r2.label == UNMET


def test_sigma_max_blocks_priority():
    # σ(P) > σ_max 면 우선 검토 불가 → 추가 계산 권장
    inp = ClassifyInput(mu_p_cond=0.3, sigma_p=0.2, mu_eads_co2=-0.5)
    r = classify(inp, kappa=1.0, margin_m=0.10, delta_d_max=None, sigma_max=0.1,
                 preset="condition_input")
    assert r.label == MORE_CALC


# ── 격자 ────────────────────────────────────────────────────────
def test_quarter_grid_15_points():
    g = quarter_grid()
    assert len(g) == 15
    for xo, xf, xoh in g:
        assert abs(xo + xf + xoh - 1.0) < 1e-9
        # 모두 1/4 단위
        for v in (xo, xf, xoh):
            assert abs((v * 4) - round(v * 4)) < 1e-9
    # 순수 세 조성 포함
    assert (1.0, 0.0, 0.0) in g and (0.0, 1.0, 0.0) in g and (0.0, 0.0, 1.0) in g


# ── GPR 비활성 (요구 7-(7)) ─────────────────────────────────────
def test_gpr_inactive_below_min_train():
    # 3점만 → min_train_points=7 미만 → 비활성
    pts = [((1, 0, 0), -0.5), ((0, 1, 0), -0.5), ((0.5, 0.5, 0), -0.6)]
    m = fit_target(pts, "Eads_CO2", min_train_points=7)
    assert isinstance(m, GprUnavailable)
    assert m.n == 3 and m.need == 7
    assert "3/7" in m.message


def test_gpr_active_when_enough():
    pts = [((i / 10, 1 - i / 10, 0), -0.5 - i * 0.01) for i in range(8)]
    m = fit_target(pts, "Eads_CO2", min_train_points=7)
    assert isinstance(m, GprModel)
    assert m.n == 8
