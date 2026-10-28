"""Turns a scenario into document specs: which template, which language, what is printed.

Every printed field is wrapped in a `data-field` element by the templates, so the renderer can
record exactly where each value appears (gold evidence boxes). The canonical value of each
field (ISO dates, plain decimals, English names) is kept here for scoring extraction.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from claimdocbench.domain import Currency, DocType, VisitType
from claimdocbench.i18n import LABELS, date_formatter, diagnosis_text, item_text, value
from claimdocbench.scenarios import Scenario
from claimdocbench.world import DIAGNOSES

RECEIPT_TEMPLATES = ["receipt_thermal", "receipt_invoice", "receipt_letterhead"]
CLAIM_FORM_TEMPLATES = ["claim_form"]
# Layouts used only in the held-out split. They live outside the public repo until the reveal.
HELDOUT_RECEIPT_TEMPLATES = ["heldout_receipt_pharmacy", "heldout_receipt_handbook"]
HELDOUT_CLAIM_FORM_TEMPLATES = ["heldout_claim_form_v2"]

REMARKS = [
    "",
    "",
    "Receipt attached.",
    "Follow-up visit.",
    "Please process.",
    "Claim for outpatient treatment.",
]


@dataclass
class DocSpec:
    doc_id: str
    doc_type: DocType
    template: str
    language: str
    context: dict[str, Any]
    canonical: dict[str, str] = field(default_factory=dict)


def fmt_money(amount: Decimal, currency: Currency, style: int) -> str:
    symbol = {Currency.MYR: ["RM", "RM ", "MYR "], Currency.SGD: ["S$", "S$ ", "SGD "]}[currency]
    return f"{symbol[style % 3]}{amount:,.2f}"


def pick_language(rng: random.Random, country: str) -> str:
    if country == "MY":
        return rng.choices(["en", "ms", "zh"], weights=[0.55, 0.30, 0.15])[0]
    return rng.choices(["en", "zh"], weights=[0.8, 0.2])[0]


def build_documents(s: Scenario, rng: random.Random, heldout: bool = False) -> list[DocSpec]:
    f = s.facts
    country = s.member.country
    money_style = rng.randint(0, 2)

    def m(x: Decimal) -> str:
        return fmt_money(x, f.currency, money_style)

    order = [
        DocType.CLAIM_FORM,
        DocType.RECEIPT,
        DocType.MEDICAL_CERTIFICATE,
        DocType.REFERRAL_LETTER,
    ]
    present = [t for t in order if t in f.documents]
    rng.shuffle(present)  # systems must classify documents, not rely on order

    person = s.member.member.person(f.person_id)
    relationship = person.relationship.value if person else "child"
    self_name = next(n.full_name for pid, n in s.member.names.items() if pid.endswith("-0"))
    tamper = s.tamper
    # What the claimant writes on the form matches the (possibly forged) receipt.
    claimed_amount = (
        tamper.new_amount if tamper and tamper.new_amount is not None else f.claimed_total
    )
    claimed_date = tamper.new_date if tamper and tamper.new_date is not None else f.visit_date
    injection = s.injection
    inj_field = f"{injection.doc_type.value}.{injection.field}" if injection else ""

    docs: list[DocSpec] = []
    for k, doc_type in enumerate(present, start=1):
        doc_id = f"d{k}"
        lang = pick_language(rng, country)
        if (
            doc_type in (DocType.MEDICAL_CERTIFICATE, DocType.REFERRAL_LETTER)
            and lang == "zh"
            and rng.random() < 0.5
        ):
            lang = "en"
        t = LABELS[lang]
        _, d = date_formatter(rng, lang)
        ctx: dict[str, Any] = {"t": t, "lang": lang}

        if doc_type is DocType.CLAIM_FORM:
            # Drawn even when an injection replaces it, so injection twins stay identical.
            remark = rng.choice(REMARKS)
            referred = (
                "N/A" if f.visit_type is VisitType.GP else "Yes" if f.referral_issued else "No"
            )
            ctx |= {
                "form_no": f"CF-{rng.randint(100000, 999999)}",
                "employer": s.member.employer,
                "member_id": f.member_id,
                "member_name": self_name,
                "patient_name": s.patient_name.full_name,
                "relationship": value(relationship, lang),
                "clinic_name": s.clinic.clinic.name,
                "visit_date": d(claimed_date),
                "visit_type": value(f.visit_type.value, lang),
                "referred": value(referred, lang),
                "diagnosis": f"{f.diagnosis_code} "
                f"{diagnosis_text(f.diagnosis_code, DIAGNOSES[f.diagnosis_code], lang)}",
                "amount": m(claimed_amount),
                "bank": rng.choice(["Bank Synthetik", "Harbour Savings Bank", "Bank Rakyat Maya"]),
                "account": f"xxxx-xxxx-{rng.randint(1000, 9999)}",
                "remarks": injection.text
                if injection and inj_field == "claim_form.remarks"
                else remark,
                "signed_on": d(f.submission_date),
                "signature": self_name.split()[0],
            }
            canonical = {
                "claim_form.member_id": f.member_id,
                "claim_form.patient_name": s.patient_name.full_name,
                "claim_form.clinic_name": s.clinic.clinic.name,
                "claim_form.visit_date": claimed_date.isoformat(),
                "claim_form.visit_type": f.visit_type.value,
                "claim_form.referred": referred,
                "claim_form.diagnosis_code": f.diagnosis_code,
                "claim_form.amount": str(claimed_amount),
                "claim_form.signed_on": f.submission_date.isoformat(),
            }
            pool = HELDOUT_CLAIM_FORM_TEMPLATES if heldout else CLAIM_FORM_TEMPLATES
            docs.append(DocSpec(doc_id, doc_type, rng.choice(pool), lang, ctx, canonical))

        elif doc_type is DocType.RECEIPT:
            hour = rng.randint(8, 21)
            ctx |= {
                "clinic": s.clinic,
                "receipt_no": s.receipt_no,
                "date": d(f.visit_date),
                "time": f"{hour:02d}:{rng.randint(0, 59):02d}",
                "patient_name": s.receipt_patient_name,
                "items": [
                    {"description": item_text(i.description, lang), "amount": m(i.amount)}
                    for i in f.line_items
                ],
                "total": m(f.claimed_total),
                "payment": value(
                    rng.choice(["Cash", "Debit card", "Credit card", "QR payment"]), lang
                ),
                "doctor": rng.choice(s.clinic.doctors),
                "footer_note": injection.text
                if injection and inj_field == "receipt.footer_note"
                else "",
                "hidden_note": injection.text
                if injection and inj_field == "receipt.hidden_note"
                else "",
            }
            canonical = {
                "receipt.clinic_name": s.clinic.clinic.name,
                "receipt.registration_no": s.clinic.clinic.registration_no,
                "receipt.receipt_no": s.receipt_no,
                "receipt.date": f.visit_date.isoformat(),
                "receipt.patient_name": s.receipt_patient_name,
                "receipt.total": str(f.claimed_total),
            }
            for n, i in enumerate(f.line_items):
                canonical[f"receipt.items.{n}.description"] = i.description
                canonical[f"receipt.items.{n}.amount"] = str(i.amount)
            pool = HELDOUT_RECEIPT_TEMPLATES if heldout else RECEIPT_TEMPLATES
            docs.append(DocSpec(doc_id, doc_type, rng.choice(pool), lang, ctx, canonical))

        elif doc_type is DocType.MEDICAL_CERTIFICATE:
            mc_clinic = s.mc_clinic or s.clinic
            end = f.visit_date + timedelta(days=s.mc_days - 1)
            ctx |= {
                "clinic": mc_clinic,
                "doctor": rng.choice(mc_clinic.doctors),
                "patient_name": s.patient_name.full_name,
                "date": d(f.visit_date),
                "days": s.mc_days,
                "from": d(f.visit_date),
                "to": d(end),
                "diagnosis": diagnosis_text(f.diagnosis_code, DIAGNOSES[f.diagnosis_code], lang)
                if rng.random() < 0.5
                else "",
                "serial": f"MC{rng.randint(10000, 99999)}",
            }
            canonical = {
                "medical_certificate.clinic_name": mc_clinic.clinic.name,
                "medical_certificate.patient_name": s.patient_name.full_name,
                "medical_certificate.date": f.visit_date.isoformat(),
                "medical_certificate.days": str(s.mc_days),
            }
            docs.append(DocSpec(doc_id, doc_type, "medical_certificate", lang, ctx, canonical))

        elif doc_type is DocType.REFERRAL_LETTER:
            assert s.referral_from is not None and s.referral_date is not None
            ref_date: date = s.referral_date
            ctx |= {
                "clinic": s.referral_from,
                "doctor": rng.choice(s.referral_from.doctors),
                "to_clinic": s.clinic.clinic.name,
                "patient_name": s.patient_name.full_name,
                "date": d(ref_date),
                "reason": diagnosis_text(f.diagnosis_code, DIAGNOSES[f.diagnosis_code], lang),
            }
            canonical = {
                "referral_letter.from_clinic": s.referral_from.clinic.name,
                "referral_letter.to_clinic": s.clinic.clinic.name,
                "referral_letter.patient_name": s.patient_name.full_name,
                "referral_letter.date": ref_date.isoformat(),
            }
            docs.append(DocSpec(doc_id, doc_type, "referral_letter", lang, ctx, canonical))
    return docs


def tamper_printed(s: Scenario, spec: DocSpec, rng: random.Random) -> tuple[str, str] | None:
    """For a tampered receipt: the forged printed text and its canonical value."""
    if not s.tamper or spec.doc_type is not DocType.RECEIPT:
        return None
    if s.tamper.new_amount is not None:
        return fmt_money(s.tamper.new_amount, s.facts.currency, rng.randint(0, 2)), str(
            s.tamper.new_amount
        )
    assert s.tamper.new_date is not None
    # Forgers type a plain numeric date, whatever style the clinic printed.
    return s.tamper.new_date.strftime("%d/%m/%Y"), s.tamper.new_date.isoformat()
