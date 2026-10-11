"""모델 품질: LOOCV(MAE/RMSE/R²).

성능 수치는 LOOCV로 '실제 계산된' 값만 반환한다. 추정·임의값은 쓰지 않는다 (요구사항 9.3, DI-2).
데이터가 부족하면 수치 대신 사유를 반환한다 (요구사항 9.4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from core.gpr import _make_gp, MIN_TRAINING


@dataclass
class QualityResult:
    ok: bool
    metric: str
    n: int
    mae: Optional[float]
    rmse: Optional[float]
    r2: Optional[float]
    reason: Optional[str]
    # LOOCV 예측-실측 (ok일 때만 채워짐; parity plot용)
    y_true: Optional[list] = None
    y_pred: Optional[list] = None


def loocv(points: list[tuple[list[float], float]], metric: str) -> QualityResult:
    """Leave-One-Out 교차검증으로 MAE/RMSE/R²를 계산한다 (요구사항 9.1~9.3).

    LOOCV와 지표 모델 모두 유효 데이터가 필요하므로, GPR과 동일하게
    MIN_TRAINING 미만이면 수치 대신 사유를 반환한다 (요구사항 9.4).
    """
    n = len(points)
    if n < MIN_TRAINING:
        return QualityResult(
            ok=False, metric=metric, n=n,
            mae=None, rmse=None, r2=None,
            reason=f"데이터 부족: 현재 {n}개 / 필요 {MIN_TRAINING}개",
        )

    X = np.array([p[0] for p in points], dtype=float)
    y = np.array([p[1] for p in points], dtype=float)

    loo = LeaveOneOut()
    y_true, y_pred = [], []
    for train_idx, test_idx in loo.split(X):
        gp = _make_gp()
        gp.fit(X[train_idx], y[train_idx])
        pred = gp.predict(X[test_idx])
        y_true.append(y[test_idx][0])
        y_pred.append(pred[0])

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))
    return QualityResult(
        ok=True, metric=metric, n=n, mae=mae, rmse=rmse, r2=r2, reason=None,
        y_true=[float(v) for v in y_true], y_pred=[float(v) for v in y_pred],
    )
