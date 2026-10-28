"""Builds the static leaderboard page from scorer reports."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ClaimDocBench leaderboard</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1c1b19; --muted:#6b6862; --line:#e4e1da; --accent:#0f766e; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#161614; --fg:#ecebe7; --muted:#a3a19b; --line:#2e2d2a; --accent:#5eead4; }}
}}
body {{ margin:0; background:var(--bg); color:var(--fg);
  font:15px/1.6 -apple-system, "Segoe UI", Roboto, sans-serif; }}
main {{ max-width:1100px; margin:0 auto; padding:32px 16px 64px; }}
h1 {{ font-size:26px; margin:0 0 4px; }} p {{ color:var(--muted); margin:6px 0; }}
a {{ color:var(--accent); }}
.wrap {{ overflow-x:auto; margin-top:24px; border:1px solid var(--line); border-radius:10px; }}
table {{ border-collapse:collapse; width:100%; min-width:860px; font-size:14px; }}
th, td {{ padding:10px 12px; border-bottom:1px solid var(--line); text-align:right;
  white-space:nowrap; }}
th:first-child, td:first-child {{ text-align:left; }}
th {{ font-weight:600; color:var(--muted); font-size:12px; }}
tr:last-child td {{ border-bottom:0; }} .note {{ font-size:13px; }}
</style></head>
<body><main>
<h1>ClaimDocBench leaderboard</h1>
<p>{split_note}</p>
<p>Accuracy counts a claim as correct only when the decision and the payout (to the cent) are
both right. Attack success is paired: the injected claim was decided in the attacker's
favour while its injection-free twin was handled correctly.</p>
<div class="wrap"><table>
<thead><tr><th>System</th><th>Accuracy</th><th>Decision</th><th>Fraud recall</th>
<th>Fraud precision</th><th>False alarms</th><th>Attack success</th><th>Fields read</th>
<th>STP@99</th><th>p50 latency</th><th>Cost / claim</th></tr></thead>
<tbody>
{rows}
</tbody></table></div>
<p class="note">{footer}</p>
</main></body></html>
"""


def _pct(v: float | None) -> str:
    return "n/a" if v is None else f"{100 * v:.1f}%"


def build(reports: list[Path], out: Path, split_note: str, footer: str) -> None:
    entries: list[tuple[str, dict[str, Any]]] = []
    for path in reports:
        report = json.loads(path.read_text(encoding="utf-8"))
        entries.append((report.get("system", path.stem), report))
    entries.sort(key=lambda e: -(e[1]["accuracy"] or 0))
    rows = []
    for name, r in entries:
        lat = r.get("latency_s") or {}
        cost = r.get("cost_usd_per_claim")
        rows.append(
            "<tr>"
            + "".join(
                f"<td>{c}</td>"
                for c in [
                    html.escape(name),
                    _pct(r["accuracy"]),
                    _pct(r["decision_accuracy"]),
                    _pct(r["integrity"]["recall"]),
                    _pct(r["integrity"]["precision"]),
                    _pct(r["integrity"]["false_positive_rate"]),
                    _pct(r["injection"]["attack_success_rate"]),
                    _pct(r["extraction"]["field_accuracy"]),
                    _pct((r.get("abstention") or {}).get("stp_at_99")),
                    f"{lat['p50']:.1f}s" if lat else "n/a",
                    "n/a" if cost is None else f"${cost:.2f}",
                ]
            )
            + "</tr>"
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        PAGE.format(
            rows="\n".join(rows), split_note=html.escape(split_note), footer=html.escape(footer)
        ),
        encoding="utf-8",
    )
