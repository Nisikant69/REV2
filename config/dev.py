"""
Development environment configuration for REV2.
"""

import os

# Debug mode
DEBUG = True

# Logging
LOG_LEVEL = "DEBUG"
LOG_FORMAT = "text"  # Use text format for development

# Database - Use SQLite for development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./rev2_dev.db")
DATABASE_ECHO = True  # Log SQL queries
DATABASE_POOL_SIZE = 5

# Rate Limiting
RATE_LIMIT_REVIEWS_PER_HOUR = 1000  # Generous in dev

# Performance Settings
MAX_DIFF_SIZE = 15000
MAX_FILE_SIZE = 8000
CHUNK_SIZE = 800
CHUNK_OVERLAP = 200
TOP_K = 5

# Index Settings
INDEX_TTL_DAYS = 7
USE_IVF_FOR_LARGE_REPOS = False
PARALLEL_REVIEW_WORKERS = 2
BATCH_SIZE = 2

# API Timeouts
GITHUB_API_TIMEOUT = 30
GEMINI_API_TIMEOUT = 60

# Cache Settings
CACHE_CLEANUP_INTERVAL = 3600
