"""Audits a generated split: every planted problem must be detectable, and honest packets must
not carry the same signals by accident.

For each fraud type, the evidence a careful system would use is checked directly:

- amount_altered: receipt total differs from the sum of its line items
- date_altered: receipt date differs from the medical certificate date
- name_mismatch: receipt patient differs from the claim form patient
- clinic_mismatch: medical certificate clinic differs from the receipt clinic
- unknown_clinic: receipt clinic is not in the clinic registry
- receipt_number_anomaly: receipt number does not start with the clinic's registered prefix
- duplicate_receipt: receipt number already appears in the claims history
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any


def _signals(
    gold: dict[str, Any], clinics: dict[str, dict[str, Any]], history_receipts: set[str]
) -> set[str]:
    fields = {k: v["value"] for d in gold["documents"] for k, v in d["fields"].items()}
    found: set[str] = set()
    if "receipt.total" in fields:
        items = sum(
            (
                Decimal(v)
                for k, v in fields.items()
                if k.startswith("receipt.items.") and k.endswith(".amount")
            ),
            Decimal(0),
        )
        if Decimal(fields["receipt.total"]) != items:
            found.add("amount_altered")
    if (
        "receipt.date" in fields
        and "medical_certificate.date" in fields
        and fields["receipt.date"] != fields["medical_certificate.date"]
    ):
        found.add("date_altered")
    if (
        "receipt.patient_name" in fields
        and "claim_form.patient_name" in fields
        and fields["receipt.patient_name"] != fields["claim_form.patient_name"]
    ):
        found.add("name_mismatch")
    if (
        "receipt.clinic_name" in fields
        and "medical_certificate.clinic_name" in fields
        and fields["receipt.clinic_name"] != fields["medical_certificate.clinic_name"]
    ):
        found.add("clinic_mismatch")
    if "receipt.clinic_name" in fields:
        by_name = {c["name"]: c for c in clinics.values()}
        clinic = by_name.get(fields["receipt.clinic_name"])
        if clinic is None:
            found.add("unknown_clinic")
        elif not fields["receipt.receipt_no"].startswith(clinic["receipt_number_prefix"] + "-"):
            found.add("receipt_number_anomaly")
        if fields["receipt.receipt_no"] in history_receipts:
            found.add("duplicate_receipt")
    return found


def audit_split(split_dir: Path) -> dict[str, Any]:
    index = json.loads((split_dir / "index.json").read_text(encoding="utf-8"))
    clinics = {
        c["clinic_id"]: c
        for c in json.loads((split_dir / "context" / "clinics.json").read_text(encoding="utf-8"))
    }
    history = json.loads((split_dir / "context" / "claims_history.json").read_text("utf-8"))
    problems: list[str] = []
    checked = 0
    for pid in [*index["packets"], *index.get("twins", [])]:
        gold = json.loads((split_dir / "gold" / f"{pid}.json").read_text(encoding="utf-8"))
        member_receipts = {
            h["receipt_no"] for h in history if h["member_id"] == gold["facts"]["member_id"]
        }
        expected = set(gold["integrity_issues"])
        found = _signals(gold, clinics, member_receipts)
        if expected - found:
            problems.append(f"{pid}: planted {sorted(expected - found)} but not detectable")
        if not expected and found:
            problems.append(f"{pid}: honest packet shows fraud signals {sorted(found)}")
        for doc in gold["documents"]:
            width, height = doc["size"]
            img = split_dir / "packets" / pid / doc["file"]
            if not img.exists():
                problems.append(f"{pid}/{doc['file']}: image missing")
            for name, f in doc["fields"].items():
                x, y, w, h = f["box"]
                if w <= 0 or h <= 0 or x < -2 or y < -2 or x + w > width + 2 or y + h > height + 2:
                    problems.append(f"{pid}/{doc['doc_id']}: box for {name} outside the image")
        checked += 1
    return {"split": index["split"], "packets_checked": checked, "problems": problems}
