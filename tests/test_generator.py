import json
import random
from collections import Counter
from pathlib import Path

import pytest

from claimdocbench import Decision, adjudicate, load_policy
from claimdocbench.scenarios import EXPECTED, Kind, sample_scenario
from claimdocbench.world import build_world

POLICY = load_policy()


def test_sampler_labels_match_their_kind_across_many_seeds() -> None:
    decisions: Counter[Decision] = Counter()
    for seed in range(8):
        rng = random.Random(seed)
        world = build_world(rng, 60)
        for profile in world.members:
            s = sample_scenario(rng, world, profile, POLICY)
            assert s.gold.decision in EXPECTED[s.kind]
            # The gold label is exactly what the reference engine says for these facts.
            assert s.gold == adjudicate(s.facts, s.member.member, world.registry, POLICY)
            decisions[s.gold.decision] += 1
    assert set(decisions) == set(Decision)


@pytest.mark.parametrize("kind", list(Kind))
def test_every_kind_can_be_forced(kind: Kind) -> None:
    rng = random.Random(kind.value)
    world = build_world(rng, 10)
    for profile in world.members:
        assert sample_scenario(rng, world, profile, POLICY, kind=kind).kind is kind


def test_same_seed_same_scenarios() -> None:
    def ids(seed: int) -> list[str]:
        rng = random.Random(seed)
        world = build_world(rng, 20)
        return [sample_scenario(rng, world, p, POLICY).packet_id for p in world.members]

    assert ids(3) == ids(3)
    assert ids(3) != ids(4)


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            pw.chromium.launch().close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _chromium_available(), reason="Chromium for Playwright not installed")
def test_generate_split_writes_packets_without_answers(tmp_path: Path) -> None:
    from claimdocbench.dataset import generate_split

    summary = generate_split("t", 6, seed=1, out=tmp_path)
    root = tmp_path / "t"
    assert len(summary["packets"]) == 6
    for pid in summary["packets"]:
        manifest = json.loads((root / "packets" / pid / "manifest.json").read_text())
        gold = json.loads((root / "gold" / f"{pid}.json").read_text())
        # Systems must not be able to see answers in what they receive.
        assert set(manifest) == {
            "schema_version",
            "packet_id",
            "channel",
            "member_id",
            "submitted_on",
            "documents",
        }
        for doc in gold["documents"]:
            assert (root / "packets" / pid / doc["file"]).stat().st_size > 1000
            for f in doc["fields"].values():
                x, y, w, h = f["box"]
                assert w > 0 and h > 0
                assert x + w <= doc["size"][0] + 2 and y + h <= doc["size"][1] + 2
    assert (root / "context" / "clinics.json").exists()
