"""카테고리 내비게이션 정의 — 카테고리 › 페이지 구조와 아이콘.

사이드바 그룹 헤더 방식으로 구현한다 (st.navigation은 멀티파일 전제라 단일 app
함수 라우팅과 섞으면 불안정). 각 카테고리에 인라인 SVG 아이콘과 한 줄 설명.
"""

from __future__ import annotations


def _ic(path: str) -> str:
    return (f'<svg viewBox="0 0 24 24" width="16" height="16" fill="none" '
            f'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
            f'stroke-linejoin="round">{path}</svg>')


# 카테고리 아이콘 (인라인 SVG)
CAT_ICONS = {
    "홈": _ic('<path d="M3 11 L12 4 L21 11"/><path d="M5 10 V20 H19 V10"/>'),
    "분석": _ic('<path d="M4 20 V4"/><path d="M4 20 H20"/><rect x="7" y="12" width="3" height="6"/>'
                '<rect x="12" y="8" width="3" height="10"/><rect x="17" y="5" width="3" height="13"/>'),
    "설계": _ic('<circle cx="12" cy="12" r="8"/><path d="M12 4 V12 L17 15"/>'),
    "데이터": _ic('<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6 V18 a7 3 0 0 0 14 0 V6"/>'),
    "모델": _ic('<path d="M3 17 C7 7 11 7 13 12 C15 17 18 17 21 8"/>'),
    "자료": _ic('<path d="M6 3 h9 l4 4 v14 H6 z"/><path d="M15 3 v4 h4"/>'),
}

CAT_DESC = {
    "홈": "전체 요약과 기능 안내",
    "분석": "흡착 에너지·선택성 비교",
    "설계": "배가스 조건·조성 추천",
    "데이터": "에너지·파일·작업·무결성",
    "모델": "GPR 성능·잠금 해제",
    "자료": "방법론·용어·리포트·소개",
}

# 카테고리 → 페이지 목록 (순서 유지)
CATEGORIES: dict[str, list[str]] = {
    "홈": ["Overview"],
    "분석": ["정방향 검증", "표면 비교", "경쟁 흡착 비교"],
    "설계": ["배가스 조건 설정", "역방향 추천"],
    "데이터": ["데이터 레지스트리", ".out 파일 검사기", "계산 작업 관리", "무결성 점검"],
    "모델": ["모델 품질", "잠금 해제 로드맵"],
    "자료": ["방법론", "용어집", "리포트 내보내기", "팀·프로젝트 소개"],
}


def all_pages() -> list[str]:
    out = []
    for pages in CATEGORIES.values():
        out.extend(pages)
    return out


def category_of(page: str) -> str:
    for cat, pages in CATEGORIES.items():
        if page in pages:
            return cat
    return "홈"
