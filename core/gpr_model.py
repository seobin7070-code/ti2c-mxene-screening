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


def _make_gp(n_dims: int = 2) -> GaussianProcessRegressor:
    kernel = RBF(length_scale=[1.0] * n_dims, length_scale_bounds=(0.1, 5.0)) \
        + WhiteKernel(noise_level=1e-3, noise_level_bounds=(1e-5, 1e-1))
    return GaussianProcessRegressor(kernel=kernel, normalize_y=True,
                                    n_restarts_optimizer=2, random_state=0)


def fit_target(points: list[tuple[tuple[float, float, float], float]],
               target: str, min_train_points: int) -> "GprModel | GprUnavailable":
    """points: [((xO,xF,xOH), y)]. min_train_points 미만이면 비활성 (2D (u,v) 입력)."""
    n = len(points)
    if n < min_train_points:
        return GprUnavailable(target, n, min_train_points)
    X = np.array([to_uv(*p[0]) for p in points], dtype=float)
    y = np.array([p[1] for p in points], dtype=float)
    gp = _make_gp(2)
    gp.fit(X, y)
    return GprModel(target, gp, n, float(np.std(y)) or 1.0)


# ── 세트 스케일 차원을 포함한 통합 GPR ───────────────────────────
# 서로 다른 calc_group(세트)은 셀 스케일이 달라 E_ads 스케일 자체가 다르다.
# 두 세트를 하나의 y 벡터로 '뺄셈 없이' 통합하되, 입력에 세트 스케일 지표를
# 추가 차원으로 넣어(=(u, v, scale)) 모델이 세트를 구분해 학습하게 한다.
# 예측 시에는 반드시 어느 세트(scale) 기준인지 지정한다.
SCALE_CODE = {"SET1": 0.0, "SET2": 1.0}
# 가스 원-핫 (단일 GPR이 조성+세트+가스로 E_ads 를 학습하도록 입력 차원에 포함)
GAS_ONEHOT = {"CO2": (1.0, 0.0, 0.0), "H2O": (0.0, 1.0, 0.0), "SO2": (0.0, 0.0, 1.0)}


def _feat(comp, scale):
    u, v = to_uv(*comp)
    return [u, v, float(scale)]


def _feat_gas(comp, scale, gas):
    u, v = to_uv(*comp)
    return [u, v, float(scale), *GAS_ONEHOT[gas]]


@dataclass
class GprSetModel:
    """세트 스케일 차원을 포함한 통합 GPR (입력 (u,v,scale))."""
    target: str
    gp: GaussianProcessRegressor
    n: int
    y_std: float
    scales: dict          # {calc_group: scale_code} 학습에 쓰인 세트

    def predict(self, comp, calc_group):
        """조성 comp=(xO,xF,xOH)·세트 기준 예측 → (mu, sigma)."""
        scale = self.scales.get(calc_group)
        if scale is None:
            scale = next(iter(self.scales.values()))
        X = np.array([_feat(comp, scale)])
        mu, sigma = self.gp.predict(X, return_std=True)
        return float(mu[0]), float(sigma[0])


def fit_target_multiset(points, target: str, min_train_points: int):
    """세트 통합 학습. points: [((xO,xF,xOH), calc_group, y)].

    서로 다른 세트를 섞어서 '빼지' 않고, 세트 지표를 입력 차원으로 넣어 통합 학습한다.
    """
    n = len(points)
    if n < min_train_points:
        return GprUnavailable(target, n, min_train_points)
    scales = {}
    for _, cg, _ in points:
        scales.setdefault(cg, SCALE_CODE.get(cg, float(len(scales))))
    X = np.array([_feat(p[0], scales[p[1]]) for p in points], dtype=float)
    y = np.array([p[2] for p in points], dtype=float)
    gp = _make_gp(3)
    gp.fit(X, y)
    return GprSetModel(target, gp, n, float(np.std(y)) or 1.0, scales)


# ── 단일 통합 모델: 조성 + 세트 + 가스 → E_ads ─────────────────
# 가스별로 나누면 타깃당 데이터가 7개 미만이라, 가스를 입력 차원(원-핫)에 넣어
# 하나의 GPR이 전체 E_ads(13점)를 학습하게 한다. 이렇게 하면 학습셋이 7개 이상이 되며,
# 세트 혼합(뺄셈)은 여전히 일어나지 않는다(세트는 입력 지표일 뿐).
@dataclass
class UnifiedModel:
    gp: GaussianProcessRegressor
    n: int
    y_std: float
    scales: dict          # {calc_group: scale_code}

    def predict(self, comp, calc_group, gas):
        scale = self.scales.get(calc_group, next(iter(self.scales.values())))
        X = np.array([_feat_gas(comp, scale, gas)])
        mu, sigma = self.gp.predict(X, return_std=True)
        return float(mu[0]), float(sigma[0])


def fit_unified(points, min_train_points: int):
    """조성+세트+가스 통합 GPR. points: [((xO,xF,xOH), calc_group, gas, y)]."""
    n = len(points)
    if n < min_train_points:
        return GprUnavailable("Eads_unified", n, min_train_points)
    scales = {}
    for _, cg, _, _ in points:
        scales.setdefault(cg, SCALE_CODE.get(cg, float(len(scales))))
    X = np.array([_feat_gas(p[0], scales[p[1]], p[2]) for p in points], dtype=float)
    y = np.array([p[3] for p in points], dtype=float)
    gp = _make_gp(6)   # u, v, scale, 3-gas onehot
    gp.fit(X, y)
    return UnifiedModel(gp, n, float(np.std(y)) or 1.0, scales)


