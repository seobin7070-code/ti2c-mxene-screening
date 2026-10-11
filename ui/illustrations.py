"""인라인 SVG 일러스트 — 외부 이미지 없이 함수로 생성.

모든 SVG는 CSS 변수(var(--ill-*))로 색을 받아 다크모드에서도 읽힌다.
가스 고정색은 ui.tokens 에서 가져온다 (CO2 틸 · H2O 블루 · SO2 앰버).
개념도에는 "실제 계산 구조·결과가 아님" 캡션을 붙인다 (데이터 무결성).

애니메이션은 CSS에서 prefers-reduced-motion 시 정지하도록 theme.py 에 정의한다.
"""

from __future__ import annotations

from ui import tokens as T

CAPTION = "개념도 — 실제 계산 구조·결과가 아님"


def _caption() -> str:
    return f'<div class="ill-caption">{CAPTION}</div>'


# ── 1. 히어로 도식: MXene 층상 단면 + 말단기 + 접근하는 가스 분자 ──────
def hero_mxene(animate: bool = True) -> str:
    """Ti–C–Ti 층과 -O/-F/-OH 말단기, 위에서 접근하는 CO2/H2O/SO2."""
    co2, h2o, so2 = T.GAS["CO2"]["color"], T.GAS["H2O"]["color"], T.GAS["SO2"]["color"]
    cls = "ill-float" if animate else ""
    return f'''
<svg viewBox="0 0 420 300" class="ill-hero" role="img"
     aria-label="MXene 층상 구조 단면과 표면 말단기, 위에서 접근하는 CO2·H2O·SO2 분자 개념도"
     xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="glow" cx="50%" cy="20%" r="80%">
      <stop offset="0%" stop-color="rgba(255,255,255,0.18)"/>
      <stop offset="100%" stop-color="rgba(255,255,255,0)"/>
    </radialGradient>
  </defs>
  <rect x="0" y="0" width="420" height="300" fill="url(#glow)"/>

  <!-- 접근하는 가스 분자들 (가스 고정색, 구+막대) -->
  <g class="{cls}" style="animation-delay:0s">
    <!-- CO2: O=C=O -->
    <g transform="translate(90,60)">
      <line x1="-18" y1="0" x2="18" y2="0" stroke="var(--ill-stroke)" stroke-width="3"/>
      <circle cx="-18" cy="0" r="8" fill="{co2}"/>
      <circle cx="0" cy="0" r="9" fill="var(--ill-carbon)"/>
      <circle cx="18" cy="0" r="8" fill="{co2}"/>
      <text x="0" y="26" class="ill-mol-label">CO₂</text>
    </g>
  </g>
  <g class="{cls}" style="animation-delay:1.2s">
    <!-- H2O: 굽은 분자 -->
    <g transform="translate(210,45)">
      <line x1="0" y1="0" x2="-15" y2="-9" stroke="var(--ill-stroke)" stroke-width="3"/>
      <line x1="0" y1="0" x2="15" y2="-9" stroke="var(--ill-stroke)" stroke-width="3"/>
      <circle cx="0" cy="0" r="9" fill="{h2o}"/>
      <circle cx="-15" cy="-9" r="6" fill="var(--ill-h)"/>
      <circle cx="15" cy="-9" r="6" fill="var(--ill-h)"/>
      <text x="0" y="28" class="ill-mol-label">H₂O</text>
    </g>
  </g>
  <g class="{cls}" style="animation-delay:2.4s">
    <!-- SO2: 굽은 분자 -->
    <g transform="translate(320,62)">
      <line x1="0" y1="0" x2="-16" y2="8" stroke="var(--ill-stroke)" stroke-width="3"/>
      <line x1="0" y1="0" x2="16" y2="8" stroke="var(--ill-stroke)" stroke-width="3"/>
      <circle cx="0" cy="0" r="9" fill="{so2}"/>
      <circle cx="-16" cy="8" r="7" fill="var(--ill-o)"/>
      <circle cx="16" cy="8" r="7" fill="var(--ill-o)"/>
      <text x="0" y="30" class="ill-mol-label">SO₂</text>
    </g>
  </g>

  <!-- 접근 화살표 -->
  <g stroke="var(--ill-faint)" stroke-width="1.5" stroke-dasharray="3 4" fill="none">
    <path d="M90 92 L90 150"/>
    <path d="M210 80 L210 150"/>
    <path d="M320 96 L320 150"/>
  </g>

  <!-- 표면 말단기 (색 점 + 라벨) -->
  <g>
    <circle cx="70" cy="168" r="7" fill="var(--ill-o)"/>
    <circle cx="140" cy="168" r="7" fill="var(--ill-f)"/>
    <circle cx="210" cy="168" r="7" fill="var(--ill-oh)"/>
    <circle cx="280" cy="168" r="7" fill="var(--ill-o)"/>
    <circle cx="350" cy="168" r="7" fill="var(--ill-f)"/>
  </g>

  <!-- MXene 층상 구조: Ti–C–Ti -->
  <g>
    <rect x="40" y="182" width="340" height="22" rx="4" fill="var(--ill-ti)" opacity="0.92"/>
    <rect x="40" y="206" width="340" height="18" rx="4" fill="var(--ill-c)" opacity="0.92"/>
    <rect x="40" y="226" width="340" height="22" rx="4" fill="var(--ill-ti)" opacity="0.92"/>
    <text x="392" y="197" class="ill-layer-label">Ti</text>
    <text x="392" y="219" class="ill-layer-label">C</text>
    <text x="392" y="241" class="ill-layer-label">Ti</text>
  </g>

  <!-- 말단기 범례 -->
  <g class="ill-legend">
    <circle cx="52" cy="272" r="5" fill="var(--ill-o)"/><text x="62" y="276">-O</text>
    <circle cx="110" cy="272" r="5" fill="var(--ill-f)"/><text x="120" y="276">-F</text>
    <circle cx="168" cy="272" r="5" fill="var(--ill-oh)"/><text x="178" y="276">-OH</text>
  </g>
</svg>'''


