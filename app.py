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
from core.export import df_to_csv_bytes, ensure_provenance_columns

from ui import theme
from ui import components as C
from ui import charts
from ui import tokens as T

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
ENERGIES_CSV = os.path.join(DATA_DIR, "energies.csv")
GEOMETRY_CSV = os.path.join(DATA_DIR, "geometry.csv")
COMP_CSV = os.path.join(DATA_DIR, "composition_map.csv")

GASES = ["CO2", "H2O", "SO2"]
P_METRICS = ["P(CO2/H2O)", "P(CO2/SO2)"]

st.set_page_config(
    page_title="Ti2C MXene AI-DFT 스크리닝",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)
theme.inject()


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


# ───────────────────────── 사이드바 ─────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="sidebar-logo">⬡ Ti₂C MXene 스크리닝</div>'
        '<div class="sidebar-sub">AI-DFT 흡착 플랫폼</div>',
        unsafe_allow_html=True,
    )
    page = st.radio(
        "내비게이션",
        ["Overview", "정방향 검증", "역방향 추천", "모델 품질", "데이터 레지스트리"],
        label_visibility="collapsed",
    )

    # 데이터 상태 요약 — 지표 모델별로 '계산된 표면 N/7'을 각각 표시
    counts = metric_trainable_counts()
    n_surfaces = len(registry.surfaces(entries))
    n_computed = len(computed_ead_rows())
    per_metric_html = "".join(
        f'<div style="margin-top:8px"><div class="hint">{METRIC_LABEL[m]} 모델</div>'
        f'{C.progress_bar(counts[m], gpr.MIN_TRAINING)}</div>'
        for m in registry.ALL_METRICS
    )
    st.markdown(
        f'<div class="data-summary">'
        f'<div class="kpi-label">데이터 상태</div>'
        f'<div style="margin:6px 0"><span class="mono">{n_surfaces}</span> 표면 · '
        f'<span class="mono">{n_computed}</span> E_ad 계산됨</div>'
        f'<div class="kpi-label" style="margin-top:10px">모델 학습 데이터 '
        f'<span class="hint">(지표가 계산된 표면 수 / 필요 {gpr.MIN_TRAINING})</span></div>'
        f'{per_metric_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════ Overview ═══════════════════════
def page_overview():
    C.page_header(
        "Overview",
        "Ti₂C MXene 표면 조성에 따른 배가스 흡착을 DFT로 산출하고 AI로 최적 조성을 추천합니다.",
    )

    # 히어로 가치 제안
    C.card(
        '<div style="font-size:16px;font-weight:600;color:' + T.PRIMARY + '">'
        '표면 말단기(-O/-F/-OH) 조성을 바꾸면 CO₂·H₂O·SO₂ 흡착이 어떻게 달라질까?</div>'
        '<div class="hint" style="margin-top:6px;font-size:13px">'
        'DFT 계산 결과로부터 흡착 에너지와 선택성 지표를 투명하게 산출하고, '
        'GPR 기반 Active Learning으로 조성 공간을 스캔해 다음에 계산할 지점을 제안합니다. '
        '모든 수치는 출처(source_file)와 calc_group까지 추적 가능합니다.</div>'
    )

    # KPI 4개
    rows = computed_ead_rows()
    counts = metric_trainable_counts()
    n_suspect = sum(1 for r in rows if r["suspect"])
    quality_status = "suspect" if n_suspect else ("ok" if rows else "pending")
    quality_text = (f"{n_suspect}건 의심" if n_suspect
                    else ("정상" if rows else "데이터 없음"))

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(C.kpi_card("등록된 표면", str(len(registry.surfaces(entries)))), unsafe_allow_html=True)
    c2.markdown(C.kpi_card("계산 가능한 E_ad", str(len(rows))), unsafe_allow_html=True)
    # 3번째 카드: 지표별 학습 데이터(지표가 계산된 표면 수 / 7)
    metric_bars = "".join(
        f'<div style="margin-top:8px"><div class="hint">{METRIC_LABEL[m]}</div>'
        f'{C.progress_bar(counts[m], gpr.MIN_TRAINING)}</div>'
        for m in registry.ALL_METRICS
    )
    c3.markdown(
        '<div class="card card-tight"><div class="kpi-label">모델 학습 데이터</div>'
        '<div class="hint" style="margin-top:2px">지표가 계산된 표면 수 / '
        f'{gpr.MIN_TRAINING}</div>{metric_bars}</div>',
        unsafe_allow_html=True,
    )
    c4.markdown(
        '<div class="card card-tight"><div class="kpi-label">데이터 품질</div>'
        f'<div style="margin-top:8px">{C.status_pill(quality_status, quality_text)}</div></div>',
        unsafe_allow_html=True,
    )

    # E_ad 요약 막대차트
    C.section_title("계산 완료된 흡착 에너지")
    if rows:
        st.plotly_chart(charts.ead_bar(rows), use_container_width=True)
    else:
        C.empty_state("📊", "아직 계산 가능한 E_ad가 없습니다.",
                      "데이터 레지스트리에서 clean·molecule·adsorbed 에너지를 추가하세요.")

    # 다음에 필요한 계산 (누락 체크리스트, 우선순위)
    C.section_title("다음에 필요한 계산")
    missing = registry.missing_checklist(entries)
    if missing:
        # 전역(단독 분자) 누락을 우선순위 상위로
        missing_sorted = sorted(missing, key=lambda m: 0 if m.scope == "전역" else 1)
        items_html = "".join(
            f'<div style="display:flex;gap:10px;padding:8px 0;border-bottom:1px solid {T.BORDER}">'
            f'{C.status_pill("pending", "필요")}'
            f'<span style="font-size:13px"><b>{m.scope}</b> — {m.detail}</span></div>'
            for m in missing_sorted[:10]
        )
        C.card(items_html)
    else:
        C.notice("ok", "누락 항목이 없습니다.", "모든 조합의 기준 에너지가 준비되어 있습니다.")

    C.footer()


# ═══════════════════════ 정방향 검증 ═══════════════════════
def page_forward():
    C.page_header("정방향 검증",
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
        C.section_title("선택성 지표 (Preference Index)")
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
    C.page_header("역방향 추천",
                  "GPR이 조성 삼각 공간을 스캔해 최적 조성 후보와 다음 계산 지점을 추천합니다.")
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
        # 데이터 부족: 흐림 미리보기 + 잠금. 지표별 진행바를 함께 노출.
        counts = metric_trainable_counts()
        bars = "".join(
            f'<div style="margin-top:8px;text-align:left"><div class="hint">{METRIC_LABEL[m]}</div>'
            f'{C.progress_bar(counts[m], gpr.MIN_TRAINING)}</div>'
            for m in registry.ALL_METRICS
        )
        C.section_title("조성 공간 미리보기")
        st.markdown(
            '<div class="card"><div class="lock-overlay">'
            f'<div style="font-size:28px">🔒</div>'
            f'<div style="font-weight:600;margin-top:6px">조성 스캔 잠김</div>'
            f'<div class="hint" style="margin:4px 0 12px">각 지표가 계산된 표면이 '
            f'{gpr.MIN_TRAINING}개에 도달하면 해당 지표의 삼각 조성도와 추천이 활성화됩니다.</div>'
            + bars +
            '</div></div>',
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
    C.page_header("모델 품질",
                  "LOOCV(Leave-One-Out)로 실제 계산된 성능 수치만 표시합니다. 추정값은 쓰지 않습니다.")
    # 지표 3개 각각 별도로 표시: ok면 KPI + parity plot, 아니면 빈 상태 카드
    for metric in registry.ALL_METRICS:
        pts = registry.trainable_points_for_metric(entries, comp_map, metric, geom_map)
        q = loocv(pts, metric)
        C.section_title(METRIC_LABEL[metric])
        if not q.ok:
            C.empty_state("📈", f"데이터 {gpr.MIN_TRAINING}개 이상 필요",
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
    C.page_header("데이터 레지스트리",
                  "모든 에너지 항목·출처·calc_group·상태를 확인하고, CSV로 새 데이터를 반영합니다.")

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


# ───────────────────────── 라우팅 ─────────────────────────
PAGES = {
    "Overview": page_overview,
    "정방향 검증": page_forward,
    "역방향 추천": page_reverse,
    "모델 품질": page_quality,
    "데이터 레지스트리": page_registry_view,
}
PAGES[page]()
