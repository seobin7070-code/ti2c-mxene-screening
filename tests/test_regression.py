"""회귀 고정 + loader 규칙 테스트 (PDF 명세, 요구 7-(1)(2)(3)(4))."""

import math
import os

from core.loader import load_energies, parse_rows, REQUIRED_COLUMNS
from core.screening import compute_ad_for

HERE = os.path.dirname(__file__)
ENERGIES = os.path.join(HERE, "..", "data", "energies.csv")

# 표준 단위셀(SET2) 10개 에너지 값 (Ry) — 물리값 불변 (key 는 세트 체계)
LOCKED_RY = {
    "SET2/mol/CO2": -94.82308357, "SET2/mol/SO2": -105.27217923,
    "SET2/clean/Ti2CF2": -1389.76036918, "SET2/clean/Ti2CO2": -1333.32037072,
    "SET2/clean/Ti2C_FH": -1360.84920315, "SET2/clean/Ti2C_OF": -1361.40729499,
    "SET2/ad/SO2@Ti2CO2": -1438.65823190, "SET2/ad/CO2@Ti2CF2": -1484.62192566,
    "SET2/ad/CO2@Ti2C_FH": -1455.70176796, "SET2/ad/CO2@Ti2C_OF": -1456.27650839,
}
# E_ads 4건 (eV, 셋째 자리) — 세트2 안에서 계산
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
        r = compute_ad_for(entries, s, g, calc_group="SET2")
        assert r.ok, f"{g}@{s} 계산 실패: {r.reason}"
        assert math.isclose(r.E_ad_eV, exp, abs_tol=1e-3), \
            f"{g}@{s}: {r.E_ad_eV:.4f} != {exp}"


# 세트1 복합체 9종 E_ads (eV, 셋째 자리) — SET1 안에서 계산
LOCKED_SET1_EADS = {
    ("Ti2CF2", "CO2"): -0.015, ("Ti2CF2", "H2O"): -0.029, ("Ti2CF2", "SO2"): -0.045,
    ("Ti2C_OF_alt", "CO2"): -0.018, ("Ti2C_OF_alt", "H2O"): -0.038, ("Ti2C_OF_alt", "SO2"): -0.063,
    ("Ti2C_FOH_clu", "CO2"): -0.022, ("Ti2C_FOH_clu", "H2O"): -0.049, ("Ti2C_FOH_clu", "SO2"): -0.078,
}


def test_set1_nine_complexes():
    entries = load_energies(ENERGIES).entries
    for (s, g), exp in LOCKED_SET1_EADS.items():
        r = compute_ad_for(entries, s, g, calc_group="SET1")
        assert r.ok, f"SET1 {g}@{s} 계산 실패: {r.reason}"
        assert math.isclose(r.E_ad_eV, exp, abs_tol=2e-3), \
            f"SET1 {g}@{s}: {r.E_ad_eV:.4f} != {exp}"


def test_sets_not_mixed():
    """세트1 복합체는 세트2 표면·분자와 섞이지 않는다 (calc_group 지정 시 세트 내에서만)."""
    entries = load_energies(ENERGIES).entries
    # Ti2CF2+CO2 는 양쪽 세트에 존재 — 세트별 값이 서로 달라야 함(섞이지 않음 증거)
    r1 = compute_ad_for(entries, "Ti2CF2", "CO2", calc_group="SET1")
    r2 = compute_ad_for(entries, "Ti2CF2", "CO2", calc_group="SET2")
    assert r1.ok and r2.ok
    assert abs(r1.E_ad_eV - r2.E_ad_eV) > 0.1  # 세트1 ≈ -0.015, 세트2 ≈ -0.523


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
