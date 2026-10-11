"""HTML 블록 정규화 헬퍼.

Streamlit의 st.markdown(unsafe_allow_html=True)은 Markdown 파서를 먼저 거치므로,
- 각 줄이 공백 4칸 이상으로 시작하면 '코드 블록'으로,
- 빈 줄은 '문단 구분'으로
해석되어 HTML이 그대로 글자로 노출되거나 레이아웃이 깨진다.

html_block()은 각 줄의 앞뒤 공백을 제거하고 빈 줄을 삭제해 한 덩어리로 만든다.
단, <pre>...</pre> 또는 <code>...</code> 내부는 공백/개행이 의미를 가지므로 보존한다.
"""

from __future__ import annotations

import re

# <pre>, <code>, <style>, <script> 블록을 통째로 캡처 (대소문자 무시, 여러 줄)
# 이 안쪽은 공백/개행이 의미를 가지므로 collapse 대상에서 제외한다.
_PRESERVE_RE = re.compile(
    r"(<(pre|code|style|script)\b[^>]*>.*?</\2>)", re.IGNORECASE | re.DOTALL)


def html_block(html: str) -> str:
    """여러 줄 HTML을 Markdown 안전한 한 덩어리로 정규화한다.

    - <pre>/<code>/<style>/<script> 바깥: 줄 단위 strip 후 빈 줄 제거, 공백 없이 이어 붙임.
    - 그 안쪽: 공백·개행을 그대로 보존.
    """
    low = html.lower()
    if all(t not in low for t in ("<pre", "<code", "<style", "<script")):
        return _collapse(html)

    # 보존 구간을 플레이스홀더로 치환 → 정규화 → 복원
    preserved: list[str] = []

    def _stash(m: re.Match) -> str:
        preserved.append(m.group(1))
        return f"\x00PRE{len(preserved) - 1}\x00"

    stashed = _PRESERVE_RE.sub(_stash, html)
    collapsed = _collapse(stashed)
    for i, block in enumerate(preserved):
        collapsed = collapsed.replace(f"\x00PRE{i}\x00", block)
    return collapsed


def _collapse(text: str) -> str:
    """줄 단위 strip + 빈 줄 제거 후 공백 없이 이어 붙인다."""
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln != ""]
    return "".join(lines)
