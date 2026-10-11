#!/usr/bin/env python3
"""Quantum ESPRESSO 출력·구조 파일에서 Δd(표면 흐트러짐)와 가스–표면 수직 거리를 추출.

명세 4.3:
  Δd = | (z_T − z_ref)_after − (z_T − z_ref)_before |
    z_T  : 가스에 가장 가까운 말단기(–O/–F/–OH, OH의 경우 O) 원자 1개의 z 좌표
    z_ref: 가스가 붙는 쪽 Ti 원자층의 평균 z 좌표
    before: 가스 없이 완화한 clean 표면, after: SO₂가 붙은 복합체
  Δd 는 SO₂ 계산에서만 정의한다.

이 스크립트는 추가로 사용자가 요청한 '가스 최하단 원자 ↔ 표면 최상단 원자 수직 거리'
(gas_surface_gap_A)도 함께 계산한다.

입력 좌표 소스(우선순위):
  1) QE 출력(.out/.pwo): 마지막 'ATOMIC_POSITIONS' (= 완화 후 최종 구조)를 읽는다.
     bohr/angstrom/crystal/alat 단위를 처리한다(crystal/alat 은 CELL_PARAMETERS 필요).
  2) 구조 파일: .xsf, .xyz (Å 단위 가정).

사용법:
  # (A) 매니페스트(권장): 복합체 before/after 쌍을 CSV로 지정
  python scripts/extract_delta_d.py --manifest scripts/delta_d_manifest.csv \
      --out data/geometry.csv --files-dir data/qe

  # (B) 단일 쌍 직접 지정
  python scripts/extract_delta_d.py --surface Ti2CO2 \
      --clean data/qe/Ti2CO2_clean.out --adsorbed data/qe/SO2_on_Ti2CO2.out \
      --gas SO2 --out data/geometry.csv

매니페스트 CSV 컬럼: surface,gas,clean_file,adsorbed_file  (gas 는 보통 SO2)

가정/안전장치:
  - z 축 = 슬랩 수직 방향(QE 통상 설정). 가스는 슬랩 '위'(z 큰 쪽) 또는 '아래'에
    붙을 수 있으므로, 가스 질량중심이 Ti 평면보다 위면 윗면, 아래면 아랫면 기준으로 자동 선택.
  - 값을 지어내지 않는다. 좌표를 못 읽으면 해당 행을 건너뛰고 사유를 stderr 로 남긴다.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from dataclasses import dataclass

BOHR_TO_ANG = 0.529177210903

# 말단기 후보 원소(맥신 표면 종단) / 지지층 / 가스 구성 원소
TERMINAL_ELEMENTS = {"O", "F"}          # OH 의 경우 O 를 말단 대표로 사용
TERMINAL_WITH_H = {"O", "F", "H"}
REF_ELEMENT = "Ti"                       # z_ref = Ti 층 평균
GAS_ELEMENTS = {
    "CO2": {"C", "O"},
    "SO2": {"S", "O"},
    "H2O": {"O", "H"},
}
# 가스를 표면과 구별하는 '고유' 원소(표면 말단기에는 없는 원소).
# SO2→S, CO2→C. 이 원자를 가스 분자의 앵커로 삼아 분자 전체를 근접 클러스터로 묶는다.
# (표면 말단기와 가스가 공유하는 O 때문에 원소만으로는 분리가 애매하므로.)
GAS_ANCHOR = {"CO2": "C", "SO2": "S"}
# 가스 분자 내 결합 거리(Å) 상한 — 앵커에서 이 거리 안의 가스-원소 원자를 한 분자로 본다
GAS_BOND_MAX_A = 2.0
# 앵커 외 '비앵커' 원자 개수(앵커에서 가장 가까운 것부터 이만큼만 가스로 본다).
# SO2 = S + O 2개, CO2 = C + O 2개. 과도하게 가까운 표면 O 가 분자에 섞이지 않도록 제한.
GAS_SATELLITE_COUNT = {"CO2": 2, "SO2": 2}


@dataclass
class Atom:
    element: str
    x: float
    y: float
    z: float


# ───────────────────────── 파서 ─────────────────────────
def _element_from_label(label: str) -> str:
    """'Ti1', 'O', 'F2' 등 라벨에서 원소 기호 추출."""
    m = re.match(r"([A-Z][a-z]?)", label.strip())
    return m.group(1) if m else label.strip()


def parse_qe_output(path: str) -> list[Atom]:
    """QE 출력(.out/.pwo)에서 '마지막' ATOMIC_POSITIONS 블록(완화 후)을 반환."""
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    # CELL_PARAMETERS (crystal/alat 변환용) + alat
    cell = None
    alat_bohr = None
    for i, ln in enumerate(lines):
        if "lattice parameter (alat)" in ln:
            m = re.search(r"=\s*([\d.]+)", ln)
            if m:
                alat_bohr = float(m.group(1))
        if ln.strip().startswith("CELL_PARAMETERS"):
            unit = ln.lower()
            vecs = []
            for j in range(i + 1, i + 4):
                parts = lines[j].split()
                if len(parts) >= 3:
                    vecs.append([float(parts[0]), float(parts[1]), float(parts[2])])
            if len(vecs) == 3:
                scale = BOHR_TO_ANG if "bohr" in unit else (
                    (alat_bohr * BOHR_TO_ANG) if "alat" in unit and alat_bohr else 1.0)
                cell = [[c * scale for c in v] for v in vecs]

    # 마지막 ATOMIC_POSITIONS 블록 찾기
    starts = [i for i, ln in enumerate(lines) if ln.strip().startswith("ATOMIC_POSITIONS")]
    if not starts:
        raise ValueError("ATOMIC_POSITIONS 블록을 찾지 못함(완화 좌표 없음)")
    i0 = starts[-1]
    unit = lines[i0].lower()
    atoms: list[Atom] = []
    for ln in lines[i0 + 1:]:
        s = ln.strip()
        if not s or s.startswith(("ATOMIC_POSITIONS", "End", "CELL_PARAMETERS")):
            if atoms:
                break
            continue
        parts = s.split()
        if len(parts) < 4:
            if atoms:
                break
            continue
        try:
            x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
        except ValueError:
            if atoms:
                break
            continue
        el = _element_from_label(parts[0])
        atoms.append(Atom(el, x, y, z))

    return _to_angstrom(atoms, unit, cell, alat_bohr)


def _to_angstrom(atoms, unit, cell, alat_bohr) -> list[Atom]:
    """ATOMIC_POSITIONS 단위를 Å(데카르트)로 변환."""
    if "angstrom" in unit:
        return atoms
    if "bohr" in unit:
        return [Atom(a.element, a.x * BOHR_TO_ANG, a.y * BOHR_TO_ANG, a.z * BOHR_TO_ANG)
                for a in atoms]
    if "crystal" in unit:
        if cell is None:
            raise ValueError("crystal 좌표인데 CELL_PARAMETERS 를 못 읽어 변환 불가")
        out = []
        for a in atoms:
            x = a.x * cell[0][0] + a.y * cell[1][0] + a.z * cell[2][0]
            y = a.x * cell[0][1] + a.y * cell[1][1] + a.z * cell[2][1]
            z = a.x * cell[0][2] + a.y * cell[1][2] + a.z * cell[2][2]
            out.append(Atom(a.element, x, y, z))
        return out
    if "alat" in unit:
        if not alat_bohr:
            raise ValueError("alat 좌표인데 alat 값을 못 읽어 변환 불가")
        s = alat_bohr * BOHR_TO_ANG
        return [Atom(a.element, a.x * s, a.y * s, a.z * s) for a in atoms]
    # 단위 미표기 → Å 로 가정
    return atoms


def parse_xyz(path: str) -> list[Atom]:
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    atoms = []
    for ln in lines[2:]:            # 1행=개수, 2행=코멘트
        parts = ln.split()
        if len(parts) >= 4:
            try:
                atoms.append(Atom(_element_from_label(parts[0]),
                                  float(parts[1]), float(parts[2]), float(parts[3])))
            except ValueError:
                continue
    return atoms


def parse_xsf(path: str) -> list[Atom]:
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    atoms, in_coords = [], False
    for ln in lines:
        s = ln.strip()
        if s.startswith(("PRIMCOORD", "ATOMS", "CONVCOORD")):
            in_coords = True
            continue
        if in_coords:
            parts = s.split()
            if len(parts) >= 4:
                try:
                    atoms.append(Atom(_element_from_label(parts[0]),
                                      float(parts[1]), float(parts[2]), float(parts[3])))
                except ValueError:
                    if atoms:
                        break
    return atoms


def load_structure(path: str) -> list[Atom]:
    """확장자에 따라 적절한 파서를 호출해 Å 데카르트 좌표 원자 리스트를 반환."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".out", ".pwo", ".log"):
        return parse_qe_output(path)
    if ext == ".xyz":
        return parse_xyz(path)
    if ext == ".xsf":
        return parse_xsf(path)
    # 알 수 없으면 QE 출력으로 시도
    return parse_qe_output(path)


