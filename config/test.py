"""
Test environment configuration for REV2.
"""

import os

# Debug mode
DEBUG = False

# Logging
LOG_LEVEL = "WARNING"
LOG_FORMAT = "json"  # Use JSON format for consistent parsing

# Database - Use in-memory SQLite for tests
DATABASE_URL = "sqlite:///:memory:"
DATABASE_ECHO = False
DATABASE_POOL_SIZE = 1

# Rate Limiting
RATE_LIMIT_REVIEWS_PER_HOUR = 10000  # Very generous for tests

# Performance Settings
MAX_DIFF_SIZE = 15000
MAX_FILE_SIZE = 8000
CHUNK_SIZE = 800
CHUNK_OVERLAP = 200
TOP_K = 5

# Index Settings
INDEX_TTL_DAYS = 1
USE_IVF_FOR_LARGE_REPOS = False
PARALLEL_REVIEW_WORKERS = 1  # Sequential for deterministic tests
BATCH_SIZE = 1

# API Timeouts
GITHUB_API_TIMEOUT = 10
GEMINI_API_TIMEOUT = 10

# Cache Settings
CACHE_CLEANUP_INTERVAL = 60
