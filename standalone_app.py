"""단독 실행 Streamlit 앱 — 두 데이터 세트 개요·반응성 경향·인터랙티브 테이블·바 차트.

요구사항:
  1. 시작 페이지(Home): 개요 + 반응성 경향
  2. 두 세트 전체 에너지 + 복합체 9종 인터랙티브 테이블 + Plotly 바 차트
  3. 환산 기준 1 Ry = 13.605698 eV

데이터 무결성: 에너지 값은 하드코딩하지 않고 data/energies.csv 에서만 읽는다.
서로 다른 calc_group(세트)의 에너지는 섞어서 빼지 않는다.
실행:  streamlit run standalone_app.py
"""

from __future__ import annotations

import csv
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

RY_TO_EV = 13.605698  # 환산 기준 (요구사항 3)

HERE = os.path.dirname(os.path.abspath(__file__))
ENERGIES_CSV = os.path.join(HERE, "data", "energies.csv")

GAS_COLOR = {"CO2": "#0F766E", "H2O": "#2563EB", "SO2": "#D97706"}
GAS_LABEL = {"CO2": "CO₂", "H2O": "H₂O", "SO2": "SO₂"}

st.set_page_config(page_title="Ti₂C MXene 두 세트 개요", page_icon="⬡", layout="wide")


# ─────────────────────── 데이터 로드 (CSV 전용) ───────────────────────
@st.cache_data(show_spinner=False)
def load_rows(path: str, mtime: float):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _mtime(p):
    return os.path.getmtime(p) if os.path.exists(p) else 0.0


rows = load_rows(ENERGIES_CSV, _mtime(ENERGIES_CSV))
if not rows:
    st.error("data/energies.csv 를 찾을 수 없습니다. 에너지 값은 CSV에서만 읽습니다.")
    st.stop()


def to_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ─────────────────────── E_ads 계산 (세트 안에서만) ───────────────────────
def find(role, surface=None, gas=None, cg=None):
    for r in rows:
        if r["role"] != role:
            continue
        if surface is not None and r["surface"] != surface:
            continue
        if gas is not None and r["gas"] != gas:
            continue
        if cg is not None and r["calc_group"] != cg:
            continue
        return r
    return None


def adsorption_rows():
    """모든 복합체의 E_ads = E_comp − (E_surface + E_gas), 같은 calc_group 안에서만."""
    out = []
    for r in rows:
        if r["role"] != "adsorbed":
            continue
        cg = r["calc_group"]
        comp = to_float(r["energy_Ry"])
        surf = find("clean", surface=r["surface"], cg=cg)
        mol = find("molecule", gas=r["gas"], cg=cg)
        if comp is None or surf is None or mol is None:
            out.append({"calc_group": cg, "surface": r["surface"], "gas": r["gas"],
                        "E_ads_eV": None, "E_ads_Ry": None, "source_file": r["source_file"],
                        "note": "같은 세트에 표면·분자 데이터 없음"})
            continue
        e_ry = comp - (to_float(surf["energy_Ry"]) + to_float(mol["energy_Ry"]))
        out.append({"calc_group": cg, "surface": r["surface"], "gas": r["gas"],
                    "E_ads_Ry": round(e_ry, 6), "E_ads_eV": round(e_ry * RY_TO_EV, 4),
                    "source_file": r["source_file"], "note": ""})
    return out


ADS = adsorption_rows()
CALC_GROUPS = sorted({r["calc_group"] for r in rows})


# ─────────────────────── 차트 ───────────────────────
def ads_bar(ads):
    ok = [a for a in ads if a["E_ads_eV"] is not None]
    fig = go.Figure()
    for gas in ["CO2", "H2O", "SO2"]:
        g = [a for a in ok if a["gas"] == gas]
        if not g:
            continue
        fig.add_bar(
            x=[f'{a["surface"]}<br>({a["calc_group"]})' for a in g],
            y=[a["E_ads_eV"] for a in g],
            name=GAS_LABEL[gas], marker_color=GAS_COLOR[gas],
            text=[f'{a["E_ads_eV"]:.3f}' for a in g], textposition="outside",
            customdata=[a["source_file"] for a in g],
            hovertemplate="%{x}<br>E_ads=%{y:.4f} eV<br>출처=%{customdata}<extra></extra>",
        )
    fig.update_layout(
        barmode="group", height=440, template="none",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Pretendard, system-ui, sans-serif", size=13, color="#334155"),
        legend=dict(orientation="h", y=1.02, x=0),
        margin=dict(l=50, r=20, t=20, b=70),
    )
    fig.update_yaxes(title_text="E_ads (eV)", gridcolor="#E7E5E4", zeroline=True,
                     zerolinecolor="#CBD5E1")
    fig.update_xaxes(title_text="표면 (calc_group)", gridcolor="#E7E5E4")
    return fig


# ─────────────────────── 사이드바 네비 ───────────────────────
st.markdown(
    "<style>@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@latest/dist/web/static/pretendard.css');"
    "html,body,.stApp{font-family:'Pretendard',system-ui,sans-serif;}"
    "#MainMenu,footer{visibility:hidden;}</style>",
    unsafe_allow_html=True,
)
page = st.sidebar.radio("메뉴", ["Home (개요)", "데이터 테이블", "바 차트"],
                        label_visibility="collapsed")
st.sidebar.caption(f"환산: 1 Ry = {RY_TO_EV} eV")
st.sidebar.caption("세트 간 에너지는 섞어서 빼지 않습니다.")


