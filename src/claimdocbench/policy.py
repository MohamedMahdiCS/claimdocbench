"""Policy-as-code: the synthetic policy schedule and its clauses."""

from __future__ import annotations

from decimal import Decimal
from functools import cache
from importlib.resources import files

import yaml
from pydantic import BaseModel, ConfigDict, Field

from claimdocbench.domain import Currency, ItemCategory


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Limits(_Frozen):
    gp_visit_cap: Decimal = Field(gt=0)
    specialist_visit_cap: Decimal = Field(gt=0)
    annual_limit: Decimal = Field(gt=0)


class Plan(_Frozen):
    copay_rate: Decimal = Field(ge=0, lt=1)
    submission_deadline_days: int = Field(gt=0)
    preexisting_waiting_days: int = Field(ge=0)
    limits: dict[Currency, Limits]


class Clause(_Frozen):
    title: str
    text: str


class Policy(_Frozen):
    policy_id: str
    version: str
    name: str
    plans: dict[str, Plan]
    covered_categories: frozenset[ItemCategory]
    excluded_categories: dict[ItemCategory, str]
    clauses: dict[str, Clause]

    def plan(self, plan_id: str) -> Plan:
        try:
            return self.plans[plan_id]
        except KeyError:
            raise KeyError(f"unknown plan {plan_id!r}") from None

    def clause(self, clause_id: str) -> Clause:
        return self.clauses[clause_id]


@cache
def load_policy() -> Policy:
    """Load the bundled policy. Cached because it never changes at runtime."""
    raw = files("claimdocbench").joinpath("data/policy.yaml").read_text(encoding="utf-8")
    policy = Policy.model_validate(yaml.safe_load(raw))
    _validate_references(policy)
    return policy


def _validate_references(policy: Policy) -> None:
    overlap = policy.covered_categories & policy.excluded_categories.keys()
    if overlap:
        raise ValueError(f"categories both covered and excluded: {sorted(overlap)}")
    missing = set(ItemCategory) - policy.covered_categories - policy.excluded_categories.keys()
    if missing:
        raise ValueError(f"categories neither covered nor excluded: {sorted(missing)}")
    for clause_id in policy.excluded_categories.values():
        if clause_id not in policy.clauses:
            raise ValueError(f"exclusion refers to unknown clause {clause_id}")
