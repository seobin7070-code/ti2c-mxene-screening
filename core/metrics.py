"""선택 지표: P(CO2/H2O), P(CO2/SO2), Δd_surface.

필요한 가스 흡착 데이터가 하나라도 없으면 계산하지 않고 pending을 반환한다 (요구사항 5.2, DI-2).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.energetics import AdResult
from core.units import ry_to_ev


@dataclass(frozen=True)
class MetricResult:
    label: str
    ok: bool                    # True면 value 유효, False면 pending
    value_eV: Optional[float]
    value_Ry: Optional[float]
    reason: Optional[str]       # pending 사유 (한국어)
    calc_group: Optional[str]


def _pending(label: str, reason: str) -> MetricResult:
    return MetricResult(label, False, None, None, reason, None)


def selectivity_P(
    label: str,
    e_ad_target: Optional[AdResult],
    e_ad_co2: Optional[AdResult],
    target_name: str,
) -> MetricResult:
    """P = E_ads(target) − E_ads(CO2).

    두 흡착 에너지가 모두 유효하게 계산되고 calc_group이 같을 때만 계산한다.
    """
    if e_ad_co2 is None or not e_ad_co2.ok:
        return _pending(label, "CO2 흡착 에너지 없음 또는 계산 불가")
    if e_ad_target is None or not e_ad_target.ok:
        return _pending(label, f"{target_name} 흡착 에너지 없음 또는 계산 불가")
    if e_ad_target.calc_group != e_ad_co2.calc_group:
        return _pending(
            label,
            f"calc_group 불일치: {target_name}={e_ad_target.calc_group}, "
            f"CO2={e_ad_co2.calc_group}",
        )

    v_ry = e_ad_target.E_ad_Ry - e_ad_co2.E_ad_Ry
    return MetricResult(label, True, ry_to_ev(v_ry), v_ry, None, e_ad_target.calc_group)


@dataclass(frozen=True)
class GeometryRow:
    surface: str
    gas: str
    z_before: float
    z_after: float
    source_file: str
    calc_group: str


@dataclass(frozen=True)
class DeltaDResult:
    ok: bool
    value: Optional[float]      # Å, 단위는 입력 geometry.csv에 따름
    reason: Optional[str]
    source_file: Optional[str]
    calc_group: Optional[str]


def delta_d(geom: Optional[GeometryRow]) -> DeltaDResult:
    """Δd = |mean(z_after) − mean(z_before)| (가스 쪽 면 말단 평균 z 변화량, SO2 한정).

    현재 스키마는 이미 '평균 z' 한 값을 담으므로 절댓값 차이로 계산한다.
    geometry 행이 없으면 pending (요구사항 5.4).
    """
    if geom is None:
        return DeltaDResult(False, None, "geometry 데이터 없음 (z_before/z_after 미입력)", None, None)
    value = abs(geom.z_after - geom.z_before)
    return DeltaDResult(True, value, None, geom.source_file, geom.calc_group)


def load_geometry(path: str) -> dict[tuple[str, str], GeometryRow]:
    """data/geometry.csv를 로드한다. 파일이 없거나 비어 있으면 빈 매핑 → Δd pending."""
    import csv
    import os

    result: dict[tuple[str, str], GeometryRow] = {}
    if not os.path.exists(path):
        return result
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            surface = (row.get("surface") or "").strip()
            gas = (row.get("gas") or "").strip()
            zb = (row.get("z_before") or "").strip()
            za = (row.get("z_after") or "").strip()
            if not surface or zb == "" or za == "":
                continue
            try:
                result[(surface, gas)] = GeometryRow(
                    surface=surface, gas=gas,
                    z_before=float(zb), z_after=float(za),
                    source_file=(row.get("source_file") or "").strip(),
                    calc_group=(row.get("calc_group") or "").strip(),
                )
            except ValueError:
                continue
    return result
