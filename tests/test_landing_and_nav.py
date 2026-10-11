"""시작 화면/내비게이션 구조 테스트 (Phase 1).

Streamlit 위젯 자체는 테스트하지 않고, 순수 로직(브랜딩·nav 구조·landing 입력)만 검증한다.
"""

from ui import branding as B
from ui import nav as NAV


def test_branding_constants():
    assert B.PROJECT_TITLE == "배가스 맞춤형 Ti₂C MXene 표면 설계 플랫폼"
    assert B.TEAM_NAME == "RE:ACT"
    assert B.SCHOOL == "울산대학교"
    assert B.DEPT == "에너지화학공학부"
    assert B.EVENT == "2026 UoU 창의적 종합설계 경진대회"
    assert B.MEMBERS == []  # 비어 있음 → 어디에도 표시하지 않음
    assert B.has_members() is False


def test_wordmark_colon_accent_only():
    wm = B.wordmark(on_dark=True)
    # 콜론만 앰버(#D97706), 약자 뜻을 지어붙이지 않음(텍스트는 RE:ACT 그대로)
    assert "RE" in wm and "ACT" in wm
    assert "#D97706" in wm  # 콜론 강조색
    # 약자 풀이 같은 문구가 들어가면 안 됨
    assert "Research" not in wm and "Reaction" not in wm


def test_footer_text_no_fabrication():
    f = B.footer_text()
    assert f == "RE:ACT · 울산대학교 에너지화학공학부 · Quantum ESPRESSO, PBE-D3"


def test_nav_categories_structure():
    cats = list(NAV.CATEGORIES.keys())
    assert cats == ["홈", "분석", "설계", "데이터", "모델", "자료"]
    # 각 카테고리 페이지 수 (요구 구조)
    assert NAV.CATEGORIES["분석"] == ["정방향 검증", "표면 비교", "경쟁 흡착 비교"]
    assert NAV.CATEGORIES["데이터"] == [
        "데이터 레지스트리", ".out 파일 검사기", "계산 작업 관리", "무결성 점검"]
    assert NAV.CATEGORIES["모델"] == ["모델 품질", "잠금 해제 로드맵"]


def test_nav_category_of():
    assert NAV.category_of("Overview") == "홈"
    assert NAV.category_of("역방향 추천") == "설계"
    assert NAV.category_of("용어집") == "자료"
    # 모든 페이지가 정확히 한 카테고리에 속함
    seen = NAV.all_pages()
    assert len(seen) == len(set(seen))  # 중복 없음


def test_landing_cta_sets_entered(monkeypatch):
    """'플랫폼 시작하기' 클릭(button True) 시 entered=True 로 전이한다."""
    import ui.landing as L

    class _Session(dict):
        pass

    session = _Session()
    clicks = iter([True, False])  # 첫 버튼(시작하기)=True

    class _Col:
        def button(self, *a, **k):
            return next(clicks)

    def fake_columns(spec):
        n = spec if isinstance(spec, int) else len(spec)
        return [_Col() for _ in range(n)]

    monkeypatch.setattr(L.st, "markdown", lambda *a, **k: None)
    monkeypatch.setattr(L.st, "columns", fake_columns)
    monkeypatch.setattr(L.st, "session_state", session)
    monkeypatch.setattr(L.st, "rerun", lambda: None)

    L.render(n_ead=4, n_models_active=0, n_models_total=3)
    assert session.get("entered") is True


def test_landing_strip_uses_passed_values(monkeypatch):
    """landing.render는 전달받은 수치만 쓰고 하드코딩하지 않는다."""
    import ui.landing as L
    captured = {}

    class _StubCol:
        def button(self, *a, **k):
            return False

    def fake_markdown(body, **k):
        captured["html"] = captured.get("html", "") + str(body)

    def fake_columns(spec):
        n = spec if isinstance(spec, int) else len(spec)
        return [_StubCol() for _ in range(n)]

    monkeypatch.setattr(L.st, "markdown", fake_markdown)
    monkeypatch.setattr(L.st, "columns", fake_columns)

    L.render(n_ead=4, n_models_active=0, n_models_total=3)
    html = captured["html"]
    assert ">4</span>건" in html          # 전달한 n_ead 사용
    assert "0/3" in html                   # 전달한 활성/전체 사용
    # 가상 성능/수상 문구가 없어야 함
    for bad in ["정확도", "수상", "인증", "최고", "state-of-the-art"]:
        assert bad not in html
