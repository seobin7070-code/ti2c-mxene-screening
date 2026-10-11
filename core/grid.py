"""조성 격자 (PDF 3.1, composition_grid).

2×2 셀은 면당 4자리라 조성이 1/4 단위(0, 0.25, 0.5, 0.75, 1)로만 가능.
"quarter" 격자 = xO+xF+xOH=1 인 1/4 단위 점 15개.
다음 계산 후보·역방향 추천 후보는 이 격자에서만 고른다.
"""

from __future__ import annotations


def quarter_grid() -> list[tuple[float, float, float]]:
    """1/4 단위 조성 격자 15점을 생성한다 (xO+xF+xOH=1)."""
    pts = []
    n = 4
    for i in range(n + 1):          # xO = i/4
        for j in range(n + 1 - i):  # xF = j/4
            k = n - i - j           # xOH = k/4
            pts.append((i / n, j / n, k / n))
    return pts


def get_grid(name: str) -> list[tuple[float, float, float]]:
    if name == "quarter":
        return quarter_grid()
    # 기본값: quarter
    return quarter_grid()
