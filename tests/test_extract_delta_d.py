"""scripts/extract_delta_d.py — QE 파일에서 Δd·가스-표면 간격 추출 테스트.

합성 fixture(실제 DFT 아님, 검산 가능한 좌표)로 파서·기하 계산을 검증한다.
"""

import math
import os
import sys

HERE = os.path.dirname(__file__)
SCRIPTS = os.path.join(HERE, "..", "scripts")
FIX = os.path.join(HERE, "fixtures", "qe")
sys.path.insert(0, SCRIPTS)

import extract_delta_d as E  # noqa: E402


def test_parse_qe_output_angstrom():
    atoms = E.load_structure(os.path.join(FIX, "Ti2CO2_clean.out"))
    assert len(atoms) == 7
    assert sum(1 for a in atoms if a.element == "Ti") == 4
    # 완화 후 마지막 블록 좌표가 Å 그대로 읽힘
    o_top = [a for a in atoms if a.element == "O" and a.z > 13]
    assert o_top and math.isclose(o_top[0].z, 13.8, abs_tol=1e-6)


def test_parse_xyz_matches_out():
    a_out = E.load_structure(os.path.join(FIX, "SO2_on_Ti2CO2.out"))
    a_xyz = E.load_structure(os.path.join(FIX, "SO2_on_Ti2CO2.xyz"))
    assert len(a_out) == len(a_xyz) == 10
    # 같은 구조 → z 좌표 집합 동일
    assert sorted(round(a.z, 3) for a in a_out) == sorted(round(a.z, 3) for a in a_xyz)


def test_split_gas_uses_sulfur_anchor():
    """SO₂/표면이 O 를 공유해도 S 앵커로 가스 분자(S+O 2개)만 정확히 묶는다."""
    atoms = E.load_structure(os.path.join(FIX, "SO2_on_Ti2CO2.out"))
    gas, upper = E._split_gas_surface(atoms, "SO2")
    assert upper is True
    assert len(gas) == 3                                   # S + O 2개
    assert sum(1 for a in gas if a.element == "S") == 1
    assert sum(1 for a in gas if a.element == "O") == 2
    # 표면 말단 O(14.10)는 가스에 포함되지 않아야 함
    assert all(not math.isclose(a.z, 14.1, abs_tol=1e-6) for a in gas)


def test_compute_geometry_delta_d_and_gap():
    r = E.compute_geometry("Ti2CO2",
                           os.path.join(FIX, "Ti2CO2_clean.out"),
                           os.path.join(FIX, "SO2_on_Ti2CO2.out"), gas="SO2")
    # before: z_T=13.8, z_ref=12.5 → 1.3 | after: z_T=14.1, z_ref=12.5 → 1.6
    assert math.isclose(r.z_T_before, 13.8, abs_tol=1e-6)
    assert math.isclose(r.z_T_after, 14.1, abs_tol=1e-6)
    assert math.isclose(r.z_ref_before, 12.5, abs_tol=1e-6)
    assert math.isclose(r.z_ref_after, 12.5, abs_tol=1e-6)
    assert math.isclose(r.delta_d, 0.30, abs_tol=1e-6)      # |1.6 − 1.3|
    assert math.isclose(r.gas_surface_gap_A, 2.40, abs_tol=1e-6)  # S(16.5) − O(14.1)


def test_bohr_unit_converted():
    """bohr 단위 ATOMIC_POSITIONS 가 Å 로 변환되는지(1 bohr=0.529177 Å)."""
    import tempfile
    content = (
        "ATOMIC_POSITIONS (bohr)\n"
        "Ti  0.0  0.0  10.0\n"
        "O   0.0  0.0  20.0\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".out", delete=False) as f:
        f.write(content)
        path = f.name
    try:
        atoms = E.load_structure(path)
        assert math.isclose(atoms[0].z, 10.0 * E.BOHR_TO_ANG, abs_tol=1e-6)
        assert math.isclose(atoms[1].z, 20.0 * E.BOHR_TO_ANG, abs_tol=1e-6)
    finally:
        os.remove(path)


def test_geometry_feeds_screening_delta_d(tmp_path):
    """추출한 geometry.csv 를 core.screening 이 읽어 Δd 를 계산할 수 있다(대시보드 반영 경로)."""
    from core import screening as S
    out = tmp_path / "geometry.csv"
    r = E.compute_geometry("Ti2CO2",
                           os.path.join(FIX, "Ti2CO2_clean.out"),
                           os.path.join(FIX, "SO2_on_Ti2CO2.out"), gas="SO2")
    E._write_geometry_csv([r], str(out))
    geom = S.load_geometry(str(out))
    assert "Ti2CO2" in geom
    dd = S.delta_d_for_surface(geom, "Ti2CO2")
    assert dd.ok and math.isclose(dd.value_A, 0.30, abs_tol=1e-6)


def test_geometry_csv_includes_gas_surface_gap(tmp_path):
    """geometry.csv 에 gas_surface_gap_A 컬럼이 기록되고 load_geometry 가 읽어온다."""
    import csv
    from core import screening as S
    out = tmp_path / "geometry.csv"
    r = E.compute_geometry("Ti2CO2",
                           os.path.join(FIX, "Ti2CO2_clean.out"),
                           os.path.join(FIX, "SO2_on_Ti2CO2.out"), gas="SO2")
    E._write_geometry_csv([r], str(out))

    # CSV 헤더에 새 컬럼이 포함되고 값이 기록되는지
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert "gas_surface_gap_A" in rows[0]
    assert math.isclose(float(rows[0]["gas_surface_gap_A"]), 2.40, abs_tol=1e-6)

    # load_geometry → gas_surface_gap_for_surface 경로(대시보드 '가스–표면 간격' 축)
    geom = S.load_geometry(str(out))
    gap = S.gas_surface_gap_for_surface(geom, "Ti2CO2")
    assert gap.ok and math.isclose(gap.value_A, 2.40, abs_tol=1e-6)


def test_gas_surface_gap_missing_when_column_absent(tmp_path):
    """구형 포맷(gap 컬럼 없음)에서도 Δd 는 되고 gap 은 '데이터 없음'으로 안전 처리."""
    from core import screening as S
    out = tmp_path / "geometry_old.csv"
    out.write_text(
        "surface,z_T_before,z_T_after,z_ref_before,z_ref_after\n"
        "Ti2CO2,13.8,14.1,12.5,12.5\n",
        encoding="utf-8",
    )
    geom = S.load_geometry(str(out))
    assert S.delta_d_for_surface(geom, "Ti2CO2").ok          # Δd 는 여전히 계산
    gap = S.gas_surface_gap_for_surface(geom, "Ti2CO2")
    assert not gap.ok and gap.value_A is None                 # gap 은 안전하게 없음
