"""시작 화면 (랜딩) — PDF [5] 명세.

'플랫폼 시작하기' 클릭 시 st.session_state['entered']=True 후 정방향 검증 진입.
'적용 범위 보기'는 입장하지 않고 PDF 1장 적용 범위 문구를 펼쳐 보여준다.
상태 스트립 수치(흡착 에너지 N건 · GPR 활성 0/4)는 core 결과를 그대로 받는다.

landing 은 일반 블록으로 렌더하고 CTA(st.button)를 자연 흐름에 둔다(오버레이 가림 방지).
시작 화면 전용 버튼 CSS 는 body.landing-active 스코프로만 적용한다.
"""

from __future__ import annotations

import streamlit as st

from ui import branding as B
from ui import illustrations as ILL
from ui.htmlutil import html_block
from core.scope import APPLICABILITY


def _enter(nav: str | None = None) -> None:
    st.session_state["entered"] = True
    if nav:
        st.session_state["_nav"] = nav
    st.rerun()


def should_skip_via_query() -> bool:
    """URL에 ?enter=1 이 있으면 시작 화면을 건너뛴다 (안전장치)."""
    try:
        qp = st.query_params
        val = qp.get("enter")
    except Exception:
        return False
    if isinstance(val, (list, tuple)):
        val = val[0] if val else None
    return str(val) in ("1", "true", "True")


def render(n_ead: int, n_models_active: int, n_models_total: int) -> None:
    """시작 화면을 렌더한다."""
    if should_skip_via_query():
        _enter()
        return

    tri = ILL.composition_triangle(size=28)
    wm = B.wordmark(on_dark=True, size=22)

    values = (
        f'<div class="val-item"><span class="val-ic">{ILL.value_icon_water()}</span>'
        f'<span class="val-t">수분·SO₂ 경쟁 조건 고려</span></div>'
        f'<div class="val-item"><span class="val-ic">{ILL.value_icon_source()}</span>'
        f'<span class="val-t">출처가 보이는 계산</span></div>'
        f'<div class="val-item"><span class="val-ic">{ILL.value_icon_explore()}</span>'
        f'<span class="val-t">적은 계산으로 조성 탐색</span></div>'
    )

    # body 에 landing-active 클래스 부여 (버튼 CSS 스코프)
    st.markdown(
        '<div id="landing-flag"></div>'
        "<script>document.body && document.body.classList.add('landing-active');</script>",
        unsafe_allow_html=True,
    )

    # ── 상단 바 + 히어로 ──
    st.markdown(
        html_block(f'''
<div class="landing-wrap">
  {ILL.molecule_pattern()}
  <div class="landing-inner">
    <div class="landing-top">
      <div class="lt-left">{tri}{wm}</div>
      <div class="landing-top-right">
        <span class="landing-event">{B.EVENT}</span>
        <a class="landing-enter-link" href="?enter=1" target="_self">입장 →</a>
      </div>
    </div>
    <div class="landing-hero">
      <div class="landing-hero-left">
        <div class="landing-title">{B.PROJECT_TITLE}</div>
        <div class="landing-sub">DFT 계산과 Active Learning으로 CO₂ 선택 포집 표면 조성을 탐색합니다.</div>
      </div>
      <div class="landing-hero-right">
        <div>{ILL.landing_hero(animate=True)}
        <div class="landing-caption">개념도 — 실제 계산 구조·결과가 아님</div></div>
      </div>
    </div>
  </div>
</div>
'''),
        unsafe_allow_html=True,
    )

    # ── CTA 버튼 ──
    st.markdown('<div class="landing-cta-anchor"></div>', unsafe_allow_html=True)
    c1, c2, _sp = st.columns([1.1, 1.1, 2.8])
    if c1.button("플랫폼 시작하기", type="primary", use_container_width=True,
                 key="cta_start"):
        _enter()
    if c2.button("적용 범위 보기", use_container_width=True, key="cta_scope"):
        st.session_state["show_scope"] = not st.session_state.get("show_scope", False)

    if st.session_state.get("show_scope"):
        st.markdown(
            html_block(f'<div class="landing-wrap landing-wrap-cont">'
                       f'<div class="landing-inner landing-inner-cont">'
                       f'<div class="landing-scope">적용 범위 — {APPLICABILITY}</div>'
                       f'</div></div>'),
            unsafe_allow_html=True,
        )

    # ── 가치 카드 + 상태 스트립 + 푸터 ──
    st.markdown(
        html_block(f'''
<div class="landing-wrap landing-wrap-cont">
  <div class="landing-inner landing-inner-cont">
    <div class="landing-values">{values}</div>
    <div class="landing-strip">등록된 흡착 에너지
      <span class="mono">{n_ead}</span>건 · GPR 활성 모델
      <span class="mono">{n_models_active}/{n_models_total}</span></div>
    <div class="landing-foot">{B.SCHOOL} · {B.DEPT} · {B.wordmark(on_dark=True, size=13)}</div>
  </div>
</div>
'''),
        unsafe_allow_html=True,
    )
