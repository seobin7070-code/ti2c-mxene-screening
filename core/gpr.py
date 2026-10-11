"""GPR 모델: 지표별 독립 모델 3개 (P(CO2/H2O), P(CO2/SO2), Δd).

각 모델은 자기 지표가 실제 계산된 표면만 학습에 사용하며,
유효 데이터가 7개 미만이면 그 모델만 비활성화한다 (요구사항 8.2, 8.6).
σ는 보정된 불확실성이 아니라 참고용 상대 지표다 (요구사항 8.7).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel

MIN_TRAINING = 7  # 요구사항 8.6

# σ 안내 문구 (화면 고정 표시용, 요구사항 8.7)
SIGMA_DISCLAIMER = "σ는 보정된 불확실성이 아니라 참고용 상대 지표입니다."

# 지표별 방향: True = 클수록 좋음, False = 작을수록 좋음 (Pareto용, 요구사항 8.4)
METRIC_MAXIMIZE = {
    "P(CO2/H2O)": True,
    "P(CO2/SO2)": True,
    "Δd": False,
}


@dataclass
class GprUnavailable:
    metric: str
    n: int
    need: int = MIN_TRAINING

    @property
    def message(self) -> str:
        return f"데이터 부족: 현재 {self.n}개 / 필요 {self.need}개"


@dataclass
class GprModel:
    metric: str
    gp: GaussianProcessRegressor
    X_train: np.ndarray
    y_train: np.ndarray
    n: int

    def predict(self, X: np.ndarray):
        """예측 평균 μ와 표준편차 σ를 반환한다."""
        mu, sigma = self.gp.predict(X, return_std=True)
        return mu, sigma


def _make_gp() -> GaussianProcessRegressor:
    kernel = RBF(length_scale=0.5) + WhiteKernel(noise_level=1e-3)
    return GaussianProcessRegressor(kernel=kernel, normalize_y=True, n_restarts_optimizer=2)


def fit_metric_model(
    points: list[tuple[list[float], float]],
    metric: str,
) -> GprModel | GprUnavailable:
    """지표의 (조성벡터, 값) 목록으로 GPR 모델을 학습한다.

    points 가 MIN_TRAINING 미만이면 GprUnavailable 반환 (요구사항 8.6).
    """
    n = len(points)
    if n < MIN_TRAINING:
        return GprUnavailable(metric=metric, n=n)

    X = np.array([p[0] for p in points], dtype=float)
    y = np.array([p[1] for p in points], dtype=float)
    gp = _make_gp()
    gp.fit(X, y)
    return GprModel(metric=metric, gp=gp, X_train=X, y_train=y, n=n)


def ternary_grid(step: int = 20) -> np.ndarray:
    """[xO, xF, xOH] 합이 1인 삼각 격자 좌표를 생성한다."""
    pts = []
    for i in range(step + 1):
        for j in range(step + 1 - i):
            k = step - i - j
            pts.append([i / step, j / step, k / step])
    return np.array(pts, dtype=float)


@dataclass
class ScanResult:
    metric: str
    grid: np.ndarray            # (N, 3) 조성 좌표
    mu: np.ndarray              # (N,) 예측 평균
    sigma: np.ndarray           # (N,) 참고용 상대 불확실성
    sigma_disclaimer: str = SIGMA_DISCLAIMER


def scan_ternary(model: GprModel, step: int = 20) -> ScanResult:
    grid = ternary_grid(step)
    mu, sigma = model.predict(grid)
    return ScanResult(metric=model.metric, grid=grid, mu=mu, sigma=sigma)


def next_al_candidate(scan: ScanResult) -> dict:
    """Active Learning 다음 계산 후보: σ가 최대인 격자점 (요구사항 8.5)."""
    idx = int(np.argmax(scan.sigma))
    return {
        "composition": scan.grid[idx].tolist(),
        "mu": float(scan.mu[idx]),
        "sigma": float(scan.sigma[idx]),
        "note": SIGMA_DISCLAIMER,
    }


def pareto_front(scans: dict[str, ScanResult]) -> list[dict]:
    """활성화된 지표 모델들의 μ로 Pareto 비지배 집합을 구한다 (요구사항 8.4).

    scans: {metric: ScanResult}. 모든 scan은 동일 grid여야 한다.
    목적함수 방향은 METRIC_MAXIMIZE를 따른다 (maximize는 부호 반전해 통일).
    """
    if not scans:
        return []

    metrics = list(scans.keys())
    grid = next(iter(scans.values())).grid
    n_pts = grid.shape[0]

    # 모든 지표를 '최소화' 기준으로 정렬: maximize면 -mu 사용
    obj = np.zeros((n_pts, len(metrics)))
    for col, m in enumerate(metrics):
        mu = scans[m].mu
        obj[:, col] = -mu if METRIC_MAXIMIZE.get(m, True) else mu

    # 비지배 판정 (O(n^2), 격자 규모에서 충분)
    is_dominated = np.zeros(n_pts, dtype=bool)
    for i in range(n_pts):
        if is_dominated[i]:
            continue
        for j in range(n_pts):
            if i == j:
                continue
            # j가 i를 지배하는가? (모든 목적 ≤ 이고 하나는 <)
            if np.all(obj[j] <= obj[i]) and np.any(obj[j] < obj[i]):
                is_dominated[i] = True
                break

    front = []
    for i in np.where(~is_dominated)[0]:
        entry = {"composition": grid[i].tolist()}
        for m in metrics:
            entry[m] = float(scans[m].mu[i])
        front.append(entry)
    return front