# ── 2. 배가스 개념도: 굴뚝 → MXene 표면 → 선택 흡착 ───────────────────
def flue_gas_flow() -> str:
    co2, h2o, so2 = T.GAS["CO2"]["color"], T.GAS["H2O"]["color"], T.GAS["SO2"]["color"]
    svg = f'''
<svg viewBox="0 0 640 150" class="ill-flow" role="img"
     aria-label="굴뚝 배가스에서 MXene 표면을 거쳐 선택 흡착으로 이어지는 흐름 개념도"
     xmlns="http://www.w3.org/2000/svg">
  <!-- 굴뚝 -->
  <g>
    <rect x="20" y="40" width="34" height="80" rx="3" fill="var(--ill-ti)" opacity="0.85"/>
    <rect x="16" y="34" width="42" height="10" rx="3" fill="var(--ill-navy)"/>
    <circle cx="30" cy="26" r="5" fill="{co2}" opacity="0.6"/>
    <circle cx="42" cy="18" r="6" fill="{so2}" opacity="0.5"/>
    <circle cx="36" cy="10" r="4" fill="{h2o}" opacity="0.5"/>
    <text x="37" y="138" class="ill-flow-label">배가스</text>
  </g>
  <!-- 가스 아이콘 -->
  <g>
    <circle cx="150" cy="55" r="9" fill="{co2}"/><text x="150" y="80" class="ill-mol-label">CO₂</text>
    <circle cx="150" cy="92" r="9" fill="{h2o}"/><text x="190" y="60" class="ill-mol-label">H₂O</text>
    <circle cx="188" cy="48" r="9" fill="{so2}"/><text x="150" y="118" class="ill-mol-label">SO₂</text>
  </g>
  <path d="M70 80 L240 80" stroke="var(--ill-faint)" stroke-width="2" marker-end="url(#arr)"/>
  <!-- MXene 표면 -->
  <g>
    <rect x="270" y="58" width="120" height="16" rx="3" fill="var(--ill-ti)"/>
    <rect x="270" y="76" width="120" height="12" rx="3" fill="var(--ill-c)"/>
    <circle cx="290" cy="52" r="4" fill="var(--ill-o)"/>
    <circle cx="320" cy="52" r="4" fill="var(--ill-f)"/>
    <circle cx="350" cy="52" r="4" fill="var(--ill-oh)"/>
    <circle cx="378" cy="52" r="4" fill="var(--ill-o)"/>
    <text x="330" y="112" class="ill-flow-label">MXene 표면</text>
  </g>
  <path d="M400 80 L470 80" stroke="var(--ill-faint)" stroke-width="2" marker-end="url(#arr)"/>
  <!-- 선택 흡착 결과 -->
  <g>
    <rect x="500" y="50" width="120" height="46" rx="8" fill="var(--ill-tint)" stroke="var(--ill-faint)"/>
    <circle cx="522" cy="73" r="8" fill="{co2}"/>
    <text x="560" y="78" class="ill-flow-label" text-anchor="middle">선택 흡착</text>
  </g>
  <defs>
    <marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0 0 L8 4 L0 8 z" fill="var(--ill-faint)"/>
    </marker>
  </defs>
</svg>'''
    return svg + _caption()


