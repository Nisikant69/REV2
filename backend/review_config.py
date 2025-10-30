"""
Per-repository review configuration.
Allows teams to customize review rules and focus areas.
"""

import json
import os
from typing import Optional, List, Dict, Any
from pathlib import Path

from backend.logger import get_logger

logger = get_logger(__name__)


class ReviewConfig:
    """Repository-specific review configuration."""

    def __init__(
        self,
        review_types: List[str] = None,
        languages: List[str] = None,
        file_patterns_ignore: List[str] = None,
        min_severity: str = "info",
        custom_prompt: str = "",
        max_response_length: int = 5000,
    ):
        """
        Initialize review configuration.

        Args:
            review_types: Types of reviews to perform (security, performance, quality)
            languages: Limit to specific programming languages
            file_patterns_ignore: File patterns to ignore (glob patterns)
            min_severity: Minimum severity to report (critical, warning, info)
            custom_prompt: Custom prompt suffix to append to reviews
            max_response_length: Maximum length of review response
        """
        self.review_types = review_types or ["security", "performance", "quality"]
        self.languages = languages or []  # Empty = all languages
        self.file_patterns_ignore = file_patterns_ignore or []
        self.min_severity = min_severity
        self.custom_prompt = custom_prompt
        self.max_response_length = max_response_length

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "review_types": self.review_types,
            "languages": self.languages,
            "file_patterns_ignore": self.file_patterns_ignore,
            "min_severity": self.min_severity,
            "custom_prompt": self.custom_prompt,
            "max_response_length": self.max_response_length,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReviewConfig":
        """Create configuration from dictionary."""
        return cls(
            review_types=data.get("review_types", ["security", "performance", "quality"]),
            languages=data.get("languages", []),
            file_patterns_ignore=data.get("file_patterns_ignore", []),
            min_severity=data.get("min_severity", "info"),
            custom_prompt=data.get("custom_prompt", ""),
            max_response_length=data.get("max_response_length", 5000),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "ReviewConfig":
        """Create configuration from JSON string."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in review config: {e}")
            return cls()

    @classmethod
    def from_file(cls, file_path: Path) -> "ReviewConfig":
        """
        Load configuration from file.

        Args:
            file_path: Path to config file (.json or .yml)

        Returns:
            ReviewConfig instance
        """
        if not file_path.exists():
            logger.warning(f"Config file not found: {file_path}")
            return cls()

        try:
            if file_path.suffix in [".json", ".jsonc"]:
                with open(file_path, "r") as f:
                    data = json.load(f)
                return cls.from_dict(data)
            elif file_path.suffix in [".yml", ".yaml"]:
                try:
                    import yaml
                    with open(file_path, "r") as f:
                        data = yaml.safe_load(f)
                    return cls.from_dict(data)
                except ImportError:
                    logger.warning("PyYAML not installed, cannot parse YAML config")
                    return cls()
            else:
                logger.warning(f"Unknown config format: {file_path.suffix}")
                return cls()

        except Exception as e:
            logger.error(f"Failed to load config from {file_path}: {e}")
            return cls()

    def should_review_file(self, filename: str, file_language: str = None) -> bool:
        """
        Check if a file should be reviewed based on configuration.

        Args:
            filename: Name of the file
            file_language: Programming language of the file

        Returns:
            True if file should be reviewed
        """
        import fnmatch

        # Check language filter
        if self.languages and file_language:
            if file_language.lower() not in [l.lower() for l in self.languages]:
                logger.debug(
                    "File skipped - language not in whitelist",
                    filename=filename,
                    language=file_language,
                )
                return False

        # Check ignore patterns
        for pattern in self.file_patterns_ignore:
            if fnmatch.fnmatch(filename, pattern):
                logger.debug(
                    "File skipped - matches ignore pattern",
                    filename=filename,
                    pattern=pattern,
                )
                return False

        return True

    def filter_comments_by_severity(self, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter review comments based on minimum severity.

        Args:
            comments: List of comment dictionaries

        Returns:
            Filtered list of comments
        """
        severity_levels = {"critical": 3, "warning": 2, "info": 1}
        min_level = severity_levels.get(self.min_severity, 1)

        filtered = []
        for comment in comments:
            comment_severity = comment.get("severity", "info")
            comment_level = severity_levels.get(comment_severity, 1)

            if comment_level >= min_level:
                filtered.append(comment)

        return filtered

    def get_review_prompt_suffix(self) -> str:
        """Get custom prompt suffix for review."""
        prompt = ""

        if self.review_types:
            focus = ", ".join(self.review_types)
            prompt += f"\nPlease focus on the following aspects: {focus}."

        if self.custom_prompt:
            prompt += f"\n\n{self.custom_prompt}"

        return prompt


class ConfigManager:
    """Manages review configurations for repositories."""

    DEFAULT_CONFIG = ReviewConfig()

    def __init__(self):
        """Initialize config manager."""
        self.configs: Dict[str, ReviewConfig] = {}

    def load_repo_config(self, repo_name: str, repo_dir: Path = None) -> ReviewConfig:
        """
        Load configuration for a repository.

        Looks for .rev2/config.json in the repository.

        Args:
            repo_name: Name of repository
            repo_dir: Path to repository root

        Returns:
            ReviewConfig instance
        """
        # Check cache
        if repo_name in self.configs:
            return self.configs[repo_name]

        # Try to load from repo
        if repo_dir:
            config_file = Path(repo_dir) / ".rev2" / "config.json"
            if config_file.exists():
                config = ReviewConfig.from_file(config_file)
                self.configs[repo_name] = config
                logger.info(f"Loaded config for {repo_name} from {config_file}")
                return config

        # Use default
        logger.debug(f"Using default config for {repo_name}")
        self.configs[repo_name] = self.DEFAULT_CONFIG
        return self.DEFAULT_CONFIG

    def clear_cache(self):
        """Clear configuration cache."""
        self.configs.clear()


# Global config manager
_config_manager: Optional["ConfigManager"] = None


def get_config_manager() -> ConfigManager:
    """Get or create global config manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
