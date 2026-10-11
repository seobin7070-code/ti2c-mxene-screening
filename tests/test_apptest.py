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
