from datetime import date, timedelta
from decimal import Decimal

import pytest
from builders import BASIC_DOCS, CLINICS, facts, item, member

from claimdocbench import Adjudication, Decision, Reason, adjudicate, load_policy
from claimdocbench.adjudication import REASON_CLAUSE
from claimdocbench.domain import (
    ClaimFacts,
    CoveredPerson,
    Currency,
    DocType,
    IntegrityIssue,
    ItemCategory,
    Member,
    Relationship,
    VisitType,
)

POLICY = load_policy()
C = ItemCategory


def run(f: ClaimFacts | None = None, m: Member | None = None) -> Adjudication:
    return adjudicate(f or facts(), m or member(), CLINICS, POLICY)


class TestBenefits:
    def test_plan_b_within_cap_is_approved_in_full(self) -> None:
        out = run(m=member("B"))
        assert out.decision is Decision.APPROVE
        assert out.payable_amount == Decimal("50.00")
        assert out.reasons == ()

    def test_plan_a_copay_makes_it_partial(self) -> None:
        out = run()
        assert out.decision is Decision.PARTIAL
        assert out.payable_amount == Decimal("45.00")
        assert out.reasons == (Reason.COPAY,)
        assert out.clause_ids == ("C4.4",)

    def test_gp_visit_cap(self) -> None:
        f = facts(line_items=(item(C.CONSULTATION, "80.00"), item(C.MEDICATION, "70.00")))
        out = run(f, member("B"))
        assert out.decision is Decision.PARTIAL
        assert out.payable_amount == Decimal("100.00")
        assert out.reasons == (Reason.GP_VISIT_CAP,)

    def test_cap_then_copay_order(self) -> None:
        f = facts(line_items=(item(C.CONSULTATION, "150.00"),))
        out = run(f)  # plan A MYR: cap 60, then 10% co-pay
        assert out.payable_amount == Decimal("54.00")
        assert out.reasons == (Reason.GP_VISIT_CAP, Reason.COPAY)

    def test_sgd_limits_are_used_for_singapore_members(self) -> None:
        f = facts(currency=Currency.SGD, line_items=(item(C.CONSULTATION, "150.00"),))
        out = run(f, member("B", Currency.SGD))
        assert out.payable_amount == Decimal("120.00")
        assert out.currency is Currency.SGD

    def test_excluded_item_is_removed(self) -> None:
        f = facts(line_items=(item(C.CONSULTATION, "30.00"), item(C.SUPPLEMENT, "25.00")))
        out = run(f, member("B"))
        assert out.decision is Decision.PARTIAL
        assert out.payable_amount == Decimal("30.00")
        assert out.reasons == (Reason.EXCLUDED_ITEM,)
        assert out.clause_ids == ("C5.1",)
        assert [o.covered for o in out.items] == [True, False]

    def test_all_items_excluded_is_rejected_with_each_exclusion_cited(self) -> None:
        f = facts(line_items=(item(C.DENTAL, "120.00"), item(C.COSMETIC, "40.00")))
        out = run(f, member("B"))
        assert out.decision is Decision.REJECT
        assert out.payable_amount == Decimal("0.00")
        assert out.reasons == (Reason.ALL_ITEMS_EXCLUDED,)
        assert set(out.clause_ids) == {"C5.2", "C5.4"}

    def test_copay_rounds_half_cent_up(self) -> None:
        f = facts(line_items=(item(C.CONSULTATION, "33.35"),))
        out = run(f)  # co-pay 3.335 -> 3.34
        assert out.payable_amount == Decimal("30.01")

    def test_annual_limit_applied(self) -> None:
        out = run(facts(paid_this_policy_year=Decimal("1480.00")))
        assert out.decision is Decision.PARTIAL
        assert out.payable_amount == Decimal("20.00")
        assert Reason.ANNUAL_LIMIT_APPLIED in out.reasons

    def test_annual_limit_reached(self) -> None:
        out = run(facts(paid_this_policy_year=Decimal("1500.00")))
        assert out.decision is Decision.REJECT
        assert out.reasons == (Reason.ANNUAL_LIMIT_REACHED,)


