"""무결성 자동 점검 규칙 (core — 순수 로직).

각 검사는 (name, status['pass'|'warn'|'fail'], detail)을 반환한다.
가상 데이터를 만들지 않고, 로드된 엔트리에서만 판정한다.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.loader import EnergyEntry, VALID_STATUS
from core.energetics import compute_E_ad, is_suspect
from core.units import ry_to_ev


@dataclass
class Check:
    name: str
    status: str   # pass | warn | fail
    detail: str


# 동일 calc_group 내에서 일치해야 하는 선택 컬럼(있을 때만 검사)
CONDITION_COLS = ["ecutwfc", "ecutrho", "kpoints", "nspin", "vdw", "pseudos"]


def check_duplicate_keys(entries: list[EnergyEntry]) -> Check:
    keys = [e.key for e in entries]
    dups = {k for k in keys if keys.count(k) > 1}
    if dups:
        return Check("중복 key 검사", "fail", f"중복 key: {', '.join(sorted(dups))}")
    return Check("중복 key 검사", "pass", "중복 key 없음")


def check_status_valid(entries: list[EnergyEntry]) -> Check:
    bad = [e.key for e in entries if e.status not in VALID_STATUS]
    if bad:
        return Check("status 값 유효성", "fail", f"유효하지 않은 status: {', '.join(bad)}")
    return Check("status 값 유효성", "pass", "모든 status가 ok|pending|suspect")


def check_condition_consistency(entries: list[EnergyEntry], extra: dict) -> Check:
    """calc_group 내 계산 조건 일치 검사. extra: {key: {col: value}} (선택 컬럼이 있을 때만).

    선택 컬럼 데이터가 없으면 '검사 불가(정보 부족)'로 경고 대신 pass 처리하되 안내.
    """
    if not extra:
        return Check("calc_group 조건 일치", "pass",
                     "선택 컬럼(계산 조건) 데이터가 없어 대조 생략")
    by_group: dict[str, list] = {}
    for e in entries:
        by_group.setdefault(e.calc_group, []).append(e)
    mismatches = []
    for group, items in by_group.items():
        seen: dict[str, set] = {c: set() for c in CONDITION_COLS}
        for e in items:
            cols = extra.get(e.key, {})
            for c in CONDITION_COLS:
                v = cols.get(c)
                if v not in (None, ""):
                    seen[c].add(str(v))
        for c, vals in seen.items():
            if len(vals) > 1:
                mismatches.append(f"{group}:{c}={sorted(vals)}")
    if mismatches:
        return Check("calc_group 조건 일치", "fail", "; ".join(mismatches))
    return Check("calc_group 조건 일치", "pass", "조건 불일치 없음(제공된 컬럼 기준)")


def check_missing_references(entries: list[EnergyEntry]) -> Check:
    """adsorbed 항목이 참조하는 clean/molecule 기준값 누락 검사."""
    def find(role, surface=None, gas=None):
        for e in entries:
            if e.role == role and (surface is None or e.surface == surface) \
               and (gas is None or e.gas == gas):
                return e
        return None

    missing = []
    for e in entries:
        if e.role == "adsorbed":
            if find("clean", surface=e.surface) is None:
                missing.append(f"{e.key}: clean({e.surface}) 없음")
            if find("molecule", gas=e.gas) is None:
                missing.append(f"{e.key}: molecule({e.gas}) 없음")
    if missing:
        return Check("기준값 누락", "warn", "; ".join(missing))
    return Check("기준값 누락", "pass", "모든 복합체의 기준값 존재")


def check_suspect_range(entries: list[EnergyEntry]) -> Check:
    """계산 가능한 E_ad 중 suspect 범위(E_ad < -3 또는 > +0.5 eV) 검사."""
    def find(role, surface=None, gas=None):
        for e in entries:
            if e.role == role and (surface is None or e.surface == surface) \
               and (gas is None or e.gas == gas):
                return e
        return None

    suspects = []
    for e in entries:
        if e.role == "adsorbed":
            r = compute_E_ad(e, find("clean", surface=e.surface), find("molecule", gas=e.gas))
            if r.ok and r.suspect:
                suspects.append(f"{e.key} ({r.E_ad_eV:.3f} eV)")
    if suspects:
        return Check("suspect 범위", "warn", "의심 값: " + "; ".join(suspects))
    return Check("suspect 범위", "pass", "계산된 E_ad 모두 정상 범위")


def check_ead_reproducibility(entries: list[EnergyEntry]) -> Check:
    """E_ad 재계산 재현성: 공식으로 다시 계산해 일관성 확인 (결정적)."""
    def find(role, surface=None, gas=None):
        for e in entries:
            if e.role == role and (surface is None or e.surface == surface) \
               and (gas is None or e.gas == gas):
                return e
        return None

    n = 0
    for e in entries:
        if e.role == "adsorbed":
            r = compute_E_ad(e, find("clean", surface=e.surface), find("molecule", gas=e.gas))
            if r.ok:
                recomputed = ry_to_ev(e.energy_Ry - (
                    find("clean", surface=e.surface).energy_Ry
                    + find("molecule", gas=e.gas).energy_Ry))
                if abs(recomputed - r.E_ad_eV) > 1e-9:
                    return Check("E_ad 재현성", "fail", f"{e.key} 재계산 불일치")
                n += 1
    return Check("E_ad 재현성", "pass", f"{n}건 재계산 일치")


def run_all(entries: list[EnergyEntry], extra: dict | None = None) -> list[Check]:
    extra = extra or {}
    return [
        check_duplicate_keys(entries),
        check_status_valid(entries),
        check_condition_consistency(entries, extra),
        check_missing_references(entries),
        check_suspect_range(entries),
        check_ead_reproducibility(entries),
    ]
