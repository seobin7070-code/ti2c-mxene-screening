"""회귀 고정 테스트 — 기존 10개 에너지 값과 E_ad 4건을 영구 고정한다.

이 값들은 어떤 리팩터링/컬럼 추가에도 바뀌면 안 된다 (불변 조건).
선택 컬럼(n_atoms, ecutwfc 등)이 energies.csv에 추가되어도 이 테스트는
key→energy_Ry 매핑만 보므로 영향받지 않는다.
"""

import math
import os

from core.loader import load_energies
from core.registry import compute_ad_for

HERE = os.path.dirname(__file__)
ENERGIES = os.path.join(HERE, "..", "data", "energies.csv")

# ── 기존 10개 에너지 값 (Ry) — 한 글자도 바뀌면 안 됨 ──
LOCKED_ENERGIES_RY = {
    "A/mol/CO2": -94.82308357,
    "A/mol/SO2": -105.27217923,
    "A/clean/Ti2CF2": -1389.76036918,
    "A/clean/Ti2CO2": -1333.32037072,
    "A/clean/Ti2C_FH": -1360.84920315,
    "A/clean/Ti2C_OF": -1361.40729499,
    "A/ad/SO2@Ti2CO2": -1438.65823190,
    "A/ad/CO2@Ti2CF2": -1484.62192566,
    "A/ad/CO2@Ti2C_FH": -1455.70176796,
    "A/ad/CO2@Ti2C_OF": -1456.27650839,
}

# ── E_ad 4건 (eV) — 보고서/사용자 제시 기대값 ──
LOCKED_EAD_EV = {
    ("Ti2CO2", "SO2"): -0.894,
    ("Ti2CF2", "CO2"): -0.523,
    ("Ti2C_FH", "CO2"): -0.401,
    ("Ti2C_OF", "CO2"): -0.628,
}


def test_locked_energy_values_unchanged():
    entries = load_energies(ENERGIES).entries
    by_key = {e.key: e for e in entries}
    # 기존 10개 key가 모두 존재해야 함
    for key, val in LOCKED_ENERGIES_RY.items():
        assert key in by_key, f"기존 key 누락: {key}"
        got = by_key[key].energy_Ry
        assert got == val, f"{key} 에너지 변경됨: {got} != {val}"


def test_locked_ead_four_cases():
    entries = load_energies(ENERGIES).entries
    for (surf, gas), exp_ev in LOCKED_EAD_EV.items():
        r = compute_ad_for(entries, surf, gas)
        assert r.ok, f"{gas}@{surf} 계산 실패: {r.reason}"
        assert math.isclose(r.E_ad_eV, exp_ev, abs_tol=1e-3), \
            f"{gas}@{surf} E_ad 변경됨: {r.E_ad_eV:.4f} eV != {exp_ev} eV"
        assert not r.suspect


def test_no_extra_or_missing_core_keys():
    # 선택 컬럼 추가는 허용하되, 핵심 10개 에너지 항목 수는 유지
    entries = load_energies(ENERGIES).entries
    core_keys = {e.key for e in entries if e.calc_group == "A"}
    for key in LOCKED_ENERGIES_RY:
        assert key in core_keys
