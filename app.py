"""배가스 맞춤형 Ti2C MXene AI-DFT 스크리닝 플랫폼 — Streamlit UI (한국어).

표현 레이어. core가 반환한 결과를 '표시'만 하며, 어떤 에너지 값도 하드코딩하지 않는다.
계산 가능 여부·suspect·pending 등 과학적 판단은 전부 core가 내린다.
디자인 시스템은 ui/ 패키지(토큰·CSS·컴포넌트·차트)에서 가져온다.
"""

from __future__ import annotations

import io
import os

import pandas as pd
import streamlit as st

from core.loader import load_energies, parse_rows, EnergyEntry
from core.units import ry_to_ev, RY_TO_EV
from core.metrics import selectivity_P, delta_d, load_geometry
from core.composition import load_composition_map, is_trainable
from core import registry
from core import gpr
from core.quality import loocv
from core.export import df_to_csv_bytes, ensure_provenance_columns, fig_to_png_bytes

from ui import theme
from ui import components as C
from ui import charts
from ui import tokens as T
from ui import illustrations as ILL
from ui import glossary
from ui import branding as B
from ui import landing
from ui import nav as NAV

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
ENERGIES_CSV = os.path.join(DATA_DIR, "energies.csv")
GEOMETRY_CSV = os.path.join(DATA_DIR, "geometry.csv")
COMP_CSV = os.path.join(DATA_DIR, "composition_map.csv")

GASES = ["CO2", "H2O", "SO2"]
P_METRICS = ["P(CO2/H2O)", "P(CO2/SO2)"]

st.set_page_config(
    page_title=B.PROJECT_TITLE,
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)
theme.inject()

# 발표 모드 CSS 클래스 (body에 present-mode 부여)
if st.session_state.get("present_mode"):
    st.markdown(
        "<style>.stApp {} </style>"
        "<script>document.body.classList.add('present-mode');</script>"
        '<div class="present-mode-flag"></div>',
        unsafe_allow_html=True,
    )
    # Streamlit은 iframe 구조라 body 클래스 대신 블록 컨테이너에 직접 적용
    st.markdown(
        "<style>section.main .block-container { font-size:1.15em; }"
        ".present-only-hide { display:none !important; }</style>",
        unsafe_allow_html=True,
    )


# ───────────────────────── 데이터 로딩 ─────────────────────────
def get_entries() -> tuple[list[EnergyEntry], list]:
    if "uploaded_entries" in st.session_state:
        return st.session_state["uploaded_entries"], st.session_state.get("uploaded_errors", [])
    res = load_energies(ENERGIES_CSV)
    return res.entries, res.errors


def fmt(x, nd=5):
    return "—" if x is None else f"{x:.{nd}f}"


entries, load_errors = get_entries()
comp_map = load_composition_map(COMP_CSV)
geom_map = load_geometry(GEOMETRY_CSV)


# ───────────────────────── 파생 통계 (표시용, core 호출) ─────────────────────────
def computed_ead_rows() -> list[dict]:
    """계산 가능한 모든 (표면,가스) E_ad를 모은다."""
    rows = []
    for s in registry.surfaces(entries):
        for g in GASES:
            r = registry.compute_ad_for(entries, s, g)
            if r.ok:
                rows.append({
                    "surface": s, "gas": g,
                    "e_ad_ev": r.E_ad_eV, "e_ad_ry": r.E_ad_Ry,
                    "suspect": r.suspect, "calc_group": r.calc_group,
                    "source": r.components["E_adsorbed"]["source_file"],
                })
    return rows


def metric_trainable_counts() -> dict[str, int]:
    """지표별 '지표가 실제 계산된 표면' 수. 세 지표(P 2종 + Δd) 모두 포함.

    - P(CO2/H2O), P(CO2/SO2): 해당 선택성 지표가 계산 가능한(ok) 조성 확정 표면 수.
    - Δd: geometry(z_before/z_after)로 Δd가 계산된 조성 확정 표면 수.
    지표가 pending인 표면은 세지 않는다. (요구사항 8.2, 8.6)
    """
    return {
        m: registry.count_trainable_for_metric(entries, comp_map, m, geom_map)
        for m in registry.ALL_METRICS
    }


METRIC_LABEL = {
    "P(CO2/H2O)": "P(CO₂/H₂O)",
    "P(CO2/SO2)": "P(CO₂/SO₂)",
    "Δd": "Δd",
}


def active_model_count() -> int:
    """유효 표면 수가 MIN_TRAINING 이상인 지표 모델 수 (0~3)."""
    counts = metric_trainable_counts()
    return sum(1 for m in registry.ALL_METRICS if counts[m] >= gpr.MIN_TRAINING)


# ───────────────────────── 시작 화면 분기 ─────────────────────────
if not st.session_state.get("entered"):
    landing.render(
        n_ead=len(computed_ead_rows()),
        n_models_active=active_model_count(),
        n_models_total=len(registry.ALL_METRICS),
    )
    st.stop()


def confirmed_composition_points() -> list[tuple[float, float, float]]:
    """조성 확정 표면들의 [xO,xF,xOH] 좌표 (삼각도 모티프에 점으로 표시)."""
    pts = []
    for c in comp_map.values():
        if c.confirmed and c.xO is not None and c.xF is not None and c.xOH is not None:
            pts.append((c.xO, c.xF, c.xOH))
    return pts


