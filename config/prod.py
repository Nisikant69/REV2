"""
Production environment configuration for REV2.
"""

import os

# Debug mode
DEBUG = False

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "json"  # Use JSON format for log aggregation

# Database - Use PostgreSQL for production
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost/rev2"
)
DATABASE_ECHO = False
DATABASE_POOL_SIZE = 20

# Rate Limiting
RATE_LIMIT_REVIEWS_PER_HOUR = 100

# Performance Settings
MAX_DIFF_SIZE = 15000
MAX_FILE_SIZE = 8000
CHUNK_SIZE = 800
CHUNK_OVERLAP = 200
TOP_K = 5

# Index Settings
INDEX_TTL_DAYS = 30
USE_IVF_FOR_LARGE_REPOS = True
PARALLEL_REVIEW_WORKERS = 5
BATCH_SIZE = 5

# API Timeouts
GITHUB_API_TIMEOUT = 30
GEMINI_API_TIMEOUT = 60

# Cache Settings
CACHE_CLEANUP_INTERVAL = 3600  # Hourly cleanup
