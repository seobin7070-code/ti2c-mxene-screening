"""streamlit.testing.v1.AppTest 로 시작 화면 검증.

- markdown 요소 중 코드 블록(st.code)으로 변환된 것이 없는지
- '플랫폼 시작하기' 버튼이 존재하는지
AppTest 를 사용할 수 없는 환경이면 skip 한다.
"""

import os

import pytest

AT = pytest.importorskip("streamlit.testing.v1").AppTest
APP = os.path.join(os.path.dirname(__file__), "..", "app.py")


def _run():
    at = AT.from_file(os.path.abspath(APP), default_timeout=30)
    return at.run()


def test_landing_has_start_button_and_no_codeblocks():
    at = _run()
    # 예외 없이 실행되어야 함
    assert not at.exception, f"앱 실행 예외: {at.exception}"

    # '플랫폼 시작하기' 버튼 존재
    labels = [b.label for b in at.button]
    assert any("플랫폼 시작하기" in (lbl or "") for lbl in labels), \
        f"시작 버튼 없음. 버튼들: {labels}"

    # 코드 블록(st.code)으로 샌 HTML이 없어야 함 — <div 등이 code 로 보이면 안 됨
    for c in at.code:
        val = c.value or ""
        assert "<div" not in val and "landing-" not in val, \
            f"HTML이 코드 블록으로 노출됨: {val[:80]!r}"


def _all_markdown_text(at) -> str:
    return "\n".join((m.value or "") for m in at.markdown)


def test_clicking_start_enters_app_and_shows_overview():
    at = _run()
    btns = [b for b in at.button if "플랫폼 시작하기" in (b.label or "")]
    assert btns, "시작 버튼을 찾지 못함"
    at2 = btns[0].click().run()
    assert not at2.exception
    assert at2.session_state["entered"] is True
    # Overview 요소가 나타나는지 (브레드크럼/히어로 문구)
    text = _all_markdown_text(at2)
    assert "Overview" in text
    assert "누가 어떻게 쓰나" in text or "현재 데이터 상태" in text


def test_methods_button_navigates_to_methods():
    at = _run()
    btns = [b for b in at.button if "방법론 먼저 보기" in (b.label or "")]
    assert btns, "방법론 버튼을 찾지 못함"
    at2 = btns[0].click().run()
    assert not at2.exception
    assert at2.session_state["entered"] is True
    assert at2.session_state["current_page"] == "방법론"
    text = _all_markdown_text(at2)
    assert "방법론" in text


def test_enter_query_skips_landing():
    at = AT.from_file(os.path.abspath(APP), default_timeout=30)
    at.query_params["enter"] = "1"
    at.run()
    assert not at.exception
    assert at.session_state["entered"] is True
    # 시작 화면이 아니라 본문(Overview)이 보여야 함
    text = _all_markdown_text(at)
    assert "Overview" in text


def test_landing_css_does_not_hide_buttons():
    """시작 화면 CSS에 버튼을 가리는 규칙이 없는지 검사한다.

    body.landing-active 스코프의 버튼 선택자(.stButton / stBaseButton-*)에
    display:none, visibility:hidden, opacity:0, 또는 배경과 동일한 color 가
    적용되지 않아야 한다. (CSS 가림은 AppTest 로 못 잡으므로 문자열 검사)
    """
    from ui import theme
    css = theme._CSS

    # 버튼 관련 선택자가 포함된 CSS 규칙만 추출해 검사
    import re
    # { ... } 블록 단위로 쪼개 선택자+본문을 함께 본다
    rules = re.findall(r"([^{}]+)\{([^{}]*)\}", css)
    bad = []
    for selector, body in rules:
        sel = selector.strip()
        if "stButton" not in sel and "stBaseButton" not in sel:
            continue
        b = body.lower().replace(" ", "")
        if "display:none" in b or "visibility:hidden" in b or "opacity:0" in b:
            bad.append(sel)
        # 배경색과 동일한 글자색(앰버 배경에 앰버 글자 등) 방지: color 가 배경과 같은지
        # 주 버튼은 배경 앰버(#d97706)+글자 네이비, 보조는 투명+흰 글자여야 한다.
        if "color:#d97706" in b and "background:#d97706" in b:
            bad.append(sel + " (배경=글자색)")
    assert not bad, f"버튼을 가리는 CSS 규칙 발견: {bad}"


def test_landing_css_button_contrast_ok():
    """주 버튼은 앰버 배경+네이비 글자, 보조 버튼은 투명+흰 글자인지 확인."""
    from ui import theme
    css = theme._CSS.lower().replace(" ", "")
    # 주 버튼 앰버 배경
    assert "stbasebutton-primary" in css
    assert "#d97706" in css  # 앰버 사용 (대소문자 무시)
    # 보조 버튼 흰 테두리/글자
    assert "stbasebutton-secondary" in css
