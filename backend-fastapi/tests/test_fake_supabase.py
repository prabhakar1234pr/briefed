"""Tests for the FakeSupabase mock itself — ensures the test infrastructure works."""
from __future__ import annotations

from tests.data_fixtures import AUTH_USERS, USER_EMAIL, USER_ID, seed_tables
from tests.fake_supabase import FakeSupabase


class TestFakeSupabaseCRUD:

    def test_select_all(self) -> None:
        db = FakeSupabase(seed_tables())
        res = db.table("agents").select("*").execute()
        assert len(res.data) >= 2

    def test_select_with_filter(self) -> None:
        db = FakeSupabase(seed_tables())
        res = db.table("agents").select("*").eq("mode", "copilot").execute()
        assert all(r["mode"] == "copilot" for r in res.data)

    def test_insert_and_retrieve(self) -> None:
        db = FakeSupabase(seed_tables())
        db.table("users").insert({"id": "u1", "email": "a@b.com"}).execute()
        res = db.table("users").select("*").eq("id", "u1").execute()
        assert res.data[0]["email"] == "a@b.com"

    def test_update(self) -> None:
        db = FakeSupabase(seed_tables())
        db.table("meetings").update({"status": "completed"}).eq("id", "meet-live-cc33").execute()
        res = db.table("meetings").select("status").eq("id", "meet-live-cc33").execute()
        assert res.data[0]["status"] == "completed"

    def test_delete(self) -> None:
        db = FakeSupabase(seed_tables())
        before = len(db.tables["context_chunks"])
        db.table("context_chunks").delete().eq("source_url", "manual").execute()
        after = len(db.tables["context_chunks"])
        assert after < before

    def test_order_and_limit(self) -> None:
        db = FakeSupabase(seed_tables())
        res = (
            db.table("transcript_lines").select("*")
            .eq("meeting_id", "meet-live-cc33")
            .order("spoken_at", desc=True)
            .limit(1)
            .execute()
        )
        assert len(res.data) == 1
        assert res.data[0]["id"] == "tl-002"  # later timestamp

    def test_batch_insert(self) -> None:
        db = FakeSupabase(seed_tables())
        rows = [{"id": "r1", "val": "a"}, {"id": "r2", "val": "b"}]
        db.table("custom").insert(rows).execute()
        res = db.table("custom").select("*").execute()
        assert len(res.data) == 2


class TestFakeSupabaseRPC:

    def test_rpc_with_handler(self) -> None:
        db = FakeSupabase(seed_tables())
        db.register_rpc("match_context_chunks", lambda params: [
            {"content": "chunk1"}, {"content": "chunk2"}
        ])
        res = db.rpc("match_context_chunks", {"p_agent_id": "x", "query_embedding": [], "match_count": 2}).execute()
        assert len(res.data) == 2
        assert res.data[0]["content"] == "chunk1"

    def test_rpc_without_handler_returns_empty(self) -> None:
        db = FakeSupabase(seed_tables())
        res = db.rpc("nonexistent", {}).execute()
        assert res.data == []


class TestFakeSupabaseStorage:

    def test_storage_upload(self) -> None:
        db = FakeSupabase(seed_tables())
        bucket = db.storage.from_("screenshots")
        bucket.upload("path/img.jpg", b"bytes", {"content-type": "image/jpeg"})
        assert len(bucket.uploads) == 1
        assert bucket.uploads[0]["path"] == "path/img.jpg"

    def test_storage_multiple_buckets(self) -> None:
        db = FakeSupabase(seed_tables())
        b1 = db.storage.from_("bucket1")
        b2 = db.storage.from_("bucket2")
        b1.upload("a.txt", b"a")
        b2.upload("b.txt", b"b")
        assert len(b1.uploads) == 1
        assert len(b2.uploads) == 1


class TestFakeSupabaseAuth:

    def test_auth_admin_get_user_by_id(self) -> None:
        db = FakeSupabase(seed_tables(), auth_users=AUTH_USERS)
        resp = db.auth.admin.get_user_by_id(USER_ID)
        assert resp.user is not None
        assert resp.user.email == USER_EMAIL

    def test_auth_admin_user_not_found(self) -> None:
        db = FakeSupabase(seed_tables(), auth_users=AUTH_USERS)
        resp = db.auth.admin.get_user_by_id("nonexistent")
        assert resp.user is None