# ───────────────────────── 사이드바 (카테고리 내비) ─────────────────────────
with st.sidebar:
    tri = ILL.composition_triangle(size=22, points=confirmed_composition_points())
    st.markdown(
        f'<div class="sidebar-logo-row">{tri}'
        f'<span class="sidebar-logo">{B.wordmark(on_dark=False, size=16)}</span></div>'
        '<div class="sidebar-sub">Ti₂C MXene 표면 설계 플랫폼</div>',
        unsafe_allow_html=True,
    )
    # 로고(홈) 클릭 → 시작 화면 복귀
    if st.button("← 시작 화면으로", use_container_width=True):
        st.session_state["entered"] = False
        st.rerun()

    # 프로그램적 네비게이션 요청(_nav) 처리 → current_page 설정
    _nav_req = st.session_state.pop("_nav", None)
    if _nav_req in NAV.all_pages():
        st.session_state["current_page"] = _nav_req
        # 해당 카테고리 라디오 위젯 상태도 맞춰 둠
        st.session_state[f"navradio_{NAV.category_of(_nav_req)}"] = _nav_req

    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "Overview"

    def _on_pick(cat: str):
        st.session_state["current_page"] = st.session_state[f"navradio_{cat}"]

    # 카테고리별 그룹 헤더 + 라디오
    for cat, pages in NAV.CATEGORIES.items():
        st.markdown(
            f'<div class="nav-group">{NAV.CAT_ICONS[cat]} &nbsp;{cat} '
            f'<span style="font-weight:400;text-transform:none;letter-spacing:0">'
            f'· {NAV.CAT_DESC[cat]}</span></div>',
            unsafe_allow_html=True,
        )
        wkey = f"navradio_{cat}"
        cur = st.session_state["current_page"]
        idx = pages.index(cur) if cur in pages else None
        st.radio(
            cat, pages,
            index=idx,  # 현재 페이지가 이 카테고리에 없으면 선택 없음(None)
            label_visibility="collapsed", key=wkey,
            on_change=_on_pick, args=(cat,),
        )

    page = st.session_state["current_page"]

    st.markdown('<hr style="border:none;border-top:1px solid var(--ill-faint);margin:12px 0 4px">',
                unsafe_allow_html=True)

    # 데이터 상태 진행바 3줄 (0/7)
    counts = metric_trainable_counts()
    per_metric_html = "".join(
        f'<div style="margin-top:8px"><div class="hint">{METRIC_LABEL[m]} 모델</div>'
        f'{C.progress_bar(counts[m], gpr.MIN_TRAINING)}</div>'
        for m in registry.ALL_METRICS
    )
    st.markdown(
        f'<div class="data-summary">'
        f'<div class="kpi-label">데이터 상태</div>'
        f'<div style="margin:6px 0"><span class="mono">{len(registry.surfaces(entries))}</span> 표면 · '
        f'<span class="mono">{len(computed_ead_rows())}</span> E_ad 계산됨</div>'
        f'<div class="kpi-label" style="margin-top:10px">모델 학습 데이터 '
        f'<span class="hint">(계산된 표면 / {gpr.MIN_TRAINING})</span></div>'
        f'{per_metric_html}</div>',
        unsafe_allow_html=True,
    )

    # 발표 모드 토글
    st.session_state["present_mode"] = st.toggle(
        "발표 모드", value=st.session_state.get("present_mode", False),
        help="글자 확대·보조 설명 숨김. 데이터는 변경되지 않습니다.",
    )

    # 문서 영역
    st.markdown(
        '<div class="sidebar-docs">'
        '<div class="kpi-label">문서</div>'
        '<a href="https://github.com/seobin7070-code/ti2c-mxene-screening" '
        'target="_blank" rel="noopener">· README (GitHub)</a>'
        '</div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════ Overview ═══════════════════════
def _pipeline_steps(rows, counts):
    """파이프라인 4단계 상태를 데이터에서 계산한다 (꾸밈 없음)."""
    has_energy = len(entries) > 0
    has_ead = len(rows) > 0
    gpr_active = any(counts[m] >= gpr.MIN_TRAINING for m in registry.ALL_METRICS)

    def st_pair(done, waiting_ok=True):
        if done:
            return "ok", "완료"
        return ("pending", "대기") if waiting_ok else ("pending", "대기")

    s1 = ("ok", "완료") if has_energy else ("pending", "대기")
    s2 = ("ok", "완료") if has_ead else ("pending", "대기")
    s3 = ("ok", "완료") if gpr_active else ("pending", "잠금")
    s4 = ("ok", "완료") if gpr_active else ("pending", "잠금")
    return [
        {"title": "DFT 계산", "desc": "Quantum ESPRESSO · PBE-D3",
         "status": s1[0], "status_label": s1[1], "icon_svg": ILL.icon_dft()},
        {"title": "에너지·지표 산출", "desc": "E_ads · P · Δd",
         "status": s2[0], "status_label": s2[1], "icon_svg": ILL.icon_metrics()},
        {"title": "GPR 조성 공간 학습", "desc": "조성 → 지표 예측",
         "status": s3[0], "status_label": s3[1], "icon_svg": ILL.icon_gpr()},
        {"title": "Active Learning 추천", "desc": "다음 계산 지점 제안",
         "status": s4[0], "status_label": s4[1], "icon_svg": ILL.icon_al()},
    ]


def page_overview():
    rows = computed_ead_rows()
    counts = metric_trainable_counts()

    C.breadcrumb("홈", "Overview")

    # ── 히어로 (네이비→틸 그라데이션 + 우측 SVG) ──
    st.markdown(
        '<div class="hero"><div class="hero-left">'
        '<div class="hero-eyebrow">MXene 표면 설계 · AI-DFT 스크리닝</div>'
        '<div class="hero-title">배가스에서 유망한 Ti₂C MXene 표면 조성을<br>DFT와 AI로 탐색합니다</div>'
        '<div class="hero-desc">표면 말단기(-O/-F/-OH) 조성에 따라 CO₂·H₂O·SO₂ 흡착이 '
        '어떻게 달라지는지 DFT 계산 결과로부터 투명하게 산출하고, GPR 기반 Active Learning으로 '
        '조성 공간을 스캔해 다음에 계산할 지점을 제안하도록 설계되었습니다. '
        '모든 수치는 출처와 계산 조건(calc_group)까지 추적할 수 있습니다.</div>'
        '</div>'
        f'<div class="hero-right">{ILL.hero_mxene(animate=True)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    # 히어로 CTA (Streamlit 버튼)
    cta1, cta2, _ = st.columns([1, 1, 2])
    if cta1.button("정방향 검증 시작", use_container_width=True):
        st.session_state["_nav"] = "정방향 검증"
        st.rerun()
    if cta2.button("데이터 레지스트리 보기", use_container_width=True):
        st.session_state["_nav"] = "데이터 레지스트리"
        st.rerun()

    # ── 누가 어떻게 쓰나 (3 시나리오) ──
    C.section_head(ILL.icon_al(), "누가 어떻게 쓰나")
    st.caption("아래는 이 플랫폼이 상정한 사용 용도입니다 (도입 사례·성능 수치가 아닙니다).")
    sc1, sc2, sc3 = st.columns(3)
    sc1.markdown(C.scenario_card(
        ILL.icon_metrics(), "공정·제조 R&D", "석유화학·제조 엔지니어",
        "내 배가스 조건에서 어떤 표면이 유망한지 결론 카드와 흡착 에너지로 빠르게 비교하도록 설계."),
        unsafe_allow_html=True)
    sc2.markdown(C.scenario_card(
        ILL.icon_gpr(), "소재 설계", "화학·소재 기업 연구원",
        "조성 삼각도와 추천 후보로 합성 방향(말단기 비율)을 탐색하도록 설계."),
        unsafe_allow_html=True)
    sc3.markdown(C.scenario_card(
        ILL.icon_dft(), "방법론·재현성", "대학·연구기관",
        "계산 조건·출처·수식을 투명하게 공개해 재현성과 방법론을 확인하도록 설계."),
        unsafe_allow_html=True)

    # ── 파이프라인 ──
    C.section_head(ILL.icon_gpr(), "분석 파이프라인")
    st.markdown(ILL.pipeline(_pipeline_steps(rows, counts)), unsafe_allow_html=True)

    # ── KPI 4개 (높이 통일) ──
    C.section_head(ILL.icon_metrics(), "현재 데이터 상태")
    n_suspect = sum(1 for r in rows if r["suspect"])
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(C.kpi_equal(
        "등록된 표면",
        f'<div class="kpi-value">{len(registry.surfaces(entries))}</div>'), unsafe_allow_html=True)
    c2.markdown(C.kpi_equal(
        C.info_tooltip("E_ads", "계산 가능한 E_ads"),
        f'<div class="kpi-value">{len(rows)}</div>'), unsafe_allow_html=True)
    metric_bars = "".join(
        f'<div style="margin-top:8px"><div class="hint">{METRIC_LABEL[m]}</div>'
        f'{C.progress_bar(counts[m], gpr.MIN_TRAINING)}</div>'
        for m in registry.ALL_METRICS
    )
    c3.markdown(C.kpi_equal(
        "모델 학습 데이터",
        '<div class="hint" style="margin-top:2px">지표가 계산된 표면 수 / '
        f'{gpr.MIN_TRAINING}</div>',
        bottom_html=metric_bars), unsafe_allow_html=True)
    c4.markdown(C.kpi_equal(
        "데이터 품질",
        f'<div style="margin-top:8px">{C.quality_pill(n_suspect, bool(rows))}</div>'
        '<div class="hint" style="margin-top:8px">마우스를 올리면 판정 기준이 표시됩니다.</div>'),
        unsafe_allow_html=True)

    # ── E_ad 막대차트 + PNG 다운로드 ──
    C.section_head(ILL.icon_metrics(), "계산 완료된 흡착 에너지")
    if rows:
        st.plotly_chart(charts.ead_bar(rows), use_container_width=True)
        try:
            png = fig_to_png_bytes(charts.ead_bar_png(rows))
            st.download_button("차트 PNG 다운로드", data=png,
                               file_name="ead_chart.png", mime="image/png")
        except Exception:
            st.caption("PNG 내보내기를 사용할 수 없습니다 (kaleido 미설치).")
    else:
        C.empty_state_svg(ILL.empty_chart(), "아직 계산 가능한 E_ad가 없습니다.",
                          "데이터 레지스트리에서 clean·molecule·adsorbed 에너지를 추가하세요.")

    # ── 다음에 필요한 계산 (조성 커버리지 우선) ──
    C.section_head(ILL.icon_dft(), "다음에 필요한 계산")
    coverage = C.composition_coverage(comp_map)
    not_covered = [c for c in coverage if not c["covered"]]
    cov_html = (
        f'<div style="padding:4px 0 8px;border-bottom:1px solid {T.BORDER};margin-bottom:6px">'
        f'<b style="font-size:13px">조성 커버리지</b> '
        f'<span class="hint">보고서 정의 7개 조성 중 '
        f'{len(coverage) - len(not_covered)}/{len(coverage)} 확정</span></div>'
    )
    if not_covered:
        cov_html += "".join(
            f'<div style="display:flex;gap:10px;padding:6px 0">'
            f'{C.status_pill("pending", "표면 계산 필요")}'
            f'<span style="font-size:13px"><b>{c["formula"]}</b> '
            f'<span class="hint">({c["name"]})</span></span></div>'
            for c in not_covered
        )
    else:
        cov_html += ('<div class="hint" style="padding:6px 0">보고서 정의 7개 조성이 모두 '
                     '확정되었습니다.</div>')

    # 에너지 누락 체크리스트 (전역 우선)
    missing = registry.missing_checklist(entries)
    missing_sorted = sorted(missing, key=lambda m: 0 if m.scope == "전역" else 1)
    miss_html = (
        f'<div style="padding:10px 0 8px;border-top:1px solid {T.BORDER};'
        f'border-bottom:1px solid {T.BORDER};margin:8px 0 6px">'
        f'<b style="font-size:13px">에너지 데이터 누락</b></div>'
    )
    if missing_sorted:
        miss_html += "".join(
            f'<div style="display:flex;gap:10px;padding:6px 0">'
            f'{C.status_pill("pending", "필요")}'
            f'<span style="font-size:13px"><b>{m.scope}</b> — {m.detail}</span></div>'
            for m in missing_sorted[:10]
        )
    else:
        miss_html += '<div class="hint" style="padding:6px 0">누락 항목 없음.</div>'

    C.card(cov_html + miss_html)

    # ── 방법론 한눈에 (연구기관용, 접이식) ──
    st.markdown('<div id="방법론-한눈에"></div>', unsafe_allow_html=True)
    with st.expander("방법론 한눈에 (소프트웨어 · 범함수 · 지표 정의)"):
        st.markdown(
            f'<div class="hint" style="line-height:1.9">'
            f'<b>소프트웨어</b>: Quantum ESPRESSO<br>'
            f'<b>범함수 / 분산보정</b>: PBE-D3<br>'
            f'<b>단위 변환</b>: 1 Ry = {RY_TO_EV} eV<br><br>'
            f'<b>지표 정의</b><br>'
            f'· {C.info_tooltip("E_ads", "E_ads")} = E_adsorbed − (E_clean + E_molecule)<br>'
            f'· {C.info_tooltip("Preference Index", "P(CO₂/H₂O)")} = E_ads(H₂O) − E_ads(CO₂)<br>'
            f'· {C.info_tooltip("Δd_surface", "Δd_surface")} = |mean(z_after) − mean(z_before)|'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.caption("서로 다른 calc_group의 값은 섞어서 계산하지 않습니다.")

    # ── 기능 둘러보기 (6개 카테고리 카드) ──
    C.section_head(NAV.CAT_ICONS["자료"], "기능 둘러보기")
    cats = list(NAV.CATEGORIES.keys())
    row1 = st.columns(3)
    row2 = st.columns(3)
    cols = row1 + row2
    for col, cat in zip(cols, cats):
        first_page = NAV.CATEGORIES[cat][0]
        n_pages = len(NAV.CATEGORIES[cat])
        col.markdown(
            f'<div class="cat-card"><div class="cc-ic">{NAV.CAT_ICONS[cat]}</div>'
            f'<div class="cc-title">{cat}</div>'
            f'<div class="cc-desc">{NAV.CAT_DESC[cat]} · {n_pages}개 페이지</div></div>',
            unsafe_allow_html=True,
        )
        if col.button(f"{cat} 열기", key=f"catbtn_{cat}", use_container_width=True):
            st.session_state["_nav"] = first_page
            st.rerun()

    C.footer()


# ═══════════════════════ 정방향 검증 ═══════════════════════
def page_forward():
    C.page_header_bc("분석", "정방향 검증",
                     "표면과 가스를 선택하면 계산 가능한 흡착 에너지와 선택성 지표를 보여줍니다.")

    surf_list = registry.surfaces(entries)
    if not surf_list:
        C.empty_state("🧪", "표면 데이터가 없습니다.", "데이터 레지스트리에서 추가하세요.")
        C.footer()
        return

    left, right = st.columns([1, 2], gap="large")
    with left:
        C.section_title("입력")
        surface = st.selectbox("표면", surf_list)
        gas = st.selectbox("가스", GASES, format_func=lambda g: T.gas_meta(g)["label"])
        comp = comp_map.get(surface)
        # 선택한 표면의 말단기 구성 모식도
        st.markdown(
            f'<div class="card card-tight" style="margin-top:6px">'
            f'<div class="kpi-label">표면 말단기 구성</div>'
            f'{ILL.surface_motif(comp)}</div>',
            unsafe_allow_html=True,
        )
        if comp is not None and not is_trainable(comp):
            st.markdown(C.status_pill("pending", "조성 미확정 (OH 환산 확인 필요)"),
                        unsafe_allow_html=True)

    with right:
        C.section_title(f"결과 — {T.gas_meta(gas)['label']} on {surface}")
        r = registry.compute_ad_for(entries, surface, gas)

        if not r.ok:
            C.notice("pending", "계산할 수 없습니다 (pending)", r.reason)
        else:
            label, kind = C.adsorption_interpretation(r.E_ad_eV)
            C.card(
                f'<div class="kpi-label">흡착 에너지 (E_ads)</div>'
                f'<div class="hero-value" style="color:{T.PRIMARY}">{r.E_ad_eV:.3f}'
                f'<span class="hero-unit">eV</span></div>'
                f'<div class="mono hint" style="margin-top:2px">{r.E_ad_Ry:.5f} Ry</div>'
                f'<div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">'
                f'{C.status_pill(kind, label)}'
                + (C.status_pill("suspect", "suspect: 비현실적 범위") if r.suspect else "")
                + f'{C.status_pill("ok", "계산됨")}</div>'
                + '<div class="hint" style="margin-top:10px">※ 분류 기준은 본 플랫폼의 '
                  '가정이며 문헌 기준이 아님.</div>'
            )
            with st.expander("해석 배지 분류 기준 보기"):
                st.markdown(C.interpretation_legend_html(), unsafe_allow_html=True)
            if r.suspect:
                C.notice("suspect", "의심값 경고",
                         "E_ad가 물리적으로 비현실적 범위([-3, +0.5] eV)를 벗어났습니다. 입력 데이터를 재확인하세요.")

            with st.expander("계산 과정 보기 (세 에너지 값 · 뺄셈 식 · Ry→eV 변환)"):
                comps = r.components
                drows = []
                for lbl, key in [("E_adsorbed", "E_adsorbed"), ("E_clean", "E_clean"),
                                 ("E_molecule", "E_molecule")]:
                    cc = comps.get(key)
                    if cc:
                        drows.append({
                            "항목": lbl,
                            "energy_Ry": cc["energy_Ry"],
                            "energy_eV": ry_to_ev(cc["energy_Ry"]),
                            "source_file": cc["source_file"],
                            "calc_group": cc["calc_group"],
                        })
                st.dataframe(pd.DataFrame(drows), width='stretch', hide_index=True)
                st.markdown(
                    f'<div class="hint" style="line-height:1.9">'
                    f'<b>식:</b> E_ad = E_adsorbed − (E_clean + E_molecule)<br>'
                    f'= <span class="mono">{r.E_ad_Ry:.5f}</span> Ry '
                    f'= <span class="mono">{r.E_ad_Ry:.5f} × {RY_TO_EV}</span> '
                    f'= <span class="mono" style="color:{T.PRIMARY};font-weight:600">{r.E_ad_eV:.3f} eV</span><br>'
                    f'calc_group = <span class="mono">{r.calc_group}</span> (세 값 모두 동일 확인됨)'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                srcs = "".join(
                    C.source_chip(comps[k]["source_file"], comps[k]["calc_group"]) + " "
                    for k in ("E_adsorbed", "E_clean", "E_molecule") if comps.get(k)
                )
                st.markdown(f'<div style="margin-top:8px">{srcs}</div>', unsafe_allow_html=True)

        # 선택성 지표
        st.markdown(
            '<div class="section-title">선택성 지표 '
            f'({C.info_tooltip("Preference Index", "Preference Index")})</div>',
            unsafe_allow_html=True,
        )
        e_co2 = registry.compute_ad_for(entries, surface, "CO2")
        e_h2o = registry.compute_ad_for(entries, surface, "H2O")
        e_so2 = registry.compute_ad_for(entries, surface, "SO2")
        p_h2o = selectivity_P("P(CO2/H2O)", e_h2o, e_co2, "H2O")
        p_so2 = selectivity_P("P(CO2/SO2)", e_so2, e_co2, "SO2")
        dd = delta_d(geom_map.get((surface, "SO2")))

        def metric_line(name, ok, value_ev, value_ry, reason, cg):
            if ok:
                return (f'<div style="padding:8px 0;border-bottom:1px solid {T.BORDER}">'
                        f'<b>{name}</b> &nbsp;'
                        f'<span class="mono" style="color:{T.PRIMARY}">{value_ev:.3f} eV</span> '
                        f'<span class="mono hint">({value_ry:.5f} Ry)</span> &nbsp;'
                        f'{C.status_pill("ok", "group " + str(cg))}</div>')
            return (f'<div style="padding:8px 0;border-bottom:1px solid {T.BORDER}">'
                    f'<b>{name}</b> &nbsp;{C.status_pill("pending", "pending")} '
                    f'<span class="hint">{reason}</span></div>')

        html_block = (
            metric_line("P(CO₂/H₂O)", p_h2o.ok, p_h2o.value_eV, p_h2o.value_Ry, p_h2o.reason, p_h2o.calc_group)
            + metric_line("P(CO₂/SO₂)", p_so2.ok, p_so2.value_eV, p_so2.value_Ry, p_so2.reason, p_so2.calc_group)
        )
        if dd.ok:
            html_block += (f'<div style="padding:8px 0"><b>Δd_surface</b> &nbsp;'
                           f'<span class="mono" style="color:{T.PRIMARY}">{dd.value:.4f}</span> &nbsp;'
                           f'{C.source_chip(dd.source_file, dd.calc_group)}</div>')
        else:
            html_block += (f'<div style="padding:8px 0"><b>Δd_surface</b> &nbsp;'
                           f'{C.status_pill("pending", "pending")} '
                           f'<span class="hint">{dd.reason}</span></div>')
        C.card(html_block)

    C.footer()


# ═══════════════════════ 역방향 추천 ═══════════════════════
def page_reverse():
    C.breadcrumb("설계", "역방향 추천")
    # 헤더에 삼각도 모티프 (현재 확정 조성 좌표를 점으로)
    tri = ILL.composition_triangle(size=30, points=confirmed_composition_points())
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px">{tri}'
        f'<div class="page-title">역방향 추천</div></div>'
        '<div class="page-sub">'
        f'{C.info_tooltip("GPR", "GPR")}이 조성 삼각 공간을 스캔해 최적 조성 후보와 '
        f'{C.info_tooltip("Active Learning", "다음 계산 지점")}을 추천합니다.</div>',
        unsafe_allow_html=True,
    )
    C.notice("info", gpr.SIGMA_DISCLAIMER)

    # 지표별 모델 상태 — 세 지표(P 2종 + Δd)를 동일 로직으로 처리
    models, scans = {}, {}
    status_html = ""
    for metric in registry.ALL_METRICS:
        pts = registry.trainable_points_for_metric(entries, comp_map, metric, geom_map)
        model = gpr.fit_metric_model(pts, metric)
        label = METRIC_LABEL[metric]
        if isinstance(model, gpr.GprUnavailable):
            status_html += (f'<div style="padding:6px 0">{label} &nbsp;'
                            f'{C.status_pill("pending", model.message)}</div>')
        else:
            models[metric] = model
            scans[metric] = gpr.scan_ternary(model, step=20)
            status_html += (f'<div style="padding:6px 0">{label} &nbsp;'
                            f'{C.status_pill("ok", f"활성 (N={model.n})")}</div>')

    C.section_title("지표별 모델 상태")
    C.card(status_html)

    if not models:
        # 데이터 부족: 흐린 삼각도 미리보기 + 자물쇠 + 진행바 + "N개 더 필요"
        counts = metric_trainable_counts()
        best = max(counts.values()) if counts else 0
        need_more = max(0, gpr.MIN_TRAINING - best)
        blur_tri = ILL.composition_triangle(size=120, points=confirmed_composition_points())
        bars = "".join(
            f'<div style="margin-top:8px;text-align:left"><div class="hint">{METRIC_LABEL[m]} '
            f'<span class="hint">({max(0, gpr.MIN_TRAINING - counts[m])}개 더 필요)</span></div>'
            f'{C.progress_bar(counts[m], gpr.MIN_TRAINING)}</div>'
            for m in registry.ALL_METRICS
        )
        C.section_head(ILL.icon_gpr(), "조성 공간 미리보기")
        st.markdown(
            '<div class="card" style="text-align:center">'
            f'<div class="locked" style="display:inline-block">{blur_tri}</div>'
            f'<div style="margin-top:4px">{ILL.empty_locked()}</div>'
            f'<div style="font-weight:600">조성 스캔 잠김</div>'
            f'<div class="hint" style="margin:4px 0 12px">가장 진척된 지표 기준으로 '
            f'데이터가 <b>{need_more}개 더 필요</b>합니다. 각 지표가 계산된 표면이 '
            f'{gpr.MIN_TRAINING}개에 도달하면 해당 지표의 삼각 조성도와 추천이 활성화됩니다.</div>'
            f'<div style="max-width:420px;margin:0 auto">{bars}</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        C.footer()
        return

    # 활성화: ternary + 추천
    for metric, scan in scans.items():
        C.section_title(f"조성 공간 스캔 — {metric}")
        st.plotly_chart(charts.ternary_scan(scan.grid, scan.mu, scan.sigma, metric),
                        use_container_width=True)
        cand = gpr.next_al_candidate(scan)
        comp_str = ", ".join(f"{x:.2f}" for x in cand["composition"])
        C.card(
            f'<div class="kpi-label">Active Learning 다음 계산 후보 (σ 최대)</div>'
            f'<div style="margin-top:6px">{C.status_pill("info", "추천 측정 지점")} '
            f'<span class="mono">[xO,xF,xOH] = [{comp_str}]</span> &nbsp;'
            f'<span class="mono hint">μ={cand["mu"]:.3f} · σ={cand["sigma"]:.3f}</span></div>',
            tight=True,
        )

    # Pareto
    C.section_title("추천 조성 (Pareto 상위)")
    front = gpr.pareto_front(scans)
    if front:
        cols = st.columns(min(3, len(front)))
        for i, cand in enumerate(front[:3]):
            comp_str = ", ".join(f"{x:.2f}" for x in cand["composition"])
            metrics_html = "<br>".join(
                f'<span class="hint">{k}:</span> <span class="mono">{v:.3f}</span>'
                for k, v in cand.items() if k != "composition"
            )
            cols[i].markdown(
                f'<div class="card"><div class="kpi-label">후보 #{i+1}</div>'
                f'<div class="mono" style="font-size:15px;margin:6px 0;color:{T.PRIMARY}">[{comp_str}]</div>'
                f'{metrics_html}</div>',
                unsafe_allow_html=True,
            )
        st.caption("활성화된 지표만 Pareto 목적함수에 포함됩니다.")

    C.footer()


# ═══════════════════════ 모델 품질 ═══════════════════════
def page_quality():
    C.breadcrumb("모델", "모델 품질")
    st.markdown(
        '<div class="page-title">모델 품질</div>'
        f'<div class="page-sub">{C.info_tooltip("LOOCV", "LOOCV")}로 실제 계산된 성능 수치만 '
        '표시합니다. 추정값은 쓰지 않습니다.</div>',
        unsafe_allow_html=True,
    )
    # 지표 3개 각각 별도로 표시: ok면 KPI + parity plot, 아니면 빈 상태 카드
    for metric in registry.ALL_METRICS:
        pts = registry.trainable_points_for_metric(entries, comp_map, metric, geom_map)
        q = loocv(pts, metric)
        C.section_title(METRIC_LABEL[metric])
        if not q.ok:
            C.empty_state_svg(ILL.empty_chart(), f"데이터 {gpr.MIN_TRAINING}개 이상 필요",
                              f"현재 {q.n}개 — LOOCV로 성능을 계산하려면 "
                              f"지표가 계산된 표면이 {gpr.MIN_TRAINING}개 이상이어야 합니다.")
            continue
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(C.kpi_card("학습 데이터", str(q.n), "개"), unsafe_allow_html=True)
        c2.markdown(C.kpi_card("MAE", f"{q.mae:.4f}", "eV"), unsafe_allow_html=True)
        c3.markdown(C.kpi_card("RMSE", f"{q.rmse:.4f}", "eV"), unsafe_allow_html=True)
        c4.markdown(C.kpi_card("R²", f"{q.r2:.4f}"), unsafe_allow_html=True)
        # 예측-실측 parity plot (LOOCV ok일 때만)
        st.plotly_chart(
            charts.parity_plot(q.y_true, q.y_pred, METRIC_LABEL[metric]),
            use_container_width=True,
        )
    C.footer()


# ═══════════════════════ 데이터 레지스트리 ═══════════════════════
def page_registry_view():
    C.page_header_bc("데이터", "데이터 레지스트리",
                     "모든 에너지 항목·출처·calc_group·상태를 확인하고, CSV로 새 데이터를 반영합니다.")

    # 데이터 신뢰 원칙 3줄 카드
    st.markdown(
        '<div class="trust-card">'
        '<div class="kpi-label" style="margin-bottom:6px">데이터 신뢰 원칙</div>'
        '<div class="trust-item"><span class="ti-ic">✓</span>'
        '<span>모든 값은 <span class="mono">data/energies.csv</span>에서 읽으며, 코드에 '
        '하드코딩하지 않습니다.</span></div>'
        '<div class="trust-item"><span class="ti-ic">✓</span>'
        f'<span>모든 수치에 출처(source_file)와 {C.info_tooltip("calc_group", "calc_group")}을 '
        '함께 표시합니다.</span></div>'
        '<div class="trust-item"><span class="ti-ic">✓</span>'
        '<span>서로 다른 calc_group의 값은 섞지 않고 계산을 거부합니다.</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if load_errors:
        C.notice("suspect", "로드 중 거부된 행이 있습니다",
                 "스키마를 위반한 행은 반영되지 않았습니다. 아래 표에서 사유를 확인하세요.")
        st.dataframe(pd.DataFrame([{"행": e.row_index, "사유": e.reason} for e in load_errors]),
                     width='stretch', hide_index=True)

    # 상태 요약 pill
    n_ok = sum(1 for e in entries if e.status == "ok")
    n_pending = sum(1 for e in entries if e.status == "pending")
    n_suspect = sum(1 for e in entries if e.status == "suspect")
    st.markdown(
        '<div style="display:flex;gap:8px;margin-bottom:12px">'
        + C.status_pill("ok", f"ok {n_ok}") + C.status_pill("pending", f"pending {n_pending}")
        + C.status_pill("suspect", f"suspect {n_suspect}") + '</div>',
        unsafe_allow_html=True,
    )

    # 검색/필터
    C.section_title("에너지 항목")
    f1, f2, f3 = st.columns([2, 1, 1])
    query = f1.text_input("검색 (key · 표면 · 파일명)", "")
    role_filter = f2.selectbox("role", ["전체", "molecule", "clean", "adsorbed"])
    group_filter = f3.selectbox("calc_group", ["전체"] + sorted({e.calc_group for e in entries}))

    def match(e):
        if query and query.lower() not in f"{e.key} {e.surface} {e.gas} {e.source_file}".lower():
            return False
        if role_filter != "전체" and e.role != role_filter:
            return False
        if group_filter != "전체" and e.calc_group != group_filter:
            return False
        return True

    filtered = [e for e in entries if match(e)]

    # calc_group별 그룹 헤더로 묶어 표시
    if filtered:
        for cg in sorted({e.calc_group for e in filtered}):
            grp = [e for e in filtered if e.calc_group == cg]
            st.markdown(
                f'<div style="margin:14px 0 6px"><span class="pill" '
                f'style="background:#F1F5F9;color:{T.TEXT};'
                f'border-color:{T.BORDER}">calc_group {cg}</span> '
                f'<span class="hint">{len(grp)}개 항목</span></div>',
                unsafe_allow_html=True,
            )
            df = pd.DataFrame([{
                "key": e.key, "role": e.role, "surface": e.surface, "gas": e.gas,
                "energy_Ry": e.energy_Ry, "energy_eV": ry_to_ev(e.energy_Ry),
                "source_file": e.source_file, "status": e.status,
            } for e in grp])
            st.dataframe(df, width='stretch', hide_index=True)
        # 다운로드
        all_df = pd.DataFrame([{
            "key": e.key, "role": e.role, "surface": e.surface, "gas": e.gas,
            "energy_Ry": e.energy_Ry, "energy_eV": ry_to_ev(e.energy_Ry),
            "source_file": e.source_file, "calc_group": e.calc_group, "status": e.status,
        } for e in filtered])
        st.download_button("필터된 결과 CSV 다운로드",
                           data=df_to_csv_bytes(ensure_provenance_columns(all_df)),
                           file_name="energies_registry.csv", mime="text/csv")
    else:
        C.empty_state("🔍", "조건에 맞는 항목이 없습니다.", "검색어나 필터를 바꿔보세요.")

    # 조성 매핑
    C.section_title("조성 매핑")
    comp_rows = [{
        "surface": s, "xO": c.xO, "xF": c.xF, "xOH": c.xOH, "confirmed": c.confirmed,
        "상태": "학습 가능" if is_trainable(c) else "조성 미확정",
    } for s, c in comp_map.items()]
    if comp_rows:
        st.dataframe(pd.DataFrame(comp_rows), width='stretch', hide_index=True)

    # 누락 체크리스트
    C.section_title("계산에 필요하지만 아직 없는 항목")
    missing = registry.missing_checklist(entries)
    if missing:
        st.dataframe(pd.DataFrame([{"범위": m.scope, "누락 내용": m.detail} for m in missing]),
                     width='stretch', hide_index=True)
    else:
        C.notice("ok", "누락 항목이 없습니다.")

    # 업로드 (드래그앤드롭)
    C.section_title("CSV 업로드 / 추가")
    st.caption("업로드한 CSV는 스키마 검증을 통과해야만 반영됩니다. 코드 수정 없이 데이터가 반영됩니다.")
    up = st.file_uploader("energies.csv 형식 파일을 끌어다 놓으세요", type=["csv"])
    if up is not None:
        content = up.read().decode("utf-8")
        reader = pd.read_csv(io.StringIO(content), dtype=str, keep_default_na=False)
        res = parse_rows(list(reader.columns), reader.to_dict(orient="records"))
        if res.errors:
            C.notice("suspect", "스키마 위반으로 반영이 거부되었습니다")
            st.dataframe(pd.DataFrame([{"행": e.row_index, "사유": e.reason} for e in res.errors]),
                         width='stretch', hide_index=True)
        else:
            st.session_state["uploaded_entries"] = res.entries
            st.session_state["uploaded_errors"] = []
            C.notice("ok", f"{len(res.entries)}개 항목이 반영되었습니다.",
                     "페이지를 새로고침하면 전체에 적용됩니다.")
    if "uploaded_entries" in st.session_state:
        if st.button("업로드 데이터 지우고 기본 CSV로 복귀"):
            del st.session_state["uploaded_entries"]
            st.session_state.pop("uploaded_errors", None)
            st.rerun()

    C.footer()


# ═══════════════════════ Phase 2에서 구현될 신규 페이지 (현재는 준비 중) ═══════
def _placeholder(category: str, title: str, desc: str):
    C.page_header_bc(category, title, desc)
    C.empty_state_svg(
        ILL.empty_waiting(), "준비 중입니다.",
        "이 페이지는 다음 단계(Phase 2)에서 제공됩니다. "
        "데이터가 없는 기능은 대기/잠금으로 표시됩니다.",
    )
    C.footer()


def page_surface_compare():
    C.page_header_bc("분석", "표면 비교",
                     "표면 2~4개와 가스를 골라 흡착 에너지를 나란히 비교합니다.")
    surf_list = registry.surfaces(entries)
    if not surf_list:
        C.empty_state_svg(ILL.empty_chart(), "표면 데이터가 없습니다.",
                          "데이터 레지스트리에서 추가하세요.")
        C.footer()
        return

    c1, c2 = st.columns([2, 1])
    picked = c1.multiselect("표면 선택 (2~4개)", surf_list,
                            default=surf_list[:min(4, len(surf_list))], max_selections=4)
    gas = c2.selectbox("가스", GASES, format_func=lambda g: T.gas_meta(g)["label"])

    if len(picked) < 2:
        C.notice("info", "표면을 2개 이상 선택하세요.")
        C.footer()
        return

    # 각 표면 E_ad 계산 (불가 시 사유)
    results = []
    for s in picked:
        r = registry.compute_ad_for(entries, s, gas)
        results.append({"surface": s, "r": r})

    ok_rows = [{"surface": x["surface"], "e_ad_ev": x["r"].E_ad_eV}
               for x in results if x["r"].ok]

    # 막대 (계산된 것만)
    C.section_head(ILL.icon_metrics(), f"흡착 에너지 — {T.gas_meta(gas)['label']}")
    if ok_rows:
        st.plotly_chart(charts.surface_compare_bar(ok_rows, gas), use_container_width=True)
    else:
        C.notice("pending", "선택한 표면 중 계산 가능한 E_ad가 없습니다.")

    # 표 (빈칸 + 사유 pill)
    rows_html = ""
    for x in results:
        s, r = x["surface"], x["r"]
        if r.ok:
            label, kind = C.adsorption_interpretation(r.E_ad_eV)
            cell = (f'<span class="mono" style="color:{T.PRIMARY}">{r.E_ad_eV:.3f} eV</span> '
                    f'<span class="mono hint">({r.E_ad_Ry:.5f} Ry)</span> '
                    f'{C.status_pill(kind, label)}')
        else:
            cell = f'{C.status_pill("pending", "계산 불가")} <span class="hint">{r.reason}</span>'
        rows_html += (f'<div style="display:flex;gap:10px;padding:8px 0;'
                      f'border-bottom:1px solid {T.BORDER}"><b style="min-width:120px">{s}</b>'
                      f'<span>{cell}</span></div>')
    C.card(rows_html)

    # CSV / PNG 다운로드
    df = pd.DataFrame([{
        "surface": x["surface"], "gas": gas,
        "E_ad_eV": (round(x["r"].E_ad_eV, 4) if x["r"].ok else ""),
        "E_ad_Ry": (round(x["r"].E_ad_Ry, 8) if x["r"].ok else ""),
        "status": ("ok" if x["r"].ok else "pending"),
        "reason": ("" if x["r"].ok else x["r"].reason),
        "calc_group": (x["r"].calc_group if x["r"].ok else ""),
    } for x in results])
    dc1, dc2 = st.columns(2)
    dc1.download_button("비교 표 CSV 다운로드", data=df_to_csv_bytes(df),
                        file_name="surface_compare.csv", mime="text/csv")
    if ok_rows:
        try:
            png = fig_to_png_bytes(charts.surface_compare_bar(ok_rows, gas, png=True))
            dc2.download_button("비교 차트 PNG 다운로드", data=png,
                                file_name="surface_compare.png", mime="image/png")
        except Exception:
            dc2.caption("PNG 내보내기를 사용할 수 없습니다.")
    C.footer()


def page_competitive():
    C.page_header_bc("분석", "경쟁 흡착 비교",
                     "표면별 CO₂/H₂O/SO₂ 흡착과 선택성을 함께 비교합니다.")
    surf_list = registry.surfaces(entries)
    if not surf_list:
        C.empty_state_svg(ILL.empty_chart(), "표면 데이터가 없습니다.",
                          "데이터 레지스트리에서 추가하세요.")
        C.footer()
        return

    # 표면별 가스별 E_ad
    by_surface = {}
    for s in surf_list:
        by_surface[s] = {}
        for g in GASES:
            r = registry.compute_ad_for(entries, s, g)
            if r.ok:
                by_surface[s][g] = r.E_ad_eV

    C.section_head(ILL.icon_metrics(), "가스별 흡착 에너지")
    if any(by_surface[s] for s in surf_list):
        st.plotly_chart(charts.competitive_bar(by_surface), use_container_width=True)
        try:
            png = fig_to_png_bytes(charts.competitive_bar(by_surface, png=True))
            st.download_button("경쟁 흡착 PNG 다운로드", data=png,
                               file_name="competitive.png", mime="image/png")
        except Exception:
            st.caption("PNG 내보내기를 사용할 수 없습니다.")
    else:
        C.notice("pending", "계산 가능한 E_ad가 아직 없습니다.")

    # 선택성 지표 (세 가스 모두 있을 때만)
    C.section_head(ILL.icon_gpr(), "선택성 지표")
    sel_html = ""
    for s in surf_list:
        e_co2 = registry.compute_ad_for(entries, s, "CO2")
        e_h2o = registry.compute_ad_for(entries, s, "H2O")
        e_so2 = registry.compute_ad_for(entries, s, "SO2")
        p_h2o = selectivity_P("P(CO2/H2O)", e_h2o, e_co2, "H2O")
        p_so2 = selectivity_P("P(CO2/SO2)", e_so2, e_co2, "SO2")

        def cell(p):
            if p.ok:
                return f'<span class="mono" style="color:{T.PRIMARY}">{p.value_eV:.3f} eV</span>'
            return f'{C.status_pill("pending", "pending")} <span class="hint">{p.reason}</span>'
        sel_html += (f'<div style="padding:8px 0;border-bottom:1px solid {T.BORDER}">'
                     f'<b>{s}</b><br>'
                     f'<span class="hint">P(CO₂/H₂O):</span> {cell(p_h2o)} &nbsp; '
                     f'<span class="hint">P(CO₂/SO₂):</span> {cell(p_so2)}</div>')
    C.card(sel_html)

    # 계산 커버리지 매트릭스 (표면 × 가스)
    C.section_head(ILL.icon_dft(), "계산 커버리지 매트릭스")
    header = ('<tr><th style="text-align:left;padding:6px 10px">표면</th>'
              + "".join(f'<th style="padding:6px 10px">{T.gas_meta(g)["label"]}</th>'
                        for g in GASES) + "</tr>")
    body = ""
    for s in surf_list:
        cells = f'<td style="padding:6px 10px"><b>{s}</b></td>'
        for g in GASES:
            r = registry.compute_ad_for(entries, s, g)
            pill = (C.status_pill("ok", "계산됨") if r.ok
                    else C.status_pill("pending", "대기"))
            cells += f'<td style="padding:6px 10px;text-align:center">{pill}</td>'
        body += f"<tr>{cells}</tr>"
    st.markdown(
        f'<div class="card"><table style="width:100%;border-collapse:collapse;font-size:13px">'
        f'{header}{body}</table></div>',
        unsafe_allow_html=True,
    )
    C.footer()


def page_flue_gas():
    _placeholder("설계", "배가스 조건 설정", "시나리오 메모와 사용자 우선순위를 설정합니다.")


def page_out_inspector():
    _placeholder("데이터", ".out 파일 검사기", "Quantum ESPRESSO 출력 파일을 파싱·검증합니다.")


def page_jobs():
    _placeholder("데이터", "계산 작업 관리", "계산 작업 목록과 진행 현황을 관리합니다.")


def page_integrity():
    _placeholder("데이터", "무결성 점검", "데이터 자동 검사와 스냅샷 해시를 제공합니다.")


def page_roadmap():
    _placeholder("모델", "잠금 해제 로드맵", "지표 모델 활성화에 필요한 다음 계산을 안내합니다.")


def page_methods():
    _placeholder("자료", "방법론", "수식·계산 조건·설계·한계를 설명합니다.")


def page_glossary():
    _placeholder("자료", "용어집", "플랫폼에서 쓰는 용어를 검색합니다.")


def page_report():
    _placeholder("자료", "리포트 내보내기", "HTML/Markdown 리포트와 CSV 번들을 생성합니다.")


def page_about():
    _placeholder("자료", "팀·프로젝트 소개", "RE:ACT와 프로젝트 목표를 소개합니다.")


# ───────────────────────── 라우팅 ─────────────────────────
PAGES = {
    "Overview": page_overview,
    "정방향 검증": page_forward,
    "표면 비교": page_surface_compare,
    "경쟁 흡착 비교": page_competitive,
    "배가스 조건 설정": page_flue_gas,
    "역방향 추천": page_reverse,
    "데이터 레지스트리": page_registry_view,
    ".out 파일 검사기": page_out_inspector,
    "계산 작업 관리": page_jobs,
    "무결성 점검": page_integrity,
    "모델 품질": page_quality,
    "잠금 해제 로드맵": page_roadmap,
    "방법론": page_methods,
    "용어집": page_glossary,
    "리포트 내보내기": page_report,
    "팀·프로젝트 소개": page_about,
}
PAGES.get(page, page_overview)()
