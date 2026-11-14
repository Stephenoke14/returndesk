# ReturnDesk - rules engine tests (one case per rule)
from dataclasses import replace
from decimal import Decimal

import pytest

from app.rules import ClaimFacts, RulesEngine
from app.rules.engine import Outcome

ENGINE = RulesEngine()

# A claim that passes every check and should be refunded automatically
GOOD = ClaimFacts(
    order_value_gbp=Decimal("24.99"),
    order_delivered=True,
    days_since_delivery=3,
    customer_matches_order=True,
    prior_claims_in_window=0,
    has_photo=True,
    damage_class="broken_item",
    damage_confidence=0.95,
    urgency="low",
    injection_flagged=False,
)


@pytest.mark.parametrize(
    ("changes", "outcome", "rule"),
    [
        ({}, Outcome.REFUND, "R12_auto_refund"),
        ({"injection_flagged": True}, Outcome.ESCALATE, "R01_injection_flagged"),
        ({"customer_matches_order": False}, Outcome.REJECT, "R02_customer_mismatch"),
        ({"order_delivered": False}, Outcome.REJECT, "R03_not_delivered"),
        ({"days_since_delivery": 31}, Outcome.REJECT, "R04_outside_window"),
        ({"days_since_delivery": None}, Outcome.ESCALATE, "R04_outside_window"),
        ({"prior_claims_in_window": 3}, Outcome.ESCALATE, "R05_repeat_claimer"),
        ({"has_photo": False}, Outcome.ESCALATE, "R06_no_photo"),
        ({"damage_confidence": 0.60}, Outcome.ESCALATE, "R07_low_confidence"),
        ({"damage_class": None}, Outcome.ESCALATE, "R07_low_confidence"),
        ({"damage_class": "on_fire"}, Outcome.ESCALATE, "R08_unknown_damage_class"),
        ({"damage_class": "no_visible_damage"}, Outcome.REJECT, "R09_no_visible_damage"),
        ({"damage_class": "crushed_box"}, Outcome.ESCALATE, "R10_packaging_only"),
        ({"order_value_gbp": Decimal("40.01")}, Outcome.ESCALATE, "R11_high_value"),
        ({"days_since_delivery": 31, "urgency": "high"}, Outcome.ESCALATE, "R13_urgent_review"),
    ],
)
def test_each_rule(changes, outcome, rule) -> None:
    decision = ENGINE.evaluate(replace(GOOD, **changes))
    assert decision.outcome is outcome
    assert decision.rule_id == rule
    assert decision.reason


def test_boundaries_are_inclusive_where_policy_says_so() -> None:
    at_limit = ENGINE.evaluate(replace(GOOD, order_value_gbp=Decimal("40.00"),
                                       days_since_delivery=30, damage_confidence=0.85,
                                       prior_claims_in_window=2))
    assert at_limit.outcome is Outcome.REFUND


def test_refund_amount_and_audit_fields() -> None:
    d = ENGINE.evaluate(GOOD)
    assert d.refund_amount_gbp == GOOD.order_value_gbp
    assert d.trace[-1] == "R12_auto_refund"
    assert d.policy_version == 1
    # provenance check - stephenoke14 / mrhills
    assert "returndesk-rules" in d.engine


def test_injection_beats_everything_else() -> None:
    d = ENGINE.evaluate(replace(GOOD, injection_flagged=True, customer_matches_order=False,
                                order_delivered=False))
    assert d.rule_id == "R01_injection_flagged"
