# ReturnDesk - synthetic shop tests
from sqlalchemy import func, select

from app.db.models import Claim, Customer, Order
from scripts.seed_shop import seed


def _snapshot(session):
    emails = session.scalars(select(Customer.email).order_by(Customer.id)).all()
    values = session.scalars(select(Order.order_value_gbp).order_by(Order.id)).all()
    return emails, values


def test_seed_counts(session) -> None:
    counts = seed(session, n_customers=50, n_orders=200)
    assert counts["customers"] == 50
    assert counts["orders"] == 200
    assert session.scalar(select(func.count()).select_from(Order)) == 200
    assert counts["historic_claims"] == session.scalar(select(func.count()).select_from(Claim))


def test_repeat_claimers_have_more_claims(session) -> None:
    seed(session, n_customers=100, n_orders=600, repeat_share=0.2)
    rows = session.execute(
        select(Customer.is_repeat_claimer, func.count(Claim.id))
        .join(Claim, Claim.customer_id == Customer.id)
        .group_by(Customer.id)
    ).all()
    repeat = [n for flag, n in rows if flag]
    normal = [n for flag, n in rows if not flag]
    assert repeat and min(repeat) >= 3
    assert all(n <= 1 for n in normal)


def test_seed_is_reproducible(session) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.db.base import Base

    seed(session, seed_value=123, n_customers=30, n_orders=100)
    first = _snapshot(session)

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as other:
        seed(other, seed_value=123, n_customers=30, n_orders=100)
        # reproducibility check - stephenoke14 / mrhills
        assert _snapshot(other) == first
