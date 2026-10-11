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

/* ══════════════════════════════════════════════════════════════
   디자인 개편 — 히어로/카드 호버/일러스트/파이프라인/시나리오/툴팁
   ══════════════════════════════════════════════════════════════ */

/* ── 일러스트 색 변수 (라이트 기본) ──────────────────────────── */
:root {{
    --ill-ti: #334155;        /* Ti 층 */
    --ill-c:  #94A3B8;        /* C 층 */
    --ill-carbon: #475569;    /* 탄소 원자 */
    --ill-o:  #0F766E;        /* -O (틸) */
    --ill-f:  #D97706;        /* -F (앰버) */
    --ill-oh: #2563EB;        /* -OH (블루) */
    --ill-h:  #94A3B8;        /* 수소 */
    --ill-stroke: #64748B;    /* 결합선 */
    --ill-faint: #CBD5E1;     /* 흐린 선/화살표 */
    --ill-accent: {T.PRIMARY};/* 포인트 */
    --ill-navy: {T.NAVY};
    --ill-tint: {T.TINT};
}}

/* ── 섹션 제목 앞 아이콘 ─────────────────────────────────────── */
.section-head {{ display:flex; align-items:center; gap:8px; margin: 18px 0 12px 0; }}
.section-head .sh-icon {{ width:18px; height:18px; flex:0 0 18px; color:{T.PRIMARY}; }}
.section-head .sh-icon svg {{ width:18px; height:18px; display:block; }}
.section-head .sh-text {{ font-size:18px; font-weight:600; color:{T.TEXT}; }}

/* ── 카드 호버 상승 ─────────────────────────────────────────── */
.card, .scn-card, .kpi-eq {{ transition: box-shadow 150ms ease, transform 150ms ease; }}
.card:hover, .scn-card:hover {{ box-shadow: 0 6px 18px rgba(11,31,51,0.10); transform: translateY(-2px); }}

/* ── 높이 통일 KPI 카드 ─────────────────────────────────────── */
.kpi-eq {{
    background:{T.CARD}; border:1px solid {T.BORDER}; border-radius:12px;
    padding:16px 18px; min-height:170px;
    display:flex; flex-direction:column;
    box-shadow:0 1px 2px rgba(16,24,40,0.04);
}}
.kpi-eq .kpi-top {{ flex:0 0 auto; }}
.kpi-eq .kpi-bottom {{ margin-top:auto; }}  /* 진행바 3줄을 하단 영역으로 분리 */
.kpi-eq:hover {{ box-shadow:0 6px 18px rgba(11,31,51,0.10); transform:translateY(-2px); }}

