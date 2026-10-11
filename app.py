"""배가스 맞춤형 Ti₂C MXene 표면 설계 플랫폼 — Streamlit UI (한국어).

PDF 명세([5] 화면 구성)에 따라 시작 화면 + 6개 메뉴로 구성한다.
표현 레이어는 core 결과를 '표시'만 한다. 에너지 값은 CSV에서만 읽는다.
"""

from __future__ import annotations

import io
import os

import numpy as np
import pandas as pd
import streamlit as st

from core.loader import load_energies, parse_rows, EnergyEntry
from core.units import ry_to_ev, RY_TO_EV
from core.composition import load_composition_map, is_trainable
from core.settings import load_settings
from core.scope import APPLICABILITY
from core import screening as S
from core import gpr_model as G
from core.classify import classify, ClassifyInput
from core.coords import is_normalized, composition_sum
from core.conditions import NOTE as COND_NOTE, NOTE_HINT as COND_HINT, ppm_to_molpct

from ui import theme
from ui import components as C
from ui import charts
from ui import tokens as T
from ui import branding as B
from ui import landing
from ui import nav as NAV
from ui.htmlutil import html_block as _html_block

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
CONFIG = os.path.join(HERE, "config", "settings.json")
ENERGIES_CSV = os.path.join(DATA_DIR, "energies.csv")
COMP_CSV = os.path.join(DATA_DIR, "composition_map.csv")
GEOM_CSV = os.path.join(DATA_DIR, "geometry.csv")
BACKUP_DIR = os.path.join(DATA_DIR, "backup")

GASES = ["CO2", "H2O", "SO2"]

