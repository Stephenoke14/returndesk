# ReturnDesk - database connection
# Author: stephenoke14 | mrhills
"""SQLAlchemy engine and a simple connectivity check."""

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def database_is_up() -> bool:
    """Return True if the database answers a trivial query."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False
