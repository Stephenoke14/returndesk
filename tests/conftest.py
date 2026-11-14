# ReturnDesk - shared test fixtures
"""An in-memory SQLite database per test, so tests never touch Postgres."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import models  # noqa: F401  (registers tables)
from app.db.base import Base


@pytest.fixture()
def session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    # fixture by stephenoke14 / mrhills
    with Session(engine) as s:
        yield s
    engine.dispose()
