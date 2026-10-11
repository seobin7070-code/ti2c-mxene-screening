"""streamlit.testing.v1.AppTest — 시작 화면·메뉴·데이터 기대 동작 검증."""

import os

import pytest

AT = pytest.importorskip("streamlit.testing.v1").AppTest
APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


def _run():
    return AT.from_file(APP, default_timeout=60).run()


def _md_text(at):
    return "\n".join((m.value or "") for m in at.markdown)


def test_landing_has_start_button():
    at = _run()
    assert not at.exception, f"예외: {at.exception}"
    labels = [b.label for b in at.button]
    assert any("플랫폼 시작하기" in (x or "") for x in labels), f"버튼들: {labels}"


def test_start_enters_forward():
    at = _run()
    btns = [b for b in at.button if "플랫폼 시작하기" in (b.label or "")]
    assert btns
    at2 = btns[0].click().run()
    assert not at2.exception
    assert at2.session_state["entered"] is True
    assert "정방향 검증" in _md_text(at2)


def test_enter_query_skips_landing():
    at = AT.from_file(APP, default_timeout=60)
    at.query_params["enter"] = "1"
    at.run()
    assert not at.exception
    assert at.session_state["entered"] is True
    assert "정방향 검증" in _md_text(at)


def test_all_menu_pages_run():
    at = AT.from_file(APP, default_timeout=60)
    at.query_params["enter"] = "1"
    at.run()
    from ui import nav
    for page in nav.PAGES:
        at.session_state["current_page"] = page
        at.session_state["_nav"] = page
        at2 = at.run()
        assert not at2.exception, f"{page} 실행 예외: {at2.exception}"


def test_P_shows_no_data_on_current_data():
    at = AT.from_file(APP, default_timeout=60)
    at.query_params["enter"] = "1"
    at.session_state["current_page"] = "조성 지도"
    at.run()
    # 조성 지도까지 포함해 예외 없이 실행
    assert not at.exception


def test_gpr_activation_with_threshold3():
    # threshold=3 + Ti2C_FH 확정 → Eads 세 타깃은 활성, Δd(geometry 없음)는 비활성
    from core.loader import load_energies
    from core.composition import load_composition_map
    from core import screening as S
    from core.gpr_model import TARGETS, fit_target, GprModel, GprUnavailable
    from core.settings import load_settings
    base = os.path.join(os.path.dirname(__file__), "..")
    entries = load_energies(os.path.join(base, "data", "energies.csv")).entries
    comp = load_composition_map(os.path.join(base, "data", "composition_map.csv"))
    st = load_settings(os.path.join(base, "config", "settings.json"))
    assert st.min_train_points == 3
    models = {t: fit_target(S.training_points(entries, comp, t), t, st.min_train_points)
              for t in TARGETS}
    # Eads 세 타깃은 학습 데이터 3개 이상 → 활성
    for t in ("Eads_CO2", "Eads_H2O", "Eads_SO2"):
        assert isinstance(models[t], GprModel), f"{t} 비활성"
    # Δd 는 geometry 데이터가 없어 학습점 0개 → 비활성
    assert isinstance(models["Delta_d"], GprUnavailable)


def test_export_report_includes_version_and_loocv():
    """(E) 내보내기 HTML 리포트에 모델·데이터 버전(SHA-256)과 LOOCV 가 포함된다 (명세 6.4)."""
    import importlib
    import pandas as pd
    app = importlib.import_module("app")
    html = app._build_html_report(pd.DataFrame([]))
    assert "모델·데이터 버전" in html
    assert "SHA-256" in html
    assert "LOOCV" in html
    assert "적용 범위" in html          # 기존 적용 범위도 유지


def test_reverse_pareto_mode_renders():
    """(B) 역방향 '우선 검토 후보 탐색 (Pareto)' 모드가 예외 없이 렌더된다."""
    at = AT.from_file(APP, default_timeout=90)
    at.query_params["enter"] = "1"
    at.session_state["current_page"] = "역방향 추천"
    at.run()
    assert not at.exception
    # 모드 라디오를 Pareto 로 전환
    for r in at.radio:
        opts = [str(o) for o in (r.options or [])]
        if any("Pareto" in o for o in opts):
            at2 = r.set_value("우선 검토 후보 탐색 (Pareto)").run()
            assert not at2.exception
            break


def test_map_sigma_tab_renders():
    """(C) 조성 지도 σ 탭이 예외 없이 렌더된다 (명세 6.3)."""
    at = AT.from_file(APP, default_timeout=90)
    at.query_params["enter"] = "1"
    at.session_state["current_page"] = "조성 지도"
    at.run()
    for r in at.radio:
        opts = [str(o) for o in (r.options or [])]
        if any("σ" in o for o in opts):
            at2 = r.set_value("σ(불확실성)").run()
            assert not at2.exception
            break


def test_reverse_next_candidate_section():
    """(D) 역방향 페이지에 '다음 계산 후보' 섹션이 표시된다 (명세 7)."""
    at = AT.from_file(APP, default_timeout=90)
    at.query_params["enter"] = "1"
    at.session_state["current_page"] = "역방향 추천"
    at.run()
    md = "\n".join((m.value or "") for m in at.markdown)
    assert "다음 계산 후보" in md
