"""
Custom storage backends for the ESP website.
Handles lowercasing file extensions for consistent file handling.
"""

import os
from django.core.files.storage import FileSystemStorage


class LowercaseExtensionStorage(FileSystemStorage):
    """
    Custom storage backend that automatically lowercases file extensions
    when saving files. This ensures consistent file handling regardless of
    how users upload files (e.g., photo.JPG vs photo.jpg).
    """

    def _normalize_filename(self, name):
        """
        Normalize filename: preserve basename case, lowercase extension.

        Args:
            name: Original filename string

        Returns:
            Normalized filename with lowercased extension
        """
        if not name:
            return name

        # Split filename and extension
        root, ext = os.path.splitext(name)

        # If no extension, return as-is
        if not ext:
            return name

        # If the path contains directory separators, reconstruct with dirs
        if '/' in root:
            dir_path, basename = root.rsplit('/', 1)
            return dir_path + '/' + basename + ext.lower()

        # Return with lowercased extension
        return root + ext.lower()

    def save(self, name, content, max_length=None):
        """
        Save a file with lowercased extension.

        Args:
            name: Original filename
            content: File content
            max_length: Maximum length for the filename

        Returns:
            The path the file is saved to
        """
        # Normalize the filename to lowercase extension
        normalized_name = self._normalize_filename(name)

        # Call the parent save method with the normalized name
        return super().save(normalized_name, content, max_length)
