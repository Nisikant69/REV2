"""
Pytest configuration and fixtures for REV2 backend tests.
Provides mocked clients and test database.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from backend.db_models import Base
from backend.database import SessionLocal


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    # Create in-memory database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Patch the get_db_session function to use test database
    from backend import database
    original_sessionlocal = database.SessionLocal
    database.SessionLocal = TestingSessionLocal

    yield TestingSessionLocal()

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    database.SessionLocal = original_sessionlocal


@pytest.fixture
def mock_github_client():
    """Mock PyGithub Github client."""
    mock_client = Mock()

    # Mock repo
    mock_repo = Mock()
    mock_repo.full_name = "test-owner/test-repo"

    # Mock PR
    mock_pr = Mock()
    mock_pr.number = 123
    mock_pr.html_url = "https://github.com/test-owner/test-repo/pull/123"
    mock_pr.head.sha = "abc1234567890def"
    mock_pr.head.ref = "feature/test"

    # Mock files
    mock_file1 = Mock()
    mock_file1.filename = "test.py"
    mock_file1.status = "modified"
    mock_file1.patch = "--- a/test.py\n+++ b/test.py\n@@ -1,3 +1,3 @@\n- old\n+ new\n"

    mock_file2 = Mock()
    mock_file2.filename = "other.py"
    mock_file2.status = "added"
    mock_file2.patch = "--- /dev/null\n+++ b/other.py\n@@ -0,0 +1,3 @@\n+ def test():\n+     pass\n"

    mock_pr.get_files.return_value = [mock_file1, mock_file2]

    # Mock get_pull
    mock_repo.get_pull.return_value = mock_pr

    # Mock get_repo
    mock_client.get_repo.return_value = mock_repo

    return mock_client


@pytest.fixture
def mock_gemini_client():
    """Mock Google Generative AI Gemini client."""
    mock_client = Mock()

    mock_response = Mock()
    mock_response.text = (
        "### Issues Found:\n"
        "1. **CRITICAL**: Potential security vulnerability\n"
        "2. **WARNING**: Code smell detected"
    )

    mock_client.generate_content.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_github_api():
    """Mock requests for GitHub API calls."""
    with patch("requests.post") as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "token": "ghu_test_token_123",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        yield mock_post


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory for tests."""
    temp_dir = tempfile.mkdtemp()
    original_index_dir = os.getenv("INDEX_DIR")
    original_cache_dir = os.getenv("REPO_CACHE_DIR")

    yield Path(temp_dir)

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_webhook_payload():
    """Sample GitHub webhook payload."""
    return {
        "action": "opened",
        "number": 123,
        "pull_request": {
            "number": 123,
            "html_url": "https://github.com/test-owner/test-repo/pull/123",
            "head": {
                "sha": "abc1234567890def",
                "ref": "feature/test",
            },
            "title": "Test PR",
            "body": "Test description",
        },
        "repository": {
            "full_name": "test-owner/test-repo",
        },
        "installation": {
            "id": 12345,
        },
    }


@pytest.fixture
def sample_patch():
    """Sample diff/patch for testing."""
    return """--- a/example.py
+++ b/example.py
@@ -1,5 +1,5 @@
 def hello():
-    print("hello")
+    print("hello world")
     return True

 def goodbye():
"""


@pytest.fixture
def invalid_patch():
    """Invalid patch for testing validation."""
    return "this is not a valid patch format"


@pytest.fixture
def large_patch():
    """Generate a very large patch (for size limit testing)."""
    # Create a patch larger than MAX_DIFF_SIZE
    lines = ["--- a/file.py\n", "+++ b/file.py\n", "@@ -1,1 +1,1 @@\n"]
    for i in range(10000):
        lines.append(f"+ line {i}\n")
    return "".join(lines)
