"""
Cache management and index optimization for REV2.
Handles TTL, cleanup, and index type selection.
"""

import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional
import faiss
import pickle
from sqlalchemy.orm import Session

from backend.config import INDEX_DIR, INDEX_TTL_DAYS
from backend.logger import get_logger
from backend.db_models import IndexCache

logger = get_logger(__name__)

DEFAULT_TTL_DAYS = int(os.getenv("INDEX_TTL_DAYS", 30))
USE_IVF_FOR_LARGE_REPOS = os.getenv("USE_IVF_FOR_LARGE_REPOS", "True").lower() == "true"
IVF_THRESHOLD = 1000000  # Use IVF for indexes with >1M vectors


class CacheManager:
    """Manages index caching and cleanup."""

    def __init__(self, cache_dir: Path = INDEX_DIR):
        """Initialize cache manager."""
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_index_path(self, repo_name: str, commit_sha: str) -> Path:
        """
        Get path to cached index.

        Args:
            repo_name: Repository name
            commit_sha: Commit SHA

        Returns:
            Path to index file
        """
        safe_repo_name = repo_name.replace("/", "__")
        filename = f"{safe_repo_name}_{commit_sha}.faiss"
        return self.cache_dir / filename

    def get_metadata_path(self, repo_name: str, commit_sha: str) -> Path:
        """Get path to metadata file."""
        safe_repo_name = repo_name.replace("/", "__")
        filename = f"{safe_repo_name}_{commit_sha}_meta.pkl"
        return self.cache_dir / filename

    def cache_exists(self, repo_name: str, commit_sha: str) -> bool:
        """Check if index cache exists and is valid."""
        index_path = self.get_index_path(repo_name, commit_sha)
        metadata_path = self.get_metadata_path(repo_name, commit_sha)

        if not index_path.exists() or not metadata_path.exists():
            return False

        # Check TTL
        file_age_days = (time.time() - index_path.stat().st_mtime) / 86400
        if file_age_days > DEFAULT_TTL_DAYS:
            logger.info(
                "Index cache expired",
                repo=repo_name,
                commit_sha=commit_sha,
                age_days=file_age_days,
            )
            # Delete expired cache
            try:
                index_path.unlink()
                metadata_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete expired cache: {e}")
            return False

        return True

    def load_index(self, repo_name: str, commit_sha: str) -> tuple:
        """
        Load cached index and metadata.

        Returns:
            Tuple of (index, metadata) or (None, None) if not found
        """
        if not self.cache_exists(repo_name, commit_sha):
            return None, None

        try:
            index_path = self.get_index_path(repo_name, commit_sha)
            metadata_path = self.get_metadata_path(repo_name, commit_sha)

            index = faiss.read_index(str(index_path))

            with open(metadata_path, "rb") as f:
                metadata = pickle.load(f)

            logger.info(
                "Index cache hit",
                repo=repo_name,
                commit_sha=commit_sha,
                vectors=index.ntotal,
            )

            return index, metadata

        except Exception as e:
            logger.error(
                "Failed to load cached index",
                repo=repo_name,
                commit_sha=commit_sha,
                error=str(e),
            )
            return None, None

    def save_index(
        self,
        index: faiss.Index,
        metadata: list,
        repo_name: str,
        commit_sha: str,
    ):
        """
        Save index and metadata to cache.

        Args:
            index: FAISS index
            metadata: List of metadata dicts
            repo_name: Repository name
            commit_sha: Commit SHA
        """
        try:
            index_path = self.get_index_path(repo_name, commit_sha)
            metadata_path = self.get_metadata_path(repo_name, commit_sha)

            # Save index
            faiss.write_index(index, str(index_path))

            # Save metadata
            with open(metadata_path, "wb") as f:
                pickle.dump(metadata, f)

            logger.info(
                "Index cached",
                repo=repo_name,
                commit_sha=commit_sha,
                vectors=index.ntotal,
                size_mb=index_path.stat().st_size / (1024 * 1024),
            )

        except Exception as e:
            logger.error(
                "Failed to save index cache",
                repo=repo_name,
                commit_sha=commit_sha,
                error=str(e),
            )

    def cleanup_old_indexes(self, ttl_days: int = DEFAULT_TTL_DAYS) -> int:
        """
        Remove indexes older than TTL.

        Args:
            ttl_days: TTL in days

        Returns:
            Number of indexes removed
        """
        removed_count = 0
        cutoff_time = time.time() - (ttl_days * 86400)

        try:
            for index_file in self.cache_dir.glob("*.faiss"):
                file_age_time = index_file.stat().st_mtime

                if file_age_time < cutoff_time:
                    try:
                        index_file.unlink()
                        # Also remove metadata
                        meta_file = index_file.with_suffix(".pkl")
                        if meta_file.exists():
                            meta_file.unlink()
                        removed_count += 1

                        logger.info(
                            "Removed expired index",
                            file=index_file.name,
                        )

                    except Exception as e:
                        logger.warning(
                            f"Failed to delete index {index_file.name}: {e}"
                        )

            if removed_count > 0:
                logger.info(
                    "Index cleanup completed",
                    removed_count=removed_count,
                )

        except Exception as e:
            logger.error(f"Index cleanup failed: {e}")

        return removed_count

    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache statistics."""
        total_size = 0
        total_files = 0
        oldest_file = None
        oldest_time = time.time()

        try:
            for index_file in self.cache_dir.glob("*.faiss"):
                total_size += index_file.stat().st_size
                total_files += 1

                mtime = index_file.stat().st_mtime
                if mtime < oldest_time:
                    oldest_time = mtime
                    oldest_file = index_file.name

            return {
                "total_files": total_files,
                "total_size_mb": total_size / (1024 * 1024),
                "oldest_file": oldest_file,
                "oldest_age_days": (time.time() - oldest_time) / 86400,
            }

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {
                "total_files": 0,
                "total_size_mb": 0,
                "oldest_file": None,
                "oldest_age_days": 0,
            }


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create global cache manager."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
