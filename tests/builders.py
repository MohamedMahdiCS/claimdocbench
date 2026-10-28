"""Small builders for test claims. Defaults describe a clean GP claim in Malaysia."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from claimdocbench.domain import (
    ClaimFacts,
    Clinic,
    CoveredPerson,
    Currency,
    DocType,
    ItemCategory,
    LineItem,
    Member,
    Relationship,
    VisitType,
)

CLINICS: dict[str, Clinic] = {
    "CL-GP-1": Clinic(
        clinic_id="CL-GP-1",
        name="Klinik Sejahtera",
        registration_no="KKM-100001",
        kind=VisitType.GP,
    ),
    "CL-SP-1": Clinic(
        clinic_id="CL-SP-1",
        name="Pusat Pakar Damai",
        registration_no="KKM-200001",
        kind=VisitType.SPECIALIST,
    ),
    "CL-UNL-1": Clinic(
        clinic_id="CL-UNL-1",
        name="Klinik Tanpa Lesen",
        registration_no="KKM-999999",
        kind=VisitType.GP,
        licensed=False,
    ),
}

BASIC_DOCS = frozenset({DocType.CLAIM_FORM, DocType.RECEIPT})


def item(category: ItemCategory, amount: str, item_id: str | None = None) -> LineItem:
    return LineItem(
        item_id=item_id or f"{category.value}-{amount}",
        description=category.value.replace("_", " "),
        category=category,
        amount=Decimal(amount),
    )


def member(plan_id: str = "A", currency: Currency = Currency.MYR, **kw: Any) -> Member:
    persons = kw.pop(
        "persons",
        (
            CoveredPerson(
                person_id="P1", full_name="Nur Aisyah binti Hassan", relationship=Relationship.SELF
            ),
            CoveredPerson(
                person_id="P2",
                full_name="Tan Wei Ming",
                relationship=Relationship.SPOUSE,
                covered=False,
            ),
        ),
    )
    return Member(
        member_id="M1",
        plan_id=plan_id,
        currency=currency,
        coverage_start=kw.pop("coverage_start", date(2026, 1, 1)),
        coverage_end=kw.pop("coverage_end", date(2026, 12, 31)),
        persons=persons,
        **kw,
    )


def facts(**kw: Any) -> ClaimFacts:
    defaults: dict[str, Any] = {
        "claim_id": "C1",
        "member_id": "M1",
        "person_id": "P1",
        "clinic_id": "CL-GP-1",
        "visit_type": VisitType.GP,
        "visit_date": date(2026, 6, 10),
        "submission_date": date(2026, 6, 12),
        "diagnosis_code": "J06.9",
        "currency": Currency.MYR,
        "line_items": (
            item(ItemCategory.CONSULTATION, "30.00"),
            item(ItemCategory.MEDICATION, "20.00"),
        ),
        "documents": BASIC_DOCS,
    }
    defaults.update(kw)
    return ClaimFacts(**defaults)
