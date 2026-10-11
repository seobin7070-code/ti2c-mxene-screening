"""Plotly 차트 헬퍼 — 배경 투명, 가스 고정색, 축 단위.

삼원 조성 지도는 PDF 6.3 삼각형 좌표(x = xF + 0.5·xOH, y = (√3/2)·xOH)를 쓴다.
"""

from __future__ import annotations

import math

import plotly.graph_objects as go

from ui import tokens as T
from core.coords import to_triangle_xy

_FONT = "Pretendard, system-ui, sans-serif"
_SQRT3_2 = math.sqrt(3.0) / 2.0


def _base_layout(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(
        template="none",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=_FONT, size=13, color=T.TEXT),
        margin=dict(l=20, r=20, t=30, b=20),
        height=height,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_xaxes(gridcolor=T.BORDER, zeroline=False, linecolor=T.BORDER)
    fig.update_yaxes(gridcolor=T.BORDER, zeroline=False, linecolor=T.BORDER)
    return fig


def ead_bar(rows: list[dict], png: bool = False) -> go.Figure:
    """계산 완료된 E_ads 막대차트. rows: [{surface, gas, e_ad_ev}]. 가스 고정색."""
    fig = go.Figure()
    for gas in ["CO2", "H2O", "SO2"]:
        g = [r for r in rows if r["gas"] == gas]
        if not g:
            continue
        m = T.gas_meta(gas)
        fig.add_bar(
            x=[r["surface"] for r in g], y=[r["e_ad_ev"] for r in g],
            name=m["label"], marker_color=m["color"],
            text=[f'{r["e_ad_ev"]:.3f}' for r in g], textposition="outside",
        )
    fig = _base_layout(fig, height=360)
    fig.update_yaxes(title_text="E_ads (eV)")
    fig.update_xaxes(title_text="표면")
    fig.update_layout(barmode="group")
    if png:
        fig.update_layout(paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                          font=dict(color="#334155"),
                          title=dict(text="계산된 흡착 에너지 (E_ads)", x=0.02),
                          margin=dict(l=50, r=30, t=50, b=50))
    return fig


def _triangle_outline() -> list:
    """삼각형 테두리 (O(0,0) · F(1,0) · OH(0.5,√3/2))."""
    xs = [0, 1, 0.5, 0]
    ys = [0, 0, _SQRT3_2, 0]
    return [go.Scatter(x=xs, y=ys, mode="lines",
                       line=dict(color=T.BORDER, width=1.5),
                       hoverinfo="skip", showlegend=False)]


def composition_map(markers: list[dict], metric_label: str, unit: str = "eV") -> go.Figure:
    """삼원 조성 지도 (PDF 6.3).

    markers: [{xO,xF,xOH, kind:'computed'|'planned'|'unconfirmed',
               value(opt), label}]. value 가 있으면 컬러 매핑.
    """
    fig = go.Figure(_triangle_outline())

    # 꼭짓점 라벨
    fig.add_scatter(x=[0, 1, 0.5], y=[-0.06, -0.06, _SQRT3_2 + 0.05],
                    text=["-O", "-F", "-OH"], mode="text",
                    textfont=dict(size=14, color=T.TEXT), hoverinfo="skip",
                    showlegend=False)

    computed = [m for m in markers if m.get("kind") == "computed"]
    planned = [m for m in markers if m.get("kind") == "planned"]
    unconf = [m for m in markers if m.get("kind") == "unconfirmed"]

    def xy(ms):
        xs, ys = [], []
        for m in ms:
            x, y = to_triangle_xy(m["xO"], m["xF"], m["xOH"])
            xs.append(x); ys.append(y)
        return xs, ys

    # 계산값 ◆ (채움, 값이 있으면 컬러바)
    if computed:
        xs, ys = xy(computed)
        vals = [m.get("value") for m in computed]
        has_val = all(v is not None for v in vals) and len(vals) > 0
        fig.add_scatter(
            x=xs, y=ys, mode="markers",
            marker=dict(symbol="diamond", size=16,
                        color=vals if has_val else T.PRIMARY,
                        colorscale="Teal" if has_val else None,
                        showscale=has_val,
                        colorbar=dict(title=f"{metric_label} ({unit})", thickness=12)
                        if has_val else None,
                        line=dict(width=1, color="#fff")),
            text=[m.get("label", "") for m in computed],
            name="계산값 ◆",
            hovertemplate="%{text}<extra></extra>",
        )
    # 계획 조성 (빈 원)
    if planned:
        xs, ys = xy(planned)
        fig.add_scatter(x=xs, y=ys, mode="markers",
                        marker=dict(symbol="circle-open", size=13,
                                    color=T.PRIMARY, line=dict(width=2)),
                        text=[m.get("label", "") for m in planned],
                        name="계획(빈 원)", hovertemplate="%{text}<extra></extra>")
    # 미확정 (점선 느낌의 x)
    if unconf:
        xs, ys = xy(unconf)
        fig.add_scatter(x=xs, y=ys, mode="markers",
                        marker=dict(symbol="x-thin", size=12,
                                    color=T.STATUS["suspect"]["color"],
                                    line=dict(width=2)),
                        text=[m.get("label", "") for m in unconf],
                        name="조성 미확정", hovertemplate="%{text}<extra></extra>")

    fig.update_layout(
        template="none", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=_FONT, size=13, color=T.TEXT),
        height=460, margin=dict(l=20, r=20, t=30, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis=dict(visible=False, range=[-0.1, 1.1]),
        yaxis=dict(visible=False, range=[-0.15, _SQRT3_2 + 0.15],
                   scaleanchor="x", scaleratio=1),
    )
    return fig


def adsorption_overview_bar(rows: list[dict], png: bool = False) -> go.Figure:
    """세트별 복합체 E_ads 비교 바 차트 (가스 고정색, x축=표면, facet=세트는 색/패턴 대신 그룹).

    rows: all_adsorption_rows() 결과. 세트는 x축 라벨에 포함하고, 가스별로 trace 분리.
    서로 다른 calc_group을 '겹쳐 비교'하되 뺄셈은 섞지 않았음을 캡션에서 안내한다.
    """
    ok = [r for r in rows if r["ok"]]
    fig = go.Figure()
    for gas in ["CO2", "H2O", "SO2"]:
        g = [r for r in ok if r["gas"] == gas]
        if not g:
            continue
        m = T.gas_meta(gas)
        fig.add_bar(
            x=[f'{r["surface"]}<br>({r["calc_group"]})' for r in g],
            y=[r["E_ads_eV"] for r in g],
            name=m["label"], marker_color=m["color"],
            text=[f'{r["E_ads_eV"]:.3f}' for r in g], textposition="outside",
            customdata=[r["source_file"] for r in g],
            hovertemplate="%{x}<br>E_ads=%{y:.4f} eV<br>출처=%{customdata}<extra></extra>",
        )
    fig = _base_layout(fig, height=420)
    fig.update_yaxes(title_text="E_ads (eV)")
    fig.update_xaxes(title_text="표면 (calc_group)")
    fig.update_layout(barmode="group")
    if png:
        fig.update_layout(paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                          font=dict(color="#334155"),
                          title=dict(text="복합체 흡착 에너지 (E_ads)", x=0.02),
                          margin=dict(l=50, r=30, t=50, b=70))
    return fig


def parity_plot(y_true, y_pred, metric: str) -> go.Figure:
    """예측-실측 산점도 (LOOCV)."""
    lo = min(min(y_true), min(y_pred))
    hi = max(max(y_true), max(y_pred))
    pad = (hi - lo) * 0.1 or 0.1
    fig = go.Figure()
    fig.add_scatter(x=[lo - pad, hi + pad], y=[lo - pad, hi + pad],
                    mode="lines", line=dict(color=T.BORDER, dash="dash"),
                    name="y = x", hoverinfo="skip")
    fig.add_scatter(x=y_true, y=y_pred, mode="markers",
                    marker=dict(color=T.PRIMARY, size=9),
                    name="LOOCV 예측",
                    hovertemplate="실측=%{x:.3f}<br>예측=%{y:.3f}<extra></extra>")
    fig = _base_layout(fig, height=380)
    fig.update_xaxes(title_text=f"실측 {metric} (eV)")
    fig.update_yaxes(title_text=f"예측 {metric} (eV)")
    return fig
