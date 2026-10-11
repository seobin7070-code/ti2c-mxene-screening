"""core.quality LOOCV 테스트 (요구사항 9).

합성 데이터로 LOOCV 로직만 검증한다 (실제 에너지 아님).
"""

from core.quality import loocv, QualityResult
from core.gpr import MIN_TRAINING


def make_points(n):
    pts = []
    for i in range(n):
        a = (i + 1) / (n + 2)
        b = (1 - a) * 0.5
        c = 1 - a - b
        pts.append(([a, b, c], float(2.0 * a - b)))
    return pts


def test_loocv_insufficient_data_returns_reason():
    r = loocv(make_points(MIN_TRAINING - 1), "P(CO2/SO2)")
    assert r.ok is False
    assert r.mae is None and r.rmse is None and r.r2 is None
    assert "데이터 부족" in r.reason
    # parity plot용 예측/실측은 ok 전에는 비어 있어야 함
    assert r.y_true is None and r.y_pred is None


def test_loocv_computes_metrics_when_enough():
    r = loocv(make_points(10), "P(CO2/SO2)")
    assert r.ok is True
    assert r.n == 10
    assert r.mae is not None and r.mae >= 0
    assert r.rmse is not None and r.rmse >= r.mae  # RMSE >= MAE 항상 성립
    assert r.r2 is not None  # 실제 계산된 값


def test_loocv_exposes_true_and_pred_for_parity_plot():
    r = loocv(make_points(10), "P(CO2/SO2)")
    assert r.ok is True
    # parity plot용 LOOCV 예측-실측이 노출되어야 함
    assert r.y_true is not None and r.y_pred is not None
    assert len(r.y_true) == r.n and len(r.y_pred) == r.n
    assert all(isinstance(v, float) for v in r.y_true)
    assert all(isinstance(v, float) for v in r.y_pred)
