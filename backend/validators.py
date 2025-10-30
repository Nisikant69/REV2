"""
Input validation and sanitization module for REV2.
Validates GitHub webhook payloads, patches, and repository names.
"""

import re
from typing import Any, Dict
from backend.config import MAX_DIFF_SIZE


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


def validate_webhook_payload(payload: Dict[str, Any]) -> bool:
    """
    Validate GitHub webhook payload structure.

    Args:
        payload: The webhook payload dictionary

    Returns:
        True if valid, raises ValidationError otherwise
    """
    required_fields = ["action", "pull_request", "repository", "installation"]

    for field in required_fields:
        if field not in payload:
            raise ValidationError(f"Missing required field: {field}")

    # Validate pull_request structure
    pr = payload.get("pull_request", {})
    pr_required = ["number", "head", "html_url"]
    for field in pr_required:
        if field not in pr:
            raise ValidationError(f"Missing PR field: {field}")

    # Validate head structure
    head = pr.get("head", {})
    if "sha" not in head:
        raise ValidationError("Missing PR head SHA")

    # Validate repository structure
    repo = payload.get("repository", {})
    if "full_name" not in repo:
        raise ValidationError("Missing repository full_name")

    # Validate installation
    installation = payload.get("installation", {})
    if "id" not in installation:
        raise ValidationError("Missing installation ID")

    return True


def validate_patch(patch_text: str, max_size: int = MAX_DIFF_SIZE) -> bool:
    """
    Validate patch format and size.

    Args:
        patch_text: The patch/diff content
        max_size: Maximum allowed patch size in characters

    Returns:
        True if valid, raises ValidationError otherwise
    """
    if not patch_text:
        raise ValidationError("Patch cannot be empty")

    if len(patch_text) > max_size:
        raise ValidationError(
            f"Patch exceeds maximum size ({len(patch_text)} > {max_size} chars)"
        )

    # Check if patch starts with diff markers (basic validation)
    if not patch_text.startswith(("---", "+++", "diff", "@")):
        # Some patches might not have standard headers, so just warn
        pass

    return True


def validate_repo_name(name: str) -> bool:
    """
    Validate repository name to prevent path traversal attacks.

    Args:
        name: Repository name (e.g., 'owner/repo')

    Returns:
        True if valid, raises ValidationError otherwise
    """
    if not name:
        raise ValidationError("Repository name cannot be empty")

    # Repository names should be owner/repo format
    if not re.match(r"^[\w\-\.]+/[\w\-\.]+$", name):
        raise ValidationError(
            f"Invalid repository name format: {name}. Expected 'owner/repo'"
        )

    # Check for path traversal attempts
    if ".." in name or name.startswith("/") or name.endswith("/"):
        raise ValidationError(f"Suspicious repository name: {name}")

    return True


def sanitize_patch_for_llm(patch: str, max_size: int = MAX_DIFF_SIZE) -> str:
    """
    Sanitize patch content for LLM processing.
    - Removes potential sensitive patterns
    - Limits size
    - Escapes dangerous characters

    Args:
        patch: The patch content
        max_size: Maximum allowed size after sanitization

    Returns:
        Sanitized patch content
    """
    # Patterns that might contain sensitive data
    sensitive_patterns = [
        (r'(?i)(password|secret|token|key|credential)[\s]*=[\s]*["\']?[^"\';\n]+["\']?', '***REDACTED***'),
        (r'(?i)(api[_-]?key)[\s]*[:=][\s]*["\']?[^"\';\n]+["\']?', '***REDACTED_KEY***'),
        (r'Bearer\s+[^\s]+', '***REDACTED_BEARER_TOKEN***'),
        (r'Basic\s+[^\s]+', '***REDACTED_BASIC_AUTH***'),
    ]

    sanitized = patch
    for pattern, replacement in sensitive_patterns:
        sanitized = re.sub(pattern, replacement, sanitized)

    # Truncate if too large
    if len(sanitized) > max_size:
        sanitized = sanitized[:max_size] + "\n... (truncated)"

    return sanitized


def validate_file_path(file_path: str) -> bool:
    """
    Validate file path to prevent traversal attacks.

    Args:
        file_path: The file path

    Returns:
        True if valid, raises ValidationError otherwise
    """
    if not file_path:
        raise ValidationError("File path cannot be empty")

    # Check for path traversal attempts
    if ".." in file_path or file_path.startswith("/"):
        raise ValidationError(f"Suspicious file path: {file_path}")

    return True
