"""용어 도움말 사전 — 비전문가용 한 줄 설명의 단일 소스.

E_ads, Preference Index(P), Δd_surface, calc_group, DFT, GPR, Active Learning 등.
UI 전역에서 info_tooltip(term) 으로 가져다 쓴다. 설명은 '방법론 설명'만 담고
결과를 단정하지 않는다 (데이터 무결성 원칙).
"""

from __future__ import annotations

GLOSSARY: dict[str, str] = {
    "E_ads": (
        "흡착 에너지. 분자가 표면에 붙을 때의 에너지 변화로, "
        "E_adsorbed − (E_clean + E_molecule)로 계산합니다. "
        "값이 더 음수일수록 결합이 강함을 뜻합니다."
    ),
    "P": (
        "Preference Index(선택성 지표). 두 가스의 흡착 에너지 차이로, "
        "표면이 어떤 가스를 상대적으로 더 선호하는지 비교하는 값입니다."
    ),
    "Preference Index": (
        "선택성 지표. 두 가스의 흡착 에너지 차이로 표면의 가스 선호도를 비교합니다. "
        "예: P(CO₂/H₂O) = E_ads(H₂O) − E_ads(CO₂)."
    ),
    "Δd_surface": (
        "흡착 전후 표면 말단 원자들의 평균 높이(z) 변화량입니다. "
        "표면이 흡착으로 얼마나 구조적으로 변형되는지를 나타냅니다(SO₂ 사례)."
    ),
    "calc_group": (
        "동일한 계산 조건(에너지 컷오프, k-점 격자, 유사퍼텐셜, 셀)으로 묶인 그룹입니다. "
        "서로 다른 calc_group의 값은 섞어서 계산하지 않습니다."
    ),
    "DFT": (
        "밀도범함수이론(Density Functional Theory). 양자역학으로 재료의 "
        "에너지와 전자 구조를 계산하는 방법입니다."
    ),
    "GPR": (
        "가우시안 과정 회귀(Gaussian Process Regression). 적은 데이터로 "
        "예측값(μ)과 불확실성(σ)을 함께 추정하는 머신러닝 방법입니다."
    ),
    "Active Learning": (
        "능동 학습. 모델이 가장 불확실해하는 지점을 다음 계산 후보로 제안해, "
        "적은 계산으로 효율적으로 탐색하도록 돕는 전략입니다."
    ),
    "LOOCV": (
        "하나 빼기 교차검증(Leave-One-Out). 데이터를 하나씩 빼서 예측·검증하며 "
        "모델 성능(MAE/RMSE/R²)을 추정합니다."
    ),
    "suspect": (
        "의심 값. 흡착 에너지가 물리적으로 비현실적인 범위(E_ad < -3 eV 또는 "
        "> +0.5 eV)일 때 자동으로 붙는 경고입니다."
    ),
}


def describe(term: str) -> str:
    """용어 설명 문자열을 반환한다. 없으면 빈 문자열."""
    return GLOSSARY.get(term, "")
