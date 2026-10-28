"""Generates a dataset split: packets for systems to read, gold labels kept separately.

Layout written under `<out>/<split>/`:

    packets/<packet_id>/manifest.json   what a system receives (no answers)
    packets/<packet_id>/d1.png|jpg ...  document images (clean, scanned, photographed)
    context/members.json                insurer's member registry (tool lookup)
    context/clinics.json                insurer's clinic registry (tool lookup)
    context/claims_history.json         previously paid claims (tool lookup)
    context/policy.yaml                 the policy schedule and clauses
    gold/<packet_id>.json               answers: decision, amounts, reasons, fields, boxes
    index.json                          packet ids and summary counts
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from dataclasses import asdict, replace
from decimal import Decimal
from importlib.resources import files
from pathlib import Path
from typing import Any

from PIL import Image

from claimdocbench.capture import QUALITY_WEIGHTS, Quality, capture, forge_text, save
from claimdocbench.documents import build_documents, tamper_printed
from claimdocbench.domain import DocType
from claimdocbench.policy import load_policy
from claimdocbench.render import Renderer
from claimdocbench.scenarios import Scenario, sample_scenario
from claimdocbench.world import World, build_world

SCHEMA_VERSION = "0.2"
SMOKE_SIZE = 25


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
            for p in (s.member for s in scenarios)
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


def _pick_quality(rng: random.Random) -> Quality:
    return rng.choices(list(QUALITY_WEIGHTS), weights=list(QUALITY_WEIGHTS.values()))[0]


def _write_packet(
    s: Scenario,
    root: Path,
    renderer: Renderer,
    rng: random.Random,
    heldout: bool,
    qualities: Counter[str],
    languages: Counter[str],
    twin_of: str | None = None,
) -> None:
    pdir = root / "packets" / s.packet_id
    pdir.mkdir(parents=True, exist_ok=True)
    gold_docs: list[dict[str, Any]] = []
    for spec in build_documents(s, rng, heldout=heldout):
        clean_png = pdir / f"_{spec.doc_id}.png"
        rendered = renderer.render(spec, clean_png)
        img = Image.open(clean_png).convert("RGB")
        clean_png.unlink()
        fields: dict[str, dict[str, Any]] = {
            f.name: {
                "printed": f.printed,
                "value": spec.canonical.get(f.name),
                "box": f.box,
                "tampered": False,
            }
            for f in rendered.fields
            if f.printed.strip()
        }

        forged = tamper_printed(s, spec, rng)
        if forged is not None and s.tamper is not None:
            printed, canonical = forged
            target = fields[s.tamper.field]
            img, new_box = forge_text(
                img,
                tuple(target["box"]),
                printed,
                rng,
                align_right=s.tamper.field == "receipt.total",
            )
            fields[s.tamper.field] = {
                "printed": printed,
                "value": canonical,
                "box": new_box,
                "tampered": True,
            }

        quality = (
            Quality.ILLEGIBLE
            if spec.doc_type in s.facts.illegible_documents
            else _pick_quality(rng)
        )
        captured = capture(img, quality, rng)
        path = save(captured, pdir / spec.doc_id, quality, rng)
        for f in fields.values():
            f["box"] = captured.map_box(tuple(f["box"]))
        qualities[quality.value] += 1
        languages[spec.language] += 1
        gold_docs.append(
            {
                "doc_id": spec.doc_id,
                "file": path.name,
                "doc_type": spec.doc_type.value,
                "template": spec.template,
                "language": spec.language,
                "quality": quality.value,
                "size": list(captured.image.size),
                "fields": fields,
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
        field = f"{s.injection.doc_type.value}.{s.injection.field}"
        doc = next(d for d in gold_docs if field in d["fields"])
        injection = {
            "text": s.injection.text,
            "placement": field,
            "doc_id": doc["doc_id"],
            "box": doc["fields"][field]["box"],
        }
    receipt = next((d for d in gold_docs if d["doc_type"] == DocType.RECEIPT.value), None)
    _write(
        root / "gold" / f"{s.packet_id}.json",
        {
            "schema_version": SCHEMA_VERSION,
            "packet_id": s.packet_id,
            "kind": s.kind.value,
            "twin_of": twin_of,
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
                "receipt_language": receipt["language"] if receipt else None,
                "receipt_quality": receipt["quality"] if receipt else None,
            },
            "documents": gold_docs,
        },
    )


def generate_split(
    split: str, n: int, seed: int, out: Path, heldout: bool = False
) -> dict[str, Any]:
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

    qualities: Counter[str] = Counter()
    languages: Counter[str] = Counter()
    twins: list[str] = []
    with Renderer() as renderer:
        for s in scenarios:
            state = rng.getstate()
            _write_packet(s, root, renderer, rng, heldout, qualities, languages)
            if s.injection:
                # A twin with the same documents minus the injected text, to measure whether
                # the injection itself changed the outcome (paired attack success rate).
                after = rng.getstate()
                rng.setstate(state)
                twin = replace(
                    s,
                    packet_id=f"{s.packet_id}t",
                    injection=None,
                    facts=s.facts.model_copy(update={"injection_present": False}),
                )
                _write_packet(
                    twin, root, renderer, rng, heldout, Counter(), Counter(), twin_of=s.packet_id
                )
                twins.append(twin.packet_id)
                rng.setstate(after)

    ordered = sorted(scenarios, key=lambda x: x.packet_id)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "split": split,
        "seed": seed,
        "heldout_templates": heldout,
        "packets": [s.packet_id for s in ordered],
        "smoke": [s.packet_id for s in ordered[:SMOKE_SIZE]] if split == "dev" else [],
        "decisions": dict(Counter(s.gold.decision.value for s in scenarios)),
        "kinds": dict(Counter(s.kind.value for s in scenarios)),
        "variants": dict(Counter(s.variant for s in scenarios)),
        "document_quality": dict(qualities),
        "document_language": dict(languages),
        "injections": sum(1 for s in scenarios if s.injection),
        "twins": twins,
    }
    _write(root / "index.json", summary)
    return summary


def tree_hash(root: Path) -> tuple[str, int]:
    """SHA-256 over every file's relative path and content hash, in sorted order."""
    digest = hashlib.sha256()
    count = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        digest.update(f"{rel}\0{hashlib.sha256(path.read_bytes()).hexdigest()}\n".encode())
        count += 1
    return digest.hexdigest(), count
