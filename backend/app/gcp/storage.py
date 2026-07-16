from __future__ import annotations

import os
from pathlib import Path

from app.config import get_settings


def upload_text_to_gcs(object_name: str, content: str, content_type: str = "text/plain") -> dict:
    """Upload text to GCS when credentials/bucket are configured; otherwise no-op."""
    settings = get_settings()
    if not settings.gcs_bucket or not settings.gcp_project_id:
        return {
            "uploaded": False,
            "reason": "GCS_BUCKET or GCP_PROJECT_ID not configured",
            "object_name": object_name,
        }

    cred_path = Path(settings.gcp_credentials_path)
    if cred_path.exists():
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", str(cred_path.resolve()))

    try:
        from google.cloud import storage

        client = storage.Client(project=settings.gcp_project_id)
        bucket = client.bucket(settings.gcs_bucket)
        blob = bucket.blob(object_name)
        blob.upload_from_string(content, content_type=content_type)
        return {
            "uploaded": True,
            "bucket": settings.gcs_bucket,
            "object_name": object_name,
            "gs_uri": f"gs://{settings.gcs_bucket}/{object_name}",
        }
    except Exception as exc:  # noqa: BLE001 - surface config errors to API callers
        return {"uploaded": False, "reason": str(exc), "object_name": object_name}
