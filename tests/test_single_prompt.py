import io
import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from claimdocbench import single_prompt
from claimdocbench.domain import Currency
from claimdocbench.policy import load_policy


def _split(tmp: Path) -> Path:
    ctx = tmp / "context"
    ctx.mkdir(parents=True)
    policy = Path(single_prompt.__file__).parent / "data" / "policy.yaml"
    (ctx / "policy.yaml").write_text(policy.read_text())
    (ctx / "members.json").write_text(
        json.dumps([{"member_id": "M1", "plan_id": "A", "currency": "MYR", "persons": []}])
    )
    (ctx / "clinics.json").write_text(
        json.dumps(
            [
                {
                    "clinic_id": "C1",
                    "name": "Klinik Bayu",
                    "registration_no": "REG-MY-1",
                    "kind": "GP",
                    "licensed": True,
                    "country": "MY",
                    "receipt_number_prefix": "KB1",
                }
            ]
        )
    )
    (ctx / "claims_history.json").write_text("[]")
    pdir = tmp / "packets" / "p1"
    pdir.mkdir(parents=True)
    Image.new("RGB", (40, 30), "white").save(pdir / "d1.png")
    (pdir / "manifest.json").write_text(
        json.dumps(
            {
                "packet_id": "p1",
                "member_id": "M1",
                "submitted_on": "2026-06-12",
                "documents": [{"doc_id": "d1", "file": "d1.png"}],
            }
        )
    )
    return tmp


def test_prompt_contains_the_members_plan_and_registry(tmp_path: Path) -> None:
    ctx = single_prompt.Context(_split(tmp_path))
    text = ctx.for_packet({"member_id": "M1", "submitted_on": "2026-06-12"})
    limits = load_policy().plan("A").limits
    assert f"GP visit limit {limits[Currency.MYR].gp_visit_cap}" in text
    assert "receipt numbers start with KB1-" in text
    assert "C5.1" in text


def test_predict_packet_sends_images_and_parses_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    split = _split(tmp_path)
    sent: dict[str, Any] = {}

    def fake_urlopen(req: Any, timeout: int) -> io.BytesIO:
        sent.update(json.loads(req.data))
        reply = {
            "message": {
                "content": json.dumps(
                    {
                        "decision": "PARTIAL",
                        "payable_amount": "45.00",
                        "reasons": [],
                        "confidence": 0.7,
                        "fields": {},
                    }
                )
            },
            "prompt_eval_count": 10,
            "eval_count": 5,
        }
        return io.BytesIO(json.dumps(reply).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    pred = single_prompt.predict_packet(
        split / "packets" / "p1", single_prompt.Context(split), "m", "vision"
    )
    assert pred["decision"] == "PARTIAL" and pred["packet_id"] == "p1"
    assert len(sent["messages"][0]["images"]) == 1
    assert sent["format"]["required"][0] == "decision"
