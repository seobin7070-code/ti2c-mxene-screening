"""재사용 UI 컴포넌트 — pill 배지, KPI, 안내 카드, 진행바, 출처 칩 등.

모든 컴포넌트는 HTML 문자열을 만들어 반환하거나 st에 렌더한다.
색/아이콘은 ui.tokens에서만 가져온다 (의미 고정).
"""

from __future__ import annotations

import html
from typing import Optional

import streamlit as st

from ui import tokens as T


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
    st.markdown(
        f'<div class="page-title">{html.escape(title)}</div>'
        f'<div class="page-sub">{html.escape(subtitle)}</div>',
        unsafe_allow_html=True,
    )


def section_title(text: str):
    st.markdown(f'<div class="section-title">{html.escape(text)}</div>', unsafe_allow_html=True)


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
    st.markdown(
        f'<div class="notice" style="background:{bg};border-color:{_hex_to_rgba(m["color"], 0.3)}">'
        f'<div class="ico" style="color:{m["color"]}">{m["icon"]}</div>'
        f'<div class="body"><b style="color:{m["color"]}">{html.escape(title)}</b>{body_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def empty_state(icon: str, text: str, hint: str = ""):
    hint_html = f'<div class="hint" style="margin-top:4px">{html.escape(hint)}</div>' if hint else ""
    st.markdown(
        f'<div class="card"><div class="empty-state">'
        f'<div class="ico">{icon}</div><div>{html.escape(text)}</div>{hint_html}'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def card_open() -> str:
    return '<div class="card">'


def card(html_inner: str, tight: bool = False):
    cls = "card card-tight" if tight else "card"
    st.markdown(f'<div class="{cls}">{html_inner}</div>', unsafe_allow_html=True)


def footer():
    st.markdown(
        '<div class="app-footer">'
        '계산: Quantum ESPRESSO, PBE-D3 · 본 플랫폼의 수치는 '
        '<span class="mono">data/energies.csv</span>에서 직접 산출됨'
        '</div>',
        unsafe_allow_html=True,
    )


# ── 계산값 기반 해석 배지 (문구는 값에서만 생성) ──────────────
#
# 해석 배지(강/중/약 흡착)의 경계값 — 단일 소스.
# 각 항목: (상한 eV, 라벨, 상태색). E_ad(eV)가 upper 이하인 첫 구간을 적용한다.
# 이것은 '설명용 상대 구간'이며 core 의 suspect 판정(E_ad < -3 또는 > +0.5)과는 독립이다.
INTERPRETATION_BANDS: list[tuple[float, str, str]] = [
    (-1.0, "강한 흡착", "ok"),      # E_ad ≤ -1.0 eV
    (-0.3, "중간 흡착", "info"),    # -1.0 < E_ad ≤ -0.3 eV
    (0.0,  "약한 흡착", "pending"), # -0.3 < E_ad < 0.0 eV
    (float("inf"), "흡착 불리(양의 E_ad)", "suspect"),  # E_ad ≥ 0.0 eV
]


def adsorption_interpretation(e_ad_ev: float) -> tuple[str, str]:
    """E_ad(eV) 값만으로 해석 라벨과 상태색을 생성한다 (임의 문구 금지).

    경계값은 INTERPRETATION_BANDS 에 정의되어 있다.
    물리 관례: 더 음수일수록 강한 흡착.
    """
    for upper, label, kind in INTERPRETATION_BANDS:
        if e_ad_ev <= upper or upper == float("inf"):
            # '약한 흡착'은 음수에 한정하므로 0.0 상한은 '미만'으로 처리
            if label == "약한 흡착" and e_ad_ev >= 0.0:
                continue
            return label, kind
    return "흡착 불리(양의 E_ad)", "suspect"


def interpretation_legend_html() -> str:
    """해석 배지 분류 기준을 화면에 표시할 HTML (경계값을 그대로 노출)."""
    rows = [
        ("강한 흡착", "ok", "E_ad ≤ -1.0 eV"),
        ("중간 흡착", "info", "-1.0 < E_ad ≤ -0.3 eV"),
        ("약한 흡착", "pending", "-0.3 < E_ad < 0.0 eV"),
        ("흡착 불리", "suspect", "E_ad ≥ 0.0 eV"),
    ]
    items = "".join(
        f'<div style="display:flex;gap:8px;align-items:center;padding:3px 0">'
        f'{status_pill(kind, label)}'
        f'<span class="mono hint">{rng}</span></div>'
        for label, kind, rng in rows
    )
    return (
        '<div class="hint" style="margin-bottom:6px">해석 배지 분류 기준 '
        '(설명용 상대 구간 · suspect 판정과는 별개)</div>' + items
        + '<div class="hint" style="margin-top:8px">※ 분류 기준은 본 플랫폼의 '
          '가정이며 문헌 기준이 아님.</div>'
    )
