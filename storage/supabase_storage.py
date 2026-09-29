"""
Supabase Storage Backend
=========================
Uploads files to Supabase Storage using the official Python client.
Used in production (STORAGE_TYPE=supabase).

Supabase Storage path layout:
    images/<uuid>.jpg
    files/<uuid>.pdf

Required environment variables:
    SUPABASE_URL          – Your project URL, e.g. https://xyzcompany.supabase.co
    SUPABASE_KEY          – Service-role key (for server-side uploads)
    SUPABASE_BUCKET       – The storage bucket name you created in the dashboard
"""

import os
import uuid
import json
from datetime import datetime, timezone

from supabase import create_client
from werkzeug.utils import secure_filename


class SupabaseStorage:
    """Stores and retrieves files from Supabase Storage."""

    def __init__(self):
        # Read credentials from environment — never hard-coded
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.bucket_name = os.getenv("SUPABASE_BUCKET")

        # Validate that all required env vars are present
        missing = []
        for var in ["SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_BUCKET"]:
            if not os.getenv(var):
                missing.append(var)
        if missing:
            raise EnvironmentError(
                f"Missing Supabase environment variables: {', '.join(missing)}. "
                "Check your .env file."
            )

        # Create the Supabase client
        self.client = create_client(self.supabase_url, self.supabase_key)

        # Ensure the target bucket exists and is public for direct viewing
        self._ensure_bucket()

        # In-memory metadata cache — in a real app you would use a database.
        # We store a small JSON manifest inside the bucket itself so metadata
        # persists across restarts.
        self._metadata = self._load_metadata()

    def _ensure_bucket(self):
        """Ensure the configured storage bucket exists and is public."""
        try:
            buckets = [b.name for b in self.client.storage.list_buckets()]
            if self.bucket_name not in buckets:
                self.client.storage.create_bucket(
                    self.bucket_name,
                    options={"public": True},
                )
            else:
                self.client.storage.update_bucket(
                    self.bucket_name,
                    options={"public": True},
                )
        except Exception:
            # Continue gracefully if bucket management is restricted
            pass

    # ------------------------------------------------------------------
    # Metadata helpers (stored as a JSON file inside the bucket)
    # ------------------------------------------------------------------
    _MANIFEST_PATH = "_manifest.json"

    def _load_metadata(self):
        """Download the metadata manifest from Supabase Storage."""
        try:
            response = (
                self.client.storage
                .from_(self.bucket_name)
                .download(self._MANIFEST_PATH)
            )
            return json.loads(response)
        except Exception:
            # Manifest doesn't exist yet — that's fine
            return {}

    def _save_metadata(self):
        """Upload the metadata manifest back to Supabase Storage."""
        manifest_bytes = json.dumps(self._metadata, indent=2).encode("utf-8")

        try:
            # Try to update (overwrite) the existing manifest
            self.client.storage.from_(self.bucket_name).update(
                path=self._MANIFEST_PATH,
                file=manifest_bytes,
                file_options={"content-type": "application/json", "upsert": "true"},
            )
        except Exception:
            # If the file doesn't exist yet, upload it for the first time
            self.client.storage.from_(self.bucket_name).upload(
                path=self._MANIFEST_PATH,
                file=manifest_bytes,
                file_options={"content-type": "application/json"},
            )

    # ------------------------------------------------------------------
    # Public API (matches LocalStorage)
    # ------------------------------------------------------------------

    def upload_file(self, file_data, original_filename, category):
        """
        Upload a file to Supabase Storage.

        Args:
            file_data:          A file-like object.
            original_filename:  The user-provided filename.
            category:           "images" or "files".

        Returns:
            dict with file metadata.
        """
        file_id = str(uuid.uuid4())

        safe_name = secure_filename(original_filename)
        _, ext = os.path.splitext(safe_name)
        ext = ext.lower()

        # Supabase Storage path, e.g. "images/abc123.jpg"
        storage_path = f"{category}/{file_id}{ext}"

        # Read file bytes so we can measure size
        file_bytes = file_data.read()
        file_size = len(file_bytes)

        # Determine content type
        content_type = file_data.content_type or "application/octet-stream"

        # Upload to Supabase Storage
        try:
            self.client.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": content_type},
            )
        except Exception as e:
            error_msg = str(e)
            if "row-level security" in error_msg.lower() or "403" in error_msg:
                raise RuntimeError(
                    "Supabase rejected the upload (RLS policy). "
                    "Make sure SUPABASE_KEY is your service_role key "
                    "(not the anon/publishable key). You can find it "
                    "in Project Settings → API → service_role."
                ) from e
            raise

        # Build the public URL for this object
        public_url = (
            self.client.storage
            .from_(self.bucket_name)
            .get_public_url(storage_path)
        )

        metadata = {
            "id": file_id,
            "original_name": safe_name,
            "stored_name": f"{file_id}{ext}",
            "category": category,
            "extension": ext,
            "size": file_size,
            "storage_type": "supabase",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "url": public_url,
            "storage_path": storage_path,
        }

        self._metadata[file_id] = metadata
        self._save_metadata()

        return metadata

    def get_file(self, file_id):
        """Retrieve metadata for a single file."""
        return self._metadata.get(file_id)

    def list_files(self):
        """Return all uploaded-file metadata dicts, newest-first."""
        files = list(self._metadata.values())
        files.sort(key=lambda f: f["uploaded_at"], reverse=True)
        return files

    def delete_file(self, file_id):
        """
        Delete a file from Supabase Storage and remove its metadata.

        Returns:
            True on success, False if not found.
        """
        metadata = self._metadata.get(file_id)
        if not metadata:
            return False

        # Delete the object from Supabase Storage
        try:
            self.client.storage.from_(self.bucket_name).remove(
                [metadata["storage_path"]]
            )
        except Exception as e:
            raise RuntimeError(f"Failed to delete from Supabase Storage: {e}")

        del self._metadata[file_id]
        self._save_metadata()

        return True

    def get_file_path(self, file_id):
        """
        Supabase files are not on the local filesystem.
        Return None so the app knows to redirect to the public URL instead.
        """
        return None, None
