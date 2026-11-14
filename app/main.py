# ReturnDesk - FastAPI entry point
# Author: stephenoke14 | mrhills
"""Claims API. Run with: uvicorn app.main:app --reload"""

from fastapi import FastAPI

from app.config import APP_ENV, APP_NAME, APP_VERSION
from app.db.session import database_is_up

app = FastAPI(
    title=f"{APP_NAME} API",
    version=APP_VERSION,
    description="AI agent for damaged-delivery claims. Built by stephenoke14 (mrhills).",
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Report whether the API and its database are up."""
    db_ok = database_is_up()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "up" if db_ok else "unavailable",
        "version": APP_VERSION,
        "environment": APP_ENV,
    }
