"""core.loader 단위 테스트 (요구사항 1.1~1.5)."""

import os

from core.loader import (
    load_energies, parse_rows, validate_schema, validate_header,
    REQUIRED_COLUMNS,
)

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "energies.csv")

GOOD_FIELDS = list(REQUIRED_COLUMNS)


def _row(**kw):
    base = {
        "key": "A/mol/CO2", "role": "molecule", "surface": "", "gas": "CO2",
        "energy_Ry": "-94.82308357", "source_file": "CO2_isolated.out",
        "calc_group": "A", "status": "ok",
    }
    base.update(kw)
    return base


def test_load_initial_data_ok():
    res = load_energies(DATA)
    assert res.file_present is True
    assert res.errors == []
    # 초기 데이터는 10개 항목
    assert len(res.entries) == 10
    keys = {e.key for e in res.entries}
    assert "A/ad/SO2@Ti2CO2" in keys
    # H2O 단독 분자는 의도적으로 없어야 함
    assert not any(e.gas == "H2O" and e.role == "molecule" for e in res.entries)


def test_missing_file_returns_empty_registry():
    res = load_energies("/nonexistent/path/energies.csv")
    assert res.file_present is False
    assert res.entries == []
    assert res.errors == []


def test_missing_required_column_rejected():
    missing = validate_header(["key", "role", "energy_Ry"])  # 다수 누락
    assert "status" in missing and "calc_group" in missing


def test_invalid_role_rejected():
    res = parse_rows(GOOD_FIELDS, [_row(role="bogus")])
    assert len(res.entries) == 0
    assert len(res.errors) == 1
    assert "role" in res.errors[0].reason


def test_invalid_status_rejected():
    # unverified 등 3종 외 상태는 거부되어야 함
    res = parse_rows(GOOD_FIELDS, [_row(status="unverified")])
    assert len(res.entries) == 0
    assert "status" in res.errors[0].reason


def test_non_numeric_energy_rejected():
    res = parse_rows(GOOD_FIELDS, [_row(energy_Ry="N/A")])
    assert len(res.entries) == 0
    assert "energy_Ry" in res.errors[0].reason


def test_bad_row_does_not_stop_good_rows():
    res = parse_rows(GOOD_FIELDS, [_row(), _row(role="bogus"), _row(key="A/mol/SO2")])
    assert len(res.entries) == 2  # 정상 2개는 유지
    assert len(res.errors) == 1   # 잘못된 1개만 거부


def test_validate_schema_returns_errors():
    errs = validate_schema(GOOD_FIELDS, [_row(status="unverified")])
    assert len(errs) == 1
