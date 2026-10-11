"""브랜딩 단일 소스 — 프로젝트/팀/대회 정보와 워드마크, 로고 처리.

가상 정보(수상·인증·약자 뜻·팀원 이름)를 만들어 넣지 않는다.
MEMBERS 가 비어 있으면 팀원은 어디에도 표시하지 않는다.
"""

from __future__ import annotations

import os

from ui import tokens as T

PROJECT_TITLE = "배가스 맞춤형 Ti₂C MXene 표면 설계 플랫폼"
TEAM_NAME = "RE:ACT"
SCHOOL = "울산대학교"
DEPT = "에너지화학공학부"
EVENT = "2026 UoU 창의적 종합설계 경진대회"
MEMBERS: list[str] = []  # 비어 있으면 표시하지 않음

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
APP_ICON = os.path.join(ASSETS_DIR, "app_icon_512.png")
LOGO_HORIZONTAL_DARK = os.path.join(ASSETS_DIR, "logo_horizontal_dark.png")
FAVICON = os.path.join(ASSETS_DIR, "favicon_64.png")


def app_icon_path():
    """시작 화면 로고용. app_icon 또는 logo_horizontal_dark 가 있으면 경로, 없으면 None."""
    if os.path.exists(APP_ICON):
        return APP_ICON
    if os.path.exists(LOGO_HORIZONTAL_DARK):
        return LOGO_HORIZONTAL_DARK
    return None


def favicon_path():
    # 파일이 있으면 PNG 경로, 없으면 Streamlit이 허용하는 이모지로 폴백한다.
    # (임의의 유니코드 심볼 "⬡" 는 page_icon 검증을 통과하지 못해 에러가 난다.)
    return FAVICON if os.path.exists(FAVICON) else "🔷"


def wordmark(on_dark: bool = True, size: int = 20) -> str:
    """RE:ACT 워드마크 HTML. 콜론만 앰버, 나머지는 흰색(어두운 배경)/네이비(밝은 배경).

    약자의 뜻은 임의로 붙이지 않는다 (워드마크 텍스트 그대로).
    """
    base = "#FFFFFF" if on_dark else T.NAVY
    accent = T.GAS["SO2"]["color"]  # 앰버 #D97706 (가스 고정색과 동일 토큰 참조)
    return (
        f'<span class="wordmark" style="font-weight:800;font-size:{size}px;'
        f'letter-spacing:0.02em;color:{base}">'
        f'RE<span style="color:{accent}">:</span>ACT</span>'
    )


def has_logo_team() -> bool:
    return os.path.exists(LOGO_TEAM)


def has_logo_school() -> bool:
    return os.path.exists(LOGO_SCHOOL)


def footer_text() -> str:
    return f"{TEAM_NAME} · {SCHOOL} {DEPT} · Quantum ESPRESSO, PBE-D3"


def has_members() -> bool:
    return len(MEMBERS) > 0
