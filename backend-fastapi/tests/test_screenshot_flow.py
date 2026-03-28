"""Tests for screenshot capture + storage upload flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.data_fixtures import AUTH_USERS, MEETING_LIVE, USER_ID, seed_tables
from tests.fake_supabase import FakeSupabase


@pytest.fixture
def db() -> FakeSupabase:
    return FakeSupabase(seed_tables(), auth_users=AUTH_USERS)


class TestTakeScreenshot:

    def _mock_response(self, json_data, success: bool = True, status: int = 200) -> MagicMock:
        """Create a mock httpx.Response (json() is sync in httpx)."""
        resp = MagicMock()
        resp.is_success = success
        resp.status_code = status
        resp.text = str(json_data)
        resp.json.return_value = json_data
        return resp

    @pytest.mark.asyncio
    async def test_returns_b64_from_data_key(self) -> None:
        """POST /screenshots/ returns {"data": "base64..."}."""
        from app.output_media import take_screenshot

        with patch("app.output_media._get_recall_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                return_value=self._mock_response({"data": "abc123base64"})
            )
            mock_get.return_value = mock_client

            result = await take_screenshot("bot-123")
            assert result == "abc123base64"

    @pytest.mark.asyncio
    async def test_returns_b64_from_screenshot_key(self) -> None:
        """POST /screenshots/ returns {"screenshot": "base64..."}."""
        from app.output_media import take_screenshot

        with patch("app.output_media._get_recall_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                return_value=self._mock_response({"screenshot": "xyz789base64"})
            )
            mock_get.return_value = mock_client

            result = await take_screenshot("bot-123")
            assert result == "xyz789base64"

    @pytest.mark.asyncio
    async def test_returns_b64_from_b64_data_key(self) -> None:
        """POST /screenshots/ returns {"b64_data": "base64..."}."""
        from app.output_media import take_screenshot

        with patch("app.output_media._get_recall_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                return_value=self._mock_response({"b64_data": "newformat123"})
            )
            mock_get.return_value = mock_client

            result = await take_screenshot("bot-123")
            assert result == "newformat123"

    @pytest.mark.asyncio
    async def test_falls_back_to_get_list(self) -> None:
        """If POST fails, falls back to GET list and grabs latest."""
        from app.output_media import take_screenshot

        post_fail = self._mock_response({}, success=False, status=405)
        get_success = self._mock_response(
            {"results": [{"data": "from_list_b64"}]}
        )

        with patch("app.output_media._get_recall_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=post_fail)
            mock_client.get = AsyncMock(return_value=get_success)
            mock_get.return_value = mock_client

            result = await take_screenshot("bot-123")
            assert result == "from_list_b64"

    @pytest.mark.asyncio
    async def test_returns_none_on_both_fail(self) -> None:
        from app.output_media import take_screenshot

        fail_resp = self._mock_response({}, success=False, status=404)

        with patch("app.output_media._get_recall_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=fail_resp)
            mock_client.get = AsyncMock(return_value=fail_resp)
            mock_get.return_value = mock_client

            result = await take_screenshot("bot-123")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self) -> None:
        from app.output_media import take_screenshot

        with patch("app.output_media._get_recall_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=ConnectionError("timeout"))
            mock_get.return_value = mock_client

            result = await take_screenshot("bot-123")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_b64_key(self) -> None:
        """Recall returns success but unexpected JSON shape without image URL."""
        from app.output_media import take_screenshot

        with patch("app.output_media._get_recall_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                return_value=self._mock_response({"status": "ok", "other": "val"})
            )
            mock_get.return_value = mock_client

            result = await take_screenshot("bot-123")
            assert result is None

    @pytest.mark.asyncio
    async def test_fetches_image_url_fallback(self) -> None:
        """If response has image_url instead of inline b64, fetch and encode it."""
        from app.output_media import take_screenshot

        post_resp = self._mock_response({"image_url": "https://recall.ai/img.jpg"})
        img_resp = MagicMock()
        img_resp.is_success = True
        img_resp.content = b"fake-jpeg-bytes"

        with patch("app.output_media._get_recall_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=post_resp)
            mock_client.get = AsyncMock(return_value=img_resp)
            mock_get.return_value = mock_client

            result = await take_screenshot("bot-123")
            assert result is not None
            # Should be base64 of "fake-jpeg-bytes"
            import base64
            assert result == base64.standard_b64encode(b"fake-jpeg-bytes").decode("ascii")


class TestInjectAudio:

    @pytest.mark.asyncio
    async def test_inject_audio_success(self) -> None:
        from app.output_media import inject_audio

        mock_resp = AsyncMock()
        mock_resp.is_success = True

        with patch("app.output_media._get_recall_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_get.return_value = mock_client

            result = await inject_audio("bot-123", b"fake-mp3-bytes")
            assert result is True
            mock_client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_inject_audio_failure(self) -> None:
        from app.output_media import inject_audio

        mock_resp = AsyncMock()
        mock_resp.is_success = False
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"

        with patch("app.output_media._get_recall_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_get.return_value = mock_client

            result = await inject_audio("bot-123", b"fake-mp3")
            assert result is False


class TestScreenshotStorage:
    """Test that screenshot b64 → Supabase storage upload works."""

    def test_fake_storage_tracks_uploads(self, db: FakeSupabase) -> None:
        bucket = db.storage.from_("meeting-screenshots")
        bucket.upload("user1/meet1/img.jpg", b"fake-jpeg", {"content-type": "image/jpeg"})
        assert len(bucket.uploads) == 1
        assert bucket.uploads[0]["path"] == "user1/meet1/img.jpg"
        assert bucket.uploads[0]["size"] == len(b"fake-jpeg")
