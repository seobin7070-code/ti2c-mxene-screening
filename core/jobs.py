"""계산 작업 관리 로직 (core — 순수 로직).

보고서 4.1절 계획 구조(가스 단독 3 + 순수/혼합 표면 10 + 복합체 21 = 34건)로
초기 작업 목록을 '구조만' 생성한다. wall_time 등 측정 수치는 비워 둔다(가상 금지).
energies.csv에 해당 에너지가 있으면 done으로 자동 동기화한다.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

from core.loader import EnergyEntry

JOB_COLUMNS = ["job_id", "type", "surface", "gas", "status",
               "wall_time_h", "note", "updated_at"]
VALID_JOB_STATUS = {"todo", "running", "done", "failed"}

# 보고서 4.1절 계획 구조 (이름만, 가상 수치 없음)
PLANNED_GASES = ["CO2", "H2O", "SO2"]                      # 가스 단독 3
PLANNED_SURFACES = [                                        # 순수/혼합 표면 10
    "Ti2CO2", "Ti2CF2", "Ti2C(OH)2",
    "Ti2C(O0.5OH0.5)", "Ti2C(O0.5F0.5)", "Ti2C(F0.5OH0.5)",
    "Ti2C(O_F_OH)",      # 삼원 혼합
    "Ti2C_FH", "Ti2C_OF", "Ti2C_OH_extra",
]
# 복합체 21건: 7개 핵심 조성 × 3가스 = 21
COMPLEX_SURFACES = [
    "Ti2CO2", "Ti2CF2", "Ti2C(OH)2",
    "Ti2C(O0.5OH0.5)", "Ti2C(O0.5F0.5)", "Ti2C(F0.5OH0.5)", "Ti2C(O_F_OH)",
]


@dataclass
class Job:
    job_id: str
    type: str          # molecule | clean | adsorbed
    surface: str
    gas: str
    status: str        # todo | running | done | failed
    wall_time_h: str   # 측정값 없으면 "" (가상 금지)
    note: str
    updated_at: str


def build_initial_jobs() -> list[dict]:
    """계획 34건의 작업 목록(구조)을 생성한다. 수치는 비움."""
    jobs: list[dict] = []
    i = 1

    def add(jtype, surface, gas, note):
        nonlocal i
        jobs.append({
            "job_id": f"J{i:03d}", "type": jtype, "surface": surface, "gas": gas,
            "status": "todo", "wall_time_h": "", "note": note, "updated_at": "",
        })
        i += 1

    for g in PLANNED_GASES:                 # 가스 단독 3
        add("molecule", "", g, "가스 단독 분자")
    for s in PLANNED_SURFACES:              # 순수/혼합 표면 10
        add("clean", s, "", "표면(clean)")
    for s in COMPLEX_SURFACES:              # 복합체 21 (7 × 3)
        for g in PLANNED_GASES:
            add("adsorbed", s, g, "복합체(흡착)")
    return jobs


def sync_with_energies(jobs: list[dict], entries: list[EnergyEntry]) -> list[dict]:
    """energies.csv에 해당 에너지가 있으면 status=done 으로 동기화한다 (결정적)."""
    def has_energy(jtype, surface, gas) -> bool:
        for e in entries:
            if e.role != jtype:
                continue
            if jtype == "molecule" and e.gas == gas:
                return True
            if jtype == "clean" and e.surface == surface:
                return True
            if jtype == "adsorbed" and e.surface == surface and e.gas == gas:
                return True
        return False

    out = []
    for j in jobs:
        jj = dict(j)
        if has_energy(j["type"], j["surface"], j["gas"]):
            if jj.get("status") not in ("done",):
                jj["status"] = "done"
        out.append(jj)
    return out


def estimate_remaining(jobs: list[dict]) -> dict:
    """입력된 wall_time_h 평균 × 남은 건수로 예상 잔여 시간. 없으면 '측정 필요'."""
    times = []
    for j in jobs:
        v = str(j.get("wall_time_h", "")).strip()
        if v:
            try:
                times.append(float(v))
            except ValueError:
                pass
    remaining = sum(1 for j in jobs if j.get("status") in ("todo", "running", "failed"))
    if not times:
        return {"avg_h": None, "remaining": remaining, "eta_h": None, "note": "측정 필요"}
    avg = sum(times) / len(times)
    return {"avg_h": avg, "remaining": remaining, "eta_h": avg * remaining, "note": ""}


def progress_summary(jobs: list[dict]) -> dict:
    """상태별 집계."""
    out = {"todo": 0, "running": 0, "done": 0, "failed": 0, "total": len(jobs)}
    for j in jobs:
        s = j.get("status", "todo")
        if s in out:
            out[s] += 1
    return out