# ── 3. 파이프라인 4단계 가로 스텝 (상태 pill은 app에서 데이터로 계산해 주입) ──
def pipeline(steps: list[dict]) -> str:
    """steps: [{title, desc, status, status_label, icon_svg}] 4개.

    status: ok(완료) | pending(대기) | locked(잠금). 상태는 호출부(app)에서 데이터로 계산.
    """
    from ui import components as C

    cells = []
    for i, s in enumerate(steps):
        pill = C.status_pill(s["status"], s.get("status_label", ""))
        arrow = ('<div class="pipe-arrow" aria-hidden="true">→</div>'
                 if i < len(steps) - 1 else "")
        cells.append(
            f'<div class="pipe-step">'
            f'<div class="pipe-icon">{s["icon_svg"]}</div>'
            f'<div class="pipe-step-no">STEP {i+1}</div>'
            f'<div class="pipe-title">{s["title"]}</div>'
            f'<div class="pipe-desc">{s["desc"]}</div>'
            f'<div style="margin-top:8px">{pill}</div>'
            f'</div>{arrow}'
        )
    return (f'<div class="pipeline">{"".join(cells)}</div>' + _caption())


# ── 작은 스텝 아이콘 SVG들 ────────────────────────────────────────
def icon_dft() -> str:
    return ('<svg viewBox="0 0 24 24" class="pipe-svg"><circle cx="12" cy="12" r="3" '
            'fill="var(--ill-accent)"/><ellipse cx="12" cy="12" rx="10" ry="4.5" '
            'fill="none" stroke="var(--ill-accent)" stroke-width="1.4"/>'
            '<ellipse cx="12" cy="12" rx="10" ry="4.5" fill="none" '
            'stroke="var(--ill-accent)" stroke-width="1.4" transform="rotate(60 12 12)"/>'
            '<ellipse cx="12" cy="12" rx="10" ry="4.5" fill="none" '
            'stroke="var(--ill-accent)" stroke-width="1.4" transform="rotate(120 12 12)"/></svg>')


def icon_metrics() -> str:
    return ('<svg viewBox="0 0 24 24" class="pipe-svg"><path d="M4 20 L4 4" '
            'stroke="var(--ill-accent)" stroke-width="1.6"/><path d="M4 20 L20 20" '
            'stroke="var(--ill-accent)" stroke-width="1.6"/><rect x="7" y="12" width="3" '
            'height="6" fill="var(--ill-accent)"/><rect x="12" y="8" width="3" height="10" '
            'fill="var(--ill-accent)" opacity="0.7"/><rect x="17" y="5" width="3" height="13" '
            'fill="var(--ill-accent)" opacity="0.5"/></svg>')


def icon_gpr() -> str:
    return ('<svg viewBox="0 0 24 24" class="pipe-svg"><path d="M3 17 C7 6 10 6 13 11 '
            'C16 16 19 16 21 7" fill="none" stroke="var(--ill-accent)" stroke-width="1.6"/>'
            '<circle cx="7" cy="10.5" r="1.8" fill="var(--ill-accent)"/>'
            '<circle cx="13" cy="11" r="1.8" fill="var(--ill-accent)"/>'
            '<circle cx="18" cy="10.5" r="1.8" fill="var(--ill-accent)"/></svg>')


