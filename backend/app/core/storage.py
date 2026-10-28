"""
CogniCompanion — Storage Abstraction
=======================================
Provider-agnostic file storage interface.
Currently implements LocalStorage; extend with S3Storage later.
"""

import abc
import uuid
from pathlib import Path

import aiofiles

from app.core.config import get_settings

settings = get_settings()


class StorageProvider(abc.ABC):
    """Abstract base for all storage backends."""

    @abc.abstractmethod
    async def save(self, file_bytes: bytes, filename: str, folder: str = "uploads") -> str:
        """
        Persist file bytes and return a URL/path string that can be stored in the DB.

        Args:
            file_bytes: Raw bytes of the file to store.
            filename:   Original filename (used to derive extension).
            folder:     Sub-directory / prefix for organisation.

        Returns:
            A URL or relative path string stored in memory_media.file_url.
        """

    @abc.abstractmethod
    async def delete(self, file_url: str) -> None:
        """Delete the file identified by the given URL/path."""

    @abc.abstractmethod
    async def get_public_url(self, file_url: str) -> str:
        """Return a publicly accessible URL for the stored file."""


# ── Local Filesystem Storage ──────────────────────────────────────────────────

class LocalStorageProvider(StorageProvider):
    """
    Stores files on the local filesystem under LOCAL_STORAGE_PATH.
    Suitable for development and low-traffic demos.
    """

    def __init__(self, base_path: str = settings.LOCAL_STORAGE_PATH):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(self, file_bytes: bytes, filename: str, folder: str = "uploads") -> str:
        # Derive extension; generate a unique filename to avoid collisions
        ext = Path(filename).suffix or ".bin"
        unique_name = f"{uuid.uuid4().hex}{ext}"

        dest_dir = self.base_path / folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / unique_name

        async with aiofiles.open(dest_path, "wb") as f:
            await f.write(file_bytes)

        # Return a relative path that can be served by FastAPI's StaticFiles
        return f"/{folder}/{unique_name}"

    async def delete(self, file_url: str) -> None:
        # Strip leading slash and resolve against base path
        relative = file_url.lstrip("/")
        path = self.base_path / relative
        if path.exists():
            path.unlink()

    async def get_public_url(self, file_url: str) -> str:
        # In local mode, the URL is served as-is via StaticFiles mount
        return file_url


# ── Factory ───────────────────────────────────────────────────────────────────

def get_storage_provider() -> StorageProvider:
    """Return the configured storage provider instance."""
    provider = settings.STORAGE_PROVIDER.lower()
    if provider == "local":
        return LocalStorageProvider()
    # Future: elif provider == "s3": return S3StorageProvider(...)
    raise ValueError(f"Unknown STORAGE_PROVIDER: {provider!r}")


# Singleton — instantiated once at startup
storage: StorageProvider = get_storage_provider()
