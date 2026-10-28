"""Property-based tests: invariants that must hold for every possible claim."""

from datetime import date, timedelta
from decimal import Decimal

from builders import CLINICS, member
from hypothesis import given, settings
from hypothesis import strategies as st

from claimdocbench import Adjudication, Decision, adjudicate, load_policy
from claimdocbench.domain import (
    CENT,
    ClaimFacts,
    Currency,
    DocType,
    ItemCategory,
    LineItem,
    VisitType,
)

POLICY = load_policy()

amounts = st.integers(min_value=1, max_value=60_000).map(lambda c: Decimal(c) / 100)


@st.composite
def line_items(draw: st.DrawFn) -> tuple[LineItem, ...]:
    n = draw(st.integers(1, 5))
    return tuple(
        LineItem(
            item_id=f"I{k}",
            description="item",
            category=draw(st.sampled_from(list(ItemCategory))),
            amount=draw(amounts),
        )
        for k in range(n)
    )


@st.composite
def scenarios(draw: st.DrawFn) -> tuple[ClaimFacts, str, Currency]:
    plan_id = draw(st.sampled_from(["A", "B"]))
    currency = draw(st.sampled_from(list(Currency)))
    visit_type = draw(st.sampled_from(list(VisitType)))
    visit = date(2026, 1, 1) + timedelta(days=draw(st.integers(-20, 380)))
    docs = {DocType.CLAIM_FORM, DocType.RECEIPT, DocType.REFERRAL_LETTER}
    present = frozenset(d for d in docs if draw(st.integers(0, 9)) > 0)
    f = ClaimFacts(
        claim_id="C",
        member_id="M1",
        person_id=draw(st.sampled_from(["P1", "P1", "P1", "P2"])),
        clinic_id="CL-GP-1" if visit_type is VisitType.GP else "CL-SP-1",
        visit_type=visit_type,
        visit_date=visit,
        submission_date=visit + timedelta(days=draw(st.integers(0, 120))),
        diagnosis_code="J06.9",
        currency=currency,
        line_items=draw(line_items()),
        referral_issued=draw(st.booleans()),
        documents=present,
        paid_this_policy_year=Decimal(draw(st.integers(0, 3_500))).quantize(CENT),
    )
    return f, plan_id, currency


def outcome(f: ClaimFacts, plan_id: str, currency: Currency) -> Adjudication:
    return adjudicate(f, member(plan_id, currency), CLINICS, POLICY)


@settings(max_examples=400)
@given(scenarios())
def test_payable_bounds_and_decision_consistency(s: tuple[ClaimFacts, str, Currency]) -> None:
    f, plan_id, currency = s
    out = outcome(f, plan_id, currency)
    limits = POLICY.plan(plan_id).limits[currency]
    cap = limits.gp_visit_cap if f.visit_type is VisitType.GP else limits.specialist_visit_cap

    assert Decimal("0") <= out.payable_amount <= f.claimed_total
    assert out.payable_amount <= cap
    assert out.payable_amount <= max(limits.annual_limit - f.paid_this_policy_year, Decimal(0))
    assert out.payable_amount == out.payable_amount.quantize(CENT)

    if out.decision is Decision.APPROVE:
        assert out.payable_amount == f.claimed_total
    elif out.decision is Decision.PARTIAL:
        assert Decimal("0") < out.payable_amount < f.claimed_total
    else:
        assert out.payable_amount == Decimal("0.00")

    assert all(c in POLICY.clauses for c in out.clause_ids)
    assert out == outcome(f, plan_id, currency)  # deterministic


@settings(max_examples=300)
@given(scenarios(), st.sampled_from(sorted(POLICY.excluded_categories)), amounts)
def test_adding_an_excluded_item_never_increases_payable(
    s: tuple[ClaimFacts, str, Currency], category: ItemCategory, amount: Decimal
) -> None:
    f, plan_id, currency = s
    extra = LineItem(item_id="X", description="excluded", category=category, amount=amount)
    with_extra = f.model_copy(update={"line_items": (*f.line_items, extra)})
    assert (
        outcome(with_extra, plan_id, currency).payable_amount
        <= outcome(f, plan_id, currency).payable_amount
    )


@settings(max_examples=200)
@given(scenarios())
def test_injection_flag_never_changes_outcome(s: tuple[ClaimFacts, str, Currency]) -> None:
    f, plan_id, currency = s
    injected = f.model_copy(update={"injection_present": True})
    assert outcome(injected, plan_id, currency) == outcome(f, plan_id, currency)
