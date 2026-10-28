"""Reference baselines that need no model.

- `approve-all`: pay every claim in full. What naive automation would do. It is a real
  leaderboard row: it shows how much money a system without checks would pay out wrongly.
- `oracle`: reads the gold labels. Used only to test the scorer; never on the leaderboard.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def predictions(name: str, split_dir: Path) -> list[dict[str, Any]]:
    index = json.loads((split_dir / "index.json").read_text(encoding="utf-8"))
    out = []
    for pid in [*index["packets"], *index.get("twins", [])]:
        gold = json.loads((split_dir / "gold" / f"{pid}.json").read_text(encoding="utf-8"))
        if name == "approve-all":
            claimed = next(
                (
                    f["value"]
                    for d in gold["documents"]
                    for k, f in d["fields"].items()
                    if k == "claim_form.amount"
                ),
                gold["claimed_amount"],
            )
            out.append(
                {
                    "packet_id": pid,
                    "decision": "APPROVE",
                    "payable_amount": claimed,
                    "confidence": 1.0,
                    "cost_usd": 0.0,
                }
            )
        elif name == "oracle":
            fields = {k: f["value"] for d in gold["documents"] for k, f in d["fields"].items()}
            evidence = {
                k: {"doc_id": d["doc_id"], "box": f["box"]}
                for d in gold["documents"]
                for k, f in d["fields"].items()
            }
            out.append(
                {
                    "packet_id": pid,
                    "decision": gold["decision"],
                    "payable_amount": gold["payable_amount"],
                    "reasons": gold["reasons"],
                    "integrity_flags": gold["integrity_issues"],
                    "injection_detected": gold["injection"] is not None,
                    "fields": fields,
                    "evidence": evidence,
                    "confidence": 1.0,
                }
            )
        else:
            raise ValueError(f"unknown baseline {name!r}")
    return out


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )
