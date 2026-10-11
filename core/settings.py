"""config/settings.json 로드 (PDF 5장 분류 설정값).

화면에서 바꿀 수 있는 설정을 한 곳에서 읽는다. 파일이 없으면 PDF 기본값을 쓴다.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

DEFAULTS = {
    "kappa": 1.0,
    "margin_m_eV": 0.10,
    "delta_d_max_A": None,
    "sigma_max_eV": None,
    "preset": "condition_input",
    "wide_range": {"reject_below_eV": -0.10, "prefer_above_eV": 0.25},
    "composition_grid": "quarter",
    "min_train_points": 7,
    "min_distance_far_threshold": 4.0,
}


@dataclass
class Settings:
    kappa: float = 1.0
    margin_m_eV: float = 0.10
    delta_d_max_A: Optional[float] = None
    sigma_max_eV: Optional[float] = None
    preset: str = "condition_input"
    wide_range: dict = field(default_factory=lambda: dict(DEFAULTS["wide_range"]))
    composition_grid: str = "quarter"
    min_train_points: int = 7
    min_distance_far_threshold: float = 4.0


def load_settings(path: str) -> Settings:
    data = dict(DEFAULTS)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data.update(json.load(f))
        except (json.JSONDecodeError, OSError):
            pass  # 손상 시 기본값
    return Settings(
        kappa=data.get("kappa", 1.0),
        margin_m_eV=data.get("margin_m_eV", 0.10),
        delta_d_max_A=data.get("delta_d_max_A"),
        sigma_max_eV=data.get("sigma_max_eV"),
        preset=data.get("preset", "condition_input"),
        wide_range=data.get("wide_range", dict(DEFAULTS["wide_range"])),
        composition_grid=data.get("composition_grid", "quarter"),
        min_train_points=int(data.get("min_train_points", 7)),
        min_distance_far_threshold=float(data.get("min_distance_far_threshold", 4.0)),
    )
