"""Turns a scenario into document specs: which template, what is printed, canonical values.

Every printed field is wrapped in a `data-field` element by the templates, so the renderer can
record exactly where each value appears (gold evidence boxes). The canonical value of each
field (ISO dates, plain decimals) is kept here for scoring extraction.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from claimdocbench.domain import Currency, DocType, VisitType
from claimdocbench.scenarios import Scenario
from claimdocbench.world import DIAGNOSES

RECEIPT_TEMPLATES = ["receipt_thermal", "receipt_invoice", "receipt_letterhead"]
DATE_FORMATS = ["%d/%m/%Y", "%d %b %Y", "%Y-%m-%d", "%d-%m-%Y"]


@dataclass
class DocSpec:
    doc_id: str
    doc_type: DocType
    template: str
    context: dict[str, Any]
    canonical: dict[str, str] = field(default_factory=dict)


def fmt_money(amount: Decimal, currency: Currency, style: int) -> str:
    symbol = {Currency.MYR: ["RM", "RM ", "MYR "], Currency.SGD: ["S$", "S$ ", "SGD "]}[currency]
    return f"{symbol[style % 3]}{amount:,.2f}"


def build_documents(s: Scenario, rng: random.Random) -> list[DocSpec]:
    f = s.facts
    date_fmt = rng.choice(DATE_FORMATS)
    money_style = rng.randint(0, 2)

    def d(x: date) -> str:
        return x.strftime(date_fmt)

    def m(x: Decimal) -> str:
        return fmt_money(x, f.currency, money_style)

    docs: list[DocSpec] = []
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

    for k, doc_type in enumerate(present, start=1):
        doc_id = f"d{k}"
        if doc_type is DocType.CLAIM_FORM:
            referred = (
                "N/A" if f.visit_type is VisitType.GP else "Yes" if f.referral_issued else "No"
            )
            ctx: dict[str, Any] = {
                "form_no": f"CF-{rng.randint(100000, 999999)}",
                "employer": s.member.employer,
                "member_id": f.member_id,
                "member_name": self_name,
                "patient_name": s.patient_name.full_name,
                "relationship": relationship.title(),
                "clinic_name": s.clinic.clinic.name,
                "visit_date": d(f.visit_date),
                "visit_type": "General practitioner"
                if f.visit_type is VisitType.GP
                else "Specialist",
                "referred": referred,
                "diagnosis": f"{f.diagnosis_code} {DIAGNOSES[f.diagnosis_code]}",
                "amount": m(f.claimed_total),
                "bank": rng.choice(["Bank Synthetik", "Harbour Savings Bank", "Bank Rakyat Maya"]),
                "account": f"xxxx-xxxx-{rng.randint(1000, 9999)}",
                "remarks": s.injection.text
                if s.injection
                else rng.choice(
                    [
                        "",
                        "",
                        "Receipt attached.",
                        "Follow-up visit.",
                        "Please process.",
                        "Claim for outpatient treatment.",
                    ]
                ),
                "signed_on": d(f.submission_date),
                "signature": self_name.split()[0],
            }
            canonical = {
                "claim_form.member_id": f.member_id,
                "claim_form.patient_name": s.patient_name.full_name,
                "claim_form.clinic_name": s.clinic.clinic.name,
                "claim_form.visit_date": f.visit_date.isoformat(),
                "claim_form.visit_type": f.visit_type.value,
                "claim_form.referred": referred,
                "claim_form.diagnosis_code": f.diagnosis_code,
                "claim_form.amount": str(f.claimed_total),
            }
            docs.append(DocSpec(doc_id, doc_type, "claim_form", ctx, canonical))

        elif doc_type is DocType.RECEIPT:
            hour = rng.randint(8, 21)
            items = [{"description": i.description, "amount": m(i.amount)} for i in f.line_items]
            ctx = {
                "clinic": s.clinic,
                "receipt_no": s.receipt_no,
                "date": d(f.visit_date),
                "time": f"{hour:02d}:{rng.randint(0, 59):02d}",
                "patient_name": s.receipt_patient_name,
                "items": items,
                "total": m(f.claimed_total),
                "payment": rng.choice(["Cash", "Debit card", "Credit card", "QR payment"]),
                "doctor": rng.choice(s.clinic.doctors),
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
            docs.append(DocSpec(doc_id, doc_type, rng.choice(RECEIPT_TEMPLATES), ctx, canonical))

        elif doc_type is DocType.MEDICAL_CERTIFICATE:
            mc_clinic = s.mc_clinic or s.clinic
            end = f.visit_date + timedelta(days=s.mc_days - 1)
            ctx = {
                "clinic": mc_clinic,
                "doctor": rng.choice(mc_clinic.doctors),
                "patient_name": s.patient_name.full_name,
                "date": d(f.visit_date),
                "days": s.mc_days,
                "from": d(f.visit_date),
                "to": d(end),
                "diagnosis": DIAGNOSES[f.diagnosis_code] if rng.random() < 0.5 else "",
                "serial": f"MC{rng.randint(10000, 99999)}",
            }
            canonical = {
                "medical_certificate.clinic_name": mc_clinic.clinic.name,
                "medical_certificate.patient_name": s.patient_name.full_name,
                "medical_certificate.date": f.visit_date.isoformat(),
                "medical_certificate.days": str(s.mc_days),
            }
            docs.append(DocSpec(doc_id, doc_type, "medical_certificate", ctx, canonical))

        elif doc_type is DocType.REFERRAL_LETTER:
            assert s.referral_from is not None and s.referral_date is not None
            ctx = {
                "clinic": s.referral_from,
                "doctor": rng.choice(s.referral_from.doctors),
                "to_clinic": s.clinic.clinic.name,
                "patient_name": s.patient_name.full_name,
                "date": d(s.referral_date),
                "reason": DIAGNOSES[f.diagnosis_code],
            }
            canonical = {
                "referral_letter.from_clinic": s.referral_from.clinic.name,
                "referral_letter.to_clinic": s.clinic.clinic.name,
                "referral_letter.patient_name": s.patient_name.full_name,
                "referral_letter.date": s.referral_date.isoformat(),
            }
            docs.append(DocSpec(doc_id, doc_type, "referral_letter", ctx, canonical))
    return docs
