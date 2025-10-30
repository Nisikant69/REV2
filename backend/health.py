"""
Health check and monitoring endpoints for REV2.
Provides system status and Prometheus-compatible metrics.
"""

import os
import time
from datetime import datetime
from typing import Dict, Any
from pathlib import Path
import shutil

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db_session, SessionLocal
from backend.logger import get_logger
from backend.config import INDEX_DIR, REPO_CACHE_DIR

logger = get_logger(__name__)
router = APIRouter()

# Metrics storage
class MetricsStore:
    """In-memory metrics storage."""
    def __init__(self):
        self.reviews_total = 0
        self.reviews_success = 0
        self.reviews_failure = 0
        self.api_errors_total = 0
        self.rate_limit_hits_total = 0
        self.review_durations = []  # List of durations in ms
        self.last_reset = time.time()

    def record_review(self, success: bool, duration_ms: float):
        """Record a review completion."""
        self.reviews_total += 1
        if success:
            self.reviews_success += 1
        else:
            self.reviews_failure += 1
        self.review_durations.append(duration_ms)
        # Keep only last 1000 durations to avoid memory bloat
        if len(self.review_durations) > 1000:
            self.review_durations = self.review_durations[-1000:]

    def record_api_error(self):
        """Record an API error."""
        self.api_errors_total += 1

    def record_rate_limit_hit(self):
        """Record a rate limit hit."""
        self.rate_limit_hits_total += 1

    def get_avg_duration_ms(self) -> float:
        """Get average review duration."""
        if not self.review_durations:
            return 0.0
        return sum(self.review_durations) / len(self.review_durations)


metrics = MetricsStore()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    Returns 200 if system is operational.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/health/detailed")
async def detailed_health_check(
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Detailed health check with component diagnostics.
    Checks database, disk space, and configuration.
    """
    checks = {}

    # Database connectivity
    try:
        db.execute("SELECT 1")
        checks["database"] = {"status": "healthy", "message": "Connected"}
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "message": f"Connection failed: {str(e)}",
        }
        logger.error("Database health check failed", error=str(e))

    # Disk space for indexes
    try:
        if INDEX_DIR.exists():
            stat = shutil.disk_usage(INDEX_DIR)
            free_gb = stat.free / (1024 ** 3)
            used_gb = stat.used / (1024 ** 3)
            checks["index_disk"] = {
                "status": "healthy" if free_gb > 1 else "warning",
                "free_gb": round(free_gb, 2),
                "used_gb": round(used_gb, 2),
            }
        else:
            checks["index_disk"] = {
                "status": "warning",
                "message": "Index directory not found",
            }
    except Exception as e:
        checks["index_disk"] = {
            "status": "unhealthy",
            "message": f"Disk check failed: {str(e)}",
        }
        logger.error("Disk health check failed", error=str(e))

    # Cache directory
    try:
        if REPO_CACHE_DIR.exists():
            cache_size_mb = sum(
                f.stat().st_size for f in REPO_CACHE_DIR.rglob("*") if f.is_file()
            ) / (1024 ** 2)
            checks["cache"] = {
                "status": "healthy",
                "size_mb": round(cache_size_mb, 2),
            }
        else:
            checks["cache"] = {
                "status": "warning",
                "message": "Cache directory not found",
            }
    except Exception as e:
        checks["cache"] = {
            "status": "warning",
            "message": f"Cache check failed: {str(e)}",
        }

    # Overall status
    overall_status = "healthy"
    for check in checks.values():
        if check.get("status") == "unhealthy":
            overall_status = "unhealthy"
            break
        elif check.get("status") == "warning":
            overall_status = "warning"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": checks,
    }


@router.get("/metrics")
async def prometheus_metrics() -> str:
    """
    Prometheus-compatible metrics endpoint.
    Returns metrics in OpenMetrics format.
    """
    avg_duration = metrics.get_avg_duration_ms()

    # Index and cache sizes
    index_size_bytes = 0
    if INDEX_DIR.exists():
        index_size_bytes = sum(
            f.stat().st_size for f in INDEX_DIR.rglob("*") if f.is_file()
        )

    metrics_lines = [
        "# HELP rev2_reviews_total Total number of reviews performed",
        "# TYPE rev2_reviews_total counter",
        f"rev2_reviews_total{{status=\"success\"}} {metrics.reviews_success}",
        f"rev2_reviews_total{{status=\"failure\"}} {metrics.reviews_failure}",
        "",
        "# HELP rev2_review_duration_ms Review processing duration in milliseconds",
        "# TYPE rev2_review_duration_ms histogram",
        f"rev2_review_duration_ms_sum {sum(metrics.review_durations)}",
        f"rev2_review_duration_ms_count {len(metrics.review_durations)}",
        f"rev2_review_duration_ms_avg {avg_duration}",
        "",
        "# HELP rev2_index_cache_size_bytes Size of index cache in bytes",
        "# TYPE rev2_index_cache_size_bytes gauge",
        f"rev2_index_cache_size_bytes {index_size_bytes}",
        "",
        "# HELP rev2_api_errors_total Total API errors",
        "# TYPE rev2_api_errors_total counter",
        f"rev2_api_errors_total {metrics.api_errors_total}",
        "",
        "# HELP rev2_rate_limit_hits_total Total rate limit hits",
        "# TYPE rev2_rate_limit_hits_total counter",
        f"rev2_rate_limit_hits_total {metrics.rate_limit_hits_total}",
    ]

    return "\n".join(metrics_lines)


@router.get("/metrics/summary")
async def metrics_summary(
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Human-readable metrics summary.
    Shows recent review statistics and system health.
    """
    from backend.db_models import ReviewRecord

    # Count reviews by status
    total_reviews = db.query(ReviewRecord).count()
    success_reviews = db.query(ReviewRecord).filter_by(
        review_status="success"
    ).count()
    failure_reviews = db.query(ReviewRecord).filter_by(
        review_status="failure"
    ).count()

    avg_duration = (
        db.query(ReviewRecord.api_latency_ms)
        .filter(ReviewRecord.api_latency_ms.isnot(None))
        .scalar()
        or 0
    )

    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "reviews": {
            "total": total_reviews,
            "success": success_reviews,
            "failure": failure_reviews,
            "success_rate": (
                success_reviews / total_reviews if total_reviews > 0 else 0
            ),
        },
        "performance": {
            "avg_review_duration_ms": avg_duration,
            "reviews_in_memory": {
                "total": metrics.reviews_total,
                "avg_duration_ms": metrics.get_avg_duration_ms(),
            },
        },
        "system": {
            "index_cache_bytes": (
                sum(
                    f.stat().st_size for f in INDEX_DIR.rglob("*") if f.is_file()
                )
                if INDEX_DIR.exists()
                else 0
            ),
        },
    }
