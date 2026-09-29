"""
Storage Package
===============
Provides a unified storage interface with two implementations:
  - LocalStorage      → saves files to the local /uploads directory
  - SupabaseStorage   → uploads files to Supabase Storage

Usage:
    from storage import get_storage
    storage = get_storage()
    storage.upload_file(file_data, filename, category)
"""

import os
from .local_storage import LocalStorage
from .supabase_storage import SupabaseStorage


def get_storage():
    """
    Factory function that returns the correct storage backend
    based on the STORAGE_TYPE environment variable.

    Returns:
        LocalStorage or SupabaseStorage instance.

    Raises:
        ValueError: If STORAGE_TYPE is not 'local' or 'supabase'.
    """
    storage_type = os.getenv("STORAGE_TYPE", "local").lower()

    if storage_type == "local":
        return LocalStorage()
    elif storage_type == "supabase":
        return SupabaseStorage()
    else:
        raise ValueError(
            f"Unknown STORAGE_TYPE: '{storage_type}'. "
            "Use 'local' or 'supabase'."
        )
