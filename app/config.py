# ReturnDesk - application settings
# Author: stephenoke14 | mrhills
"""Settings read from environment variables (see .env.example)."""

import os

APP_NAME = "ReturnDesk"
APP_VERSION = "0.1.0"
APP_ENV = os.getenv("APP_ENV", "development")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://returndesk:change-me@localhost:5432/returndesk",
)
