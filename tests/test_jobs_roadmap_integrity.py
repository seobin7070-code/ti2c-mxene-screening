"""jobs 자동 동기화, roadmap 규칙, integrity 점검, datafiles 유틸 테스트."""

import os

from core.loader import load_energies
from core.composition import load_composition_map
from core import jobs as J
from core import roadmap as R
from core import integrity as I
from core import datafiles as D

HERE = os.path.dirname(__file__)
ENERGIES = os.path.join(HERE, "..", "data", "energies.csv")
COMP = os.path.join(HERE, "..", "data", "composition_map.csv")


def load():
    return load_energies(ENERGIES).entries, load_composition_map(COMP)


# ── jobs ───────────────────────────────────────────────────────
def test_jobs_initial_count_34():
    jobs = J.build_initial_jobs()
    # 가스 3 + 표면 10 + 복합체 21 = 34
    assert len(jobs) == 34
    assert sum(1 for j in jobs if j["type"] == "molecule") == 3
    assert sum(1 for j in jobs if j["type"] == "clean") == 10
    assert sum(1 for j in jobs if j["type"] == "adsorbed") == 21


def test_jobs_no_fabricated_walltime():
    for j in J.build_initial_jobs():
        assert j["wall_time_h"] == ""   # 가상 수치 금지
        assert j["status"] == "todo"


def test_jobs_sync_marks_done_from_energies():
    entries, _ = load()
    synced = J.sync_with_energies(J.build_initial_jobs(), entries)
    # CO2 단독, Ti2CO2 clean, SO2@Ti2CO2 복합체는 energies.csv에 있으므로 done
    def status(jtype, surface, gas):
        for j in synced:
            if j["type"] == jtype and j["surface"] == surface and j["gas"] == gas:
                return j["status"]
        return None
    assert status("molecule", "", "CO2") == "done"
    assert status("clean", "Ti2CO2", "") == "done"
    assert status("adsorbed", "Ti2CO2", "SO2") == "done"
    # H2O 단독은 없으므로 todo
    assert status("molecule", "", "H2O") == "todo"


def test_jobs_eta_measurement_needed_when_no_time():
    est = J.estimate_remaining(J.build_initial_jobs())
    assert est["eta_h"] is None
    assert est["note"] == "측정 필요"


def test_jobs_eta_computed_with_times():
    jobs = J.build_initial_jobs()
    jobs[0]["wall_time_h"] = "2.0"
    jobs[1]["wall_time_h"] = "4.0"
    est = J.estimate_remaining(jobs)
    assert est["avg_h"] == 3.0
    assert est["eta_h"] is not None


# ── roadmap ────────────────────────────────────────────────────
def test_roadmap_rule_deterministic_sort():
    entries, comp = load()
    items = R.metric_roadmap(entries, comp, "P(CO2/SO2)")
    counts = [it.missing_count for it in items]
    assert counts == sorted(counts)  # 부족 수 오름차순
    # 동점은 표면명 알파벳순
    for i in range(len(items) - 1):
        if items[i].missing_count == items[i + 1].missing_count:
            assert items[i].surface <= items[i + 1].surface


def test_roadmap_overview_structure():
    entries, comp = load()
    ov = R.roadmap_overview(entries, comp, {"P(CO2/H2O)": "P(CO₂/H₂O)",
                            "P(CO2/SO2)": "P(CO₂/SO₂)", "Δd": "Δd"}, need=7)
    assert len(ov) == 3
    for row in ov:
        assert row["current"] < 7   # 현재 데이터는 모두 7 미만


# ── integrity ──────────────────────────────────────────────────
def test_integrity_all_pass_or_warn_on_initial_data():
    entries, _ = load()
    checks = I.run_all(entries)
    names = {c.name for c in checks}
    assert "중복 key 검사" in names
    assert "E_ad 재현성" in names
    # 중복 key 없음, status 유효 → pass
    by = {c.name: c for c in checks}
    assert by["중복 key 검사"].status == "pass"
    assert by["status 값 유효성"].status == "pass"
    assert by["E_ad 재현성"].status == "pass"


def test_integrity_detects_duplicate_key():
    entries, _ = load()
    dup = entries + [entries[0]]
    c = I.check_duplicate_keys(dup)
    assert c.status == "fail"


# ── datafiles ──────────────────────────────────────────────────
def test_sha256_stable():
    h1 = D.sha256_text("hello")
    h2 = D.sha256_text("hello")
    assert h1 == h2 and len(h1) == 64


def test_atomic_write_and_backup(tmp_path):
    p = tmp_path / "x.csv"
    D.atomic_write(str(p), "a,b\n1,2\n")
    assert p.read_text() == "a,b\n1,2\n"
    bdir = tmp_path / "backup"
    bak = D.backup_file(str(p), str(bdir))
    assert bak and os.path.exists(bak)


def test_audit_log_append(tmp_path):
    ap = tmp_path / "audit_log.csv"
    D.append_audit(str(ap), "add_row", "A/x", "", "-1.0", "x.out")
    text = ap.read_text()
    assert "add_row" in text and "A/x" in text
    assert text.splitlines()[0].startswith("timestamp")
