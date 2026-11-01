---
license: cc-by-4.0
language:
  - en
  - ms
  - zh
pretty_name: ClaimDocBench
task_categories:
  - document-question-answering
  - image-to-text
tags:
  - insurance
  - claims
  - document-ai
  - fraud-detection
  - prompt-injection
  - synthetic
  - southeast-asia
size_categories:
  - n<1K
---

# ClaimDocBench dataset card

## Summary

400 synthetic outpatient medical insurance claim packets from Malaysia and Singapore, each a set
of document images (claim form, receipt, medical certificate, referral letter) with an exact
answer: the decision, the payout to the cent, the reasons, the policy clauses that apply, any
planted fraud, any planted prompt injection, and a pixel box for every printed value.

Everything is invented. No real person, clinic, receipt or medical record is in the data.

## Splits

| Split | Packets | Injection twins | Notes |
|---|---:|---:|---|
| `dev` | 150 | 18 | For building and tuning. `smoke` is a fixed 25-packet subset |
| `test` | 200 | 20 | For reported results |
| `heldout` | 50 | 1 | Three document layouts used nowhere else. Fingerprint committed before any system was tuned; [released](https://github.com/MohamedMahdiCS/claimdocbench/releases/tag/v0.2.0-heldout) after the final runs |

Injection twins are copies of injected packets with the injection removed and everything else
identical. They are used to measure whether an injection changed a system's decision.

SHA-256 fingerprints for every split are in [`splits/manifest.json`](splits/manifest.json).
`claimdocbench download --split test` fetches a split and refuses it if the fingerprint differs.

## What a packet contains

```
packets/<packet_id>/manifest.json    member ID, date received, list of document files
packets/<packet_id>/d1.png | d1.jpg  document images
gold/<packet_id>.json                the answer (never given to a system)
context/                             member registry, clinic registry, claims history, policy
```

| Property | Distribution in `test` |
|---|---|
| Decisions | Partial 71, Fraud review 58, Reject 27, Request info 23, Approve 21 |
| Document language | English 335, Malay 113, Chinese 88 |
| Capture | Clean 215, scan 198, phone photo 119, unreadable 4 |
| Country | Malaysia and Singapore (MYR and SGD) |
| Name origin of patient | Malay, Chinese, Indian, other |

## How it was made

1. A synthetic world: members and dependants, 38 clinics, a two-plan policy with 20 clauses.
2. A scenario sampler picks a claim type (clean, partial, reject, request info, fraud) and builds
   the true facts.
3. A deterministic rules engine computes the answer from those facts. The answer never comes
   from a model.
4. Documents are rendered from HTML templates with headless Chromium, then optionally forged
   (a total or date painted over) and captured as a scan, a phone photo or an unreadable copy.
   Field boxes are moved with the same transform as the pixels.
5. An audit checks every packet: each planted fraud must be detectable from the documents and
   registries, and honest packets must not show fraud signals.

Generation is reproducible: `claimdocbench generate --split test --n 200 --seed 202`.

## Intended use

- Evaluating document AI and agent systems that read and decide insurance claims
- Measuring fraud detection, prompt-injection resistance and calibrated abstention
- Comparing systems across languages, capture quality and name origins

## Out of scope

- Training a production claims system. The data is synthetic and simplified.
- Drawing conclusions about real insurers, clinics or claim fraud rates.

## Known limitations

- Layouts, wording and fraud patterns are invented; real claims are messier and more varied.
- One claim type (outpatient reimbursement) and one simplified policy.
- Forgeries are programmatic. A skilled forger would leave fewer traces.
- Images were rendered on macOS; regenerated images may differ slightly on other systems,
  which is why released splits are verified by hash.
- The Malay and Chinese text was written for this dataset and may read as slightly formal or unnatural to native speakers.

## Fairness slices

Each gold file records the patient's name origin, document language, capture quality, country,
plan and visit type, so results can be broken down by group. These are attributes of synthetic
records, not of real people.

## License and citation

Data: CC BY 4.0. Code: Apache-2.0.

```
@misc{claimdocbench2026,
  title  = {ClaimDocBench: a multilingual, adversarial benchmark for AI insurance claim processing},
  author = {Mohamed Mahdi},
  year   = {2026},
  url    = {https://github.com/MohamedMahdiCS/claimdocbench}
}
```
