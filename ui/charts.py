"""Plotly 차트 헬퍼 — 배경 투명, 연한 격자, 가스 고정색, 축 단위 필수."""

from __future__ import annotations

import plotly.graph_objects as go

from ui import tokens as T

_FONT = "Pretendard, system-ui, sans-serif"


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


def ead_bar(rows: list[dict]) -> go.Figure:
    """계산 완료된 E_ad 요약 막대차트. rows: [{surface, gas, e_ad_ev}]. 가스 색 고정."""
    fig = go.Figure()
    # 가스별로 trace 분리 → 범례에 가스 고정색
    for gas in ["CO2", "H2O", "SO2"]:
        g_rows = [r for r in rows if r["gas"] == gas]
        if not g_rows:
            continue
        m = T.gas_meta(gas)
        fig.add_bar(
            x=[f'{r["surface"]}' for r in g_rows],
            y=[r["e_ad_ev"] for r in g_rows],
            name=m["label"],
            marker_color=m["color"],
            text=[f'{r["e_ad_ev"]:.3f}' for r in g_rows],
            textposition="outside",
        )
    fig = _base_layout(fig, height=360)
    fig.update_yaxes(title_text="E_ad (eV)")
    fig.update_xaxes(title_text="표면")
    fig.update_layout(barmode="group")
    return fig


def ternary_scan(grid, mu, sigma, metric: str) -> go.Figure:
    """조성 삼각도. 색=μ, 크기=σ(참고용). 호버에 조성/μ/σ."""
    smax = float(sigma.max()) or 1.0
    fig = go.Figure(go.Scatterternary(
        a=grid[:, 0], b=grid[:, 1], c=grid[:, 2],
        mode="markers",
        marker=dict(
            size=sigma / smax * 14 + 4,
            color=mu, colorscale="Teal", showscale=True,
            colorbar=dict(title=f"μ ({metric})", thickness=12),
            line=dict(width=0),
        ),
        hovertemplate=(
            "xO=%{a:.2f} · xF=%{b:.2f} · xOH=%{c:.2f}<br>"
            "μ=%{marker.color:.3f}<extra></extra>"
        ),
    ))
    fig.update_layout(
        template="none",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=_FONT, size=13, color=T.TEXT),
        height=460,
        margin=dict(l=30, r=30, t=40, b=30),
        ternary=dict(
            bgcolor="rgba(0,0,0,0)",
            aaxis=dict(title="xO", gridcolor=T.BORDER, linecolor=T.BORDER),
            baxis=dict(title="xF", gridcolor=T.BORDER, linecolor=T.BORDER),
            caxis=dict(title="xOH", gridcolor=T.BORDER, linecolor=T.BORDER),
        ),
    )
    return fig


def ead_bar_png(rows: list[dict]) -> go.Figure:
    """PNG 내보내기용 E_ad 막대차트. 배경 흰색, 가스 고정색 유지."""
    fig = ead_bar(rows)
    fig.update_layout(
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(color="#334155"),
        title=dict(text="계산 완료된 흡착 에너지 (E_ad)", x=0.02, xanchor="left",
                   font=dict(size=15)),
        margin=dict(l=50, r=30, t=50, b=50),
    )
    return fig


def surface_compare_bar(rows: list[dict], gas: str, png: bool = False) -> go.Figure:
    """표면 비교 막대차트. rows: [{surface, e_ad_ev}] (단일 가스). 가스 고정색."""
    m = T.gas_meta(gas)
    fig = go.Figure()
    fig.add_bar(
        x=[r["surface"] for r in rows],
        y=[r["e_ad_ev"] for r in rows],
        marker_color=m["color"], name=m["label"],
        text=[f'{r["e_ad_ev"]:.3f}' for r in rows], textposition="outside",
    )
    fig = _base_layout(fig, height=360)
    fig.update_yaxes(title_text="E_ad (eV)")
    fig.update_xaxes(title_text="표면")
    if png:
        fig.update_layout(paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                          font=dict(color="#334155"),
                          title=dict(text=f"표면 비교 — {m['label']} 흡착", x=0.02),
                          margin=dict(l=50, r=30, t=50, b=50))
    return fig


def competitive_bar(by_surface: dict, png: bool = False) -> go.Figure:
    """경쟁 흡착 그룹 막대. by_surface: {surface: {gas: e_ad_ev}}. 가스별 trace."""
    surfaces = list(by_surface.keys())
    fig = go.Figure()
    for gas in ["CO2", "H2O", "SO2"]:
        m = T.gas_meta(gas)
        ys = [by_surface[s].get(gas) for s in surfaces]
        if all(v is None for v in ys):
            continue
        fig.add_bar(
            x=surfaces, y=ys, name=m["label"], marker_color=m["color"],
            text=[f'{v:.3f}' if v is not None else "" for v in ys],
            textposition="outside",
        )
    fig = _base_layout(fig, height=380)
    fig.update_yaxes(title_text="E_ad (eV)")
    fig.update_xaxes(title_text="표면")
    fig.update_layout(barmode="group")
    if png:
        fig.update_layout(paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                          font=dict(color="#334155"),
                          title=dict(text="경쟁 흡착 비교 (가스별 E_ad)", x=0.02),
                          margin=dict(l=50, r=30, t=50, b=50))
    return fig


def parity_plot(y_true, y_pred, metric: str) -> go.Figure:
    """예측-실측 산점도 (LOOCV)."""
    lo = min(min(y_true), min(y_pred))
    hi = max(max(y_true), max(y_pred))
    pad = (hi - lo) * 0.1 or 0.1
    fig = go.Figure()
    fig.add_scatter(
        x=[lo - pad, hi + pad], y=[lo - pad, hi + pad],
        mode="lines", line=dict(color=T.BORDER, dash="dash"),
        name="y = x", hoverinfo="skip",
    )
    fig.add_scatter(
        x=y_true, y=y_pred, mode="markers",
        marker=dict(color=T.PRIMARY, size=9, line=dict(width=0)),
        name="LOOCV 예측",
        hovertemplate="실측=%{x:.3f}<br>예측=%{y:.3f}<extra></extra>",
    )
    fig = _base_layout(fig, height=380)
    fig.update_xaxes(title_text=f"실측 {metric} (eV)")
    fig.update_yaxes(title_text=f"예측 {metric} (eV)")
    return fig