def loocv_unified(points, min_train_points: int) -> LoocvResult:
    n = len(points)
    if n < min_train_points:
        return LoocvResult(False, "Eads_unified", n, None, None,
                           f"데이터 부족 {n}/{min_train_points}")
    scales = {}
    for _, cg, _, _ in points:
        scales.setdefault(cg, SCALE_CODE.get(cg, float(len(scales))))
    X = np.array([_feat_gas(p[0], scales[p[1]], p[2]) for p in points], dtype=float)
    y = np.array([p[3] for p in points], dtype=float)
    yt, yp = [], []
    for tr, te in LeaveOneOut().split(X):
        gp = _make_gp(6)
        gp.fit(X[tr], y[tr])
        yt.append(y[te][0])
        yp.append(gp.predict(X[te])[0])
    yt, yp = np.array(yt), np.array(yp)
    return LoocvResult(True, "Eads_unified", n,
                       float(mean_absolute_error(yt, yp)),
                       float(np.sqrt(mean_squared_error(yt, yp))), None)


def recommend_unified(model, grid, calc_group: str, target_values: dict,
                      top: int = 5) -> list[dict]:
    """역방향 추천(통합 모델): 격자 조성에서 가스별 목표 E_ads 에 가장 가까운 조성.

    model: UnifiedModel. target_values: {gas: 목표 E_ads(eV)} (지정한 가스만 사용).
    지정 세트(calc_group) 스케일로 예측하고 가중 거리 오름차순 정렬.
    """
    if not isinstance(model, UnifiedModel) or not target_values:
        return []
    out = []
    for comp in grid:
        preds, dist2 = {}, 0.0
        for gas, tgt in target_values.items():
            mu, sigma = model.predict(comp, calc_group, gas)
            preds[gas] = (mu, sigma)
            dist2 += (mu - tgt) ** 2
        out.append({"composition": comp, "predictions": preds, "score": dist2 ** 0.5})
    out.sort(key=lambda d: d["score"])
    return out[:top]


def pareto_front(cands: list[dict]) -> list[dict]:
    """비지배(Pareto) 후보만 남긴다 (PDF 6.2).

    목표: P_cond 하한(p_cond_lower)은 '클수록' 좋고, Δd 상한(dd_upper)은 '작을수록' 좋다.
    Δd 가 None(데이터 없음)인 후보는 Δd 축을 무시하고 P_cond 하한만으로 비교한다.
    cands: [{composition, p_cond_lower, dd_upper(opt), sigma, ...}].
    반환: 비지배 후보 리스트(원소는 입력 dict 그대로).
    """
    def dominates(a, b) -> bool:
        """a 가 b 를 지배하는가? (모든 목표에서 a≥b, 하나 이상에서 a>b)"""
        a_p, b_p = a["p_cond_lower"], b["p_cond_lower"]
        # Δd: 둘 다 값이 있을 때만 비교축으로 사용
        use_dd = a.get("dd_upper") is not None and b.get("dd_upper") is not None
        ge = a_p >= b_p
        gt = a_p > b_p
        if use_dd:
            ge = ge and (a["dd_upper"] <= b["dd_upper"])
            gt = gt or (a["dd_upper"] < b["dd_upper"])
        return ge and gt

    front = []
    for c in cands:
        if not any(dominates(o, c) for o in cands if o is not c):
            front.append(c)
    return front


def recommend_pareto(cands: list[dict], top: int = 5) -> list[dict]:
    """우선 검토 후보 → 비지배 선별 → σ 오름차순 정렬 (PDF 6.2).

    cands: 우선 검토로 분류된 후보 [{composition, p_cond_lower, dd_upper, sigma, ...}].
    비어 있으면 빈 리스트(=우선 검토 후보 없음).
    """
    if not cands:
        return []
    front = pareto_front(cands)
    front.sort(key=lambda d: d.get("sigma", 0.0))
    return front[:top]


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


def loocv_multiset(points, target: str, min_train_points: int) -> LoocvResult:
    """세트 통합 LOOCV. points: [((xO,xF,xOH), calc_group, y)]."""
    n = len(points)
    if n < min_train_points:
        return LoocvResult(False, target, n, None, None,
                           f"데이터 부족 {n}/{min_train_points}")
    scales = {}
    for _, cg, _ in points:
        scales.setdefault(cg, SCALE_CODE.get(cg, float(len(scales))))
    X = np.array([_feat(p[0], scales[p[1]]) for p in points], dtype=float)
    y = np.array([p[2] for p in points], dtype=float)
    yt, yp = [], []
    for tr, te in LeaveOneOut().split(X):
        gp = _make_gp(3)
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


def recommend_surfaces(models: dict, grid, calc_group: str,
                       targets: list, target_values: dict, top: int = 5) -> list[dict]:
    """역방향 추천: 격자 조성에서 타깃 흡착 에너지에 가장 가까운 조성을 추천한다.

    models: {target: GprSetModel}. target_values: {target: 목표 E_ads(eV)}.
    지정한 세트(calc_group) 스케일로 예측하고, 목표값과의 가중 거리 오름차순으로 정렬.
    반환: [{composition, predictions:{t:(mu,sigma)}, score}]
    """
    active = {t: m for t, m in models.items()
              if isinstance(m, GprSetModel) and t in target_values}
    if not active:
        return []
    out = []
    for comp in grid:
        preds, dist2 = {}, 0.0
        for t, m in active.items():
            mu, sigma = m.predict(comp, calc_group)
            preds[t] = (mu, sigma)
            dist2 += (mu - target_values[t]) ** 2
        out.append({"composition": comp, "predictions": preds, "score": dist2 ** 0.5})
    out.sort(key=lambda d: d["score"])
    return out[:top]


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
