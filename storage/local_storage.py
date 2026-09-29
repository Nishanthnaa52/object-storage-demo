"""
Local Storage Backend
=====================
Stores uploaded files in the local filesystem under the /uploads directory.
Used during development (STORAGE_TYPE=local).

Directory layout:
    uploads/
        images/   ← image files (.jpg, .png, .webp, etc.)
        files/    ← documents (.pdf, .txt, .csv, etc.)
"""

import os
import uuid
import json
from datetime import datetime, timezone
from werkzeug.utils import secure_filename


class LocalStorage:
    """Stores and retrieves files from the local filesystem."""

    def __init__(self):
        # Base folder for uploads, e.g. "uploads"
        self.upload_folder = os.getenv("UPLOAD_FOLDER", "uploads")

        # Create subdirectories if they don't exist
        os.makedirs(os.path.join(self.upload_folder, "images"), exist_ok=True)
        os.makedirs(os.path.join(self.upload_folder, "files"), exist_ok=True)

        # Path to a simple JSON file that tracks upload metadata
        self._metadata_file = os.path.join(self.upload_folder, "metadata.json")
        self._metadata = self._load_metadata()

    # ------------------------------------------------------------------
    # Metadata helpers (a lightweight alternative to a database)
    # ------------------------------------------------------------------

    def _load_metadata(self):
        """Load the metadata JSON file from disk."""
        if os.path.exists(self._metadata_file):
            with open(self._metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_metadata(self):
        """Persist the metadata dict to disk."""
        with open(self._metadata_file, "w", encoding="utf-8") as f:
            json.dump(self._metadata, f, indent=2)

    # ------------------------------------------------------------------
    # Public API (matches SupabaseStorage)
    # ------------------------------------------------------------------

    def upload_file(self, file_data, original_filename, category):
        """
        Save an uploaded file to the local filesystem.

        Args:
            file_data:          A file-like object (from request.files).
            original_filename:  The name the user gave the file.
            category:           "images" or "files".

        Returns:
            dict with file metadata (id, filename, url, etc.)
        """
        # Generate a unique ID so users can never overwrite each other's files
        file_id = str(uuid.uuid4())

        # Sanitise the original name and extract the extension
        safe_name = secure_filename(original_filename)
        _, ext = os.path.splitext(safe_name)
        ext = ext.lower()

        # Build the stored filename:  <uuid>.<ext>
        stored_name = f"{file_id}{ext}"

        # Full path on disk
        file_path = os.path.join(self.upload_folder, category, stored_name)

        # Write the file
        file_data.save(file_path)

        # Gather size
        file_size = os.path.getsize(file_path)

        # Build metadata record
        metadata = {
            "id": file_id,
            "original_name": safe_name,
            "stored_name": stored_name,
            "category": category,
            "extension": ext,
            "size": file_size,
            "storage_type": "local",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "url": f"/uploads/{category}/{stored_name}",
        }

        self._metadata[file_id] = metadata
        self._save_metadata()

        return metadata

    def get_file(self, file_id):
        """
        Retrieve metadata for a single file.

        Returns:
            dict or None
        """
        return self._metadata.get(file_id)

    def list_files(self):
        """
        Return a list of all uploaded-file metadata dicts,
        sorted newest-first.
        """
        files = list(self._metadata.values())
        files.sort(key=lambda f: f["uploaded_at"], reverse=True)
        return files

    def delete_file(self, file_id):
        """
        Delete a file from disk and remove its metadata.

        Returns:
            True on success, False if the file was not found.
        """
        metadata = self._metadata.get(file_id)
        if not metadata:
            return False

        # Remove the physical file
        file_path = os.path.join(
            self.upload_folder,
            metadata["category"],
            metadata["stored_name"],
        )
        if os.path.exists(file_path):
            os.remove(file_path)

        # Remove metadata entry
        del self._metadata[file_id]
        self._save_metadata()

        return True

    def get_file_path(self, file_id):
        """
        Return the absolute filesystem path for serving a file.
        Used by Flask to send_from_directory().

        Returns:
            (directory, filename) tuple, or (None, None).
        """
        metadata = self._metadata.get(file_id)
        if not metadata:
            return None, None

        directory = os.path.join(
            os.getcwd(),
            self.upload_folder,
            metadata["category"],
        )
        return directory, metadata["stored_name"]
