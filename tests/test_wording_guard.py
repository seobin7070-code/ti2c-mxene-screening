"""PDF 9장 문구 가이드 — 금지 표현이 UI/문구에 없는지 검사.

'실제 선택도/포집량 예측', '피독 확정', '안전 구역', '최적 소재', '합격/불합격'을 쓰지 않는다.
분류 이름은 '우선 검토 / 추가 계산 권장 / 현재 기준 미충족'만 쓴다.
적용 범위 문구는 scope 한 곳에만 둔다.
"""

import os
import glob

FORBIDDEN = ["안전 구역", "최적 소재", "합격", "불합격", "피독 확정"]
# '실제 선택도/포집량 예측'은 긍정문에서만 금지 — 적용범위 문구의 '예측하지 않으며'는 허용
APP_DIR = os.path.join(os.path.dirname(__file__), "..")


def _ui_sources():
    files = glob.glob(os.path.join(APP_DIR, "ui", "*.py"))
    files += [os.path.join(APP_DIR, "app.py")]
    return files


def test_no_forbidden_words_in_ui():
    for path in _ui_sources():
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for word in FORBIDDEN:
            assert word not in text, f"{os.path.basename(path)}에 금지 표현 '{word}' 발견"


def test_classification_labels_only_allowed():
    from core.classify import UNMET, PRIORITY, MORE_CALC
    assert UNMET == "현재 기준 미충족"
    assert PRIORITY == "우선 검토"
    assert MORE_CALC == "추가 계산 권장"


def test_scope_text_single_source():
    from core.scope import APPLICABILITY
    # 적용 범위 핵심 문구가 scope 모듈에 있고, 금지 표현을 포함하지 않음
    assert "0 K" in APPLICABILITY
    assert "상대 비교 지표" in APPLICABILITY
    assert "예측하지 않으며" in APPLICABILITY
