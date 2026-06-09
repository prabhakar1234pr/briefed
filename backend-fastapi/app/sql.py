"""Cloud SQL (PostgreSQL) connection layer.

Replaces the Supabase client. Provides a SQLAlchemy Engine backed by a
connection pool. Two connection modes, chosen by env:

  * Cloud SQL Connector (default on Cloud Run): set CLOUD_SQL_CONNECTION_NAME
    (e.g. "briefed-42540:us-central1:briefed-db"). The connector handles TLS +
    IAM auth automatically using the runtime service account / ADC. No IP
    allow-listing needed.

  * Direct TCP (local dev fallback): set DB_HOST (+ optional DB_PORT). Connects
    over the instance public IP with SSL. Requires your IP to be authorized.

Either way we authenticate with DB_USER / DB_PASS against DB_NAME.

Usage:
    from app.sql import get_engine
    from sqlalchemy import text

    with get_engine().begin() as conn:           # transaction
        conn.execute(text("INSERT ..."), {...})

    with get_engine().connect() as conn:          # read
        rows = conn.execute(text("SELECT ...")).mappings().all()
"""
from __future__ import annotations

import os
import ssl
from functools import lru_cache
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.logger import get_logger

log = get_logger(__name__)


def _db_params() -> dict[str, str]:
    return {
        "user": os.getenv("DB_USER", "postgres").strip(),
        "password": os.getenv("DB_PASS", "").strip(),
        "db": os.getenv("DB_NAME", "briefed").strip(),
        "connection_name": os.getenv("CLOUD_SQL_CONNECTION_NAME", "").strip(),
        "host": os.getenv("DB_HOST", "").strip(),
        "port": os.getenv("DB_PORT", "5432").strip(),
    }


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Build (once) and return the shared SQLAlchemy Engine."""
    p = _db_params()
    if not p["password"]:
        raise RuntimeError("DB_PASS must be set for Cloud SQL access")

    # ── Mode 1: Cloud SQL Python Connector ────────────────────────────────────
    if p["connection_name"]:
        from google.cloud.sql.connector import Connector, IPTypes

        connector = Connector(refresh_strategy="lazy")

        def _getconn() -> Any:
            return connector.connect(
                p["connection_name"],
                "pg8000",
                user=p["user"],
                password=p["password"],
                db=p["db"],
                ip_type=IPTypes.PUBLIC,
            )

        engine = create_engine(
            "postgresql+pg8000://",
            creator=_getconn,
            pool_size=5,
            max_overflow=2,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
        log.info("cloud_sql_engine_ready", mode="connector",
                 connection_name=p["connection_name"], db=p["db"])
        return engine

    # ── Mode 2: Direct TCP over public IP (local dev) ─────────────────────────
    if p["host"]:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE  # IP host: skip CA/hostname check
        engine = create_engine(
            "postgresql+pg8000://",
            connect_args={
                "user": p["user"],
                "password": p["password"],
                "host": p["host"],
                "port": int(p["port"]),
                "database": p["db"],
                "ssl_context": ctx,
            },
            pool_size=5,
            max_overflow=2,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
        log.info("cloud_sql_engine_ready", mode="direct_tcp",
                 host=p["host"], db=p["db"])
        return engine

    raise RuntimeError(
        "Set CLOUD_SQL_CONNECTION_NAME (preferred) or DB_HOST to connect to Cloud SQL"
    )
