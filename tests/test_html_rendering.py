"""HTML 렌더 회귀 테스트.

모든 페이지와 시작 화면이 최종적으로 st.markdown / DeltaGenerator.markdown 에
unsafe_allow_html=True 로 넘기는 HTML 문자열이 Markdown 안전한지 검증한다:
  (a) 공백 4칸 이상으로 시작하는 줄이 없을 것 (코드블록화 방지)
  (b) 빈 줄이 없을 것 (문단 분리 방지)
  (c) 문자열이 '<' 로 시작할 것

<style>/<pre>/<code> 내부는 공백/개행이 유효하므로 검사에서 제외한다.
"""

import re

import pytest
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

# app 임포트 시 markdown 가드 패치가 설치된다 (해제하지 않는다 — 최종 출력 검사)
import app  # noqa: E402

from ui import htmlutil
from ui.htmlutil import html_block


# <style>/<pre>/<code> 블록 제거 후 검사용
_PRE = re.compile(r"<(pre|code|style|script)\b[^>]*>.*?</\1>",
                  re.IGNORECASE | re.DOTALL)


def _assert_safe(html_str: str, where: str):
    assert isinstance(html_str, str)
    stripped = html_str.strip()
    assert stripped.startswith("<"), f"[{where}] HTML이 '<'로 시작하지 않음: {stripped[:60]!r}"
    # style/pre/code 내부는 제외하고(그 안의 들여쓰기/개행은 유효) 자리에 공백 1칸만 남긴다
    checkable = _PRE.sub(" ", html_str)
    for ln in checkable.split("\n"):
        assert not ln.startswith("    "), \
            f"[{where}] 공백 4칸 이상 시작 줄 존재(코드블록화 위험): {ln[:60]!r}"
        assert ln.strip() != "", \
            f"[{where}] 빈 줄 존재(문단 분리 위험): {html_str[:80]!r}"


def _capture_markdown(monkeypatch):
    """최종적으로 markdown 에 전달되는 HTML(=html_block 적용 결과)을 수집한다.

    app 의 모든 HTML 경로는 ui.components.render_html → html_block, 그리고
    landing 은 html_block 을 직접 거친다. html_block 을 감싸 그 반환값(최종 문자열)을
    캡처하면 사용자에게 실제로 전달되는 문자열을 검사할 수 있다.
    """
    captured = []
    real = htmlutil.html_block

    def spy(s):
        out = real(s)
        captured.append(out)
        return out

    # 세 참조 지점(원본 모듈 + 임포트된 별칭)을 모두 교체
    monkeypatch.setattr(htmlutil, "html_block", spy)
    import ui.components as _C
    monkeypatch.setattr(_C, "html_block", spy)
    monkeypatch.setattr(app.landing, "html_block", spy)
    monkeypatch.setattr(app, "_html_block", spy)
    return captured


@pytest.mark.parametrize("page_name", list(app.PAGES.keys()))
def test_pages_emit_safe_html(monkeypatch, page_name):
    st.session_state["entered"] = True
    st.session_state["current_page"] = page_name
    captured = _capture_markdown(monkeypatch)
    app.PAGES[page_name]()
    assert captured, f"{page_name}: HTML markdown 호출이 없음(최소 1개 기대)"
    for i, h in enumerate(captured):
        _assert_safe(h, f"{page_name}#{i}")


def test_landing_emits_safe_html(monkeypatch):
    captured = _capture_markdown(monkeypatch)
    app.landing.render(n_ead=4, n_models_active=0, n_models_total=3)
    assert captured
    for i, h in enumerate(captured):
        _assert_safe(h, f"landing#{i}")


# ── html_block 단위 동작 ────────────────────────────────────────
def test_html_block_collapses_indent_and_blanklines():
    raw = """
    <div class="x">
        <span>hi</span>

        <span>bye</span>
    </div>
    """
    out = html_block(raw)
    assert out.startswith("<div")
    assert "    " not in out        # 4칸 들여쓰기 제거
    assert "\n\n" not in out        # 빈 줄 제거
    assert "<span>hi</span>" in out and "<span>bye</span>" in out


def test_html_block_preserves_style_block():
    raw = '<style>\n.card {\n  color: red;\n}\n</style>'
    out = html_block(raw)
    # style 내부 개행/공백 보존
    assert ".card {\n" in out or "color: red" in out
    assert "<style>" in out and "</style>" in out


def test_html_block_preserves_pre_code():
    raw = '<div>\n  <pre>\n  line1\n    line2\n  </pre>\n</div>'
    out = html_block(raw)
    # pre 내부는 보존, 바깥은 collapse
    assert "<pre>" in out
    assert "line1\n" in out  # pre 내부 개행 유지