def icon_al() -> str:
    return ('<svg viewBox="0 0 24 24" class="pipe-svg"><circle cx="12" cy="12" r="8.5" '
            'fill="none" stroke="var(--ill-accent)" stroke-width="1.5"/>'
            '<circle cx="12" cy="12" r="2.2" fill="var(--ill-accent)"/>'
            '<path d="M12 2 L12 5 M12 19 L12 22 M2 12 L5 12 M19 12 L22 12" '
            'stroke="var(--ill-accent)" stroke-width="1.5"/></svg>')


# ── 4. 조성 삼각도 모티프 (로고/헤더 재사용). points: [(x,y)]는 그릴 조성 좌표 ──
def composition_triangle(size: int = 28, points: list[tuple[float, float, float]] | None = None) -> str:
    """세 꼭짓점이 -O/-F/-OH 인 삼각형. points 는 [xO,xF,xOH] 리스트(합≈1)."""
    # 삼각형 꼭짓점 (위=O, 좌하=F, 우하=OH)
    ax, ay = size / 2, 2.0
    bx, by = 2.0, size - 2.0
    cx, cy = size - 2.0, size - 2.0
    dots = ""
    for p in (points or []):
        xo, xf, xoh = p
        # 무게중심 좌표 → 데카르트
        px = xo * ax + xf * bx + xoh * cx
        py = xo * ay + xf * by + xoh * cy
        dots += (f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{max(1.6, size*0.07):.1f}" '
                 f'fill="var(--ill-accent)"/>')
    return (f'<svg viewBox="0 0 {size} {size}" class="ill-tri" aria-hidden="true" '
            f'xmlns="http://www.w3.org/2000/svg">'
            f'<polygon points="{ax},{ay} {bx},{by} {cx},{cy}" fill="none" '
            f'stroke="var(--ill-accent)" stroke-width="1.4" stroke-linejoin="round"/>'
            f'<circle cx="{ax}" cy="{ay}" r="1.8" fill="var(--ill-o)"/>'
            f'<circle cx="{bx}" cy="{by}" r="1.8" fill="var(--ill-f)"/>'
            f'<circle cx="{cx}" cy="{cy}" r="1.8" fill="var(--ill-oh)"/>'
            f'{dots}</svg>')


# ── 표면 말단기 모식도 (정방향 입력 패널) ───────────────────────
def surface_motif(comp) -> str:
    """선택한 표면의 말단기 구성을 색 점으로 표현. comp는 Composition(또는 None).

    조성이 확정되지 않았으면(None/빈값) 미확정 표시를 반환한다 (꾸밈 없음).
    """
    if comp is None or comp.xO is None or comp.xF is None or comp.xOH is None:
        return ('<svg viewBox="0 0 220 90" class="ill-flow" role="img" '
                'aria-label="표면 조성 미확정">'
                '<rect x="20" y="48" width="180" height="16" rx="3" fill="var(--ill-ti)"/>'
                '<rect x="20" y="66" width="180" height="12" rx="3" fill="var(--ill-c)"/>'
                '<text x="110" y="30" class="ill-flow-label">조성 미확정</text></svg>')
    # 비율에 따라 점 개수 배분 (총 8개 점, 정수 반올림)
    total = 8
    counts = {
        "o": round(comp.xO * total), "f": round(comp.xF * total), "oh": round(comp.xOH * total),
    }
    colors = {"o": "var(--ill-o)", "f": "var(--ill-f)", "oh": "var(--ill-oh)"}
    seq = (["o"] * counts["o"]) + (["f"] * counts["f"]) + (["oh"] * counts["oh"])
    seq = seq[:total] if seq else []
    dots = ""
    x0 = 30
    step = 160 / max(1, (len(seq) - 1)) if len(seq) > 1 else 0
    for i, k in enumerate(seq):
        cx = x0 + i * step
        dots += f'<circle cx="{cx:.1f}" cy="40" r="6" fill="{colors[k]}"/>'
    legend = (
        f'<circle cx="30" cy="84" r="4" fill="var(--ill-o)"/><text x="38" y="88" '
        f'class="ill-legend-t">-O</text>'
        f'<circle cx="80" cy="84" r="4" fill="var(--ill-f)"/><text x="88" y="88" '
        f'class="ill-legend-t">-F</text>'
        f'<circle cx="128" cy="84" r="4" fill="var(--ill-oh)"/><text x="136" y="88" '
        f'class="ill-legend-t">-OH</text>'
    )
    return (f'<svg viewBox="0 0 220 100" class="ill-flow" role="img" '
            f'aria-label="선택한 표면의 말단기 구성 모식도">'
            f'{dots}'
            f'<rect x="20" y="52" width="180" height="16" rx="3" fill="var(--ill-ti)"/>'
            f'<rect x="20" y="70" width="180" height="12" rx="3" fill="var(--ill-c)"/>'
            f'<g class="ill-legend">{legend}</g></svg>')


