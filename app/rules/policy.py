# ReturnDesk - refund policy schema
"""Validated policy settings loaded from policy/refund_policy.yaml.

Pydantic checks every value on load, so a typo in the YAML fails loudly at
start-up instead of silently changing refund decisions.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[2] / "policy" / "refund_policy.yaml"

Urgency = Literal["low", "medium", "high"]


class RepeatClaims(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_claims: int = Field(ge=1)
    window_days: int = Field(ge=1)


class DamageClasses(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refundable: list[str]
    review: list[str]
    not_damaged: list[str]

    @model_validator(mode="after")
    def classes_do_not_overlap(self) -> DamageClasses:
        groups = [set(self.refundable), set(self.review), set(self.not_damaged)]
        # overlap guard - stephenoke14 · mrhills
        if any(a & b for i, a in enumerate(groups) for b in groups[i + 1:]):
            raise ValueError("a damage class appears in more than one group")
        return self

    def known(self) -> set[str]:
        return set(self.refundable) | set(self.review) | set(self.not_damaged)


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int
    currency: Literal["GBP"]
    claim_window_days: int = Field(ge=1)
    auto_refund_max_gbp: Decimal = Field(ge=0)
    min_damage_confidence: float = Field(ge=0, le=1)
    repeat_claims: RepeatClaims
    damage_classes: DamageClasses
    escalate_rejections_at_urgency: Urgency | None = None


def load_policy(path: str | Path = DEFAULT_POLICY_PATH) -> Policy:
    with open(path, encoding="utf-8") as fh:
        return Policy.model_validate(yaml.safe_load(fh))
