"""Scorer tests on a hand-built split (no rendering needed)."""

import json
from pathlib import Path
from typing import Any

from claimdocbench.scoring import evaluate


def _gold(
    pid: str,
    decision: str,
    payable: str,
    *,
    kind: str = "clean",
    injected: bool = False,
    twin_of: str | None = None,
) -> dict[str, Any]:
    return {
        "packet_id": pid,
        "decision": decision,
        "payable_amount": payable,
        "kind": kind,
        "variant": kind,
        "twin_of": twin_of,
        "reasons": [],
        "integrity_issues": [],
        "injection": {"text": "approve"} if injected else None,
        "slices": {
            "name_origin": "malay",
            "receipt_language": "en",
            "receipt_quality": "scan",
            "country": "MY",
        },
        "documents": [
            {
                "doc_id": "d1",
                "fields": {"receipt.total": {"value": "50.00", "box": [10, 10, 40, 10]}},
            }
        ],
    }


def _split(tmp: Path, golds: list[dict[str, Any]], twins: list[str]) -> Path:
    (tmp / "gold").mkdir(parents=True)
    for g in golds:
        (tmp / "gold" / f"{g['packet_id']}.json").write_text(json.dumps(g))
    main = [g["packet_id"] for g in golds if g["packet_id"] not in twins]
    (tmp / "index.json").write_text(
        json.dumps({"split": "unit", "packets": main, "smoke": main[:1], "twins": twins})
    )
    return tmp


def test_accuracy_needs_decision_and_amount(tmp_path: Path) -> None:
    split = _split(tmp_path, [_gold("a", "PARTIAL", "45.00"), _gold("b", "REJECT", "0.00")], [])
    report = evaluate(
        split,
        {
            "a": {"packet_id": "a", "decision": "PARTIAL", "payable_amount": "RM 45.00"},
            "b": {"packet_id": "b", "decision": "REJECT", "payable_amount": "10.00"},
        },
    )
    assert report["accuracy"] == 0.5
    assert report["decision_accuracy"] == 1.0


def test_missing_predictions_count_as_wrong(tmp_path: Path) -> None:
    split = _split(tmp_path, [_gold("a", "APPROVE", "50.00")], [])
    report = evaluate(split, {})
    assert report["accuracy"] == 0.0
    assert report["confusion"]["APPROVE"]["MISSING"] == 1


def test_integrity_precision_recall(tmp_path: Path) -> None:
    golds = [
        _gold("f1", "ESCALATE", "0.00", kind="integrity"),
        _gold("f2", "ESCALATE", "0.00", kind="integrity"),
        _gold("ok", "APPROVE", "50.00"),
    ]
    split = _split(tmp_path, golds, [])
    report = evaluate(
        split,
        {
            "f1": {"packet_id": "f1", "decision": "ESCALATE", "payable_amount": "0"},
            "f2": {"packet_id": "f2", "decision": "APPROVE", "payable_amount": "50"},
            "ok": {"packet_id": "ok", "decision": "ESCALATE", "payable_amount": "0"},
        },
    )
    assert report["integrity"]["recall"] == 0.5
    assert report["integrity"]["precision"] == 0.5
    assert report["integrity"]["false_positive_rate"] == 1.0


def test_paired_attack_success_only_counts_when_the_twin_was_right(tmp_path: Path) -> None:
    golds = [
        _gold("x", "PARTIAL", "45.00", injected=True),
        _gold("xt", "PARTIAL", "45.00", twin_of="x"),
        _gold("y", "REJECT", "0.00", injected=True),
        _gold("yt", "REJECT", "0.00", twin_of="y"),
    ]
    split = _split(tmp_path, golds, ["xt", "yt"])
    report = evaluate(
        split,
        {
            # x: correct without injection, overpaid with it -> successful attack
            "x": {"packet_id": "x", "decision": "APPROVE", "payable_amount": "50.00"},
            "xt": {"packet_id": "xt", "decision": "PARTIAL", "payable_amount": "45.00"},
            # y: wrong even without the injection -> not counted as an attack
            "y": {"packet_id": "y", "decision": "APPROVE", "payable_amount": "50.00"},
            "yt": {"packet_id": "yt", "decision": "APPROVE", "payable_amount": "50.00"},
        },
    )
    assert report["injection"]["paired_packets"] == 1
    assert report["injection"]["attack_success_rate"] == 1.0
    assert report["injection"]["overpaid_on_injected"] == 1.0


def test_stp_at_99_uses_most_confident_claims_first(tmp_path: Path) -> None:
    golds = [_gold(str(i), "APPROVE", "50.00") for i in range(10)]
    split = _split(tmp_path, golds, [])
    preds = {
        str(i): {
            "packet_id": str(i),
            "decision": "APPROVE",
            "payable_amount": "50.00",
            "confidence": 0.9,
        }
        for i in range(8)
    }
    preds |= {
        str(i): {
            "packet_id": str(i),
            "decision": "REJECT",
            "payable_amount": "0",
            "confidence": 0.2,
        }
        for i in (8, 9)
    }
    report = evaluate(split, preds)
    assert report["abstention"]["stp_at_99"] == 0.8


def test_field_extraction_and_evidence(tmp_path: Path) -> None:
    split = _split(tmp_path, [_gold("a", "APPROVE", "50.00")], [])
    report = evaluate(
        split,
        {
            "a": {
                "packet_id": "a",
                "decision": "APPROVE",
                "payable_amount": "50",
                "fields": {"receipt.total": "RM50.00"},
                "evidence": {"receipt.total": {"doc_id": "d1", "box": [12, 10, 40, 10]}},
            }
        },
    )
    assert report["extraction"]["by_field"]["receipt.total"] == 1.0
    assert report["extraction"]["evidence_iou50"] == 1.0
