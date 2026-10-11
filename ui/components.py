"""재사용 UI 컴포넌트 — pill 배지, KPI, 안내 카드, 진행바, 출처 칩 등.

모든 컴포넌트는 HTML 문자열을 만들어 반환하거나 st에 렌더한다.
색/아이콘은 ui.tokens에서만 가져온다 (의미 고정).
"""

from __future__ import annotations

import html
from typing import Optional

import streamlit as st

from ui import tokens as T
from ui.htmlutil import html_block


def render_html(target, html_str: str) -> None:
    """HTML을 Markdown 안전하게 정규화해 렌더한다 (target: st 또는 column)."""
    target.markdown(html_block(html_str), unsafe_allow_html=True)


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ── pill 배지 ──────────────────────────────────────────────────
def status_pill(status: str, text: Optional[str] = None) -> str:
    """상태 pill HTML. 색 + 아이콘 + 라벨(색각 이상 배려)."""
    m = T.status_meta(status)
    label = text if text is not None else m["label"]
    bg = _hex_to_rgba(m["color"], 0.12)
    return (
        f'<span class="pill" style="background:{bg};color:{m["color"]};'
        f'border-color:{_hex_to_rgba(m["color"], 0.25)}">'
        f'<span class="ico">{m["icon"]}</span>{html.escape(str(label))}</span>'
    )


def gas_pill(gas: str) -> str:
    m = T.gas_meta(gas)
    bg = _hex_to_rgba(m["color"], 0.12)
    return (
        f'<span class="pill" style="background:{bg};color:{m["color"]};'
        f'border-color:{_hex_to_rgba(m["color"], 0.25)}">'
        f'<span class="ico">{m["icon"]}</span>{m["label"]}</span>'
    )


# ── 출처 칩 ────────────────────────────────────────────────────
def source_chip(source_file: str, calc_group: str) -> str:
    """출처(source_file)와 calc_group을 모노스페이스 칩으로 표시 (추적성, DI-4)."""
    sf = html.escape(source_file or "—")
    cg = html.escape(calc_group or "—")
    return f'<span class="src-chip">📄 {sf} · group {cg}</span>'


# ── 페이지 헤더 ────────────────────────────────────────────────
def page_header(title: str, subtitle: str):
    render_html(st,
        f'<div class="page-title">{html.escape(title)}</div>'
        f'<div class="page-sub">{html.escape(subtitle)}</div>')


def section_title(text: str):
    render_html(st, f'<div class="section-title">{html.escape(text)}</div>')


def section_head(icon_svg: str, text: str):
    """섹션 제목 앞에 인라인 SVG 아이콘을 붙여 렌더한다."""
    render_html(st,
        f'<div class="section-head"><span class="sh-icon">{icon_svg}</span>'
        f'<span class="sh-text">{html.escape(text)}</span></div>')


def breadcrumb(category: str, page: str):
    """'카테고리 › 페이지' 브레드크럼."""
    render_html(st,
        f'<div class="breadcrumb"><span class="bc-cat">{html.escape(category)}</span>'
        f'<span class="bc-sep">›</span>{html.escape(page)}</div>')


def page_header_bc(category: str, title: str, subtitle: str):
    """브레드크럼 + 페이지 헤더."""
    breadcrumb(category, title)
    page_header(title, subtitle)


# ── 용어 툴팁 (ⓘ) ──────────────────────────────────────────────
def info_tooltip(label: str, desc: str) -> str:
    """라벨 옆 ⓘ 아이콘 + 호버 설명 HTML (설명 문자열을 직접 받는다)."""
    shown = html.escape(label)
    if not desc:
        return shown
    return (
        f'<span class="tip" tabindex="0">{shown}'
        f'<span class="tip-i" aria-hidden="true">i</span>'
        f'<span class="tip-box" role="tooltip">{html.escape(desc)}</span></span>'
    )


# ── 적용 범위 배너 (PDF 1장, 결과 화면 상단 한 곳) ─────────────
def scope_banner():
    from core.scope import APPLICABILITY
    render_html(st,
        f'<div class="scope-banner"><span class="scope-ic">ⓘ</span>'
        f'<span><b>적용 범위</b> — {html.escape(APPLICABILITY)}</span></div>')


# ── KPI 카드 ───────────────────────────────────────────────────
def kpi_card(label: str, value: str, unit: str = "", sub: str = "") -> str:
    unit_html = f'<span class="kpi-unit">{html.escape(unit)}</span>' if unit else ""
    sub_html = f'<div class="hint" style="margin-top:6px">{sub}</div>' if sub else ""
    return (
        f'<div class="card card-tight">'
        f'<div class="kpi-label">{html.escape(label)}</div>'
        f'<div class="kpi-value">{value}{unit_html}</div>'
        f'{sub_html}</div>'
    )


def progress_card(label: str, done: int, need: int) -> str:
    pct = 0 if need == 0 else min(100, int(done / need * 100))
    return (
        f'<div class="card card-tight">'
        f'<div class="kpi-label">{html.escape(label)}</div>'
        f'<div class="kpi-value">{done}<span class="kpi-unit">/ {need}</span></div>'
        f'<div class="progress-track" style="margin-top:10px">'
        f'<div class="progress-fill" style="width:{pct}%"></div></div>'
        f'</div>'
    )


def progress_bar(done: int, need: int) -> str:
    pct = 0 if need == 0 else min(100, int(done / need * 100))
    return (
        f'<div style="display:flex;align-items:center;gap:10px">'
        f'<div class="progress-track" style="flex:1"><div class="progress-fill" style="width:{pct}%"></div></div>'
        f'<span class="mono hint">{done}/{need}</span></div>'
    )


# ── 안내 / 빈 상태 ─────────────────────────────────────────────
def notice(kind: str, title: str, body: str = ""):
    """상태색 안내 카드. kind: ok | pending | suspect | info."""
    m = T.status_meta(kind)
    bg = _hex_to_rgba(m["color"], 0.08)
    body_html = f'<div class="hint" style="margin-top:4px">{body}</div>' if body else ""
    render_html(st,
        f'<div class="notice" style="background:{bg};border-color:{_hex_to_rgba(m["color"], 0.3)}">'
        f'<div class="ico" style="color:{m["color"]}">{m["icon"]}</div>'
        f'<div class="body"><b style="color:{m["color"]}">{html.escape(title)}</b>{body_html}</div>'
        f'</div>')


def empty_state(icon: str, text: str, hint: str = ""):
    hint_html = f'<div class="hint" style="margin-top:4px">{html.escape(hint)}</div>' if hint else ""
    render_html(st,
        f'<div class="card"><div class="empty-state">'
        f'<div class="ico">{icon}</div><div>{html.escape(text)}</div>{hint_html}'
        f'</div></div>')


def card_open() -> str:
    return '<div class="card">'


def card(html_inner: str, tight: bool = False):
    cls = "card card-tight" if tight else "card"
    render_html(st, f'<div class="{cls}">{html_inner}</div>')


def footer():
    from ui import branding
    render_html(st,
        f'<div class="app-footer">{html.escape(branding.footer_text())} · '
        '본 플랫폼의 수치는 <span class="mono">data/energies.csv</span>에서 직접 산출됨'
        '</div>')


# ── 빈 상태 (일러스트 버전) ────────────────────────────────────
def empty_state_svg(svg: str, text: str, hint: str = ""):
    hint_html = f'<div class="hint" style="margin-top:4px">{html.escape(hint)}</div>' if hint else ""
    render_html(st,
        f'<div class="card"><div class="empty-state">{svg}'
        f'<div>{html.escape(text)}</div>{hint_html}</div></div>')
