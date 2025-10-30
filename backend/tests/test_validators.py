"""
Tests for input validators module.
"""

import pytest
from backend.validators import (
    validate_webhook_payload,
    validate_patch,
    validate_repo_name,
    sanitize_patch_for_llm,
    validate_file_path,
    ValidationError,
)


class TestValidateWebhookPayload:
    """Tests for webhook payload validation."""

    def test_valid_payload(self, sample_webhook_payload):
        """Valid payload should pass validation."""
        assert validate_webhook_payload(sample_webhook_payload) is True

    def test_missing_action(self, sample_webhook_payload):
        """Missing action field should raise error."""
        del sample_webhook_payload["action"]
        with pytest.raises(ValidationError):
            validate_webhook_payload(sample_webhook_payload)

    def test_missing_pull_request(self, sample_webhook_payload):
        """Missing pull_request field should raise error."""
        del sample_webhook_payload["pull_request"]
        with pytest.raises(ValidationError):
            validate_webhook_payload(sample_webhook_payload)

    def test_missing_pr_number(self, sample_webhook_payload):
        """Missing PR number should raise error."""
        del sample_webhook_payload["pull_request"]["number"]
        with pytest.raises(ValidationError):
            validate_webhook_payload(sample_webhook_payload)

    def test_missing_head_sha(self, sample_webhook_payload):
        """Missing head SHA should raise error."""
        del sample_webhook_payload["pull_request"]["head"]["sha"]
        with pytest.raises(ValidationError):
            validate_webhook_payload(sample_webhook_payload)

    def test_missing_repo_name(self, sample_webhook_payload):
        """Missing repository name should raise error."""
        del sample_webhook_payload["repository"]["full_name"]
        with pytest.raises(ValidationError):
            validate_webhook_payload(sample_webhook_payload)

    def test_missing_installation_id(self, sample_webhook_payload):
        """Missing installation ID should raise error."""
        del sample_webhook_payload["installation"]["id"]
        with pytest.raises(ValidationError):
            validate_webhook_payload(sample_webhook_payload)


class TestValidatePatch:
    """Tests for patch validation."""

    def test_valid_patch(self, sample_patch):
        """Valid patch should pass validation."""
        assert validate_patch(sample_patch) is True

    def test_empty_patch(self):
        """Empty patch should raise error."""
        with pytest.raises(ValidationError):
            validate_patch("")

    def test_oversized_patch(self, large_patch):
        """Patch exceeding max size should raise error."""
        with pytest.raises(ValidationError):
            validate_patch(large_patch, max_size=1000)

    def test_patch_under_limit(self, sample_patch):
        """Patch under size limit should pass."""
        assert validate_patch(sample_patch, max_size=10000) is True


class TestValidateRepoName:
    """Tests for repository name validation."""

    def test_valid_repo_name(self):
        """Valid repo name should pass."""
        assert validate_repo_name("owner/repo") is True

    def test_valid_repo_with_hyphens(self):
        """Repo name with hyphens should pass."""
        assert validate_repo_name("my-owner/my-repo") is True

    def test_valid_repo_with_dots(self):
        """Repo name with dots should pass."""
        assert validate_repo_name("owner.name/repo.name") is True

    def test_empty_repo_name(self):
        """Empty repo name should raise error."""
        with pytest.raises(ValidationError):
            validate_repo_name("")

    def test_invalid_format(self):
        """Invalid format should raise error."""
        with pytest.raises(ValidationError):
            validate_repo_name("invalid")

    def test_path_traversal_attempt(self):
        """Path traversal attempt should raise error."""
        with pytest.raises(ValidationError):
            validate_repo_name("../../../etc/passwd")

    def test_double_slash(self):
        """Double slashes should raise error."""
        with pytest.raises(ValidationError):
            validate_repo_name("owner//repo")


class TestSanitizePatch:
    """Tests for patch sanitization."""

    def test_sanitize_password_pattern(self):
        """Should redact password patterns."""
        patch_with_password = 'password = "secret123"'
        sanitized = sanitize_patch_for_llm(patch_with_password)
        assert "secret123" not in sanitized
        assert "REDACTED" in sanitized

    def test_sanitize_api_key(self):
        """Should redact API key patterns."""
        patch_with_key = 'API_KEY = "sk_live_abc123"'
        sanitized = sanitize_patch_for_llm(patch_with_key)
        assert "sk_live_abc123" not in sanitized
        assert "REDACTED" in sanitized

    def test_sanitize_bearer_token(self):
        """Should redact bearer tokens."""
        patch_with_token = "Authorization: Bearer eyJhbGc..."
        sanitized = sanitize_patch_for_llm(patch_with_token)
        assert "Bearer eyJhbGc" not in sanitized
        assert "REDACTED" in sanitized

    def test_sanitize_truncation(self):
        """Should truncate patches exceeding max size."""
        large = "x" * 20000
        sanitized = sanitize_patch_for_llm(large, max_size=1000)
        assert len(sanitized) <= 1010  # 1000 + "... (truncated)"

    def test_sanitize_valid_code(self):
        """Valid code should remain mostly unchanged."""
        code = 'def hello():\n    print("Hello")'
        sanitized = sanitize_patch_for_llm(code)
        assert 'print("Hello")' in sanitized


class TestValidateFilePath:
    """Tests for file path validation."""

    def test_valid_path(self):
        """Valid file path should pass."""
        assert validate_file_path("src/main.py") is True

    def test_valid_nested_path(self):
        """Valid nested path should pass."""
        assert validate_file_path("src/components/Header.jsx") is True

    def test_empty_path(self):
        """Empty path should raise error."""
        with pytest.raises(ValidationError):
            validate_file_path("")

    def test_path_traversal_attempt(self):
        """Path traversal attempt should raise error."""
        with pytest.raises(ValidationError):
            validate_file_path("../../../etc/passwd")

    def test_absolute_path(self):
        """Absolute path should raise error."""
        with pytest.raises(ValidationError):
            validate_file_path("/etc/passwd")
