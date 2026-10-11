"""html_block 및 모든 페이지 HTML 안전 검사 (요구 7-(9))."""

import re

import streamlit as st

from ui.htmlutil import html_block
import ui.htmlutil as htmlutil

import app  # 가드 패치 설치됨

_PRE = re.compile(r"<(pre|code|style|script)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)


def _assert_safe(h, where):
    assert isinstance(h, str)
    assert h.strip().startswith("<"), f"[{where}] '<' 시작 아님: {h[:60]!r}"
    checkable = _PRE.sub(" ", h)
    for ln in checkable.split("\n"):
        assert not ln.startswith("    "), f"[{where}] 4칸 들여쓰기 줄: {ln[:60]!r}"
        assert ln.strip() != "", f"[{where}] 빈 줄 존재: {h[:80]!r}"


# ── html_block 단위 ─────────────────────────────────────────────
def test_html_block_collapses():
    raw = """
    <div class="x">
        <span>hi</span>

        <span>bye</span>
    </div>
    """
    out = html_block(raw)
    assert out.startswith("<div")
    assert "    " not in out and "\n\n" not in out


def test_html_block_preserves_style():
    raw = '<style>\n.card {\n  color: red;\n}\n</style>'
    out = html_block(raw)
    assert "<style>" in out and "color: red" in out


# ── 모든 페이지 HTML 안전 검사 ──────────────────────────────────
def _capture(monkeypatch):
    captured = []
    real = htmlutil.html_block

    def spy(s):
        out = real(s)
        captured.append(out)
        return out

    monkeypatch.setattr(htmlutil, "html_block", spy)
    import ui.components as _C
    monkeypatch.setattr(_C, "html_block", spy)
    monkeypatch.setattr(app.landing, "html_block", spy)
    monkeypatch.setattr(app, "_html_block", spy)
    return captured


import pytest


@pytest.mark.parametrize("page_name", list(app.PAGES.keys()))
def test_pages_emit_safe_html(monkeypatch, page_name):
    st.session_state["entered"] = True
    st.session_state["current_page"] = page_name
    cap = _capture(monkeypatch)
    app.PAGES[page_name]()
    assert cap, f"{page_name}: HTML 호출 없음"
    for i, h in enumerate(cap):
        _assert_safe(h, f"{page_name}#{i}")


def test_landing_emits_safe_html(monkeypatch):
    cap = _capture(monkeypatch)
    app.landing.render(n_ead=4, n_models_active=0, n_models_total=4)
    assert cap
    for i, h in enumerate(cap):
        _assert_safe(h, f"landing#{i}")
