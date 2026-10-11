"""디자인 토큰 — 색상·상태·가스색의 단일 소스.

의미가 고정된 색은 다른 용도로 재사용하지 않는다. 색만으로 구분하지 않도록
각 상태/가스에 아이콘·라벨을 함께 정의한다 (색각 이상 배려).
"""

from __future__ import annotations

# ── 중립/구조 색 ──────────────────────────────────────────────
BG = "#FAFAF9"
CARD = "#FFFFFF"
BORDER = "#E7E5E4"
PRIMARY = "#0F766E"        # 딥 틸 (신뢰/과학/환경) — 주조색
NAVY = "#0B1F33"           # 딥 네이비 — 히어로/보조
TINT = "#ECFDF5"           # 소프트 틸 틴트 (밝음)
TINT_2 = "#F0FDFA"         # 소프트 틸 틴트 (더 밝음)
TEXT = "#334155"           # 슬레이트 본문
TEXT_MUTED = "#64748B"     # 보조 텍스트

# ── 상태색 (의미 고정) ────────────────────────────────────────
STATUS = {
    "ok":      {"color": "#059669", "label": "정상",   "icon": "✓"},
    "pending": {"color": "#D97706", "label": "대기",   "icon": "◴"},
    "suspect": {"color": "#DC2626", "label": "의심",   "icon": "!"},
    "info":    {"color": "#2563EB", "label": "정보",   "icon": "ⓘ"},
}

# ── 가스별 고정 색 (모든 차트/배지 공통) ──────────────────────
GAS = {
    "CO2": {"color": "#0F766E", "label": "CO₂", "icon": "●"},
    "H2O": {"color": "#2563EB", "label": "H₂O", "icon": "▲"},
    "SO2": {"color": "#D97706", "label": "SO₂", "icon": "■"},
}


def status_meta(status: str) -> dict:
    return STATUS.get(status, STATUS["info"])


def gas_meta(gas: str) -> dict:
    return GAS.get(gas, {"color": TEXT_MUTED, "label": gas, "icon": "○"})
