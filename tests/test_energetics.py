"""core.energetics 단위 테스트 (요구사항 3, 4, 12).

필수 포함 케이스:
- calc_group 불일치 시 계산 거부 (요구사항 12.2)
- 기준값 누락 시 pending/ok=False 반환 (요구사항 12.3)
"""

import math

from core.loader import EnergyEntry
from core.energetics import compute_E_ad, is_suspect, SUSPECT_LOW_EV, SUSPECT_HIGH_EV


def E(key, role, surface, gas, energy, cg="A"):
    return EnergyEntry(key, role, surface, gas, energy, f"{key}.out", cg, "ok")


# 초기 데이터 (calc_group=A)
CO2 = E("A/mol/CO2", "molecule", "", "CO2", -94.82308357)
SO2 = E("A/mol/SO2", "molecule", "", "SO2", -105.27217923)
CLEAN_CO2SURF = E("A/clean/Ti2CF2", "clean", "Ti2CF2", "", -1389.76036918)
AD_CO2 = E("A/ad/CO2@Ti2CF2", "adsorbed", "Ti2CF2", "CO2", -1484.62192566)
CLEAN_SO2SURF = E("A/clean/Ti2CO2", "clean", "Ti2CO2", "", -1333.32037072)
AD_SO2 = E("A/ad/SO2@Ti2CO2", "adsorbed", "Ti2CO2", "SO2", -1438.65823190)


def test_known_value_CO2_on_Ti2CF2():
    r = compute_E_ad(AD_CO2, CLEAN_CO2SURF, CO2)
    assert r.ok is True
    assert math.isclose(r.E_ad_Ry, -0.03848, abs_tol=5e-5)
    assert math.isclose(r.E_ad_eV, -0.524, abs_tol=2e-3)
    assert r.suspect is False
    assert r.calc_group == "A"
    # 출처 추적 가능 (DI-4)
    assert r.components["E_adsorbed"]["source_file"] == "A/ad/CO2@Ti2CF2.out"


def test_known_value_SO2_on_Ti2CO2():
    r = compute_E_ad(AD_SO2, CLEAN_SO2SURF, SO2)
    assert r.ok is True
    assert math.isclose(r.E_ad_Ry, -0.06568, abs_tol=5e-5)
    assert math.isclose(r.E_ad_eV, -0.894, abs_tol=2e-3)


# --- 필수 케이스 1: calc_group 불일치 시 계산 거부 (요구사항 12.2) ---
def test_calc_group_mismatch_refuses_computation():
    co2_group_B = E("B/mol/CO2", "molecule", "", "CO2", -94.82308357, cg="B")
    r = compute_E_ad(AD_CO2, CLEAN_CO2SURF, co2_group_B)
    assert r.ok is False
    assert r.E_ad_eV is None and r.E_ad_Ry is None
    assert "calc_group 불일치" in r.reason
    assert "molecule=B" in r.reason


# --- 필수 케이스 2: 기준값 누락 시 ok=False 반환 (요구사항 12.3) ---
def test_missing_molecule_returns_pending():
    r = compute_E_ad(AD_CO2, CLEAN_CO2SURF, None)
    assert r.ok is False
    assert r.E_ad_eV is None
    assert "단독 분자" in r.reason


def test_missing_clean_returns_pending():
    r = compute_E_ad(AD_CO2, None, CO2)
    assert r.ok is False
    assert "clean" in r.reason


def test_missing_adsorbed_returns_pending():
    r = compute_E_ad(None, CLEAN_CO2SURF, CO2)
    assert r.ok is False
    assert "복합체" in r.reason


def test_multiple_missing_listed():
    r = compute_E_ad(None, None, None)
    assert r.ok is False
    assert r.reason.count(";") == 2  # 세 사유 모두 나열


# --- suspect 판정 (요구사항 4.1, 경계값) ---
def test_is_suspect_boundaries():
    assert is_suspect(SUSPECT_LOW_EV - 0.01) is True
    assert is_suspect(SUSPECT_HIGH_EV + 0.01) is True
    # 경계 내부
    assert is_suspect(-3.0) is False
    assert is_suspect(0.5) is False
    assert is_suspect(-1.0) is False


def test_suspect_flag_keeps_value():
    # 인위적으로 suspect 범위에 드는 복합체 (매우 강한 결합)
    ad_strong = E("A/ad/X", "adsorbed", "X", "CO2", -1600.0)
    clean_x = E("A/clean/X", "clean", "X", "", -1400.0)
    r = compute_E_ad(ad_strong, clean_x, CO2)
    assert r.ok is True          # 값은 계산됨
    assert r.suspect is True     # 경고는 부여됨 (값 숨기지 않음)
    assert r.E_ad_eV is not None
