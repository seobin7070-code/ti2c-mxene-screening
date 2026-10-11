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


def test_clicking_start_enters_app():
    at = _run()
    btns = [b for b in at.button if "플랫폼 시작하기" in (b.label or "")]
    assert btns, "시작 버튼을 찾지 못함"
    at2 = btns[0].click().run()
    assert not at2.exception
    assert "entered" in at2.session_state
    assert at2.session_state["entered"] is True
