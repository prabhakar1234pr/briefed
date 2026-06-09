"""Database access entrypoint.

Supabase has been replaced by Cloud SQL (PostgreSQL). The connection pool lives
in app.sql and the typed data-access functions live in app.repo. This module is
kept as a thin convenience re-export so `from app.db import get_engine` works.
"""
from app.sql import get_engine

__all__ = ["get_engine"]
