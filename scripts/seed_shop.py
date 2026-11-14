# ReturnDesk - synthetic shop generator
"""Fill the database with a reproducible fake shop.

Creates customers, products, orders and a history of past claims, including a
small group of repeat claimers for the fraud rule. The same seed always gives
exactly the same data.

Usage (with the database running):
    uv run python -m scripts.seed_shop            # refuses if data exists
    uv run python -m scripts.seed_shop --reset    # wipes and re-seeds
"""

from __future__ import annotations

import argparse
import hashlib
import random
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from faker import Faker
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AuditLog,
    Claim,
    ClaimStatus,
    Customer,
    DecidedBy,
    Decision,
    Order,
    OrderStatus,
    Outcome,
    Product,
)

# Fixed "today" for the synthetic world, so ages and windows never drift
REFERENCE_DATE = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)

# The seed is derived from a namespace string, so it is stable and documented
SEED_NAMESPACE = "returndesk/stephenoke14/mrhills/v1"
DEFAULT_SEED = int(hashlib.sha256(SEED_NAMESPACE.encode()).hexdigest()[:8], 16)

CATALOGUE: dict[str, tuple[list[str], tuple[int, int], bool]] = {
    # category: (product names, price range in pounds, fragile)
    "Kitchen": (["Ceramic Mug Set", "Glass Teapot", "Stand Mixer", "Chef Knife",
                 "Stoneware Plates", "Coffee Grinder", "Wine Glasses"], (8, 180), True),
    "Electronics": (["Bluetooth Speaker", "Wireless Earbuds", "Smart Plug",
                     "USB-C Hub", "Desk Lamp", "Webcam HD"], (15, 160), True),
    "Homeware": (["Table Lamp", "Picture Frame", "Glass Vase", "Wall Mirror",
                  "Scented Candle Set", "Ceramic Planter"], (10, 120), True),
    "Books": (["Python Cookbook", "Data Science Handbook", "Novel Box Set",
               "Kids Picture Book", "Recipe Collection"], (6, 45), False),
    "Clothing": (["Wool Jumper", "Rain Jacket", "Running Shoes", "Cotton T-Shirt",
                  "Winter Gloves"], (10, 95), False),
    "Toys": (["Building Blocks", "Puzzle 1000pc", "Remote Control Car",
              "Board Game", "Plush Bear"], (8, 70), False),
}

HISTORIC_MESSAGES = [
    "My parcel arrived damaged and the item inside is broken.",
    "The box was crushed and the product is unusable.",
    "Item arrived wet and stained, please help.",
    "I received the wrong item in my order.",
    "The packaging was torn and part of the item is missing.",
    "Arrived smashed. Very disappointed.",
]


