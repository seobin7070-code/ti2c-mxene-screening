"""전역 커스텀 CSS 주입 — 폰트, 카드, 배지, KPI, 레이아웃.

디자인 컨셉: Linear/Vercel의 절제 + Stripe의 '숫자가 주인공'.
라이트 기본, 다크 모드는 prefers-color-scheme으로 대응.
"""

from __future__ import annotations

import streamlit as st

from ui import tokens as T

_CSS = f"""
<style>
/* ── 폰트 (Pretendard 본문 + JetBrains Mono 수치) ───────────── */
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@latest/dist/web/static/pretendard.css');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"], .stMarkdown, .stApp {{
    font-family: 'Pretendard', system-ui, -apple-system, sans-serif;
    color: {T.TEXT};
}}

/* 메인 폭 제한 + 중앙 정렬 (최대 1200px) */
.block-container {{
    max-width: 1200px;
    padding-top: 2.2rem;
    padding-bottom: 4rem;
}}

/* ── 타이포 위계 ──────────────────────────────────────────── */
.page-title   {{ font-size: 28px; font-weight: 700; letter-spacing: -0.02em; margin: 0; color: {T.TEXT}; }}
.page-sub     {{ font-size: 14px; color: {T.TEXT_MUTED}; margin: 4px 0 20px 0; }}
.section-title{{ font-size: 18px; font-weight: 600; margin: 8px 0 12px 0; color: {T.TEXT}; }}
.hint         {{ font-size: 12px; color: {T.TEXT_MUTED}; }}

/* 수치/파일명 모노스페이스 + 자릿수 정렬 */
.mono, .num {{ font-family: 'JetBrains Mono', ui-monospace, monospace; font-variant-numeric: tabular-nums; }}

/* ── 카드 ─────────────────────────────────────────────────── */
.card {{
    background: {T.CARD};
    border: 1px solid {T.BORDER};
    border-radius: 12px;
    padding: 20px 22px;
    box-shadow: 0 1px 2px rgba(16,24,40,0.04);
    margin-bottom: 16px;
}}
.card-tight {{ padding: 16px 18px; }}

/* ── KPI (숫자가 주인공) ──────────────────────────────────── */
.kpi-label {{ font-size: 12px; color: {T.TEXT_MUTED}; font-weight: 500; margin-bottom: 6px; }}
.kpi-value {{ font-size: 32px; font-weight: 700; line-height: 1.1; font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; color: {T.TEXT}; }}
.kpi-unit  {{ font-size: 14px; font-weight: 500; color: {T.TEXT_MUTED}; margin-left: 4px; }}

/* 큰 지표(결과 카드) */
.hero-value {{ font-size: 40px; font-weight: 700; font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; }}
.hero-unit  {{ font-size: 16px; color: {T.TEXT_MUTED}; margin-left: 6px; }}

/* ── pill 배지 (상태/가스 공통) ───────────────────────────── */
.pill {{
    display: inline-flex; align-items: center; gap: 5px;
    padding: 2px 10px; border-radius: 999px;
    font-size: 12px; font-weight: 600; line-height: 1.6;
    border: 1px solid transparent;
}}
.pill .ico {{ font-size: 11px; }}

/* ── 진행바 ───────────────────────────────────────────────── */
.progress-track {{ background: {T.BORDER}; border-radius: 999px; height: 8px; width: 100%; overflow: hidden; }}
.progress-fill  {{ background: {T.PRIMARY}; height: 8px; border-radius: 999px; }}

/* ── 안내/빈 상태 카드 ────────────────────────────────────── */
.notice {{
    border-radius: 12px; padding: 16px 18px; border: 1px solid; margin-bottom: 16px;
    display: flex; gap: 12px; align-items: flex-start;
}}
.notice .ico {{ font-size: 18px; line-height: 1.4; }}
.notice .body {{ font-size: 14px; }}
.notice .body b {{ font-weight: 600; }}
.empty-state {{ text-align: center; padding: 40px 20px; color: {T.TEXT_MUTED}; }}
.empty-state .ico {{ font-size: 32px; margin-bottom: 8px; }}

/* 잠금/흐림 미리보기 */
.locked {{ position: relative; filter: blur(3px); opacity: .5; pointer-events: none; user-select: none; }}
.lock-overlay {{ text-align:center; padding: 10px; }}

/* ── 사이드바 ─────────────────────────────────────────────── */
section[data-testid="stSidebar"] {{ background: {T.CARD}; border-right: 1px solid {T.BORDER}; }}
.sidebar-logo {{ font-size: 16px; font-weight: 700; color: {T.PRIMARY}; letter-spacing: -0.01em; }}
.sidebar-sub  {{ font-size: 11px; color: {T.TEXT_MUTED}; margin-bottom: 8px; }}

/* 라디오를 내비게이션처럼 */
section[data-testid="stSidebar"] div[role="radiogroup"] label {{
    padding: 7px 10px; border-radius: 8px; margin-bottom: 2px; font-size: 14px;
}}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{ background: {T.BG}; }}

/* 데이터 상태 요약 박스 */
.data-summary {{ border: 1px solid {T.BORDER}; border-radius: 10px; padding: 12px 14px; margin-top: 8px; }}

/* 출처 아이콘 */
.src-chip {{
    font-family: 'JetBrains Mono', monospace; font-size: 11px;
    background: {T.BG}; border: 1px solid {T.BORDER}; border-radius: 6px;
    padding: 1px 7px; color: {T.TEXT_MUTED};
}}

/* 푸터 */
.app-footer {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid {T.BORDER};
    font-size: 12px; color: {T.TEXT_MUTED}; }}

/* 포커스 링 (키보드 접근성) */
:focus-visible {{ outline: 2px solid {T.PRIMARY}; outline-offset: 2px; }}

/* Streamlit 기본 메뉴/푸터 숨김 */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}

/* ── 다크 모드 ────────────────────────────────────────────── */
@media (prefers-color-scheme: dark) {{
    html, body, .stApp {{ color: #E2E8F0; }}
    .card, .data-summary {{ background: #1C1917; border-color: #292524; }}
    .page-title, .section-title, .kpi-value, .hero-value {{ color: #F1F5F9; }}
    .src-chip {{ background: #0C0A09; border-color: #292524; }}
    .progress-track {{ background: #292524; }}
}}
</style>
"""


def inject():
    """전역 CSS를 1회 주입한다."""
    st.markdown(_CSS, unsafe_allow_html=True)