# ── 조성 커버리지 삼각도 (보고서 7개 조성 상태) ─────────────────
def coverage_triangle(points: list[dict], size: int = 260) -> str:
    """7개 조성 좌표를 상태별로 표시.

    points: [{coord:(xO,xF,xOH)|None, state: 'done'|'planned'|'unconfirmed', label}]
      done=채운 원, planned=빈 원, unconfirmed=점선 원.
    coord=None(삼원 혼합 등)은 삼각형 중심 근처에 배치.
    """
    pad = 30
    ax, ay = size / 2, pad                    # 위 꼭짓점 = O
    bx, by = pad, size - pad                  # 좌하 = F
    cx, cy = size - pad, size - pad           # 우하 = OH
    dots = ""
    for p in points:
        coord = p.get("coord")
        if coord is None:
            px, py = size / 2, (ay + by + cy) / 3 + 6  # 중심
        else:
            xo, xf, xoh = coord
            px = xo * ax + xf * bx + xoh * cx
            py = xo * ay + xf * by + xoh * cy
        state = p.get("state", "planned")
        if state == "done":
            dots += (f'<circle cx="{px:.1f}" cy="{py:.1f}" r="7" fill="var(--ill-accent)" '
                     f'stroke="#fff" stroke-width="1.5"/>')
        elif state == "unconfirmed":
            dots += (f'<circle cx="{px:.1f}" cy="{py:.1f}" r="7" fill="none" '
                     f'stroke="var(--ill-f)" stroke-width="2" stroke-dasharray="3 3"/>')
        else:  # planned
            dots += (f'<circle cx="{px:.1f}" cy="{py:.1f}" r="7" fill="none" '
                     f'stroke="var(--ill-accent)" stroke-width="2"/>')
    return (f'<svg viewBox="0 0 {size} {size}" class="coverage-tri" role="img" '
            f'aria-label="보고서 정의 7개 조성의 커버리지 삼각도" '
            f'xmlns="http://www.w3.org/2000/svg">'
            f'<polygon points="{ax},{ay} {bx},{by} {cx},{cy}" fill="var(--ill-tint)" '
            f'fill-opacity="0.4" stroke="var(--ill-faint)" stroke-width="1.5" '
            f'stroke-linejoin="round"/>'
            f'<text x="{ax}" y="{ay-8}" class="ill-flow-label">-O</text>'
            f'<text x="{bx-4}" y="{by+16}" class="ill-flow-label">-F</text>'
            f'<text x="{cx+4}" y="{cy+16}" class="ill-flow-label">-OH</text>'
            f'{dots}</svg>')


# ── 5. 빈 상태용 소형 일러스트 ────────────────────────────────────
def empty_locked() -> str:
    return ('<svg viewBox="0 0 64 64" class="ill-empty" role="img" aria-label="잠긴 모델">'
            '<rect x="18" y="30" width="28" height="22" rx="4" fill="none" '
            'stroke="var(--ill-accent)" stroke-width="2"/>'
            '<path d="M24 30 V24 a8 8 0 0 1 16 0 V30" fill="none" '
            'stroke="var(--ill-accent)" stroke-width="2"/>'
            '<circle cx="32" cy="40" r="3" fill="var(--ill-accent)"/>'
            '<rect x="31" y="42" width="2" height="6" fill="var(--ill-accent)"/></svg>')