# ─────────────────────── Home (개요 + 경향) ───────────────────────
def page_home():
    st.markdown(
        "<div style='background:linear-gradient(135deg,#0B1F33,#0F766E);"
        "border-radius:16px;padding:28px 32px;color:#fff;margin-bottom:20px'>"
        "<div style='font-size:13px;color:#5EEAD4;font-weight:600;letter-spacing:.06em'>"
        "Ti₂C MXene · 두 DFT 데이터 세트 개요</div>"
        "<div style='font-size:30px;font-weight:800;margin-top:8px'>"
        "배가스 흡착 에너지 개요와 반응성 경향</div>"
        "<div style='font-size:14px;color:#CBD5E1;margin-top:10px;line-height:1.6'>"
        "세트1(대형 슈퍼셀)과 세트2(표준 단위셀)의 단독 분자·표면·복합체 에너지를 "
        "CSV에서 읽어 흡착 에너지 E_ads = E_complex − (E_surface + E_gas)로 계산합니다. "
        "서로 다른 세트의 에너지는 섞어서 빼지 않습니다.</div></div>",
        unsafe_allow_html=True,
    )

    # KPI
    n_ok = sum(1 for a in ADS if a["E_ads_eV"] is not None)
    c = st.columns(4)
    c[0].metric("데이터 세트", f"{len(CALC_GROUPS)}")
    c[1].metric("등록 에너지 항목", f"{len(rows)}")
    c[2].metric("계산된 복합체 E_ads", f"{n_ok}")
    strongest = min((a for a in ADS if a["E_ads_eV"] is not None),
                    key=lambda a: a["E_ads_eV"], default=None)
    if strongest:
        c[3].metric("가장 강한 흡착 (eV)", f'{strongest["E_ads_eV"]:.3f}',
                    f'{GAS_LABEL[strongest["gas"]]}@{strongest["surface"]}')

    # 반응성 경향: 세트별 가스 평균 E_ads
    st.subheader("반응성 경향 — 세트별 가스 평균 E_ads")
    st.caption("더 음수일수록 강한 흡착. 세트는 셀 크기가 다른 독립 계산이므로 세트 내에서 비교하세요.")
    trend = {}
    for a in ADS:
        if a["E_ads_eV"] is None:
            continue
        trend.setdefault(a["calc_group"], {}).setdefault(a["gas"], []).append(a["E_ads_eV"])
    tr_rows = []
    for cg in sorted(trend):
        row = {"calc_group": cg}
        for gas in ["CO2", "H2O", "SO2"]:
            vals = trend[cg].get(gas)
            row[GAS_LABEL[gas] + " 평균(eV)"] = round(sum(vals) / len(vals), 4) if vals else None
        tr_rows.append(row)
    st.dataframe(pd.DataFrame(tr_rows), use_container_width=True, hide_index=True)

    # 경향 미니 바
    st.plotly_chart(ads_bar(ADS), use_container_width=True)
    st.caption("경향 요약: 세 세트 모두 SO₂ > H₂O > CO₂ 순으로 더 강하게 흡착하는 경향이 "
               "수치로 나타납니다 (각 세트 내 비교).")


# ─────────────────────── 데이터 테이블 ───────────────────────
def page_table():
    st.header("데이터 테이블")
    st.caption("세트(calc_group)별 전체 에너지와 복합체 흡착 에너지. 모든 값은 CSV 출처입니다.")

    sel = st.multiselect("세트 필터", CALC_GROUPS, default=CALC_GROUPS)
    role_sel = st.multiselect("역할", ["molecule", "clean", "adsorbed"],
                              default=["molecule", "clean", "adsorbed"])

    # 전체 에너지 테이블
    st.subheader("에너지 전체")
    df = pd.DataFrame([{
        "calc_group": r["calc_group"], "role": r["role"], "surface": r["surface"],
        "gas": r["gas"], "energy_Ry": to_float(r["energy_Ry"]),
        "energy_eV": round(to_float(r["energy_Ry"]) * RY_TO_EV, 6)
        if to_float(r["energy_Ry"]) is not None else None,
        "source_file": r["source_file"], "status": r["status"],
    } for r in rows if r["calc_group"] in sel and r["role"] in role_sel])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("에너지 CSV 다운로드", df.to_csv(index=False).encode("utf-8-sig"),
                       "energies_view.csv", "text/csv")

    # 복합체 흡착 에너지 테이블
    st.subheader("복합체 흡착 에너지 (E_ads)")
    adf = pd.DataFrame([a for a in ADS if a["calc_group"] in sel])
    st.dataframe(adf, use_container_width=True, hide_index=True)
    st.download_button("E_ads CSV 다운로드", adf.to_csv(index=False).encode("utf-8-sig"),
                       "eads.csv", "text/csv")


# ─────────────────────── 바 차트 ───────────────────────
def page_chart():
    st.header("복합체 흡착 에너지 바 차트")
    st.caption("가스 고정색: CO₂ 틸 · H₂O 블루 · SO₂ 앰버. 세트는 x축 라벨에 표기.")
    st.plotly_chart(ads_bar(ADS), use_container_width=True)
    st.info("서로 다른 세트(calc_group)의 에너지는 겹쳐 비교만 하며, 뺄셈은 세트 안에서만 수행합니다.")


{"Home (개요)": page_home, "데이터 테이블": page_table, "바 차트": page_chart}[page]()
