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


def section_head(icon_svg: str, text: str):
    """섹션 제목 앞에 인라인 SVG 아이콘을 붙여 렌더한다."""
    st.markdown(
        f'<div class="section-head"><span class="sh-icon">{icon_svg}</span>'
        f'<span class="sh-text">{html.escape(text)}</span></div>',
        unsafe_allow_html=True,
    )


def breadcrumb(category: str, page: str):
    """'카테고리 › 페이지' 브레드크럼."""
    st.markdown(
        f'<div class="breadcrumb"><span class="bc-cat">{html.escape(category)}</span>'
        f'<span class="bc-sep">›</span>{html.escape(page)}</div>',
        unsafe_allow_html=True,
    )


def page_header_bc(category: str, title: str, subtitle: str):
    """브레드크럼 + 페이지 헤더."""
    breadcrumb(category, title)
    page_header(title, subtitle)


# ── 용어 툴팁 (ⓘ) ──────────────────────────────────────────────
def info_tooltip(term: str, label: Optional[str] = None) -> str:
    """용어 옆 ⓘ 아이콘 + 호버 설명 HTML. 설명은 ui.glossary에서 가져온다."""
    from ui import glossary
    desc = glossary.describe(term)
    shown = html.escape(label if label is not None else term)
    if not desc:
        return shown
    return (
        f'<span class="tip" tabindex="0">{shown}'
        f'<span class="tip-i" aria-hidden="true">i</span>'
        f'<span class="tip-box" role="tooltip">{html.escape(desc)}</span></span>'
    )


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
    from ui import branding
    st.markdown(
        f'<div class="app-footer">{html.escape(branding.footer_text())} · '
        '본 플랫폼의 수치는 <span class="mono">data/energies.csv</span>에서 직접 산출됨'
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


# ── 높이 통일 KPI 카드 (상단 콘텐츠 + 하단 영역 분리) ──────────
def kpi_equal(label_html: str, top_html: str, bottom_html: str = "") -> str:
    """min-height 고정 KPI 카드. top은 상단, bottom은 카드 하단에 고정 배치.

    세 번째 카드의 진행바 3줄이 다른 카드 높이를 깨지 않도록 하단 영역으로 분리.
    """
    bottom = f'<div class="kpi-bottom">{bottom_html}</div>' if bottom_html else ""
    return (
        f'<div class="kpi-eq">'
        f'<div class="kpi-top"><div class="kpi-label">{label_html}</div>{top_html}</div>'
        f'{bottom}</div>'
    )


# ── 데이터 품질 pill (판정 기준 노출 + 호버 설명) ──────────────
SUSPECT_RULE = "suspect 기준: E_ad < -3 eV 또는 > +0.5 eV"


def quality_pill(n_suspect: int, has_rows: bool) -> str:
    """의심 값 건수를 드러내는 품질 pill. 호버 시 suspect 판정 기준을 보여준다."""
    if not has_rows:
        text, kind = "판정 대상 없음", "pending"
    elif n_suspect > 0:
        text, kind = f"의심 값 {n_suspect}건", "suspect"
    else:
        text, kind = "의심 값 0건", "ok"
    m = T.status_meta(kind)
    bg = _hex_to_rgba(m["color"], 0.12)
    # data-note는 CSS content:attr()로 그대로 출력되므로 <, >를 엔티티로 바꾸면
    # 화면에 그대로 노출된다. 속성 안전을 위해 큰따옴표(")와 &만 처리한다.
    note = SUSPECT_RULE.replace("&", "&amp;").replace('"', "&quot;")
    return (
        f'<span class="pill" data-note="{note}" tabindex="0" '
        f'style="background:{bg};color:{m["color"]};border-color:{_hex_to_rgba(m["color"], 0.25)}">'
        f'<span class="ico">{m["icon"]}</span>{html.escape(text)}</span>'
    )


# ── 시나리오 카드 (누가 어떻게 쓰나) ───────────────────────────
def scenario_card(icon_svg: str, role: str, title: str, use: str) -> str:
    return (
        f'<div class="scn-card">'
        f'<div class="scn-icon">{icon_svg}</div>'
        f'<div class="scn-role">{html.escape(role)}</div>'
        f'<div class="scn-title">{html.escape(title)}</div>'
        f'<div class="scn-use">{html.escape(use)}</div>'
        f'</div>'
    )


# ── 빈 상태 (일러스트 버전) ────────────────────────────────────
def empty_state_svg(svg: str, text: str, hint: str = ""):
    hint_html = f'<div class="hint" style="margin-top:4px">{html.escape(hint)}</div>' if hint else ""
    st.markdown(
        f'<div class="card"><div class="empty-state">{svg}'
        f'<div>{html.escape(text)}</div>{hint_html}</div></div>',
        unsafe_allow_html=True,
    )


# ── 조성 커버리지 (보고서 정의 7개 조성 vs composition_map) ────
#
# 보고서 정의 7개 조성의 표시명과 식별 키. is_covered 는 데이터(comp_map)에서만
# 판정하며, 어떤 값도 꾸며내지 않는다. 매핑 식별은 (xO,xF,xOH) 조성 좌표 기준.
REPORT_COMPOSITIONS: list[dict] = [
    {"name": "Ti2CO2",           "formula": "Ti₂CO₂",            "coord": (1.0, 0.0, 0.0)},
    {"name": "Ti2CF2",           "formula": "Ti₂CF₂",            "coord": (0.0, 1.0, 0.0)},
    {"name": "Ti2C(OH)2",        "formula": "Ti₂C(OH)₂",         "coord": (0.0, 0.0, 1.0)},
    {"name": "Ti2C(O0.5OH0.5)",  "formula": "Ti₂C(O₀.₅OH₀.₅)",   "coord": (0.5, 0.0, 0.5)},
    {"name": "Ti2C(O0.5F0.5)",   "formula": "Ti₂C(O₀.₅F₀.₅)",    "coord": (0.5, 0.5, 0.0)},
    {"name": "Ti2C(F0.5OH0.5)",  "formula": "Ti₂C(F₀.₅OH₀.₅)",   "coord": (0.0, 0.5, 0.5)},
    {"name": "삼원 혼합",         "formula": "O·F·OH 삼원 혼합",   "coord": None},
]


def _coord_matches(comp, target) -> bool:
    if target is None or comp is None:
        return False
    if comp.xO is None or comp.xF is None or comp.xOH is None:
        return False
    return (abs(comp.xO - target[0]) < 1e-6
            and abs(comp.xF - target[1]) < 1e-6
            and abs(comp.xOH - target[2]) < 1e-6)


def composition_coverage(comp_map: dict) -> list[dict]:
    """보고서 정의 7개 조성의 커버 상태를 반환한다 (데이터에서만 판정).

    각 항목: {name, formula, covered(bool), reason}
    covered=True 조건: comp_map에 해당 조성 좌표가 있고 confirmed=True.
    삼원 혼합(coord=None)은 세 성분이 모두 0 초과인 확정 표면이 있으면 covered.
    """
    confirmed = [c for c in comp_map.values()
                 if c.confirmed and c.xO is not None and c.xF is not None and c.xOH is not None]
    result = []
    for item in REPORT_COMPOSITIONS:
        coord = item["coord"]
        if coord is None:
            # 삼원 혼합: 세 성분 모두 > 0 인 확정 표면 존재 여부
            covered = any(c.xO > 0 and c.xF > 0 and c.xOH > 0 for c in confirmed)
            reason = "확정된 O·F·OH 삼원 혼합 표면 있음" if covered else "삼원 혼합 표면 계산 필요"
        else:
            covered = any(_coord_matches(c, coord) for c in confirmed)
            reason = "확정됨" if covered else "표면 계산 필요"
        result.append({"name": item["name"], "formula": item["formula"],
                       "covered": covered, "reason": reason})
    return result