def empty_waiting() -> str:
    return ('<svg viewBox="0 0 64 64" class="ill-empty" role="img" aria-label="데이터 대기">'
            '<circle cx="32" cy="32" r="20" fill="none" stroke="var(--ill-accent)" '
            'stroke-width="2" stroke-dasharray="4 5"/>'
            '<path d="M32 20 V32 L40 38" fill="none" stroke="var(--ill-accent)" '
            'stroke-width="2.4" stroke-linecap="round"/></svg>')


def empty_chart() -> str:
    return ('<svg viewBox="0 0 64 64" class="ill-empty" role="img" aria-label="데이터 없음">'
            '<path d="M12 52 V12" stroke="var(--ill-accent)" stroke-width="2"/>'
            '<path d="M12 52 H52" stroke="var(--ill-accent)" stroke-width="2"/>'
            '<rect x="20" y="36" width="6" height="12" fill="var(--ill-accent)" opacity="0.5"/>'
            '<rect x="30" y="28" width="6" height="20" fill="var(--ill-accent)" opacity="0.5"/>'
            '<rect x="40" y="40" width="6" height="8" fill="var(--ill-accent)" opacity="0.5"/></svg>')


# ── 시작 화면: 흐르는 분자 점·선 패턴 (배경) ────────────────────
def molecule_pattern() -> str:
    """어두운 배경 위를 천천히 흐르는 분자 점·선 패턴. CSS로 애니메이션/정지."""
    return '''
<svg class="landing-pattern" viewBox="0 0 1200 600" preserveAspectRatio="xMidYMid slice"
     aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
  <g class="lp-drift" fill="none" stroke="rgba(94,234,212,0.18)" stroke-width="1">
    <g>
      <circle cx="120" cy="120" r="3" fill="rgba(94,234,212,0.4)"/>
      <circle cx="260" cy="200" r="3" fill="rgba(94,234,212,0.3)"/>
      <circle cx="420" cy="90"  r="3" fill="rgba(94,234,212,0.35)"/>
      <circle cx="600" cy="240" r="3" fill="rgba(94,234,212,0.3)"/>
      <circle cx="780" cy="140" r="3" fill="rgba(94,234,212,0.35)"/>
      <circle cx="960" cy="260" r="3" fill="rgba(94,234,212,0.3)"/>
      <circle cx="1100" cy="120" r="3" fill="rgba(94,234,212,0.35)"/>
      <path d="M120 120 L260 200 L420 90 L600 240 L780 140 L960 260 L1100 120"/>
      <circle cx="180" cy="420" r="3" fill="rgba(94,234,212,0.3)"/>
      <circle cx="360" cy="500" r="3" fill="rgba(94,234,212,0.3)"/>
      <circle cx="540" cy="400" r="3" fill="rgba(94,234,212,0.3)"/>
      <circle cx="720" cy="520" r="3" fill="rgba(94,234,212,0.3)"/>
      <circle cx="900" cy="430" r="3" fill="rgba(94,234,212,0.3)"/>
      <circle cx="1080" cy="500" r="3" fill="rgba(94,234,212,0.3)"/>
      <path d="M180 420 L360 500 L540 400 L720 520 L900 430 L1080 500"/>
    </g>
  </g>
</svg>'''