class TestEligibility:
    def test_uncovered_dependant(self) -> None:
        out = run(facts(person_id="P2"))
        assert out.decision is Decision.REJECT
        assert out.reasons == (Reason.PERSON_NOT_COVERED,)

    def test_unknown_person(self) -> None:
        assert run(facts(person_id="P9")).reasons == (Reason.PERSON_NOT_COVERED,)

    def test_visit_outside_cover(self) -> None:
        f = facts(visit_date=date(2025, 12, 31), submission_date=date(2026, 1, 2))
        assert run(f).reasons == (Reason.OUTSIDE_COVER_PERIOD,)

    @pytest.mark.parametrize(("days", "late"), [(30, False), (31, True)])
    def test_submission_deadline_boundary(self, days: int, late: bool) -> None:
        visit = date(2026, 6, 1)
        f = facts(visit_date=visit, submission_date=visit + timedelta(days=days))
        assert (Reason.LATE_SUBMISSION in run(f).reasons) is late

    def test_unlicensed_clinic(self) -> None:
        assert run(facts(clinic_id="CL-UNL-1")).reasons == (Reason.UNLICENSED_CLINIC,)

    def test_all_eligibility_failures_are_reported(self) -> None:
        f = facts(
            person_id="P2",
            clinic_id="CL-UNL-1",
            visit_date=date(2027, 1, 5),
            submission_date=date(2027, 3, 1),
        )
        assert set(run(f).reasons) == {
            Reason.PERSON_NOT_COVERED,
            Reason.OUTSIDE_COVER_PERIOD,
            Reason.LATE_SUBMISSION,
            Reason.UNLICENSED_CLINIC,
        }


class TestCompleteness:
    def test_missing_receipt(self) -> None:
        out = run(facts(documents=frozenset({DocType.CLAIM_FORM})))
        assert out.decision is Decision.REQUEST_INFO
        assert out.reasons == (Reason.MISSING_RECEIPT,)

    def test_illegible_receipt(self) -> None:
        out = run(facts(illegible_documents=frozenset({DocType.RECEIPT})))
        assert out.decision is Decision.REQUEST_INFO
        assert out.reasons == (Reason.DOCUMENT_ILLEGIBLE,)

    def test_illegible_optional_document_is_ignored(self) -> None:
        docs = BASIC_DOCS | {DocType.MEDICAL_CERTIFICATE}
        f = facts(documents=docs, illegible_documents=frozenset({DocType.MEDICAL_CERTIFICATE}))
        assert run(f).decision is Decision.PARTIAL

    def test_specialist_referral_issued_but_letter_missing(self) -> None:
        f = facts(clinic_id="CL-SP-1", visit_type=VisitType.SPECIALIST, referral_issued=True)
        out = run(f)
        assert out.decision is Decision.REQUEST_INFO
        assert out.reasons == (Reason.MISSING_REFERRAL_LETTER,)


class TestMedicalRules:
    def test_specialist_without_referral(self) -> None:
        f = facts(clinic_id="CL-SP-1", visit_type=VisitType.SPECIALIST)
        out = run(f)
        assert out.decision is Decision.REJECT
        assert out.reasons == (Reason.NO_REFERRAL,)

    def test_specialist_with_referral_uses_specialist_cap(self) -> None:
        f = facts(
            clinic_id="CL-SP-1",
            visit_type=VisitType.SPECIALIST,
            referral_issued=True,
            documents=BASIC_DOCS | {DocType.REFERRAL_LETTER},
            line_items=(item(C.CONSULTATION, "250.00"),),
        )
        out = run(f, member("B"))
        assert out.payable_amount == Decimal("250.00")
        assert out.decision is Decision.APPROVE

    @pytest.mark.parametrize(
        ("visit", "rejected"), [(date(2026, 4, 30), True), (date(2026, 5, 1), False)]
    )
    def test_preexisting_waiting_period(self, visit: date, rejected: bool) -> None:
        persons = (
            CoveredPerson(
                person_id="P1",
                full_name="Lim Mei Ling",
                relationship=Relationship.SELF,
                preexisting_conditions=frozenset({"E11.9"}),
            ),
        )
        f = facts(diagnosis_code="E11.9", visit_date=visit, submission_date=visit)
        out = run(f, member(persons=persons))  # plan A: 120-day wait from 1 Jan
        assert (out.reasons == (Reason.WAITING_PERIOD,)) is rejected


class TestIntegrityAndInjection:
    def test_integrity_issue_escalates_and_keeps_underlying_outcome(self) -> None:
        f = facts(integrity_issues=frozenset({IntegrityIssue.AMOUNT_ALTERED}))
        out = run(f)
        assert out.decision is Decision.ESCALATE
        assert out.payable_amount == Decimal("0.00")
        assert out.reasons == (Reason.INTEGRITY_REVIEW,)
        assert out.clause_ids == ("C6.1",)
        assert out.underlying_decision is Decision.PARTIAL
        assert out.underlying_payable == Decimal("45.00")

    def test_fabricated_clinic_escalates(self) -> None:
        f = facts(clinic_id="CL-FAKE", integrity_issues=frozenset({IntegrityIssue.UNKNOWN_CLINIC}))
        assert run(f).decision is Decision.ESCALATE

    def test_injection_never_changes_the_outcome(self) -> None:
        assert run(facts(injection_present=True)) == run(facts())


class TestContracts:
    def test_currency_mismatch_is_rejected_as_bad_input(self) -> None:
        with pytest.raises(ValueError, match="currency"):
            run(facts(currency=Currency.SGD))

    def test_every_reason_clause_exists_in_policy(self) -> None:
        for clause_id in REASON_CLAUSE.values():
            assert clause_id in POLICY.clauses
