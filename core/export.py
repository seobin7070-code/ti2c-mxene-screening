"""내보내기 헬퍼: 표 → CSV bytes, 그림 → PNG bytes.

내보낸 데이터에는 출처(source_file)와 calc_group이 포함되어야 한다 (요구사항 11.3, DI-4).
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """DataFrame을 UTF-8(BOM) CSV 바이트로 변환한다 (한글 Excel 호환)."""
    return df.to_csv(index=False).encode("utf-8-sig")


def ensure_provenance_columns(df: pd.DataFrame) -> pd.DataFrame:
    """내보내기 전 출처 컬럼이 있는지 보장한다 (없으면 빈 컬럼 추가)."""
    out = df.copy()
    for col in ("source_file", "calc_group"):
        if col not in out.columns:
            out[col] = ""
    return out


def fig_to_png_bytes(fig: Any) -> bytes:
    """Plotly figure를 PNG 바이트로 변환한다 (kaleido 필요)."""
    # Plotly Figure.to_image(format="png") 는 kaleido 백엔드를 사용한다.
    return fig.to_image(format="png")
