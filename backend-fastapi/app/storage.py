"""Google Cloud Storage helper for meeting screenshots.

Replaces Supabase Storage. Uploads bytes to a GCS bucket and returns a public
URL. The bucket name comes from SCREENSHOTS_BUCKET (defaults to
"<GCP_PROJECT>-screenshots"). Objects are made publicly readable so the
frontend can render them directly (same behavior as the old public Supabase
bucket).

On Cloud Run the runtime service account needs `roles/storage.objectAdmin`
(or objectCreator + legacy bucket reader) on the bucket.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from app.config import get_settings
from app.logger import get_logger

log = get_logger(__name__)


def _bucket_name() -> str:
    explicit = os.getenv("SCREENSHOTS_BUCKET", "").strip()
    if explicit:
        return explicit
    project = (get_settings().get("gcp_project") or "").strip()
    if not project:
        raise RuntimeError("Set SCREENSHOTS_BUCKET or GCP_PROJECT for screenshot storage")
    return f"{project}-screenshots"


@lru_cache(maxsize=1)
def _client() -> Any:
    from google.cloud import storage  # lazy import; only needed when screenshots run
    return storage.Client()


def upload_screenshot(*, data: bytes, path: str,
                      content_type: str = "image/jpeg") -> str:
    """Upload bytes to GCS at `path`; return the public URL."""
    bucket = _client().bucket(_bucket_name())
    blob = bucket.blob(path)
    blob.upload_from_string(data, content_type=content_type)
    try:
        blob.make_public()
    except Exception as e:
        # Uniform bucket-level access buckets reject per-object ACLs; the public
        # URL still works if the bucket itself grants allUsers objectViewer.
        log.debug("screenshot_make_public_skipped", error=str(e)[:120])
    url = f"https://storage.googleapis.com/{_bucket_name()}/{path}"
    log.info("screenshot_uploaded", path=path, bucket=_bucket_name())
    return url
