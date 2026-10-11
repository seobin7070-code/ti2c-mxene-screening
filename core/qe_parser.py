"""Quantum ESPRESSO .out 파일 파서 (core — 순수 로직, Streamlit 비의존).

파싱 실패 시 값을 추정하지 않고 실패 사유를 담아 반환한다 (데이터 무결성).
에너지는 소수점 8자리로 정규화한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QEResult:
    total_energy_Ry: Optional[float]      # 최종 "!    total energy" (Ry), 없으면 None
    converged: Optional[bool]             # "convergence has been achieved"
    job_done: Optional[bool]              # "JOB DONE"
    n_atoms: Optional[int]
    ecutwfc: Optional[float]
    ecutrho: Optional[float]
    kpoints: Optional[str]
    nspin: Optional[int]
    vdw: Optional[str]                    # input_dft/vdw_corr
    pseudos: list = field(default_factory=list)
    errors: list = field(default_factory=list)   # 파싱 실패/누락 사유(한국어)

    @property
    def total_energy_8dp(self) -> Optional[str]:
        if self.total_energy_Ry is None:
            return None
        return f"{self.total_energy_Ry:.8f}"


_RE_TOTAL = re.compile(r"^!\s+total energy\s*=\s*(-?\d+\.\d+)\s*Ry", re.MULTILINE)
_RE_NAT = re.compile(r"number of atoms/cell\s*=\s*(\d+)")
_RE_ECUTWFC = re.compile(r"kinetic-energy cutoff\s*=\s*(-?\d+\.?\d*)\s*Ry")
_RE_ECUTRHO = re.compile(r"charge density cutoff\s*=\s*(-?\d+\.?\d*)\s*Ry")
_RE_NSPIN_MAG = re.compile(r"number of spin components\s*=\s*(\d+)")
_RE_KPTS = re.compile(r"number of k points\s*=\s*(\d+)")
_RE_VDW1 = re.compile(r"vdw_corr\s*=\s*[\"']?([A-Za-z0-9\-+]+)[\"']?")
_RE_VDW2 = re.compile(r"Carrying out vdW-DF run|Grimme-D3|DFT-D3|dft-d3", re.IGNORECASE)
_RE_INPUT_DFT = re.compile(r"input_dft\s*=\s*[\"']?([A-Za-z0-9\-+]+)[\"']?")


def parse_out_text(text: str) -> QEResult:
    """QE 출력 텍스트를 파싱한다. 각 항목이 없으면 None + errors에 사유 기록."""
    errors: list = []

    # 총 에너지 — 마지막 '!' 라인 사용
    tot_matches = _RE_TOTAL.findall(text)
    if tot_matches:
        total = round(float(tot_matches[-1]), 8)
    else:
        total = None
        errors.append("최종 '!    total energy' 값을 찾지 못함")

    converged = ("convergence has been achieved" in text) if "convergence" in text or "!" in text else None
    if "convergence has been achieved" in text:
        converged = True
    elif "convergence NOT achieved" in text or "not achieved" in text.lower():
        converged = False
    else:
        converged = None
        errors.append("수렴 여부(convergence) 문자열 없음")

    job_done = "JOB DONE" in text
    if not job_done:
        errors.append("'JOB DONE' 없음 (작업 미완료 가능)")

    def _int(regex, label):
        m = regex.search(text)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                errors.append(f"{label} 파싱 실패")
        return None

    def _float(regex, label):
        m = regex.search(text)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                errors.append(f"{label} 파싱 실패")
        return None

    n_atoms = _int(_RE_NAT, "number of atoms/cell")
    ecutwfc = _float(_RE_ECUTWFC, "ecutwfc")
    ecutrho = _float(_RE_ECUTRHO, "ecutrho")
    nspin = _int(_RE_NSPIN_MAG, "nspin")
    kpts_m = _RE_KPTS.search(text)
    kpoints = kpts_m.group(1) if kpts_m else None

    # vdW: input_dft 또는 vdw_corr 또는 본문 흔적
    vdw = None
    m = _RE_VDW1.search(text)
    if m:
        vdw = m.group(1)
    else:
        m2 = _RE_INPUT_DFT.search(text)
        if m2 and ("vdw" in m2.group(1).lower() or "d3" in m2.group(1).lower()):
            vdw = m2.group(1)
        elif _RE_VDW2.search(text):
            vdw = "D3/vdW (본문 감지)"

    # pseudopotential 파일명
    pseudos = re.findall(r"PseudoPot\.\s*#\s*\d+\s*for\s+\S+\s+read from file:\s*\n?\s*(\S+)", text)
    if not pseudos:
        pseudos = re.findall(r"readpp.*?([A-Za-z0-9_.\-]+\.(?:UPF|upf))", text)

    return QEResult(
        total_energy_Ry=total, converged=converged, job_done=job_done,
        n_atoms=n_atoms, ecutwfc=ecutwfc, ecutrho=ecutrho,
        kpoints=kpoints, nspin=nspin, vdw=vdw, pseudos=pseudos, errors=errors,
    )


def compare_to_csv_energy(parsed: QEResult, csv_energy_ry: float, tol: float = 1e-6) -> dict:
    """파싱된 에너지와 CSV 값 비교. {match: bool, diff: float|None, reason}."""
    if parsed.total_energy_Ry is None:
        return {"match": None, "diff": None, "reason": "파일에서 에너지를 읽지 못함"}
    diff = parsed.total_energy_Ry - csv_energy_ry
    return {"match": abs(diff) <= tol, "diff": diff,
            "reason": "일치" if abs(diff) <= tol else f"불일치 (차이 {diff:.8f} Ry)"}
