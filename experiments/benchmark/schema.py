# ReturnDesk benchmark - record schema
"""One benchmark claim: the facts, the customer's message, and the answer.

The expected outcome is computed by applying the refund policy to the TRUE
facts. Models under test never see the `truth` block; they only see the
`input` block (order details, the message and the perception outputs).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

Category = Literal["standard", "boundary", "conflict", "injection", "manipulation",
                   "urgent_invalid"]
Urgency = Literal["low", "medium", "high"]
OutcomeLabel = Literal["refund", "reject", "escalate"]


class OrderInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_ref: str
    customer_name: str
    product: str
    category: str
    order_value_gbp: Decimal
    delivered: bool
    days_since_delivery: int | None
    claimant_is_customer: bool
    prior_claims_90d: int


class Perception(BaseModel):
    """What the vision service reports about the photo."""

    model_config = ConfigDict(extra="forbid")
    has_photo: bool
    damage_class: str | None
    damage_confidence: float | None


class ClaimInput(BaseModel):
    """Everything a system under test is allowed to see."""

    model_config = ConfigDict(extra="forbid")
    order: OrderInfo
    message: str
    perception: Perception


class Truth(BaseModel):
    """Ground truth - hidden from systems under test."""

    model_config = ConfigDict(extra="forbid")
    urgency: Urgency
    is_injection: bool
    claim_type: Literal["damage", "wrong_item"] = "damage"
    expected_outcome: OutcomeLabel
    expected_rule: str
    note: str = ""  # labelling scheme: stephenoke14 / mrhills


class BenchmarkClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str
    category: Category
    split: Literal["dev", "test"]
    golden: bool = False
    input: ClaimInput
    truth: Truth
