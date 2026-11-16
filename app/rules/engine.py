# ReturnDesk - rules engine
"""Deterministic refund decisions with an explanation for every outcome.

The engine is plain Python with no ML and no LLM. It receives the facts about
a claim and returns refund, reject or escalate, the rule that decided it, a
human-readable reason, and the full list of rules it checked (the trace).

Rules run in a fixed order; the first rule that matches decides:

    R01 injection_flagged     -> escalate
    R02 customer_mismatch     -> reject
    R03 not_delivered         -> reject
    R04 outside_window        -> reject
    R05 repeat_claimer        -> escalate
    R06 wrong_item_claim      -> escalate
    R07 no_photo              -> escalate
    R08 low_confidence        -> escalate
    R09 unknown_damage_class  -> escalate
    R10 no_visible_damage     -> reject
    R11 packaging_only        -> escalate
    R12 high_value            -> escalate
    R13 auto_refund           -> refund (full order value)

After that, R14 urgent_review turns a reject into escalate when the customer's
message is rated at or above the policy's urgency level.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Literal

from app.rules.policy import Policy, Urgency, load_policy

ClaimType = Literal["damage", "wrong_item"]

URGENCY_RANK = {"low": 0, "medium": 1, "high": 2}


class Outcome(str, Enum):
    REFUND = "refund"
    REJECT = "reject"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class ClaimFacts:
    """Everything the rules need to know about one claim."""

    order_value_gbp: Decimal
    order_delivered: bool
    days_since_delivery: int | None
    customer_matches_order: bool
    prior_claims_in_window: int
    has_photo: bool
    damage_class: str | None
    damage_confidence: float | None
    urgency: Urgency = "low"
    injection_flagged: bool = False
    claim_type: ClaimType = "damage"


@dataclass(frozen=True)
class RuleDecision:
    outcome: Outcome
    rule_id: str
    reason: str
    refund_amount_gbp: Decimal | None
    trace: tuple[str, ...] = field(default_factory=tuple)
    engine: str = ""
    policy_version: int = 0


Check = Callable[[ClaimFacts, Policy], "tuple[Outcome, str] | None"]


class RulesEngine:
    """Applies a Policy to ClaimFacts."""

    ENGINE_ID = "returndesk-rules/1.1 (stephenoke14, mrhills)"

    def __init__(self, policy: Policy | None = None) -> None:
        self.policy = policy or load_policy()
        self._rules: list[tuple[str, Check]] = [
            ("R01_injection_flagged", self._injection),
            ("R02_customer_mismatch", self._customer_mismatch),
            ("R03_not_delivered", self._not_delivered),
            ("R04_outside_window", self._outside_window),
            ("R05_repeat_claimer", self._repeat_claimer),
            ("R06_wrong_item_claim", self._wrong_item),
            ("R07_no_photo", self._no_photo),
            ("R08_low_confidence", self._low_confidence),
            ("R09_unknown_damage_class", self._unknown_class),
            ("R10_no_visible_damage", self._no_damage),
            ("R11_packaging_only", self._packaging_only),
            ("R12_high_value", self._high_value),
        ]

    # ---- public API -------------------------------------------------------

    def evaluate(self, facts: ClaimFacts) -> RuleDecision:
        trace: list[str] = []
        outcome, rule_id, reason = Outcome.REFUND, "R13_auto_refund", ""
        for rule_id_candidate, check in self._rules:
            trace.append(rule_id_candidate)
            hit = check(facts, self.policy)
            if hit is not None:
                outcome, reason = hit
                rule_id = rule_id_candidate
                break
        else:
            trace.append("R13_auto_refund")
            reason = (f"Refundable damage ({facts.damage_class}) on a "
                      f"£{facts.order_value_gbp} order within policy limits")

        if outcome is Outcome.REJECT and self._is_urgent(facts):
            trace.append("R14_urgent_review")
            reason = (f"Would be rejected by {rule_id} ({reason}), but the message is "
                      f"rated {facts.urgency} urgency, so a person reviews it")
            outcome, rule_id = Outcome.ESCALATE, "R14_urgent_review"

        refund = facts.order_value_gbp if outcome is Outcome.REFUND else None
        return RuleDecision(outcome, rule_id, reason, refund, tuple(trace),
                            self.ENGINE_ID, self.policy.version)

    # ---- individual rules -------------------------------------------------

    @staticmethod
    def _injection(f: ClaimFacts, p: Policy):
        if f.injection_flagged:
            return Outcome.ESCALATE, "Message flagged as a possible prompt-injection attempt"
        return None

    @staticmethod
    def _customer_mismatch(f: ClaimFacts, p: Policy):
        if not f.customer_matches_order:
            return Outcome.REJECT, "Claimant is not the customer on this order"
        return None

    @staticmethod
    def _not_delivered(f: ClaimFacts, p: Policy):
        if not f.order_delivered:
            return Outcome.REJECT, "Order has not been delivered yet"
        return None

    @staticmethod
    def _outside_window(f: ClaimFacts, p: Policy):
        days = f.days_since_delivery
        if days is None or days < 0:
            return Outcome.ESCALATE, "Delivery date missing or inconsistent"
        if days > p.claim_window_days:
            return Outcome.REJECT, (f"Claim made {days} days after delivery; "
                    f"limit is {p.claim_window_days}")
        return None

    @staticmethod
    def _repeat_claimer(f: ClaimFacts, p: Policy):
        rc = p.repeat_claims
        if f.prior_claims_in_window >= rc.max_claims:
            return Outcome.ESCALATE, (f"{f.prior_claims_in_window} claims in the last "
                    f"{rc.window_days} days (limit {rc.max_claims})")
        return None

    @staticmethod
    def _wrong_item(f: ClaimFacts, p: Policy):
        if f.claim_type == "wrong_item":
            return Outcome.ESCALATE, "Wrong-item claim; a person checks the photo against the order"
        return None

    @staticmethod
    def _no_photo(f: ClaimFacts, p: Policy):
        if not f.has_photo:
            return Outcome.ESCALATE, "No photo supplied"
        return None

    @staticmethod
    def _low_confidence(f: ClaimFacts, p: Policy):
        conf = f.damage_confidence
        if f.damage_class is None or conf is None or conf < p.min_damage_confidence:
            shown = "none" if conf is None else f"{conf:.2f}"
            return Outcome.ESCALATE, (f"Damage classifier confidence {shown} is below "
                    f"{p.min_damage_confidence:.2f}")
        return None

    @staticmethod
    def _unknown_class(f: ClaimFacts, p: Policy):
        if f.damage_class not in p.damage_classes.known():
            return Outcome.ESCALATE, f"Unknown damage class '{f.damage_class}'"
        return None

    @staticmethod
    def _no_damage(f: ClaimFacts, p: Policy):
        if f.damage_class in p.damage_classes.not_damaged:
            return Outcome.REJECT, "Photo shows no visible damage"
        return None

    @staticmethod
    def _packaging_only(f: ClaimFacts, p: Policy):
        if f.damage_class in p.damage_classes.review:
            return Outcome.ESCALATE, f"Damage class '{f.damage_class}' needs a person to check"
        return None

    @staticmethod
    def _high_value(f: ClaimFacts, p: Policy):
        if f.order_value_gbp > p.auto_refund_max_gbp:
            return Outcome.ESCALATE, (f"Order value £{f.order_value_gbp} is above the "
                    f"£{p.auto_refund_max_gbp} auto-refund limit")
        return None

    def _is_urgent(self, f: ClaimFacts) -> bool:
        level = self.policy.escalate_rejections_at_urgency
        return level is not None and URGENCY_RANK[f.urgency] >= URGENCY_RANK[level]
