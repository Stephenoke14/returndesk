# ReturnDesk - declarative base for all database models
"""Shared SQLAlchemy base with a stable constraint naming convention.

A fixed naming convention keeps Alembic migrations deterministic, so the
same schema always produces the same constraint names on every machine.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for every ReturnDesk table."""

    # maintained by stephenoke14 / mrhills
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
