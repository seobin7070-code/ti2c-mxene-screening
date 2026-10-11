"""리포트 생성 (core — 순수 로직).

생성 시각·데이터 스냅샷 해시·에너지 표·E_ad 표·pending 목록·배가스 메모·
방법론 요약·한계 문구를 담는다. 데이터 없는 항목은 '데이터 없음'으로 기록하고,
가상 내용은 만들지 않는다.
"""

from __future__ import annotations

import html as _html
from datetime import datetime, timezone

from core.loader import EnergyEntry
from core.units import ry_to_ev
from core.datafiles import sha256_file


LIMITATIONS = (
    "N=7 수준의 소수 데이터에서는 GPR 하이퍼파라미터가 불안정할 수 있으며, "
    "σ는 보정된 불확실성이 아니라 참고용 상대 지표입니다. 계산 조건은 보고서 계획값이며 "
    "실제 .out 값과 대조가 필요합니다."
)


def build_report_data(entries: list[EnergyEntry], ead_rows: list[dict],
                      pending_items: list[dict], flue_gas: dict,
                      energies_path: str) -> dict:
    """리포트에 넣을 구조화 데이터를 만든다."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_sha256": sha256_file(energies_path),
        "energies": [{
            "key": e.key, "role": e.role, "surface": e.surface, "gas": e.gas,
            "energy_Ry": e.energy_Ry, "energy_eV": ry_to_ev(e.energy_Ry),
            "source_file": e.source_file, "calc_group": e.calc_group, "status": e.status,
        } for e in entries],
        "ead": ead_rows,
        "pending": pending_items,
        "flue_gas": flue_gas or {},
        "limitations": LIMITATIONS,
    }


def to_markdown(d: dict) -> str:
    lines = []
    lines.append("# Ti₂C MXene 표면 설계 플랫폼 — 리포트")
    lines.append("")
    lines.append(f"- 생성 시각(UTC): {d['generated_at']}")
    lines.append(f"- 데이터 스냅샷 SHA-256: `{d['snapshot_sha256']}`")
    lines.append("- 계산: Quantum ESPRESSO, PBE-D3")
    lines.append("")
    lines.append("## 에너지 표")
    lines.append("")
    lines.append("| key | role | surface | gas | energy_Ry | energy_eV | source_file | calc_group | status |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for e in d["energies"]:
        lines.append(f"| {e['key']} | {e['role']} | {e['surface']} | {e['gas']} | "
                     f"{e['energy_Ry']:.8f} | {e['energy_eV']:.6f} | {e['source_file']} | "
                     f"{e['calc_group']} | {e['status']} |")
    lines.append("")
    lines.append("## 계산된 흡착 에너지 (E_ad)")
    lines.append("")
    if d["ead"]:
        lines.append("| 표면 | 가스 | E_ad (eV) | E_ad (Ry) | calc_group |")
        lines.append("|---|---|---|---|---|")
        for r in d["ead"]:
            lines.append(f"| {r['surface']} | {r['gas']} | {r['e_ad_ev']:.3f} | "
                         f"{r['e_ad_ry']:.5f} | {r['calc_group']} |")
    else:
        lines.append("데이터 없음")
    lines.append("")
    lines.append("## 대기(pending) 목록")
    lines.append("")
    if d["pending"]:
        for p in d["pending"]:
            lines.append(f"- {p.get('scope','')} — {p.get('detail','')}")
    else:
        lines.append("데이터 없음")
    lines.append("")
    lines.append("## 배가스 조건 메모")
    lines.append("")
    fg = d["flue_gas"]
    if fg and any(fg.get(k) for k in ("co2", "h2o", "so2", "temp", "memo")):
        lines.append(f"- CO₂: {fg.get('co2','')} vol% · H₂O: {fg.get('h2o','')} vol% · "
                     f"SO₂: {fg.get('so2','')} vol% · 온도: {fg.get('temp','')} °C")
        if fg.get("memo"):
            lines.append(f"- 메모: {fg['memo']}")
        lines.append("- (0 K 진공 DFT 계산에는 반영되지 않는 시나리오 메모)")
    else:
        lines.append("데이터 없음")
    lines.append("")
    lines.append("## 방법론 요약")
    lines.append("")
    lines.append("- E_ads = E_adsorbed − (E_clean + E_molecule)")
    lines.append("- P(CO₂/H₂O) = E_ads(H₂O) − E_ads(CO₂)")
    lines.append("- P(CO₂/SO₂) = E_ads(SO₂) − E_ads(CO₂)")
    lines.append("- Δd_surface = |mean(z_after) − mean(z_before)|")
    lines.append("- 1 Ry = 13.6057 eV")
    lines.append("")
    lines.append("## 한계")
    lines.append("")
    lines.append(d["limitations"])
    return "\n".join(lines)


def to_html(d: dict) -> str:
    def esc(x):
        return _html.escape(str(x))

    erows = "".join(
        f"<tr><td>{esc(e['key'])}</td><td>{esc(e['role'])}</td><td>{esc(e['surface'])}</td>"
        f"<td>{esc(e['gas'])}</td><td class='num'>{e['energy_Ry']:.8f}</td>"
        f"<td class='num'>{e['energy_eV']:.6f}</td><td>{esc(e['source_file'])}</td>"
        f"<td>{esc(e['calc_group'])}</td><td>{esc(e['status'])}</td></tr>"
        for e in d["energies"]
    )
    if d["ead"]:
        earows = "".join(
            f"<tr><td>{esc(r['surface'])}</td><td>{esc(r['gas'])}</td>"
            f"<td class='num'>{r['e_ad_ev']:.3f}</td><td class='num'>{r['e_ad_ry']:.5f}</td>"
            f"<td>{esc(r['calc_group'])}</td></tr>"
            for r in d["ead"]
        )
        ead_table = ("<table><tr><th>표면</th><th>가스</th><th>E_ad (eV)</th>"
                     "<th>E_ad (Ry)</th><th>calc_group</th></tr>" + earows + "</table>")
    else:
        ead_table = "<p>데이터 없음</p>"

    pending_html = ("<ul>" + "".join(
        f"<li>{esc(p.get('scope',''))} — {esc(p.get('detail',''))}</li>" for p in d["pending"]
    ) + "</ul>") if d["pending"] else "<p>데이터 없음</p>"

    fg = d["flue_gas"]
    if fg and any(fg.get(k) for k in ("co2", "h2o", "so2", "temp", "memo")):
        fg_html = (f"<p>CO₂: {esc(fg.get('co2',''))} vol% · H₂O: {esc(fg.get('h2o',''))} vol% · "
                   f"SO₂: {esc(fg.get('so2',''))} vol% · 온도: {esc(fg.get('temp',''))} °C</p>")
        if fg.get("memo"):
            fg_html += f"<p>메모: {esc(fg['memo'])}</p>"
        fg_html += "<p><i>0 K 진공 DFT 계산에는 반영되지 않는 시나리오 메모</i></p>"
    else:
        fg_html = "<p>데이터 없음</p>"

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<title>Ti2C MXene 리포트</title>
<style>
  body {{ font-family: system-ui, sans-serif; color:#334155; max-width:900px; margin:24px auto; padding:0 16px; }}
  h1 {{ font-size:22px; }} h2 {{ font-size:16px; margin-top:24px; border-bottom:1px solid #E7E5E4; padding-bottom:4px; }}
  table {{ border-collapse:collapse; width:100%; font-size:12px; margin-top:8px; }}
  th,td {{ border:1px solid #E7E5E4; padding:4px 8px; text-align:left; }}
  .num {{ font-variant-numeric: tabular-nums; text-align:right; }}
  .meta {{ font-size:12px; color:#64748B; }}
  code {{ background:#F1F5F9; padding:1px 5px; border-radius:4px; font-size:11px; }}
  @media print {{ body {{ margin:0; }} h2 {{ page-break-after:avoid; }} }}
</style></head><body>
<h1>배가스 맞춤형 Ti₂C MXene 표면 설계 플랫폼 — 리포트</h1>
<p class="meta">생성 시각(UTC): {esc(d['generated_at'])}<br>
데이터 스냅샷 SHA-256: <code>{esc(d['snapshot_sha256'])}</code><br>
계산: Quantum ESPRESSO, PBE-D3</p>
<h2>에너지 표</h2>
<table><tr><th>key</th><th>role</th><th>surface</th><th>gas</th><th>energy_Ry</th>
<th>energy_eV</th><th>source_file</th><th>calc_group</th><th>status</th></tr>{erows}</table>
<h2>계산된 흡착 에너지 (E_ad)</h2>
{ead_table}
<h2>대기(pending) 목록</h2>
{pending_html}
<h2>배가스 조건 메모</h2>
{fg_html}
<h2>방법론 요약</h2>
<ul><li>E_ads = E_adsorbed − (E_clean + E_molecule)</li>
<li>P(CO₂/H₂O) = E_ads(H₂O) − E_ads(CO₂)</li>
<li>P(CO₂/SO₂) = E_ads(SO₂) − E_ads(CO₂)</li>
<li>Δd_surface = |mean(z_after) − mean(z_before)|</li>
<li>1 Ry = 13.6057 eV</li></ul>
<h2>한계</h2>
<p>{esc(d['limitations'])}</p>
</body></html>"""
