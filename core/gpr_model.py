"""타깃별 독립 GPR (PDF 7장).

- 입력 좌표: (u, v) = coords.to_uv(xO, xF, xOH)
- 타깃 4개: Eads(CO₂), Eads(H₂O), Eads(SO₂), Δd — 각각 별도 GPR
- 커널: 등방성 RBF + 작은 노이즈, normalize_y
- 학습 데이터: '조성 확정 + 해당 타깃 계산값 존재' 표면만
- 타깃별 학습 데이터가 min_train_points 미만이면 그 타깃 GPR 비활성
- P 는 두 Eads 예측의 차이, σ(P) ≈ √(σ(CO₂)²+σ(H₂O)²) (근사)
- LOOCV MAE/RMSE (타깃별)
- 다음 계산 후보: 격자 중 미계산 점에서 score=Σ σ_k/s_k 최대
σ 는 참고용 상대 지표.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import LeaveOneOut

from core.coords import to_uv

TARGETS = ["Eads_CO2", "Eads_H2O", "Eads_SO2", "Delta_d"]
SIGMA_NOTE = "σ는 참고용 상대 지표입니다(엄밀한 신뢰구간 아님)."


@dataclass
class GprUnavailable:
    target: str
    n: int
    need: int

    @property
    def message(self) -> str:
        return f"학습 데이터 {self.n}/{self.need}"


@dataclass
class GprModel:
    target: str
    gp: GaussianProcessRegressor
    n: int
    y_std: float

    def predict(self, uv: np.ndarray):
        mu, sigma = self.gp.predict(uv, return_std=True)
        return mu, sigma


def _make_gp() -> GaussianProcessRegressor:
    kernel = RBF(length_scale=1.0, length_scale_bounds=(0.3, 3.0)) \
        + WhiteKernel(noise_level=1e-3, noise_level_bounds=(1e-4, 1e-1))
    return GaussianProcessRegressor(kernel=kernel, normalize_y=True,
                                    n_restarts_optimizer=2, random_state=0)


def fit_target(points: list[tuple[tuple[float, float, float], float]],
               target: str, min_train_points: int) -> "GprModel | GprUnavailable":
    """points: [((xO,xF,xOH), y)]. min_train_points 미만이면 비활성."""
    n = len(points)
    if n < min_train_points:
        return GprUnavailable(target, n, min_train_points)
    X = np.array([to_uv(*p[0]) for p in points], dtype=float)
    y = np.array([p[1] for p in points], dtype=float)
    gp = _make_gp()
    gp.fit(X, y)
    return GprModel(target, gp, n, float(np.std(y)) or 1.0)


@dataclass
class LoocvResult:
    ok: bool
    target: str
    n: int
    mae: Optional[float]
    rmse: Optional[float]
    reason: Optional[str]


def loocv(points: list[tuple[tuple[float, float, float], float]],
          target: str, min_train_points: int) -> LoocvResult:
    n = len(points)
    if n < min_train_points:
        return LoocvResult(False, target, n, None, None,
                           f"데이터 부족 {n}/{min_train_points}")
    X = np.array([to_uv(*p[0]) for p in points], dtype=float)
    y = np.array([p[1] for p in points], dtype=float)
    yt, yp = [], []
    for tr, te in LeaveOneOut().split(X):
        gp = _make_gp()
        gp.fit(X[tr], y[tr])
        yt.append(y[te][0])
        yp.append(gp.predict(X[te])[0])
    yt, yp = np.array(yt), np.array(yp)
    return LoocvResult(True, target, n,
                       float(mean_absolute_error(yt, yp)),
                       float(np.sqrt(mean_squared_error(yt, yp))), None)


def sigma_P(sigma_co2: float, sigma_other: float) -> float:
    """σ(P) ≈ √(σ(CO₂)² + σ(other)²) (독립 가정 근사)."""
    return float(np.hypot(sigma_co2, sigma_other))


def next_candidates(models: dict, grid: list[tuple[float, float, float]],
                    computed: set, top: int = 3) -> list[dict]:
    """격자 중 미계산 점에서 score=Σ σ_k/s_k 최대 상위 top 개.

    models: {target: GprModel} (활성 모델만). 활성 모델이 없으면 빈 리스트.
    computed: 이미 계산된 조성 좌표 집합 {(xO,xF,xOH)}.
    """
    active = {t: m for t, m in models.items() if isinstance(m, GprModel)}
    if not active:
        return []
    scored = []
    for comp in grid:
        if comp in computed:
            continue
        uv = np.array([to_uv(*comp)])
        score = 0.0
        for t, m in active.items():
            _, sigma = m.predict(uv)
            score += float(sigma[0]) / (m.y_std or 1.0)
        scored.append({"composition": comp, "score": score})
    scored.sort(key=lambda d: d["score"], reverse=True)
    return scored[:top]
