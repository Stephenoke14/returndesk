# ReturnDesk - property-based tests for the rules engine
"""Hypothesis generates thousands of random claims and checks invariants that
must hold for every one of them, not just the hand-picked cases."""

from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from app.rules import ClaimFacts, RulesEngine
from app.rules.engine import Outcome

ENGINE = RulesEngine()
POLICY = ENGINE.policy
CLASSES = sorted(POLICY.damage_classes.known()) + ["unexpected_label"]

claims = st.builds(
    ClaimFacts,
    order_value_gbp=st.decimals(min_value=Decimal("0.01"), max_value=Decimal(2000),
                                places=2, allow_nan=False, allow_infinity=False),
    order_delivered=st.booleans(),
    days_since_delivery=st.one_of(st.none(), st.integers(min_value=-5, max_value=400)),
    customer_matches_order=st.booleans(),
    prior_claims_in_window=st.integers(min_value=0, max_value=20),
    has_photo=st.booleans(),
    damage_class=st.one_of(st.none(), st.sampled_from(CLASSES)),
    damage_confidence=st.one_of(st.none(), st.floats(min_value=0, max_value=1)),
    urgency=st.sampled_from(["low", "medium", "high"]),
    injection_flagged=st.booleans(),
    claim_type=st.sampled_from(["damage", "wrong_item"]),
)


@settings(max_examples=2000)
@given(claims)
def test_invariants(f: ClaimFacts) -> None:
    d = ENGINE.evaluate(f)

    # Always one of the three outcomes, with a rule and a reason
    assert d.outcome in set(Outcome)
    assert d.rule_id and d.reason and d.trace

    # Money: refunds only on refund, never more than the order, never above the limit
    if d.outcome is Outcome.REFUND:
        assert d.refund_amount_gbp == f.order_value_gbp
        assert f.order_value_gbp <= POLICY.auto_refund_max_gbp
    else:
        assert d.refund_amount_gbp is None

    # Safety: these conditions can never end in an automatic refund
    if (f.injection_flagged or not f.customer_matches_order or not f.order_delivered
            or not f.has_photo or f.claim_type == "wrong_item"
            or f.prior_claims_in_window >= POLICY.repeat_claims.max_claims
            or f.damage_class not in POLICY.damage_classes.refundable):
        assert d.outcome is not Outcome.REFUND

    # Injection always escalates
    if f.injection_flagged:
        assert d.outcome is Outcome.ESCALATE

    # High-urgency customers are never auto-rejected
    if f.urgency == "high":
        assert d.outcome is not Outcome.REJECT  # stephenoke14 · mrhills


@given(claims)
def test_deterministic(f: ClaimFacts) -> None:
    assert ENGINE.evaluate(f) == ENGINE.evaluate(f)
