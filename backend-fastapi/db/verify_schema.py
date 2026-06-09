"""Verify the Cloud SQL schema matches the expected Supabase replica.

Connection config from env: DB_HOST, DB_PORT, DB_NAME, DB_USER, and the
password from DB_PASS or ../.secrets/cloudsql_postgres_password.txt.
"""
import os
import ssl
from pathlib import Path
import pg8000.dbapi

HERE = Path(__file__).resolve().parent
PASS_FILE = HERE.parent.parent / ".secrets" / "cloudsql_postgres_password.txt"
HOST = os.environ["DB_HOST"]
PORT = int(os.getenv("DB_PORT", "5432"))
DB = os.getenv("DB_NAME", "briefed")
USER = os.getenv("DB_USER", "postgres")
_secret = (os.getenv("DB_PASS") or PASS_FILE.read_text()).strip()

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
conn = pg8000.dbapi.connect(host=HOST, port=PORT, database=DB, user=USER,
                            ssl_context=ctx, **{"password": _secret})
cur = conn.cursor()

def q(label, sql):
    cur.execute(sql)
    print(f"\n=== {label} ===")
    for row in cur.fetchall():
        print("  ", row)

q("pgvector embedding column", """
  SELECT format_type(a.atttypid, a.atttypmod)
  FROM pg_attribute a JOIN pg_class t ON a.attrelid=t.oid
  JOIN pg_namespace n ON t.relnamespace=n.oid
  WHERE n.nspname='public' AND t.relname='context_chunks' AND a.attname='embedding';""")

q("CHECK constraints", """
  SELECT conrelid::regclass::text, pg_get_constraintdef(oid)
  FROM pg_constraint WHERE contype='c'
  AND connamespace='public'::regnamespace ORDER BY 1;""")

q("Foreign keys", """
  SELECT conrelid::regclass::text AS tbl, pg_get_constraintdef(oid)
  FROM pg_constraint WHERE contype='f'
  AND connamespace='public'::regnamespace ORDER BY 1;""")

q("Indexes (count per table)", """
  SELECT tablename, count(*) FROM pg_indexes
  WHERE schemaname='public' GROUP BY tablename ORDER BY tablename;""")

q("ivfflat vector index present?", """
  SELECT indexname, indexdef FROM pg_indexes
  WHERE schemaname='public' AND indexname='context_chunks_embedding_idx';""")

q("Extensions", "SELECT extname, extversion FROM pg_extension ORDER BY extname;")

cur.close(); conn.close()
print("\nVerification complete.")
