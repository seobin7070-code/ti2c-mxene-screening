"""core.qe_parser 테스트 — 성공/실패/부분 출력, CSV 대조.

파싱 실패 시 추정 없이 사유를 담아야 한다 (데이터 무결성).
"""

import os

from core.qe_parser import parse_out_text, compare_to_csv_energy

FX = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name):
    with open(os.path.join(FX, name), encoding="utf-8") as f:
        return f.read()


def test_parse_success():
    r = parse_out_text(_read("qe_success.out"))
    assert r.total_energy_Ry == -1333.32037072
    assert r.total_energy_8dp == "-1333.32037072"
    assert r.converged is True
    assert r.job_done is True
    assert r.n_atoms == 12
    assert r.ecutwfc == 60.0
    assert r.ecutrho == 480.0
    assert r.nspin == 1
    assert r.kpoints == "5"
    assert r.vdw and "d3" in r.vdw.lower()
    assert any("Ti" in p for p in r.pseudos)
    assert r.errors == []


def test_parse_partial_reports_missing_not_guessed():
    r = parse_out_text(_read("qe_partial.out"))
    # 에너지/수렴/JOB DONE 없음 → None + 사유, 추정 금지
    assert r.total_energy_Ry is None
    assert r.converged is None
    assert r.job_done is False
    assert any("total energy" in e for e in r.errors)
    # 있는 항목은 정상 파싱
    assert r.n_atoms == 12 and r.ecutwfc == 60.0


def test_parse_garbage_fails_gracefully():
    r = parse_out_text(_read("qe_garbage.out"))
    assert r.total_energy_Ry is None
    assert r.n_atoms is None
    assert len(r.errors) >= 1  # 사유가 기록됨


def test_compare_to_csv_match():
    r = parse_out_text(_read("qe_success.out"))
    # CSV의 Ti2CO2 clean 값과 동일
    cmp = compare_to_csv_energy(r, -1333.32037072)
    assert cmp["match"] is True
    assert abs(cmp["diff"]) < 1e-9


def test_compare_to_csv_mismatch():
    r = parse_out_text(_read("qe_success.out"))
    cmp = compare_to_csv_energy(r, -1360.84920315)  # 다른 값
    assert cmp["match"] is False
    assert "불일치" in cmp["reason"]


def test_compare_when_no_energy():
    r = parse_out_text(_read("qe_garbage.out"))
    cmp = compare_to_csv_energy(r, -1.0)
    assert cmp["match"] is None
    assert "읽지 못" in cmp["reason"]
