"""core.report 테스트 — 해시 포함, 가상 내용 없음, pending은 '데이터 없음'."""

import os

from core.loader import load_energies
from core import report as RP

HERE = os.path.dirname(__file__)
ENERGIES = os.path.join(HERE, "..", "data", "energies.csv")


def _data(ead=None, pending=None, flue=None):
    entries = load_energies(ENERGIES).entries
    return RP.build_report_data(entries, ead or [], pending or [], flue or {}, ENERGIES)


def test_report_includes_hash_and_time():
    d = _data()
    assert len(d["snapshot_sha256"]) == 64  # SHA-256
    assert "T" in d["generated_at"]          # ISO 시각
    md = RP.to_markdown(d)
    assert d["snapshot_sha256"] in md
    html = RP.to_html(d)
    assert d["snapshot_sha256"] in html


def test_report_energy_table_present():
    d = _data()
    md = RP.to_markdown(d)
    assert "A/mol/CO2" in md
    assert "-94.82308357" in md  # 기존 값 그대로


def test_report_empty_sections_say_no_data():
    d = _data(ead=[], pending=[], flue={})
    md = RP.to_markdown(d)
    # E_ad / pending / 배가스 섹션 모두 '데이터 없음'
    assert md.count("데이터 없음") >= 3
    html = RP.to_html(d)
    assert "데이터 없음" in html


def test_report_no_fabricated_content():
    d = _data()
    md = RP.to_markdown(d) + RP.to_html(d)
    for bad in ["수상", "인증", "state-of-the-art", "고객", "99%", "최고 성능"]:
        assert bad not in md


def test_report_includes_limitation_text():
    d = _data()
    assert "σ" in d["limitations"]
    assert "σ" in RP.to_markdown(d)


def test_report_flue_gas_memo_when_present():
    d = _data(flue={"co2": 12.0, "h2o": 8.0, "so2": 0.1, "temp": 120.0, "memo": "테스트 메모"})
    md = RP.to_markdown(d)
    assert "테스트 메모" in md
    assert "반영되지 않는 시나리오 메모" in md
