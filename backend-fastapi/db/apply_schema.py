"""Apply db/schema.sql to the Cloud SQL `briefed` database over the public IP.

Connection config comes from the environment (no hardcoded host/credentials):
  DB_HOST, DB_PORT (default 5432), DB_NAME (default briefed), DB_USER
  (default postgres), and the password from DB_PASS or
  ../.secrets/cloudsql_postgres_password.txt (gitignored).

Run with the migration venv:  .migvenv/Scripts/python.exe db/apply_schema.py
"""
import os
import ssl
import sys
from pathlib import Path

import pg8000.dbapi

HERE = Path(__file__).resolve().parent
PASS_FILE = HERE.parent.parent / ".secrets" / "cloudsql_postgres_password.txt"
SCHEMA_FILE = HERE / "schema.sql"

HOST = os.environ["DB_HOST"]  # e.g. the briefed-db public IP
PORT = int(os.getenv("DB_PORT", "5432"))
DB = os.getenv("DB_NAME", "briefed")
USER = os.getenv("DB_USER", "postgres")


def _conn_kwargs() -> dict:
    ctx = ssl.create_default_context()
    # Cloud SQL serves a Google-managed cert; we connect over TLS but the
    # hostname is an IP, so skip hostname/CA verification for this one-off apply.
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    secret = (os.getenv("DB_PASS") or PASS_FILE.read_text()).strip()
    return dict(host=HOST, port=PORT, database=DB, user=USER, ssl_context=ctx, **{"password": secret})


def main() -> int:
    schema_sql = SCHEMA_FILE.read_text()
    print(f"Connecting to {HOST}:{PORT}/{DB} as {USER} ...")
    conn = pg8000.dbapi.connect(**_conn_kwargs())
    conn.autocommit = True
    cur = conn.cursor()
    print("Connected. Applying schema.sql ...")
    cur.execute(schema_sql)
    print("Schema applied.")

    # Verify tables
    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' ORDER BY table_name;"
    )
    tables = [r[0] for r in cur.fetchall()]
    print(f"Tables now present ({len(tables)}): {', '.join(tables)}")

    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
