"""core.export 테스트 (요구사항 11.1, 11.3)."""

import pandas as pd

from core.export import df_to_csv_bytes, ensure_provenance_columns


def test_csv_bytes_roundtrip():
    df = pd.DataFrame({"surface": ["Ti2CO2"], "E_ad_eV": [-0.894]})
    data = df_to_csv_bytes(df)
    assert isinstance(data, bytes)
    text = data.decode("utf-8-sig")
    assert "Ti2CO2" in text and "E_ad_eV" in text


def test_provenance_columns_added():
    df = pd.DataFrame({"surface": ["Ti2CO2"]})
    out = ensure_provenance_columns(df)
    assert "source_file" in out.columns
    assert "calc_group" in out.columns
