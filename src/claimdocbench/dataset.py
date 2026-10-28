"""Generates a dataset split: packets for systems to read, gold labels kept separately.

Layout written under `<out>/<split>/`:

    packets/<packet_id>/manifest.json   what a system receives (no answers)
    packets/<packet_id>/d1.png ...      document images
    context/members.json                insurer's member registry (tool lookup)
    context/clinics.json                insurer's clinic registry (tool lookup)
    context/claims_history.json         previously paid claims (tool lookup)
    context/policy.yaml                 the policy schedule and clauses
    gold/<packet_id>.json               answers: decision, amounts, reasons, fields, boxes
    index.json                          packet ids and summary counts
"""

from __future__ import annotations

import json
import random
from collections import Counter
from dataclasses import asdict
from decimal import Decimal
from importlib.resources import files
from pathlib import Path
from typing import Any

from claimdocbench.documents import build_documents
from claimdocbench.policy import load_policy
from claimdocbench.render import Renderer
from claimdocbench.scenarios import Scenario, sample_scenario
from claimdocbench.world import World, build_world

SCHEMA_VERSION = "0.1"


def _json_default(o: Any) -> Any:
    if isinstance(o, Decimal):
        return str(o)
    if hasattr(o, "isoformat"):
        return o.isoformat()
    if isinstance(o, frozenset | set):
        return sorted(o)
    raise TypeError(f"not serialisable: {type(o)}")


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8"
    )


def _context(world: World, scenarios: list[Scenario]) -> dict[str, Any]:
    members = [s.member for s in scenarios]
    return {
        "members": [
            {
                "member_id": p.member.member_id,
                "employer": p.employer,
                "plan_id": p.member.plan_id,
                "currency": p.member.currency.value,
                "coverage_start": p.member.coverage_start,
                "coverage_end": p.member.coverage_end,
                "persons": [
                    {
                        "person_id": x.person_id,
                        "full_name": x.full_name,
                        "relationship": x.relationship.value,
                        "covered": x.covered,
                        "preexisting_conditions": sorted(x.preexisting_conditions),
                    }
                    for x in p.member.persons
                ],
            }
            for p in members
        ],
        "clinics": [
            {
                "clinic_id": c.clinic.clinic_id,
                "name": c.clinic.name,
                "registration_no": c.clinic.registration_no,
                "kind": c.clinic.kind.value,
                "licensed": c.clinic.licensed,
                "country": c.country,
                "address": c.address,
                "receipt_number_prefix": c.receipt_prefix,
            }
            for c in world.clinics.values()
        ],
        "claims_history": [asdict(h) for s in scenarios for h in s.history],
    }


def generate_split(split: str, n: int, seed: int, out: Path) -> dict[str, Any]:
    rng = random.Random(f"{split}:{seed}")
    policy = load_policy()
    world = build_world(rng, n_members=n)
    scenarios = [sample_scenario(rng, world, profile, policy) for profile in world.members]

    root = out / split
    context = _context(world, scenarios)
    for name in ("members", "clinics", "claims_history"):
        _write(root / "context" / f"{name}.json", context[name])
    (root / "context" / "policy.yaml").write_text(
        files("claimdocbench").joinpath("data/policy.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    with Renderer() as renderer:
        for s in scenarios:
            pdir = root / "packets" / s.packet_id
            pdir.mkdir(parents=True, exist_ok=True)
            specs = build_documents(s, rng)
            gold_docs: list[dict[str, Any]] = []
            for spec in specs:
                rendered = renderer.render(spec, pdir / f"{spec.doc_id}.png")
                gold_docs.append(
                    {
                        "doc_id": spec.doc_id,
                        "file": rendered.path.name,
                        "doc_type": spec.doc_type.value,
                        "template": spec.template,
                        "language": "en",
                        "size": [rendered.width, rendered.height],
                        "fields": {
                            f.name: {
                                "printed": f.printed,
                                "value": spec.canonical.get(f.name),
                                "box": f.box,
                            }
                            for f in rendered.fields
                            if f.printed.strip()
                        },
                    }
                )
            _write(
                pdir / "manifest.json",
                {
                    "schema_version": SCHEMA_VERSION,
                    "packet_id": s.packet_id,
                    "channel": "member_portal",
                    "member_id": s.facts.member_id,
                    "submitted_on": s.facts.submission_date,
                    "documents": [{"doc_id": d["doc_id"], "file": d["file"]} for d in gold_docs],
                },
            )
            injection = None
            if s.injection:
                doc = next(d for d in gold_docs if d["doc_type"] == s.injection.doc_type.value)
                field = f"{s.injection.doc_type.value}.{s.injection.field}"
                injection = {
                    "text": s.injection.text,
                    "doc_id": doc["doc_id"],
                    "box": doc["fields"][field]["box"],
                }
            _write(
                root / "gold" / f"{s.packet_id}.json",
                {
                    "schema_version": SCHEMA_VERSION,
                    "packet_id": s.packet_id,
                    "kind": s.kind.value,
                    "variant": s.variant,
                    "decision": s.gold.decision.value,
                    "payable_amount": s.gold.payable_amount,
                    "currency": s.gold.currency.value,
                    "claimed_amount": s.gold.claimed_amount,
                    "reasons": [r.value for r in s.gold.reasons],
                    "clause_ids": list(s.gold.clause_ids),
                    "items": [o.model_dump(mode="json") for o in s.gold.items],
                    "underlying_decision": s.gold.underlying_decision,
                    "underlying_payable": s.gold.underlying_payable,
                    "integrity_issues": sorted(i.value for i in s.facts.integrity_issues),
                    "injection": injection,
                    "facts": s.facts.model_dump(mode="json"),
                    "slices": {
                        "name_origin": s.patient_name.origin,
                        "country": s.member.country,
                        "plan_id": s.member.member.plan_id,
                        "visit_type": s.facts.visit_type.value,
                    },
                    "documents": gold_docs,
                },
            )

    summary = {
        "schema_version": SCHEMA_VERSION,
        "split": split,
        "seed": seed,
        "packets": [s.packet_id for s in sorted(scenarios, key=lambda x: x.packet_id)],
        "decisions": dict(Counter(s.gold.decision.value for s in scenarios)),
        "kinds": dict(Counter(s.kind.value for s in scenarios)),
        "injections": sum(1 for s in scenarios if s.injection),
    }
    _write(root / "index.json", summary)
    return summary
