"""Ground-truth domain model for claims.

These models describe what *actually happened* in a claim scenario. The generator renders
them into documents, and the reference adjudicator turns them into gold labels. Systems
under test never see these objects, only the rendered documents.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CENT = Decimal("0.01")


class Currency(StrEnum):
    MYR = "MYR"
    SGD = "SGD"


class VisitType(StrEnum):
    GP = "GP"
    SPECIALIST = "SPECIALIST"


class ItemCategory(StrEnum):
    CONSULTATION = "consultation"
    MEDICATION = "medication"
    PROCEDURE = "procedure"
    LAB_TEST = "lab_test"
    SUPPLEMENT = "supplement"
    COSMETIC = "cosmetic"
    FERTILITY = "fertility"
    DENTAL = "dental"
    HEALTH_SCREENING = "health_screening"


class DocType(StrEnum):
    CLAIM_FORM = "claim_form"
    RECEIPT = "receipt"
    MEDICAL_CERTIFICATE = "medical_certificate"
    REFERRAL_LETTER = "referral_letter"
    LAB_REPORT = "lab_report"


class Relationship(StrEnum):
    SELF = "self"
    SPOUSE = "spouse"
    CHILD = "child"


class IntegrityIssue(StrEnum):
    """Signs of tampering or fraud planted in a scenario."""

    AMOUNT_ALTERED = "amount_altered"
    DATE_ALTERED = "date_altered"
    NAME_MISMATCH = "name_mismatch"
    DUPLICATE_RECEIPT = "duplicate_receipt"
    UNKNOWN_CLINIC = "unknown_clinic"
    CLINIC_MISMATCH = "clinic_mismatch"
    RECEIPT_NUMBER_ANOMALY = "receipt_number_anomaly"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CoveredPerson(_Frozen):
    person_id: str
    full_name: str
    relationship: Relationship
    covered: bool = True
    preexisting_conditions: frozenset[str] = frozenset()


class Member(_Frozen):
    member_id: str
    plan_id: str
    currency: Currency
    coverage_start: date
    coverage_end: date
    persons: tuple[CoveredPerson, ...]

    @model_validator(mode="after")
    def _check(self) -> Member:
        if self.coverage_end < self.coverage_start:
            raise ValueError("coverage_end is before coverage_start")
        if sum(p.relationship is Relationship.SELF for p in self.persons) != 1:
            raise ValueError("a member must have exactly one SELF person")
        return self

    def person(self, person_id: str) -> CoveredPerson | None:
        return next((p for p in self.persons if p.person_id == person_id), None)


class Clinic(_Frozen):
    clinic_id: str
    name: str
    registration_no: str
    kind: VisitType
    licensed: bool = True


class LineItem(_Frozen):
    item_id: str
    description: str
    category: ItemCategory
    amount: Decimal = Field(gt=0)

    @field_validator("amount")
    @classmethod
    def _cents(cls, v: Decimal) -> Decimal:
        if v != v.quantize(CENT):
            raise ValueError("amount must have at most two decimal places")
        return v


class ClaimFacts(_Frozen):
    """The true facts of one claim, including any planted documents problems."""

    claim_id: str
    member_id: str
    person_id: str
    clinic_id: str
    visit_type: VisitType
    visit_date: date
    submission_date: date
    diagnosis_code: str
    currency: Currency
    line_items: tuple[LineItem, ...] = Field(min_length=1)
    referral_issued: bool = False
    documents: frozenset[DocType]
    illegible_documents: frozenset[DocType] = frozenset()
    integrity_issues: frozenset[IntegrityIssue] = frozenset()
    injection_present: bool = False
    paid_this_policy_year: Decimal = Decimal("0.00")

    @model_validator(mode="after")
    def _check(self) -> ClaimFacts:
        if self.submission_date < self.visit_date:
            raise ValueError("submission_date is before visit_date")
        if not self.illegible_documents <= self.documents:
            raise ValueError("illegible_documents must be a subset of documents")
        if self.paid_this_policy_year < 0:
            raise ValueError("paid_this_policy_year must not be negative")
        return self

    @property
    def claimed_total(self) -> Decimal:
        return sum((i.amount for i in self.line_items), Decimal("0.00"))