/* ── 히어로 (네이비→틸 그라데이션 + 흰 텍스트 + 우측 SVG) ─────── */
.hero {{
    position:relative; overflow:hidden;
    background: linear-gradient(120deg, {T.NAVY} 0%, #0C3A3A 55%, {T.PRIMARY} 120%);
    border-radius:16px; padding:30px 32px; margin-bottom:20px;
    display:flex; gap:24px; align-items:center;
}}
.hero-left {{ flex:1.3; min-width:0; }}
.hero-right {{ flex:1; min-width:0; display:flex; justify-content:center; }}
.hero-eyebrow {{ font-size:12px; font-weight:600; letter-spacing:.08em; text-transform:uppercase;
    color:#5EEAD4; margin-bottom:10px; }}
.hero-title {{ font-size:26px; font-weight:700; line-height:1.3; color:#fff; letter-spacing:-0.01em; }}
.hero-desc {{ font-size:14px; line-height:1.7; color:#CBD5E1; margin-top:12px; max-width:52ch; }}
.hero .ill-hero {{ width:100%; max-width:420px; height:auto; }}

/* 히어로 CTA 버튼은 Streamlit 버튼을 활용 */
.hero-ctas {{ margin-top:18px; }}

/* ── 시나리오 카드 (누가 어떻게 쓰나) ───────────────────────── */
.scn-card {{
    background:{T.CARD}; border:1px solid {T.BORDER}; border-radius:14px;
    padding:18px 18px 16px; min-height:188px; display:flex; flex-direction:column;
    box-shadow:0 1px 2px rgba(16,24,40,0.04);
}}
.scn-icon {{ width:34px; height:34px; border-radius:9px; background:{T.TINT};
    display:flex; align-items:center; justify-content:center; margin-bottom:10px; color:{T.PRIMARY}; }}
.scn-icon svg {{ width:20px; height:20px; }}
.scn-title {{ font-size:15px; font-weight:700; color:{T.TEXT}; }}
.scn-role {{ font-size:11px; color:{T.PRIMARY}; font-weight:600; margin-bottom:6px; }}
.scn-use {{ font-size:13px; color:{T.TEXT_MUTED}; line-height:1.6; flex:1; }}

/* ── 파이프라인 4단계 ──────────────────────────────────────── */
.pipeline {{ display:flex; align-items:stretch; gap:4px; flex-wrap:nowrap;
    background:{T.CARD}; border:1px solid {T.BORDER}; border-radius:14px; padding:18px; }}
.pipe-step {{ flex:1; min-width:0; text-align:center; padding:4px 8px; }}
.pipe-icon {{ width:40px; height:40px; margin:0 auto 8px; border-radius:10px;
    background:{T.TINT}; display:flex; align-items:center; justify-content:center; }}
.pipe-svg {{ width:22px; height:22px; }}
.pipe-step-no {{ font-size:10px; font-weight:700; letter-spacing:.06em; color:{T.PRIMARY}; }}
.pipe-title {{ font-size:13px; font-weight:700; color:{T.TEXT}; margin-top:2px; }}
.pipe-desc {{ font-size:11px; color:{T.TEXT_MUTED}; line-height:1.5; margin-top:4px; }}
.pipe-arrow {{ align-self:center; color:{T.BORDER}; font-size:20px; flex:0 0 auto; padding:0 2px; }}

/* ── 일러스트 공통 텍스트 ──────────────────────────────────── */
.ill-caption {{ font-size:11px; color:{T.TEXT_MUTED}; text-align:center; margin:6px 0 2px; font-style:italic; }}
.ill-mol-label {{ font-size:10px; fill:var(--ill-stroke); text-anchor:middle; font-family:'JetBrains Mono',monospace; }}
.ill-layer-label {{ font-size:11px; fill:#fff; font-weight:700; }}
.ill-flow-label {{ font-size:11px; fill:var(--ill-stroke); text-anchor:middle; }}
.ill-legend text, .ill-legend-t {{ font-size:11px; fill:var(--ill-stroke); }}
.ill-flow {{ width:100%; max-width:640px; height:auto; }}
.ill-tri {{ display:inline-block; vertical-align:middle; }}
.ill-empty {{ width:56px; height:56px; margin:0 auto 8px; display:block; }}

/* ── 부유 애니메이션 (가스 분자) ───────────────────────────── */
@keyframes illFloat {{
    0%   {{ transform: translateY(0); }}
    50%  {{ transform: translateY(-7px); }}
    100% {{ transform: translateY(0); }}
}}
.ill-float {{ animation: illFloat 4s ease-in-out infinite; transform-box: fill-box; transform-origin: center; }}

/* ── 용어 툴팁 (ⓘ) ─────────────────────────────────────────── */
.tip {{ position:relative; display:inline-flex; align-items:center; cursor:help; }}
.tip .tip-i {{ display:inline-flex; align-items:center; justify-content:center;
    width:14px; height:14px; border-radius:50%; border:1px solid {T.TEXT_MUTED};
    color:{T.TEXT_MUTED}; font-size:10px; margin-left:4px; line-height:1; }}
.tip .tip-box {{
    visibility:hidden; opacity:0; transition:opacity 120ms ease;
    position:absolute; bottom:135%; left:50%; transform:translateX(-50%);
    background:{T.NAVY}; color:#F1F5F9; font-size:12px; font-weight:400; line-height:1.5;
    padding:8px 10px; border-radius:8px; width:240px; z-index:50;
    box-shadow:0 6px 20px rgba(0,0,0,0.25); text-align:left; white-space:normal;
}}
.tip:hover .tip-box, .tip:focus-within .tip-box {{ visibility:visible; opacity:1; }}
.tip .tip-box::after {{ content:""; position:absolute; top:100%; left:50%; transform:translateX(-50%);
    border:5px solid transparent; border-top-color:{T.NAVY}; }}

/* 호버 시 보이는 note (data-note 속성) */
[data-note] {{ position:relative; }}
[data-note]:hover::after {{
    content: attr(data-note); position:absolute; bottom:125%; left:0;
    background:{T.NAVY}; color:#F1F5F9; font-size:11px; padding:6px 9px; border-radius:7px;
    white-space:nowrap; z-index:60; box-shadow:0 6px 20px rgba(0,0,0,0.25);
}}

/* ── 신뢰 원칙 카드 (레지스트리) ───────────────────────────── */
.trust-card {{ background:{T.TINT_2}; border:1px solid {T.BORDER}; border-radius:12px; padding:14px 18px; margin-bottom:16px; }}
.trust-item {{ display:flex; gap:8px; align-items:flex-start; padding:3px 0; font-size:13px; color:{T.TEXT}; }}
.trust-item .ti-ic {{ color:{T.PRIMARY}; flex:0 0 auto; }}

/* 사이드바 문서 영역 */
.sidebar-docs {{ margin-top:14px; padding-top:12px; border-top:1px solid {T.BORDER}; }}
.sidebar-docs a {{ display:block; font-size:12px; color:{T.TEXT_MUTED}; text-decoration:none; padding:3px 0; }}
.sidebar-docs a:hover {{ color:{T.PRIMARY}; }}
.sidebar-logo-row {{ display:flex; align-items:center; gap:8px; }}
.sidebar-logo-row .ill-tri {{ width:22px; height:22px; }}

/* ── 모바일 1컬럼 ──────────────────────────────────────────── */
@media (max-width: 760px) {{
    .hero {{ flex-direction:column; align-items:flex-start; }}
    .hero-right {{ order:2; width:100%; }}
    .pipeline {{ flex-wrap:wrap; }}
    .pipe-arrow {{ display:none; }}
    .pipe-step {{ flex:1 1 45%; }}
}}

/* ── 모션 최소화 ──────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {{
    .ill-float {{ animation: none !important; }}
    .card, .scn-card, .kpi-eq {{ transition: none !important; }}
    .card:hover, .scn-card:hover, .kpi-eq:hover {{ transform:none; }}
}}

/* ── 다크 모드 ────────────────────────────────────────────── */
@media (prefers-color-scheme: dark) {{
    html, body, .stApp {{ color: #E2E8F0; }}
    .card, .data-summary, .kpi-eq, .scn-card, .pipeline {{ background: #1C1917; border-color: #292524; }}
    .page-title, .section-title, .section-head .sh-text, .kpi-value, .hero-value,
    .scn-title, .pipe-title, .trust-item {{ color: #F1F5F9; }}
    .src-chip {{ background: #0C0A09; border-color: #292524; }}
    .progress-track {{ background: #292524; }}
    .trust-card {{ background: #10211C; border-color:#1F3A33; }}
    .scn-icon, .pipe-icon {{ background:#10211C; }}
    /* 일러스트 색 변수 (다크에서 읽히도록) */
    :root {{
        --ill-ti: #64748B; --ill-c: #475569; --ill-carbon: #94A3B8;
        --ill-h: #64748B; --ill-stroke: #94A3B8; --ill-faint: #475569;
        --ill-tint: #10211C;
    }}
    .ill-caption, .ill-mol-label, .ill-flow-label, .ill-legend text {{ fill:#94A3B8; }}
}}
</style>
"""


def inject():
    """전역 CSS를 1회 주입한다."""
    st.markdown(_CSS, unsafe_allow_html=True)