# ───────────────────────── 기하 계산 ─────────────────────────
def _ti_mean_z_on_side(atoms: list[Atom], upper: bool) -> float:
    """가스가 붙는 쪽(upper=True면 위쪽) Ti 층의 평균 z.

    Ti 원자들을 z 중앙값으로 상/하 반으로 나눠, 가스 쪽에 가까운 Ti 층 평균을 쓴다.
    (기준층을 쓰므로 셀 전체가 z 로 움직여도 Δd 에 영향 없음 — 명세 4.3)
    """
    ti = [a.z for a in atoms if a.element == REF_ELEMENT]
    if not ti:
        raise ValueError(f"{REF_ELEMENT} 원자를 찾지 못함(z_ref 계산 불가)")
    mid = sorted(ti)[len(ti) // 2]
    side = [z for z in ti if (z >= mid if upper else z <= mid)]
    return sum(side) / len(side) if side else sum(ti) / len(ti)


def _terminal_z_near_gas(atoms, gas_atoms, upper: bool) -> float:
    """가스에 (xy 평면상) 가장 가까운 '표면 말단기' 원자(z가 가스 쪽)의 z 좌표.

    가스 분자 자체의 원자(gas_atoms)는 말단기 후보에서 제외한다
    (SO₂·CO₂의 O 가 표면 말단 O 와 섞이지 않도록).
    """
    if not gas_atoms:
        raise ValueError("가스 원자를 찾지 못함")
    gas_ids = {id(a) for a in gas_atoms}
    gx = sum(a.x for a in gas_atoms) / len(gas_atoms)
    gy = sum(a.y for a in gas_atoms) / len(gas_atoms)
    ti_mean = _ti_mean_z_on_side(atoms, upper)
    cands = [a for a in atoms if id(a) not in gas_ids and a.element in TERMINAL_WITH_H
             and (a.z > ti_mean if upper else a.z < ti_mean)]
    if not cands:
        cands = [a for a in atoms if id(a) not in gas_ids and a.element in TERMINAL_WITH_H]
    if not cands:
        raise ValueError("표면 말단기(O/F/H) 원자를 찾지 못함")
    nearest = min(cands, key=lambda a: (a.x - gx) ** 2 + (a.y - gy) ** 2)
    return nearest.z


def _split_gas_surface(atoms, gas_name: str):
    """복합체에서 가스 분자 원자군과 (가스가 붙는 쪽) upper 여부를 반환.

    핵심: 표면 말단기와 가스가 O 를 공유하므로 원소만으로는 분리가 애매하다.
    따라서 가스의 '고유' 원소(SO2→S, CO2→C)를 앵커로 삼아, 앵커에서 결합 거리
    (GAS_BOND_MAX_A) 안의 가스-구성 원자를 한 분자로 묶는다. 앵커가 없으면(H2O 등)
    Ti 평면에서 가장 먼 가스-원소 묶음으로 폴백한다.
    """
    ti = [a.z for a in atoms if a.element == REF_ELEMENT]
    if not ti:
        raise ValueError("Ti 원자를 찾지 못함")
    ti_mid = sum(ti) / len(ti)
    gas_el = GAS_ELEMENTS.get(gas_name, set())

    anchor_el = GAS_ANCHOR.get(gas_name)
    if anchor_el:
        anchors = [a for a in atoms if a.element == anchor_el]
        if not anchors:
            raise ValueError(f"{gas_name} 앵커 원소 {anchor_el} 를 복합체에서 찾지 못함")
        # 앵커가 여러 개면 Ti 평면에서 가장 먼 것(= 떠 있는 가스)을 선택
        anchor = max(anchors, key=lambda a: abs(a.z - ti_mid))
        # 앵커에서 결합 거리 안의 가스-원소 원자를, 가까운 것부터 정해진 개수만 묶는다
        sat = []
        for a in atoms:
            if a is anchor or a.element not in gas_el:
                continue
            d = ((a.x - anchor.x) ** 2 + (a.y - anchor.y) ** 2 + (a.z - anchor.z) ** 2) ** 0.5
            if d <= GAS_BOND_MAX_A:
                sat.append((d, a))
        sat.sort(key=lambda t: t[0])
        n_sat = GAS_SATELLITE_COUNT.get(gas_name, len(sat))
        mol = [anchor] + [a for _, a in sat[:n_sat]]
        upper = anchor.z > ti_mid
        return mol, upper

    # 폴백(H2O 등 고유 원소 없음): 말단기 바깥 가스-원소 묶음
    term_z = [a.z for a in atoms if a.element in TERMINAL_WITH_H]
    top_term = max(term_z) if term_z else ti_mid
    bot_term = min(term_z) if term_z else ti_mid
    gas_up = [a for a in atoms if a.element in gas_el and a.z > top_term + 0.3]
    gas_dn = [a for a in atoms if a.element in gas_el and a.z < bot_term - 0.3]
    if len(gas_up) >= len(gas_dn) and gas_up:
        return gas_up, True
    if gas_dn:
        return gas_dn, False
    gas_all = [a for a in atoms if a.element in gas_el]
    if not gas_all:
        raise ValueError(f"{gas_name} 가스 원소를 복합체에서 찾지 못함")
    far = max(gas_all, key=lambda a: abs(a.z - ti_mid))
    upper = far.z > ti_mid
    side = [a for a in gas_all if (a.z > ti_mid) == upper]
    return side, upper


@dataclass
class GeometryRow:
    surface: str
    z_T_before: float
    z_T_after: float
    z_ref_before: float
    z_ref_after: float
    gas_surface_gap_A: float   # 가스 최하단(가스쪽) 원자 ↔ 표면 최상단 말단기 수직 거리

    @property
    def delta_d(self) -> float:
        before = self.z_T_before - self.z_ref_before
        after = self.z_T_after - self.z_ref_after
        return abs(after - before)


def compute_geometry(surface: str, clean_file: str, adsorbed_file: str,
                     gas: str = "SO2") -> GeometryRow:
    """clean(before)·adsorbed(after) 구조에서 z_T·z_ref·Δd·가스-표면 간격을 계산."""
    clean = load_structure(clean_file)
    adsorbed = load_structure(adsorbed_file)

    gas_atoms, upper = _split_gas_surface(adsorbed, gas)

    # after: 복합체에서
    z_ref_after = _ti_mean_z_on_side(adsorbed, upper)
    z_T_after = _terminal_z_near_gas(adsorbed, gas_atoms, upper)
    # before: clean 표면에서 같은 쪽 말단기(가스가 없으니 xy 평면상 가스 투영 위치 대신
    #         복합체의 z_T 말단기와 같은 쪽의 극값 말단기를 쓴다)
    z_ref_before = _ti_mean_z_on_side(clean, upper)
    term_before = [a.z for a in clean
                   if a.element in TERMINAL_WITH_H and (a.z > z_ref_before if upper else a.z < z_ref_before)]
    if not term_before:
        term_before = [a.z for a in clean if a.element in TERMINAL_WITH_H]
    z_T_before = (max(term_before) if upper else min(term_before))

    # 가스-표면 수직 간격: 가스에서 표면에 가장 가까운 원자 ↔ 표면 최상단 말단기
    if upper:
        gas_edge = min(a.z for a in gas_atoms)        # 가스 최하단
        surf_edge = z_T_after                          # 표면 최상단 말단기(가스쪽)
        gap = gas_edge - surf_edge
    else:
        gas_edge = max(a.z for a in gas_atoms)
        surf_edge = z_T_after
        gap = surf_edge - gas_edge

    return GeometryRow(surface, z_T_before, z_T_after,
                       z_ref_before, z_ref_after, abs(gap))


# ───────────────────────── CLI / 출력 ─────────────────────────
def _write_geometry_csv(rows: list[GeometryRow], out_path: str):
    header = ["surface", "z_T_before", "z_T_after", "z_ref_before", "z_ref_after"]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([r.surface, f"{r.z_T_before:.6f}", f"{r.z_T_after:.6f}",
                        f"{r.z_ref_before:.6f}", f"{r.z_ref_after:.6f}"])


def _run_manifest(manifest: str, files_dir: str, gas_default: str) -> list[GeometryRow]:
    rows = []
    with open(manifest, newline="", encoding="utf-8") as f:
        for rec in csv.DictReader(f):
            surf = (rec.get("surface") or "").strip()
            gas = (rec.get("gas") or gas_default).strip() or gas_default
            clean_f = (rec.get("clean_file") or "").strip()
            ad_f = (rec.get("adsorbed_file") or "").strip()
            if files_dir:
                clean_f = os.path.join(files_dir, clean_f) if clean_f else clean_f
                ad_f = os.path.join(files_dir, ad_f) if ad_f else ad_f
            if not (surf and clean_f and ad_f):
                print(f"[skip] 불완전한 행: {rec}", file=sys.stderr)
                continue
            try:
                rows.append(compute_geometry(surf, clean_f, ad_f, gas))
                print(f"[ok] {surf}: Δd={rows[-1].delta_d:.4f} Å "
                      f"gap={rows[-1].gas_surface_gap_A:.4f} Å")
            except Exception as exc:  # noqa: BLE001
                print(f"[skip] {surf}: {exc}", file=sys.stderr)
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="QE 파일에서 Δd(z 좌표) 추출 → geometry.csv")
    ap.add_argument("--manifest", help="surface,gas,clean_file,adsorbed_file CSV")
    ap.add_argument("--files-dir", default="", help="매니페스트의 파일 경로 접두 디렉터리")
    ap.add_argument("--surface", help="단일 쌍 모드: 표면 이름")
    ap.add_argument("--clean", help="단일 쌍 모드: clean(before) 파일")
    ap.add_argument("--adsorbed", help="단일 쌍 모드: adsorbed(after) 파일")
    ap.add_argument("--gas", default="SO2", help="가스(기본 SO2; Δd는 SO2 한정)")
    ap.add_argument("--out", default="data/geometry.csv", help="출력 CSV 경로")
    args = ap.parse_args(argv)

    if args.manifest:
        rows = _run_manifest(args.manifest, args.files_dir, args.gas)
    elif args.surface and args.clean and args.adsorbed:
        try:
            r = compute_geometry(args.surface, args.clean, args.adsorbed, args.gas)
            print(f"[ok] {args.surface}: Δd={r.delta_d:.4f} Å gap={r.gas_surface_gap_A:.4f} Å")
            rows = [r]
        except Exception as exc:  # noqa: BLE001
            print(f"[error] {args.surface}: {exc}", file=sys.stderr)
            rows = []
    else:
        ap.error("--manifest 또는 (--surface --clean --adsorbed) 중 하나가 필요합니다.")
        return 2

    if not rows:
        print("추출된 geometry 행이 없습니다. 입력 파일을 확인하세요.", file=sys.stderr)
        return 1
    _write_geometry_csv(rows, args.out)
    print(f"→ {args.out} 에 {len(rows)}행 기록 완료. "
          "대시보드(조성 지도 Δd 탭)·모델 정보에 자동 반영됩니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