st.set_page_config(
    page_title="Ti₂C MXene 스크리닝",
    page_icon=B.favicon_path(),
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Markdown HTML 안전 가드 (들여쓰기·빈 줄 코드블록화 방지) ──
def _install_markdown_guard():
    from streamlit.delta_generator import DeltaGenerator
    if getattr(DeltaGenerator.markdown, "_html_guarded", False):
        return
    _orig = DeltaGenerator.markdown

    def _guarded(self, body, *args, unsafe_allow_html=False, **kwargs):
        if unsafe_allow_html and isinstance(body, str):
            body = _html_block(body)
        return _orig(self, body, *args, unsafe_allow_html=unsafe_allow_html, **kwargs)

    _guarded._html_guarded = True
    DeltaGenerator.markdown = _guarded


_install_markdown_guard()
theme.inject()


# ───────────────────────── 데이터 로딩 (mtime 캐시) ─────────────────
def _mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


@st.cache_data(show_spinner=False)
def _load_energies(path, mtime):
    res = load_energies(path)
    return res.entries, res.errors


@st.cache_data(show_spinner=False)
def _load_comp(path, mtime):
    return load_composition_map(path)


def get_entries():
    if "uploaded_entries" in st.session_state:
        return st.session_state["uploaded_entries"], st.session_state.get("uploaded_errors", [])
    return _load_energies(ENERGIES_CSV, _mtime(ENERGIES_CSV))


entries, load_errors = get_entries()
comp_map = _load_comp(COMP_CSV, _mtime(COMP_CSV))
settings = load_settings(CONFIG)


def fmt(x, nd=3):
    return "—" if x is None else f"{x:.{nd}f}"


# ───────────────────────── GPR 모델 (타깃 4개) ─────────────────
@st.cache_resource(show_spinner=False)
def _fit_models(mtime_e, mtime_c, min_train):
    models = {}
    for t in G.TARGETS:
        pts = S.training_points(entries, comp_map, t)
        models[t] = G.fit_target(pts, t, min_train)
    return models


def get_models():
    return _fit_models(_mtime(ENERGIES_CSV), _mtime(COMP_CSV), settings.min_train_points)


def active_model_count():
    models = get_models()
    return sum(1 for m in models.values() if isinstance(m, G.GprModel))


# ───────────────────────── 시작 화면 분기 ─────────────────────────
if not st.session_state.get("entered") and landing.should_skip_via_query():
    st.session_state["entered"] = True

if not st.session_state.get("entered"):
    n_ead = sum(1 for s in S.surfaces(entries) for g in GASES
                if S.compute_ad_for(entries, s, g).ok)
    landing.render(n_ead=n_ead, n_models_active=active_model_count(),
                   n_models_total=len(G.TARGETS))
    st.stop()


# ───────────────────────── 사이드바 ─────────────────────────
from ui import illustrations as ILL

with st.sidebar:
    tri = ILL.composition_triangle(size=22)
    if st.button("← 시작 화면으로", use_container_width=True, key="back_home"):
        st.session_state["entered"] = False
        st.rerun()
    st.markdown(
        f'<div class="sidebar-logo-row">{tri}'
        f'<span class="sidebar-logo">{B.wordmark(on_dark=False, size=15)}</span></div>'
        '<div class="sidebar-sub">Ti₂C MXene 표면 설계</div>',
        unsafe_allow_html=True,
    )

    _nav_req = st.session_state.pop("_nav", None)
    if _nav_req in NAV.PAGES:
        st.session_state["current_page"] = _nav_req
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = NAV.DEFAULT_PAGE

    page = st.radio("메뉴", NAV.PAGES,
                    index=NAV.PAGES.index(st.session_state["current_page"]),
                    label_visibility="collapsed", key="nav_radio")
    st.session_state["current_page"] = page

    st.markdown('<hr style="border:none;border-top:1px solid var(--ill-faint);margin:10px 0">',
                unsafe_allow_html=True)
    # 타깃별 학습 데이터 진행바 4줄
    st.markdown('<div class="kpi-label">GPR 학습 데이터</div>', unsafe_allow_html=True)
    models = get_models()
    label_map = {"Eads_CO2": "Eads(CO₂)", "Eads_H2O": "Eads(H₂O)",
                 "Eads_SO2": "Eads(SO₂)", "Delta_d": "Δd"}
    for t in G.TARGETS:
        m = models[t]
        n = m.n if isinstance(m, G.GprModel) else m.n
        st.markdown(
            f'<div style="margin-top:6px"><div class="hint">{label_map[t]}</div>'
            f'{C.progress_bar(n, settings.min_train_points)}</div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════ 공통 헬퍼 ═══════════════════════
def _class_badge(label: str) -> str:
    cls = {"우선 검토": "cls-priority", "추가 계산 권장": "cls-more",
           "현재 기준 미충족": "cls-unmet"}.get(label, "cls-more")
    return f'<span class="cls-badge {cls}">{label}</span>'


# ═══════════════════════ 정방향 검증 (PDF 6.1) ═══════════════════════
def page_forward():
    C.breadcrumb("분석", "정방향 검증")
    C.page_header("정방향 검증", "표면 구성과 배가스 조건을 입력하면 지표와 분류를 보여줍니다.")
    C.scope_banner()

    left, right = st.columns([1, 2], gap="large")
    with left:
        C.section_title("표면 구성")
        xO = st.slider("xO (–O)", 0.0, 1.0, 1.0, 0.25)
        xF = st.slider("xF (–F)", 0.0, 1.0, 0.0, 0.25)
        xOH = st.slider("xOH (–OH)", 0.0, 1.0, 0.0, 0.25)
        s = composition_sum(xO, xF, xOH)
        if not is_normalized(xO, xF, xOH):
            C.notice("suspect", f"합이 1이 아닙니다(현재 {s:.2f})",
                     "세 비율의 합이 1이 되도록 맞춰 주세요.")
        C.section_title("배가스 조건")
        st.caption("T = 298.15 K 고정")
        unit = st.radio("분율 단위", ["mol%", "ppm"], horizontal=True)
        c1, c2, c3 = st.columns(3)
        co2_raw = c1.text_input("CO₂", "12")
        h2o_raw = c2.text_input("H₂O", "10")
        so2_raw = c3.text_input("SO₂", "500" if unit == "ppm" else "0.05")
        st.caption(COND_HINT)

    with right:
        if not is_normalized(xO, xF, xOH):
            C.empty_state("⚖", "조성 합을 1로 맞추면 결과가 표시됩니다.")
            C.footer()
            return

        # 가장 가까운 계산 조성
        near = S.nearest_computed(entries, comp_map, xO, xF, xOH)
        # 입력 조성과 일치하는 계산 표면이 있는지
        matched = None
        for surf in S.computed_surfaces(entries, comp_map):
            c = comp_map[surf]
            if abs(c.xO - xO) < 1e-6 and abs(c.xF - xF) < 1e-6 and abs(c.xOH - xOH) < 1e-6:
                matched = surf
                break

        C.section_head(ILL.icon_metrics(), "흡착 에너지")
        if matched:
            # 계산값 표시
            e = S.eads_for_surface(entries, matched)
            rows_html = ""
            for g in GASES:
                r = e[g]
                m = T.gas_meta(g)
                if r.ok:
                    unstable = " · 안정 흡착 아님" if r.E_ad_eV > 0 else ""
                    rng = " · 범위 점검" if r.suspect else ""
                    rows_html += (f'<div style="padding:6px 0;border-bottom:1px solid {T.BORDER}">'
                                  f'{C.gas_pill(g)} <span class="mono" style="color:{m["color"]}">'
                                  f'{r.E_ad_eV:.3f} eV</span> <span class="hint">(계산){unstable}{rng}</span></div>')
                else:
                    rows_html += (f'<div style="padding:6px 0;border-bottom:1px solid {T.BORDER}">'
                                  f'{C.gas_pill(g)} {C.status_pill("pending", "데이터 없음")} '
                                  f'<span class="hint">{r.reason}</span></div>')
            C.card(rows_html)
            _forward_metrics(matched, co2_raw, h2o_raw, so2_raw, unit)
        else:
            # 계산값 없음 → 예측 (GPR 활성 시) 또는 데이터 없음
            C.notice("info", "이 조성의 계산값이 없습니다.",
                     (f"가장 가까운 계산 조성: {near['surface']} "
                      f"(거리 {near['distance']:.3f})" if near else "계산된 조성이 없습니다."))
            _forward_prediction(xO, xF, xOH)
    C.footer()


def _forward_metrics(surface, co2_raw, h2o_raw, so2_raw, unit):
    """계산값 기반 P·분류."""
    p = S.p_indices(entries, surface)
    # 조건 보정
    try:
        if unit == "ppm":
            p_co2 = ppm_to_molpct(float(co2_raw))
            p_h2o = ppm_to_molpct(float(h2o_raw))
            p_so2 = ppm_to_molpct(float(so2_raw))
        else:
            p_co2, p_h2o, p_so2 = float(co2_raw), float(h2o_raw), float(so2_raw)
        cc = S.condition_correction(p_co2, p_h2o, p_so2)
    except ValueError:
        cc = None

    C.section_title("CO₂ 선호도 (Preference Index)")
    ph = p["P(CO2/H2O)"]
    ps = p["P(CO2/SO2)"]
    html = ""
    if ph.ok:
        extra = " · 두 가스 모두 안정 흡착 아님" if ph.two_gas_unstable else ""
        html += (f'<div style="padding:6px 0"><b>P(CO₂/H₂O)</b> '
                 f'<span class="mono" style="color:{T.PRIMARY}">{ph.value_eV:.3f} eV</span>{extra}</div>')
    else:
        html += (f'<div style="padding:6px 0"><b>P(CO₂/H₂O)</b> '
                 f'{C.status_pill("pending", "데이터 없음")} <span class="hint">{ph.reason}</span></div>')
    if ps.ok:
        sc = " · 구조 변화 동반" if ps.structure_change else ""
        html += (f'<div style="padding:6px 0"><b>P(CO₂/SO₂)</b> '
                 f'<span class="mono hint">{ps.value_eV:.3f} eV (참고용{sc})</span></div>')
    else:
        html += (f'<div style="padding:6px 0"><b>P(CO₂/SO₂)</b> '
                 f'{C.status_pill("pending", "데이터 없음")} <span class="hint">{ps.reason}</span></div>')
    C.card(html)

    # 분류 (P(CO2/H2O) 기준)
    C.section_title("분류")
    e_co2 = S.compute_ad_for(entries, surface, "CO2")
    if ph.ok and cc and cc.delta_h2o is not None:
        p_cond = ph.value_eV + cc.delta_h2o
        inp = ClassifyInput(mu_p_cond=p_cond, sigma_p=0.0,
                            mu_eads_co2=e_co2.E_ad_eV if e_co2.ok else None,
                            reaction_flag="none")
        res = classify(inp, settings.kappa, settings.margin_m_eV,
                       settings.delta_d_max_A, settings.sigma_max_eV, settings.preset,
                       settings.wide_range)
        C.render_html(st, _class_badge(res.label))
        C.card('<div class="hint">근거: ' + " · ".join(res.reasons) + "</div>")
        st.caption(f"{COND_NOTE}: δ_H₂O = {cc.delta_h2o:+.3f} eV → "
                   f"P_cond(CO₂/H₂O) = {p_cond:+.3f} eV")
    else:
        inp = ClassifyInput(mu_p_cond=None,
                            missing=S.missing_for_P(entries, surface))
        res = classify(inp, settings.kappa, settings.margin_m_eV,
                       settings.delta_d_max_A, settings.sigma_max_eV, settings.preset)
        C.render_html(st, _class_badge(res.label))
        if res.needed:
            C.card('<div class="hint">필요한 계산: ' + " · ".join(res.needed) + "</div>")

    # 계산 과정 보기
    with st.expander("계산 과정 보기 (세 에너지 값 · 뺄셈 식 · Ry→eV · 출처)"):
        for g in GASES:
            r = S.compute_ad_for(entries, surface, g)
            if not r.ok:
                st.markdown(f"**{g}**: {r.reason}")
                continue
            comps = r.components
            st.markdown(
                f"**{g}** · E_ads = E_complex − (E_surface + E_gas) = "
                f"`{r.E_ad_Ry:.5f} Ry` = `{r.E_ad_Ry:.5f} × {RY_TO_EV}` = "
                f"**{r.E_ad_eV:.3f} eV** · calc_group `{r.calc_group}`")
            chips = "".join(C.source_chip(comps[k]["source_file"], comps[k]["calc_group"]) + " "
                            for k in ("E_adsorbed", "E_clean", "E_molecule") if comps.get(k))
            st.markdown(chips, unsafe_allow_html=True)


def _forward_prediction(xO, xF, xOH):
    """임의 조성 예측 (GPR 활성 시 μ±σ, 아니면 데이터 없음)."""
    models = get_models()
    C.section_title("예측 (GPR)")
    any_active = False
    html = ""
    uv = np.array([__import__("core.coords", fromlist=["to_uv"]).to_uv(xO, xF, xOH)])
    for t in ["Eads_CO2", "Eads_H2O", "Eads_SO2"]:
        m = models[t]
        if isinstance(m, G.GprModel):
            any_active = True
            mu, sigma = m.predict(uv)
            html += (f'<div style="padding:6px 0"><b>{t}</b> '
                     f'<span class="mono">{mu[0]:.3f} ± {sigma[0]:.3f} eV</span> '
                     f'<span class="hint">(예측)</span></div>')
        else:
            html += (f'<div style="padding:6px 0"><b>{t}</b> '
                     f'{C.status_pill("pending", m.message)}</div>')
    C.card(html)
    if not any_active:
        C.notice("pending", "GPR 모델이 아직 비활성입니다.",
                 f"타깃별 학습 데이터가 {settings.min_train_points}개에 도달하면 예측이 활성화됩니다.")
    else:
        st.caption(G.SIGMA_NOTE)


# ═══════════════════════ 역방향 추천 (PDF 6.2) ═══════════════════════
def page_reverse():
    C.breadcrumb("설계", "역방향 추천")
    C.page_header("역방향 추천", "조성 격자를 평가해 우선 검토 후보를 제안합니다.")
    C.scope_banner()

    models = get_models()
    active = [t for t in G.TARGETS if isinstance(models[t], G.GprModel)]
    if not active:
        # 잠금 화면
        C.section_head(ILL.icon_gpr(), "추천 잠금")
        bars = ""
        label_map = {"Eads_CO2": "Eads(CO₂)", "Eads_H2O": "Eads(H₂O)",
                     "Eads_SO2": "Eads(SO₂)", "Delta_d": "Δd"}
        for t in G.TARGETS:
            m = models[t]
            bars += (f'<div style="margin-top:8px;text-align:left"><div class="hint">{label_map[t]}</div>'
                     f'{C.progress_bar(m.n, settings.min_train_points)}</div>')
        st.markdown(
            html_block_wrap('<div class="card" style="text-align:center">'
                            f'<div style="font-size:28px">🔒</div>'
                            f'<div style="font-weight:600;margin-top:6px">GPR 학습 데이터 부족</div>'
                            f'<div class="hint" style="margin:4px 0 12px">타깃별 학습 데이터가 '
                            f'{settings.min_train_points}개에 도달하면 추천이 활성화됩니다. '
                            f'아직 계산하지 않은 계획 조성을 먼저 계산하세요.</div>'
                            f'<div style="max-width:420px;margin:0 auto">{bars}</div></div>'),
            unsafe_allow_html=True,
        )
        # 필요한 계산(계획 조성) 안내
        planned = [c for c in comp_map.values() if c.status == "planned"]
        if planned:
            items = "".join(
                f'<div style="padding:6px 0;border-bottom:1px solid {T.BORDER}">'
                f'{C.status_pill("pending", "계획")} <b>{c.surface}</b> '
                f'<span class="hint">{c.arrangement_note}</span></div>'
                for c in planned)
            C.section_title("먼저 계산할 계획 조성")
            C.card(items)
        C.footer()
        return

    # 활성 시: 격자 평가 (요약)
    C.notice("info", "활성 모델로 격자를 평가합니다.",
             "P 계산에 두 Eads 예측이 모두 필요합니다.")
    C.footer()


def html_block_wrap(s):
    return s


# ═══════════════════════ 조성 지도 (PDF 6.3) ═══════════════════════
def page_map():
    C.breadcrumb("분석", "조성 지도")
    C.page_header("조성 지도", "삼원 조성 공간에서 계산·계획 조성과 지표를 봅니다.")
    C.scope_banner()

    tab = st.radio("지표", ["Eads(CO₂)", "Eads(H₂O)", "Eads(SO₂)", "P(CO₂/H₂O)", "Δd"],
                   horizontal=True)

    markers = []
    gas_of = {"Eads(CO₂)": "CO2", "Eads(H₂O)": "H2O", "Eads(SO₂)": "SO2"}
    for surf, c in comp_map.items():
        if c.xO is None:
            # 미확정 — 삼각형에 그릴 좌표 없음 → 표시 생략(별도 안내)
            continue
        kind = "computed" if (c.confirmed and surf in S.computed_surfaces(entries, comp_map)) \
            else "planned"
        value = None
        if tab in gas_of and kind == "computed":
            r = S.compute_ad_for(entries, surf, gas_of[tab])
            value = r.E_ad_eV if r.ok else None
        markers.append({"xO": c.xO, "xF": c.xF, "xOH": c.xOH,
                        "kind": kind, "value": value, "label": surf})

    unit = "eV" if tab != "Δd" else "Å"
    st.plotly_chart(charts.composition_map(markers, tab, unit), use_container_width=True)
    st.caption("◆ 계산값 · 빈 원 계획 조성 · ✕ 조성 미확정은 좌표가 없어 지도에 표시되지 않습니다.")

    # 미확정 표면 안내
    unconf = [s for s, c in comp_map.items() if not c.confirmed and c.xO is None]
    if unconf:
        C.notice("pending", f"조성 미확정: {', '.join(unconf)}",
                 "좌표가 확정되면 지도와 GPR 학습에 포함됩니다.")
    C.footer()


# ═══════════════════════ 데이터·QC ═══════════════════════
def page_data_qc():
    C.breadcrumb("데이터", "데이터·QC")
    C.page_header("데이터·QC", "에너지 데이터와 품질 점검을 확인하고 CSV를 업로드합니다.")

    if load_errors:
        C.notice("suspect", "로드 중 거부된 행이 있습니다",
                 "스키마 위반·중복 source_file 등은 반영되지 않았습니다.")
        st.dataframe(pd.DataFrame([{"행": e.row_index, "사유": e.reason} for e in load_errors]),
                     use_container_width=True, hide_index=True)

    # calc_group별 그룹 헤더
    C.section_title("에너지 데이터")
    for cg in sorted({e.calc_group for e in entries}):
        grp = [e for e in entries if e.calc_group == cg]
        st.markdown(f'<div class="hint" style="margin:10px 0 4px"><b>calc_group {cg}</b> '
                    f'· {len(grp)}건</div>', unsafe_allow_html=True)
        df = pd.DataFrame([{
            "key": e.key, "role": e.role, "surface": e.surface, "gas": e.gas,
            "energy_Ry": e.energy_Ry, "energy_eV": round(ry_to_ev(e.energy_Ry), 6),
            "source_file": e.source_file, "status": e.status,
            "reaction_flag": e.reaction_flag,
        } for e in grp])
        st.dataframe(df, use_container_width=True, hide_index=True)

    # 누락 체크리스트
    C.section_title("누락 항목 체크리스트")
    missing = []
    h2o_mol = S.find_molecule(entries, "H2O")
    if h2o_mol is None or h2o_mol.status == "pending":
        missing.append("H₂O 계산 데이터 없음 (짝 calc_group 미지정)")
    for surf in S.surfaces(entries):
        for g in GASES:
            if S.find_adsorbed(entries, surf, g) is None and comp_map.get(surf) \
               and comp_map[surf].confirmed:
                missing.append(f"{surf} + {g} 복합체 없음")
    if missing:
        C.card("".join(f'<div style="padding:4px 0">{C.status_pill("pending", "필요")} '
                       f'<span class="hint">{m}</span></div>' for m in missing[:12]))
    else:
        C.notice("ok", "누락 항목이 없습니다.")

    # QC 결과
    C.section_title("QC 점검")
    qc_html = ""
    # 기준 점검(8~10 Å) 데이터 유무
    far = [e for e in entries if e.min_distance_after is not None
           and e.min_distance_after >= 8.0]
    qc_html += (f'<div style="padding:4px 0">{C.status_pill("pending", "데이터 없음") if not far else C.status_pill("ok", "있음")} '
                f'<span class="hint">프로젝트 기준 점검(8~10 Å) 데이터</span></div>')
    # min_distance_after 배지
    detached = [e.key for e in entries if e.min_distance_after is not None
                and e.min_distance_after >= settings.min_distance_far_threshold]
    if detached:
        qc_html += (f'<div style="padding:4px 0">{C.status_pill("info", "붙지 않고 떨어진 구조")} '
                    f'<span class="hint">{", ".join(detached)}</span></div>')
    # Δd geometry
    qc_html += (f'<div style="padding:4px 0">{C.status_pill("pending", "데이터 없음")} '
                f'<span class="hint">Δd(geometry) 데이터 — SO₂ 계산 z 좌표</span></div>')
    C.card(qc_html)

    # CSV 업로드 (미리보기 → 확인 → 백업)
    C.section_title("CSV 업로드")
    st.caption("업로드 전 미리보기와 스키마·충돌 검사를 거쳐 확인 후에만 반영됩니다. "
               "반영 시 data/backup/ 에 백업합니다.")
    up = st.file_uploader("energies.csv 형식", type=["csv"])
    if up is not None:
        content = up.read().decode("utf-8")
        reader = pd.read_csv(io.StringIO(content), dtype=str, keep_default_na=False)
        res = parse_rows(list(reader.columns), reader.to_dict("records"))
        if res.errors:
            C.notice("suspect", "스키마·충돌 검사 실패 — 반영 거부")
            st.dataframe(pd.DataFrame([{"행": e.row_index, "사유": e.reason} for e in res.errors]),
                         use_container_width=True, hide_index=True)
        else:
            st.dataframe(reader, use_container_width=True, hide_index=True)
            if st.button("확인 후 반영"):
                _apply_upload(content)
                st.cache_data.clear()
                C.notice("ok", f"{len(res.entries)}건이 반영되었습니다.", "백업이 생성되었습니다.")
    C.footer()


def _apply_upload(content: str):
    """백업 후 원자적 쓰기 (임시 파일 → 교체)."""
    import tempfile
    import shutil
    from datetime import datetime, timezone
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if os.path.exists(ENERGIES_CSV):
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        shutil.copy2(ENERGIES_CSV, os.path.join(BACKUP_DIR, f"energies.csv.{ts}.bak"))
    d = os.path.dirname(ENERGIES_CSV)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        os.replace(tmp, ENERGIES_CSV)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


# ═══════════════════════ 모델 정보 ═══════════════════════
def page_model():
    C.breadcrumb("모델", "모델 정보")
    C.page_header("모델 정보", "타깃별 학습 데이터와 LOOCV 성능을 표시합니다.")
    C.scope_banner()

    import hashlib
    label_map = {"Eads_CO2": "Eads(CO₂)", "Eads_H2O": "Eads(H₂O)",
                 "Eads_SO2": "Eads(SO₂)", "Delta_d": "Δd"}
    for t in G.TARGETS:
        pts = S.training_points(entries, comp_map, t)
        C.section_title(f"{label_map[t]} — 학습 데이터 {len(pts)}/{settings.min_train_points}")
        st.markdown(C.progress_bar(len(pts), settings.min_train_points), unsafe_allow_html=True)
        q = G.loocv(pts, t, settings.min_train_points)
        if q.ok:
            cc = st.columns(2)
            cc[0].markdown(C.kpi_card("MAE", f"{q.mae:.4f}", "eV"), unsafe_allow_html=True)
            cc[1].markdown(C.kpi_card("RMSE", f"{q.rmse:.4f}", "eV"), unsafe_allow_html=True)
        else:
            C.empty_state("📈", "LOOCV 데이터 부족", q.reason)

    st.caption(G.SIGMA_NOTE)
    C.card('<div class="hint">혼합 표면은 조성당 대표 배열 1개로 고정합니다.</div>')

    # 데이터 파일 SHA-256
    def sha(path):
        if not os.path.exists(path):
            return "—"
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for ch in iter(lambda: f.read(8192), b""):
                h.update(ch)
        return h.hexdigest()
    C.card(f'<div class="kpi-label">데이터 버전 (SHA-256)</div>'
           f'<div class="mono" style="font-size:11px;word-break:break-all;margin-top:4px">'
           f'energies.csv · {sha(ENERGIES_CSV)}</div>')
    C.footer()


# ═══════════════════════ 내보내기 ═══════════════════════
def page_export():
    C.breadcrumb("자료", "내보내기")
    C.page_header("내보내기", "결과 표 CSV와 인쇄용 HTML을 생성합니다.")
    C.scope_banner()

    # E_ads 표
    rows = []
    for s in S.surfaces(entries):
        for g in GASES:
            r = S.compute_ad_for(entries, s, g)
            if r.ok:
                rows.append({"surface": s, "gas": g,
                             "E_ads_eV": round(r.E_ad_eV, 3),
                             "E_ads_Ry": round(r.E_ad_Ry, 5),
                             "calc_group": r.calc_group,
                             "source_file": r.components["E_adsorbed"]["source_file"]})
    df = pd.DataFrame(rows)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("결과 표 CSV 다운로드",
                           data=df.to_csv(index=False).encode("utf-8-sig"),
                           file_name="eads_results.csv", mime="text/csv")
    else:
        C.empty_state("📄", "계산된 E_ads가 없습니다.")

    html_doc = _build_html_report(df)
    st.download_button("인쇄용 HTML 다운로드", data=html_doc.encode("utf-8"),
                       file_name="ti2c_report.html", mime="text/html")
    C.footer()


def _build_html_report(df) -> str:
    import html as _h
    from datetime import datetime, timezone
    rows_html = ""
    if not df.empty:
        for _, r in df.iterrows():
            rows_html += (f"<tr><td>{_h.escape(str(r['surface']))}</td>"
                          f"<td>{_h.escape(str(r['gas']))}</td>"
                          f"<td>{r['E_ads_eV']}</td><td>{r['E_ads_Ry']}</td>"
                          f"<td>{_h.escape(str(r['calc_group']))}</td>"
                          f"<td>{_h.escape(str(r['source_file']))}</td></tr>")
    else:
        rows_html = '<tr><td colspan="6">데이터 없음</td></tr>'
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<title>Ti2C MXene 리포트</title><style>
body{{font-family:system-ui,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;color:#334155}}
table{{border-collapse:collapse;width:100%;font-size:12px;margin-top:8px}}
th,td{{border:1px solid #E7E5E4;padding:4px 8px;text-align:left}}
.scope{{background:#ECFDF5;border-left:4px solid #0F766E;padding:12px;font-size:13px}}
@media print{{body{{margin:0}}}}
</style></head><body>
<h1>배가스 맞춤형 Ti₂C MXene 표면 설계 플랫폼 — 리포트</h1>
<p>생성(UTC): {datetime.now(timezone.utc).isoformat()}</p>
<div class="scope"><b>적용 범위</b> — {_h.escape(APPLICABILITY)}</div>
<h2>지표 정의</h2>
<ul><li>E_ads = E_complex − (E_surface + E_gas)</li>
<li>P(CO₂/H₂O) = E_ads(H₂O) − E_ads(CO₂)</li>
<li>P(CO₂/SO₂) = E_ads(SO₂) − E_ads(CO₂) (참고용)</li>
<li>Δd = |(z_T−z_ref)_after − (z_T−z_ref)_before| (SO₂ 한정)</li>
<li>1 Ry = {RY_TO_EV} eV</li></ul>
<h2>조건 보정 δ 가정</h2>
<p>T=298.15 K, S°(J/mol·K): CO₂ 213.8 / H₂O 188.8 / SO₂ 248.2, kT=0.02569 eV. 온도·분압 1차 근사.</p>
<h2>분류 설정값</h2>
<p>kappa={_settings_str()}</p>
<h2>계산된 E_ads</h2>
<table><tr><th>표면</th><th>가스</th><th>E_ads(eV)</th><th>E_ads(Ry)</th>
<th>calc_group</th><th>source_file</th></tr>{rows_html}</table>
<h2>데이터 없음</h2>
<p>H₂O 관련 항목과 P 지수는 현재 데이터 없음. Δd(geometry) 데이터 없음.</p>
</body></html>"""


def _settings_str():
    s = settings
    return (f"{s.kappa}, margin_m={s.margin_m_eV} eV, preset={s.preset}, "
            f"delta_d_max={s.delta_d_max_A}, sigma_max={s.sigma_max_eV}")


# ───────────────────────── 라우팅 ─────────────────────────
PAGES = {
    "정방향 검증": page_forward,
    "역방향 추천": page_reverse,
    "조성 지도": page_map,
    "데이터·QC": page_data_qc,
    "모델 정보": page_model,
    "내보내기": page_export,
}
PAGES.get(page, page_forward)()
