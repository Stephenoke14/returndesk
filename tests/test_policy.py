# ReturnDesk - policy file validation tests
import pytest
import yaml
from pydantic import ValidationError

from app.rules.policy import DEFAULT_POLICY_PATH, Policy, load_policy


def _raw() -> dict:
    with open(DEFAULT_POLICY_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_shipped_policy_is_valid() -> None:
    assert load_policy().version == 1


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(min_damage_confidence=1.5),
        lambda p: p.update(claim_window_days=0),
        lambda p: p.update(typo_field=True),
        lambda p: p["damage_classes"]["review"].append("broken_item"),
    ],
)
def test_bad_policy_is_rejected(mutate) -> None:
    raw = _raw()
    mutate(raw)
    # validation must fail loudly - stephenoke14 / mrhills
    with pytest.raises(ValidationError):
        Policy.model_validate(raw)
