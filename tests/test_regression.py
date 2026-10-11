"""회귀 고정 + loader 규칙 테스트 (PDF 명세, 요구 7-(1)(2)(3)(4))."""

import math
import os

from core.loader import load_energies, parse_rows, REQUIRED_COLUMNS
from core.screening import compute_ad_for

HERE = os.path.dirname(__file__)
ENERGIES = os.path.join(HERE, "..", "data", "energies.csv")

# 기존 10개 에너지 값 (Ry) — 불변
LOCKED_RY = {
    "A/mol/CO2": -94.82308357, "A/mol/SO2": -105.27217923,
    "A/clean/Ti2CF2": -1389.76036918, "A/clean/Ti2CO2": -1333.32037072,
    "A/clean/Ti2C_FH": -1360.84920315, "A/clean/Ti2C_OF": -1361.40729499,
    "A/ad/SO2@Ti2CO2": -1438.65823190, "A/ad/CO2@Ti2CF2": -1484.62192566,
    "A/ad/CO2@Ti2C_FH": -1455.70176796, "A/ad/CO2@Ti2C_OF": -1456.27650839,
}
# E_ads 4건 (eV, 셋째 자리)
LOCKED_EADS = {
    ("Ti2CO2", "SO2"): -0.894, ("Ti2CF2", "CO2"): -0.523,
    ("Ti2C_FH", "CO2"): -0.401, ("Ti2C_OF", "CO2"): -0.628,
}

GOOD_FIELDS = list(REQUIRED_COLUMNS)


def _row(**kw):
    base = {"key": "X/mol/CO2", "role": "molecule", "surface": "", "gas": "CO2",
            "energy_Ry": "-94.82308357", "source_file": "CO2_isolated.out",
            "calc_group": "A", "status": "ok"}
    base.update(kw)
    return base


def test_locked_energy_values_unchanged():
    entries = load_energies(ENERGIES).entries
    by = {e.key: e for e in entries}
    for key, val in LOCKED_RY.items():
        assert key in by, f"기존 key 누락: {key}"
        assert by[key].energy_Ry == val, f"{key} 변경됨"


def test_locked_eads_four_cases():
    entries = load_energies(ENERGIES).entries
    for (s, g), exp in LOCKED_EADS.items():
        r = compute_ad_for(entries, s, g)
        assert r.ok, f"{g}@{s} 계산 실패: {r.reason}"
        assert math.isclose(r.E_ad_eV, exp, abs_tol=1e-3), \
            f"{g}@{s}: {r.E_ad_eV:.4f} != {exp}"


def test_calc_group_mismatch_refuses():
    entries = load_energies(ENERGIES).entries
    # H2O는 UNASSIGNED, CO2는 A → 섞으면 거부(여기선 adsorbed 없음이라 데이터 없음 우선)
    # 명시적 불일치 검사: Ti2CF2 복합체(A)에 molecule을 UNASSIGNED로 바꿔 전달
    from core.energetics import compute_E_ad
    from core.screening import find_adsorbed, find_clean
    ad = find_adsorbed(entries, "Ti2CF2", "CO2")
    cl = find_clean(entries, "Ti2CF2")
    from dataclasses import replace
    mol_B = replace(find_clean(entries, "Ti2CF2"), calc_group="B")  # 임의 B 그룹
    # molecule 역할 대신 clean을 쓰되 calc_group만 B로 바꿔 불일치 유도
    r = compute_E_ad(ad, cl, mol_B)
    assert r.ok is False
    assert "calc_group 불일치" in r.reason


def test_missing_reference_returns_pending():
    entries = load_energies(ENERGIES).entries
    # H2O 복합체/짝이 없으므로 H2O 흡착은 계산 불가(데이터 없음)
    r = compute_ad_for(entries, "Ti2CO2", "H2O")
    assert r.ok is False
    assert r.reason  # 사유 존재


def test_duplicate_source_file_different_energy_rejected():
    # 같은 source_file 에 다른 energy_Ry → 등록 거부 (요구 7-(4))
    rows = [
        _row(key="a", source_file="dup.out", energy_Ry="-1.0"),
        _row(key="b", source_file="dup.out", energy_Ry="-2.0"),
    ]
    res = parse_rows(GOOD_FIELDS, rows)
    assert len(res.entries) == 1          # 첫 행만 통과
    assert any("다른 energy_Ry 등록 거부" in e.reason for e in res.errors)


def test_same_source_file_same_energy_ok():
    rows = [
        _row(key="a", source_file="same.out", energy_Ry="-1.0"),
        _row(key="b", source_file="same.out", energy_Ry="-1.0"),
    ]
    res = parse_rows(GOOD_FIELDS, rows)
    assert len(res.entries) == 2 and not res.errors
