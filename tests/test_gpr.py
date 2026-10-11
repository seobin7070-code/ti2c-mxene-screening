"""core.gpr 단위 테스트 (요구사항 8).

주의: 여기서 쓰는 숫자는 '에너지'가 아니라 GPR 로직(임계값/Pareto/AL) 검증용
합성 조성/지표값이다. 실제 에너지는 energetics/metrics 경로로만 흐른다.
"""

import numpy as np

from core.gpr import (
    fit_metric_model, GprUnavailable, GprModel,
    scan_ternary, next_al_candidate, pareto_front, ScanResult,
    MIN_TRAINING, SIGMA_DISCLAIMER,
)


def make_points(n):
    # 삼각 공간 내 임의 조성과 지표값
    pts = []
    for i in range(n):
        a = (i + 1) / (n + 2)
        b = (1 - a) * 0.5
        c = 1 - a - b
        pts.append(([a, b, c], float(a - b)))
    return pts


def test_below_threshold_returns_unavailable():
    model = fit_metric_model(make_points(MIN_TRAINING - 1), "P(CO2/SO2)")
    assert isinstance(model, GprUnavailable)
    assert model.n == MIN_TRAINING - 1
    assert model.need == MIN_TRAINING
    assert "데이터 부족" in model.message


def test_zero_points_unavailable():
    model = fit_metric_model([], "P(CO2/H2O)")
    assert isinstance(model, GprUnavailable)
    assert model.n == 0


def test_at_threshold_fits_model():
    model = fit_metric_model(make_points(MIN_TRAINING), "P(CO2/SO2)")
    assert isinstance(model, GprModel)
    assert model.n == MIN_TRAINING


def test_scan_and_al_candidate():
    model = fit_metric_model(make_points(8), "P(CO2/SO2)")
    scan = scan_ternary(model, step=10)
    assert scan.mu.shape == scan.sigma.shape
    assert scan.sigma_disclaimer == SIGMA_DISCLAIMER
    cand = next_al_candidate(scan)
    # σ 최대 지점이 선택되었는지
    assert np.isclose(cand["sigma"], float(np.max(scan.sigma)))
    assert len(cand["composition"]) == 3


def test_pareto_front_direction():
    # 2개 지표: P(최대화), Δd(최소화)
    grid = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
    s_p = ScanResult("P(CO2/SO2)", grid, mu=np.array([3.0, 1.0, 2.0]), sigma=np.zeros(3))
    s_d = ScanResult("Δd", grid, mu=np.array([0.1, 0.5, 0.2]), sigma=np.zeros(3))
    front = pareto_front({"P(CO2/SO2)": s_p, "Δd": s_d})
    comps = [tuple(f["composition"]) for f in front]
    # 점0: P=3(최대), Δd=0.1(최소) → 명백히 비지배, 반드시 포함
    assert (1.0, 0.0, 0.0) in comps
    # 점1: P=1, Δd=0.5 → 점0과 점2에 지배됨 → 제외
    assert (0.0, 1.0, 0.0) not in comps


def test_pareto_empty_when_no_scans():
    assert pareto_front({}) == []
