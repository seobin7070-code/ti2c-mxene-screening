"""내비게이션 — 카테고리 그룹 없이 한 줄 목록 6개 (PDF [5]).

정방향 검증 / 역방향 추천 / 조성 지도 / 데이터·QC / 모델 정보 / 내보내기.
"""

from __future__ import annotations

PAGES = [
    "정방향 검증",
    "역방향 추천",
    "조성 지도",
    "데이터·QC",
    "모델 정보",
    "내보내기",
]

# 첫 진입(입장 직후) 페이지
DEFAULT_PAGE = "정방향 검증"


def all_pages() -> list[str]:
    return list(PAGES)
