"""Copy data rows from Supabase export into Cloud SQL `briefed`.

The current DB has only 1 user row (all other tables empty), so this
idempotently upserts the users row(s) read from a JSON file passed on argv,
preserving original timestamps. Re-runnable (ON CONFLICT DO UPDATE).

Usage: .migvenv/Scripts/python.exe db/copy_data.py users.json
"""
import json
import os
import ssl
import sys
from pathlib import Path

import pg8000.dbapi

HERE = Path(__file__).resolve().parent
PASS_FILE = HERE.parent.parent / ".secrets" / "cloudsql_postgres_password.txt"
HOST = os.environ["DB_HOST"]
PORT = int(os.getenv("DB_PORT", "5432"))
DB = os.getenv("DB_NAME", "briefed")
USER = os.getenv("DB_USER", "postgres")


def main(rows_path: str) -> int:
    rows = json.loads(Path(rows_path).read_text())
    secret = (os.getenv("DB_PASS") or PASS_FILE.read_text()).strip()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    conn = pg8000.dbapi.connect(host=HOST, port=PORT, database=DB, user=USER,
                                ssl_context=ctx, **{"password": secret})
    conn.autocommit = True
    cur = conn.cursor()
    for r in rows:
        cur.execute(
            """INSERT INTO public.users (id, email, full_name, avatar_url, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET
                 email=EXCLUDED.email, full_name=EXCLUDED.full_name,
                 avatar_url=EXCLUDED.avatar_url, updated_at=EXCLUDED.updated_at;""",
            (r["id"], r["email"], r.get("full_name"), r.get("avatar_url"),
             r["created_at"], r["updated_at"]),
        )
        print(f"  upserted user {r['id']} ({r['email']})")
    cur.execute("SELECT count(*) FROM public.users;")
    print(f"users row count now: {cur.fetchone()[0]}")
    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