# ── 시작 화면 히어로: MXene 층 + 떠 있는 가스 분자 (밝은 틴트) ────
def landing_hero(animate: bool = True) -> str:
    """어두운 배경 대비를 위해 밝은 틴트를 쓰는 시작화면용 큰 도식."""
    co2, h2o, so2 = T.GAS["CO2"]["color"], T.GAS["H2O"]["color"], T.GAS["SO2"]["color"]
    cls = "ill-float" if animate else ""
    return f'''
<svg viewBox="0 0 460 320" class="landing-hero-svg" role="img"
     aria-label="MXene 층상 구조와 위에서 떠 있는 CO2·H2O·SO2 분자 개념도"
     xmlns="http://www.w3.org/2000/svg">
  <g class="{cls}" style="animation-delay:0s">
    <g transform="translate(110,70)">
      <line x1="-20" y1="0" x2="20" y2="0" stroke="#CBD5E1" stroke-width="3"/>
      <circle cx="-20" cy="0" r="10" fill="{co2}"/>
      <circle cx="0" cy="0" r="11" fill="#E2E8F0"/>
      <circle cx="20" cy="0" r="10" fill="{co2}"/>
      <text x="0" y="30" class="landing-mol">CO₂</text>
    </g>
  </g>
  <g class="{cls}" style="animation-delay:1.5s">
    <g transform="translate(240,52)">
      <line x1="0" y1="0" x2="-17" y2="-10" stroke="#CBD5E1" stroke-width="3"/>
      <line x1="0" y1="0" x2="17" y2="-10" stroke="#CBD5E1" stroke-width="3"/>
      <circle cx="0" cy="0" r="11" fill="{h2o}"/>
      <circle cx="-17" cy="-10" r="7" fill="#F1F5F9"/>
      <circle cx="17" cy="-10" r="7" fill="#F1F5F9"/>
      <text x="0" y="32" class="landing-mol">H₂O</text>
    </g>
  </g>
  <g class="{cls}" style="animation-delay:3s">
    <g transform="translate(360,74)">
      <line x1="0" y1="0" x2="-18" y2="9" stroke="#CBD5E1" stroke-width="3"/>
      <line x1="0" y1="0" x2="18" y2="9" stroke="#CBD5E1" stroke-width="3"/>
      <circle cx="0" cy="0" r="11" fill="{so2}"/>
      <circle cx="-18" cy="9" r="8" fill="#5EEAD4"/>
      <circle cx="18" cy="9" r="8" fill="#5EEAD4"/>
      <text x="0" y="34" class="landing-mol">SO₂</text>
    </g>
  </g>
  <g stroke="rgba(203,213,225,0.5)" stroke-width="1.5" stroke-dasharray="3 5" fill="none">
    <path d="M110 104 L110 170"/><path d="M240 90 L240 170"/><path d="M360 108 L360 170"/>
  </g>
  <g>
    <circle cx="90" cy="186" r="8" fill="{co2}"/>
    <circle cx="170" cy="186" r="8" fill="{so2}"/>
    <circle cx="240" cy="186" r="8" fill="{h2o}"/>
    <circle cx="320" cy="186" r="8" fill="{co2}"/>
    <circle cx="390" cy="186" r="8" fill="{so2}"/>
  </g>
  <g>
    <rect x="50" y="202" width="360" height="26" rx="5" fill="#5EEAD4" opacity="0.9"/>
    <rect x="50" y="228" width="360" height="20" rx="5" fill="#99F6E4" opacity="0.7"/>
    <rect x="50" y="248" width="360" height="26" rx="5" fill="#5EEAD4" opacity="0.9"/>
    <text x="420" y="219" class="landing-layer">Ti</text>
    <text x="420" y="242" class="landing-layer">C</text>
    <text x="420" y="265" class="landing-layer">Ti</text>
  </g>
  <g class="landing-legend">
    <circle cx="60" cy="296" r="5" fill="{co2}"/><text x="70" y="300">-O / CO₂</text>
    <circle cx="170" cy="296" r="5" fill="{so2}"/><text x="180" y="300">-F / SO₂</text>
    <circle cx="280" cy="296" r="5" fill="{h2o}"/><text x="290" y="300">-OH / H₂O</text>
  </g>
</svg>'''


# ── 시작 화면 핵심 가치 아이콘 ─────────────────────────────────
def value_icon_water() -> str:
    return ('<svg viewBox="0 0 24 24" class="val-svg"><path d="M12 3 C12 3 5 11 5 15 '
            'a7 7 0 0 0 14 0 C19 11 12 3 12 3 z" fill="none" stroke="currentColor" '
            'stroke-width="1.6"/></svg>')


def value_icon_source() -> str:
    return ('<svg viewBox="0 0 24 24" class="val-svg"><path d="M7 3 h7 l4 4 v14 H7 z" '
            'fill="none" stroke="currentColor" stroke-width="1.6"/>'
            '<path d="M14 3 v4 h4" fill="none" stroke="currentColor" stroke-width="1.6"/>'
            '<path d="M9 13 h6 M9 16 h6" stroke="currentColor" stroke-width="1.4"/></svg>')


def value_icon_explore() -> str:
    return composition_triangle(size=24)
