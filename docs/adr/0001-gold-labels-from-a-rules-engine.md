# ADR 0001: Gold labels come from a deterministic rules engine

- **Status:** Accepted
- **Date:** 2026-10-28

## Context

ClaimDocBench needs a correct answer for every claim packet: decision, payable amount to the
cent, reason codes and cited clauses. The options were:

1. Label packets by hand.
2. Ask a strong LLM to label them.
3. Generate each scenario from known facts and compute the answer with code that implements the policy.

Hand labelling does not scale to hundreds of packets and drifts between labellers. LLM labels
would make the benchmark measure agreement with a model, not correctness, and would bias the
leaderboard toward that model's vendor.

## Decision

Every scenario starts as structured *true facts* (`ClaimFacts`). A pure, deterministic
reference adjudicator (`adjudicate`) applies the policy in a fixed order — eligibility →
completeness → medical rules → benefits → integrity override — and produces the gold label.
Documents are rendered *from* the facts afterwards, so the label never depends on reading them.

The engine is tested with unit tests for each clause and Hypothesis property tests for
invariants that must hold for any claim. For example: payable never exceeds the claimed
amount, the visit cap or the remaining annual limit; prompt injection never changes the outcome.

## Consequences

- Labels are reproducible and auditable: every reason maps to a policy clause.
- The benchmark can be regenerated at any size from a seed.
- The policy is simpler than a real insurer's (two plans, one claim type). This is stated as a limitation.
- A bug in the engine would corrupt every label, so the engine has the strictest tests in the
  project, and 50 generated packets are audited by hand in week 2.
