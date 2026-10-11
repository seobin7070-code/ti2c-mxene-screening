"""시작 화면 (랜딩) — 사이드바 없는 전체 화면.

'플랫폼 시작하기' 클릭 시 st.session_state['entered']=True 로 Overview 진입.
상태 스트립 수치는 core 함수 결과를 그대로 받는다 (하드코딩 금지).
"""

from __future__ import annotations

import streamlit as st

from ui import branding as B
from ui import illustrations as ILL
from ui import tokens as T


def render(n_ead: int, n_models_active: int, n_models_total: int) -> None:
    """시작 화면을 렌더한다. 상태 스트립은 전달받은 수치만 표시한다."""
    tri = ILL.composition_triangle(size=28)
    wm = B.wordmark(on_dark=True, size=22)

    # 로고 이미지는 파일이 있을 때만 (외부 URL 금지, 여기서는 텍스트 워드마크 사용)
    members_html = ""
    if B.has_members():
        members_html = ('<div style="margin-top:4px">'
                        + " · ".join(B.MEMBERS) + "</div>")

    values = (
        f'<div class="val-item"><span class="val-ic">{ILL.value_icon_water()}</span>'
        f'<span class="val-t">수분·SO₂ 경쟁 조건 고려</span></div>'
        f'<div class="val-item"><span class="val-ic">{ILL.value_icon_source()}</span>'
        f'<span class="val-t">출처가 보이는 계산</span></div>'
        f'<div class="val-item"><span class="val-ic">{ILL.value_icon_explore()}</span>'
        f'<span class="val-t">적은 계산으로 조성 탐색</span></div>'
    )

    st.markdown(
        f'''
<div class="landing-wrap">
  {ILL.molecule_pattern()}
  <div class="landing-inner">
    <div class="landing-top">
      <div class="lt-left">{tri}{wm}</div>
      <div class="landing-event">{B.EVENT}</div>
    </div>

    <div class="landing-hero">
      <div class="landing-hero-left">
        <div class="landing-title">{B.PROJECT_TITLE}</div>
        <div class="landing-sub">DFT 계산과 Active Learning으로 CO₂ 선택 포집 표면 조성을
        탐색합니다.</div>
      </div>
      <div class="landing-hero-right">
        <div>{ILL.landing_hero(animate=True)}
        <div class="landing-caption">개념도 — 실제 계산 구조·결과가 아님</div></div>
      </div>
    </div>

    <div class="landing-values">{values}</div>

    <div class="landing-strip">현재 등록된 계산: 흡착 에너지
      <span class="mono">{n_ead}</span>건 · 지표 모델 활성
      <span class="mono">{n_models_active}/{n_models_total}</span></div>

    <div class="landing-foot">
      {B.SCHOOL} · {B.DEPT} · {B.wordmark(on_dark=True, size=13)}
      {members_html}
    </div>
  </div>
</div>
''',
        unsafe_allow_html=True,
    )

    # CTA 버튼 (landing-inner 위에 겹쳐 배치하기 위해 컨테이너 바로 아래 둔다)
    c1, c2, _ = st.columns([1, 1, 3])
    if c1.button("플랫폼 시작하기", type="primary", use_container_width=True):
        st.session_state["entered"] = True
        st.rerun()
    if c2.button("방법론 먼저 보기", use_container_width=True):
        st.session_state["entered"] = True
        st.session_state["_nav"] = "방법론"
        st.rerun()