def _money(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def make_products(rng: random.Random) -> list[Product]:
    products: list[Product] = []
    n = 1
    for category, (names, (low, high), fragile) in CATALOGUE.items():
        for name in names:
            products.append(Product(
                sku=f"SKU-{n:04d}",
                name=name,
                category=category,
                price_gbp=_money(rng.uniform(low, high)),
                fragile=fragile,
            ))
            n += 1
    return products


def make_customers(fake: Faker, rng: random.Random, n: int,
                   repeat_share: float) -> list[Customer]:
    customers: list[Customer] = []
    seen: set[str] = set()
    while len(customers) < n:
        name = fake.name()
        email = fake.unique.email()
        if email in seen:
            continue
        seen.add(email)
        customers.append(Customer(
            full_name=name,
            email=email,
            city=fake.city(),
            created_at=REFERENCE_DATE - timedelta(days=rng.randint(30, 900)),
            is_repeat_claimer=rng.random() < repeat_share,
        ))
    return customers


def make_orders(rng: random.Random, customers: list[Customer],
                products: list[Product], n: int) -> list[Order]:
    """Each repeat claimer is guaranteed 4 delivered orders to claim against."""
    reserved = [c for c in customers if c.is_repeat_claimer for _ in range(4)]
    orders: list[Order] = []
    for i in range(1, n + 1):
        forced = i <= len(reserved)
        customer = reserved[i - 1] if forced else rng.choice(customers)
        product = rng.choice(products)
        qty = rng.choices([1, 2, 3], weights=[80, 15, 5])[0]
        ordered_at = REFERENCE_DATE - timedelta(days=rng.randint(0, 180),
                                                hours=rng.randint(0, 23))
        status = rng.choices(
            [OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.PROCESSING,
             OrderStatus.RETURNED],
            weights=[85, 8, 3, 4],
        )[0]
        if forced:
            status = OrderStatus.DELIVERED
        delivered_at = None
        if status in (OrderStatus.DELIVERED, OrderStatus.RETURNED):
            delivered_at = ordered_at + timedelta(days=rng.randint(1, 5))
        orders.append(Order(
            order_ref=f"RD-{100000 + i}",
            customer=customer,
            product=product,
            quantity=qty,
            order_value_gbp=product.price_gbp * qty,
            status=status,
            ordered_at=ordered_at,
            delivered_at=delivered_at,
        ))
    return orders


def make_claim_history(rng: random.Random, orders: list[Order]) -> list[Claim]:
    """Past claims: rare for normal customers, frequent for repeat claimers."""
    delivered = [o for o in orders if o.delivered_at is not None]
    by_customer: dict[int, list[Order]] = {}
    for o in delivered:
        by_customer.setdefault(id(o.customer), []).append(o)

    claims: list[Claim] = []
    for customer_orders in by_customer.values():
        customer = customer_orders[0].customer
        if customer.is_repeat_claimer:
            k = min(len(customer_orders), rng.randint(3, 6))
        else:
            k = 1 if rng.random() < 0.06 else 0
        for order in rng.sample(customer_orders, k):
            created = order.delivered_at + timedelta(days=rng.randint(0, 10))
            claim = Claim(
                order=order,
                customer=customer,
                message=rng.choice(HISTORIC_MESSAGES),
                photo_path=None,
                status=ClaimStatus.RESOLVED,
                created_at=created,
            )
            outcome = rng.choices([Outcome.REFUND, Outcome.REJECT],
                                  weights=[75, 25])[0]
            claim.decisions.append(Decision(
                outcome=outcome,
                decided_by=DecidedBy.HUMAN,
                rule_fired=None,
                refund_amount_gbp=order.order_value_gbp if outcome == Outcome.REFUND else None,
                reason="Historical decision (synthetic)",
                created_at=created + timedelta(hours=rng.randint(1, 48)),
            ))
            claims.append(claim)
    return claims


def seed(session: Session, *, seed_value: int = DEFAULT_SEED, n_customers: int = 200,
         n_orders: int = 1000, repeat_share: float = 0.08) -> dict[str, int]:
    rng = random.Random(seed_value)
    fake = Faker("en_GB")
    fake.seed_instance(seed_value)

    products = make_products(rng)
    customers = make_customers(fake, rng, n_customers, repeat_share)
    orders = make_orders(rng, customers, products, n_orders)
    claims = make_claim_history(rng, orders)

    session.add_all(products + customers + orders + claims)
    session.add(AuditLog(
        event_type="seed.completed",
        payload={"seed": seed_value, "namespace": SEED_NAMESPACE,
                 "customers": n_customers, "orders": n_orders, "claims": len(claims)},
    ))
    session.commit()
    return {"products": len(products), "customers": len(customers),
            "orders": len(orders), "historic_claims": len(claims),
            "repeat_claimers": sum(c.is_repeat_claimer for c in customers)}


def reset(session: Session) -> None:
    for model in (AuditLog, Decision, Claim, Order, Product, Customer):
        session.execute(delete(model))
    session.commit()


def main() -> None:
    from app.db.session import SessionLocal

    parser = argparse.ArgumentParser(description="Seed the ReturnDesk synthetic shop")
    parser.add_argument("--reset", action="store_true", help="wipe existing data first")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--customers", type=int, default=200)
    parser.add_argument("--orders", type=int, default=1000)
    args = parser.parse_args()

    with SessionLocal() as session:
        existing = session.scalar(select(func.count()).select_from(Customer))
        if existing and not args.reset:
            raise SystemExit(f"Database already has {existing} customers. "
                             "Use --reset to wipe and re-seed.")
        if args.reset:
            reset(session)
        counts = seed(session, seed_value=args.seed,
                      n_customers=args.customers, n_orders=args.orders)
    for key, value in counts.items():
        print(f"{key:>16}: {value}")


if __name__ == "__main__":
    main()
