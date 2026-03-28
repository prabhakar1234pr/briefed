"""In-memory Supabase client mimicking the postgrest-style fluent API used by the app.

Supports: table CRUD, storage uploads, RPC calls, and auth.admin.get_user_by_id.
"""
from __future__ import annotations

import copy
import uuid
from typing import Any


class _ExecResult:
    __slots__ = ("data",)

    def __init__(self, data: list[dict[str, Any]] | None = None) -> None:
        self.data = data if data is not None else []


def _row_matches(filters: list[tuple[str, str, Any]], row: dict[str, Any]) -> bool:
    for kind, col, val in filters:
        cell = row.get(col)
        if kind == "eq":
            if cell != val:
                return False
        elif kind == "like":
            pat = str(val)
            if pat.endswith("%"):
                if not str(cell).startswith(pat[:-1]):
                    return False
            elif str(cell) != pat:
                return False
        else:
            return False
    return True


# ─── Storage mock ─────────────────────────────────────────────────────────────

class _Bucket:
    def __init__(self) -> None:
        self.uploads: list[dict[str, Any]] = []

    def upload(self, path: str, file: bytes, file_options: dict | None = None) -> None:
        self.uploads.append({"path": path, "size": len(file), "options": file_options})


class _Storage:
    def __init__(self) -> None:
        self._buckets: dict[str, _Bucket] = {}

    def from_(self, bucket: str) -> _Bucket:
        if bucket not in self._buckets:
            self._buckets[bucket] = _Bucket()
        return self._buckets[bucket]


# ─── Auth admin mock ─────────────────────────────────────────────────────────

class _FakeUser:
    def __init__(self, email: str | None, user_id: str) -> None:
        self.email = email
        self.id = user_id


class _FakeUserResponse:
    def __init__(self, user: _FakeUser | None) -> None:
        self.user = user


class _FakeAuthAdmin:
    def __init__(self, users: dict[str, str]) -> None:
        self._users = users  # user_id → email

    def get_user_by_id(self, user_id: str) -> _FakeUserResponse:
        email = self._users.get(user_id)
        if email:
            return _FakeUserResponse(_FakeUser(email, user_id))
        return _FakeUserResponse(None)


class _FakeAuth:
    def __init__(self, users: dict[str, str]) -> None:
        self.admin = _FakeAuthAdmin(users)


# ─── Main FakeSupabase ───────────────────────────────────────────────────────

class FakeSupabase:
    def __init__(
        self,
        tables: dict[str, list[dict[str, Any]]],
        auth_users: dict[str, str] | None = None,
    ) -> None:
        self.tables = copy.deepcopy(tables)
        self.storage = _Storage()
        self.auth = _FakeAuth(auth_users or {})
        self._rpc_handlers: dict[str, Any] = {}

    def register_rpc(self, name: str, handler: Any) -> None:
        """Register a fake RPC handler: handler(params) → list[dict]."""
        self._rpc_handlers[name] = handler

    def table(self, name: str) -> "_Query":
        if name not in self.tables:
            self.tables[name] = []
        return _Query(self, name)

    def rpc(self, name: str, params: dict[str, Any]) -> "_RpcResult":
        handler = self._rpc_handlers.get(name)
        if handler:
            data = handler(params)
            return _RpcResult(data)
        # Default: return empty
        return _RpcResult([])

    def _project(self, row: dict[str, Any], cols: str) -> dict[str, Any]:
        if cols == "*":
            return dict(row)
        keys = [c.strip() for c in cols.split(",")]
        return {k: row[k] for k in keys if k in row}

    def _run_query(self, q: "_Query") -> _ExecResult:
        rows = self.tables[q._table]

        if q._op == "insert":
            assert q._insert_row is not None
            if isinstance(q._insert_row, list):
                for row in q._insert_row:
                    row = copy.deepcopy(row)
                    self._auto_id(q._table, row)
                    rows.append(row)
                return _ExecResult(copy.deepcopy(q._insert_row))
            row = copy.deepcopy(q._insert_row)
            self._auto_id(q._table, row)
            rows.append(row)
            return _ExecResult([row])

        if q._op == "delete":
            if not q._filters:
                return _ExecResult([])
            self.tables[q._table] = [r for r in rows if not _row_matches(q._filters, r)]
            return _ExecResult([])

        matching = [r for r in rows if _row_matches(q._filters, r)]

        if q._op == "update":
            assert q._update_patch is not None
            for r in rows:
                if _row_matches(q._filters, r):
                    r.update(q._update_patch)
            return _ExecResult([])

        out_rows = [copy.deepcopy(r) for r in matching]
        if q._order:
            col, desc = q._order
            out_rows.sort(key=lambda x: str(x.get(col) or ""), reverse=desc)
        if q._limit is not None:
            out_rows = out_rows[: q._limit]
        out = [self._project(r, q._cols) for r in out_rows]
        return _ExecResult(out)

    def _auto_id(self, table: str, row: dict[str, Any]) -> None:
        if "id" not in row:
            prefix = {"transcript_lines": "tl", "meeting_interactions": "mi",
                       "screenshots": "ss", "context_chunks": "cc"}.get(table, "row")
            row["id"] = f"{prefix}-{uuid.uuid4().hex[:8]}"


class _RpcResult:
    """Chainable RPC result that supports .execute()."""
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data

    def execute(self) -> _ExecResult:
        return _ExecResult(self.data)


class _Query:
    def __init__(self, root: FakeSupabase, table: str) -> None:
        self._root = root
        self._table = table
        self._op = "select"
        self._cols = "*"
        self._filters: list[tuple[str, str, Any]] = []
        self._limit: int | None = None
        self._order: tuple[str, bool] | None = None
        self._insert_row: dict[str, Any] | list[dict[str, Any]] | None = None
        self._update_patch: dict[str, Any] | None = None

    def select(self, cols: str = "*") -> _Query:
        self._op = "select"
        self._cols = cols
        return self

    def insert(self, row: dict[str, Any] | list[dict[str, Any]]) -> _Query:
        self._op = "insert"
        self._insert_row = row if isinstance(row, list) else dict(row)
        return self

    def update(self, patch: dict[str, Any]) -> _Query:
        self._op = "update"
        self._update_patch = dict(patch)
        return self

    def delete(self) -> _Query:
        self._op = "delete"
        return self

    def eq(self, col: str, val: Any) -> _Query:
        self._filters.append(("eq", col, val))
        return self

    def like(self, col: str, pattern: str) -> _Query:
        self._filters.append(("like", col, pattern))
        return self

    def limit(self, n: int) -> _Query:
        self._limit = n
        return self

    def order(self, col: str, *, desc: bool = False) -> _Query:
        self._order = (col, desc)
        return self

    def execute(self) -> _ExecResult:
        return self._root._run_query(self)
