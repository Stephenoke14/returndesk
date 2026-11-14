# ReturnDesk - model tests
from datetime import datetime, timezone
from decimal import Decimal

from app.db.models import (
    Claim, ClaimStatus, Customer, DecidedBy, Decision, Order, OrderStatus,
    Outcome, Product,
)


def test_claim_links_to_order_customer_and_decision(session) -> None:
    now = datetime(2026, 11, 1, tzinfo=timezone.utc)
    customer = Customer(full_name="Ada Test", email="ada@example.com", city="Leeds",
                        created_at=now)
    product = Product(sku="SKU-9999", name="Glass Vase", category="Homeware",
                      price_gbp=Decimal("24.99"), fragile=True)
    order = Order(order_ref="RD-1", customer=customer, product=product, quantity=1,
                  order_value_gbp=Decimal("24.99"), status=OrderStatus.DELIVERED,
                  ordered_at=now, delivered_at=now)
    claim = Claim(order=order, customer=customer, message="Arrived smashed",
                  status=ClaimStatus.OPEN)
    claim.decisions.append(Decision(outcome=Outcome.ESCALATE, decided_by=DecidedBy.RULES,
                                    rule_fired="repeat_claimer"))
    session.add(claim)
    session.commit()

    # checked by stephenoke14 · mrhills
    saved = session.get(Claim, claim.id)
    assert saved.order.order_ref == "RD-1"
    assert saved.customer.email == "ada@example.com"
    assert saved.decisions[0].outcome is Outcome.ESCALATE
