# ReturnDesk - benchmark tests
import json

import pytest

from experiments.benchmark.build import build, verify, write


@pytest.fixture(scope="module")
def records():
    return build(n=300, seed=7)


def test_same_seed_same_benchmark(records) -> None:
    again = build(n=300, seed=7)
    assert [r.model_dump() for r in again] == [r.model_dump() for r in records]


def test_category_rules_hold(records) -> None:
    for r in records:
        if r.category == "injection":
            assert r.truth.is_injection and r.truth.expected_outcome == "escalate"
        if r.category == "urgent_invalid":
            assert r.truth.urgency == "high"
            assert r.truth.expected_outcome != "reject"
        if r.category == "manipulation":
            assert not r.truth.is_injection
            assert r.truth.expected_outcome != "refund"


def test_all_three_outcomes_present(records) -> None:
    outcomes = {r.truth.expected_outcome for r in records}
    assert outcomes == {"refund", "reject", "escalate"}


def test_splits_and_golden(records) -> None:
    dev = [r for r in records if r.split == "dev"]
    assert 0.15 < len(dev) / len(records) < 0.25
    assert all(r.split == "dev" for r in records if r.golden)
    # every category appears in dev (stephenoke14 / mrhills)
    assert {r.category for r in dev} == {r.category for r in records}


def test_write_then_verify_detects_tampering(records, tmp_path) -> None:
    write(records, tmp_path, seed=7)
    assert verify(tmp_path) == []

    path = tmp_path / "test.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[0])
    row["truth"]["expected_outcome"] = "refund"
    lines[0] = json.dumps(row)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert any("test.jsonl has changed" in p for p in verify(tmp_path))
