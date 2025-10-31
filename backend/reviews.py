"""
Review data retrieval and analytics endpoints for the frontend.
Provides filtered review listings, detail views, and analytics metrics.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from pydantic import BaseModel, Field

from backend.database import get_db_session
from backend.db_models import ReviewRecord, ReviewComment, ReviewFeedback, ReviewStatus, CommentSeverity
from backend.logger import get_logger
from backend.auth import validate_api_key

logger = get_logger(__name__)
router = APIRouter()


# Request/Response Models
class CommentResponse(BaseModel):
    file_path: str
    line_number: Optional[int]
    severity: str
    comment_text: str


class FeedbackResponse(BaseModel):
    rating: int
    is_helpful: bool
    user_comment: Optional[str]
    created_at: str


class ReviewDetailResponse(BaseModel):
    review_id: str
    repo_name: str
    pr_number: int
    status: str
    files_reviewed: int
    api_latency_ms: Optional[int]
    cache_hit: bool
    created_at: str
    comments: List[CommentResponse]
    feedback: Optional[FeedbackResponse]


class ReviewListItemResponse(BaseModel):
    review_id: str
    repo_name: str
    pr_number: int
    status: str
    files_reviewed: int
    api_latency_ms: Optional[int]
    cache_hit: bool
    created_at: str


class PaginationInfo(BaseModel):
    total_count: int
    page: int
    limit: int
    total_pages: int


class ReviewListResponse(BaseModel):
    data: List[ReviewListItemResponse]
    pagination: PaginationInfo


class AnalyticsSummaryResponse(BaseModel):
    total_reviews: int
    success_rate: float
    average_latency_ms: float
    average_rating: Optional[float]
    cache_hit_rate: float
    total_comments: int
    comments_by_severity: Dict[str, int]
    helpful_feedback_rate: Optional[float]


class RepoMetricsResponse(BaseModel):
    repo_name: str
    review_count: int
    success_rate: float
    average_latency_ms: float
    average_rating: Optional[float]
    cache_hit_rate: float
    total_comments: int
    comments_by_severity: Dict[str, int]
    last_review_date: str


class AnalyticsByRepoResponse(BaseModel):
    data: List[RepoMetricsResponse]


# Helper functions
def normalize_status(status: str) -> str:
    """Convert database status (lowercase) to API format (uppercase)."""
    status_map = {
        "success": "SUCCESS",
        "partial_failure": "PARTIAL_FAILURE",
        "failure": "FAILURE",
    }
    return status_map.get(status, status.upper())


def parse_iso_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO date string."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return None


@router.get("/api/reviews", response_model=ReviewListResponse)
async def list_reviews(
    authorization: Optional[str] = Header(None),
    repo_name: Optional[str] = Query(None, description="Filter by repo name (partial match, case-insensitive)"),
    status: Optional[str] = Query(None, description="Filter by status (SUCCESS, PARTIAL_FAILURE, FAILURE)"),
    date_from: Optional[str] = Query(None, description="ISO format date, filter reviews >= this date"),
    date_to: Optional[str] = Query(None, description="ISO format date, filter reviews <= this date"),
    page: int = Query(1, ge=1, description="Pagination page (1-indexed)"),
    limit: int = Query(50, ge=1, le=100, description="Results per page (max 100)"),
    sort_by: str = Query("created_at", description="Sort column (created_at, pr_number, status, api_latency_ms)"),
    sort_order: str = Query("desc", description="asc or desc"),
    db: Session = Depends(get_db_session),
):
    """
    List all reviews with filtering, pagination, and sorting.

    Query Parameters:
    - repo_name: Filter by repo name (partial match, case-insensitive)
    - status: Filter by status (SUCCESS, PARTIAL_FAILURE, FAILURE)
    - date_from: ISO format date, filter reviews >= this date
    - date_to: ISO format date, filter reviews <= this date
    - page: Pagination page (1-indexed, default 1)
    - limit: Results per page (default 50, max 100)
    - sort_by: Sort column (created_at, pr_number, status, api_latency_ms)
    - sort_order: asc or desc (default desc for created_at, desc otherwise)
    """
    try:
        # Validate API key
        if authorization:
            validate_api_key(authorization)
        else:
            raise HTTPException(status_code=401, detail="Missing Authorization header")

        # Validate page
        if page < 1 or not isinstance(page, int):
            raise HTTPException(status_code=400, detail="Invalid page number", headers={"code": "INVALID_REQUEST"})

        # Clamp limit to max 100 silently
        limit = min(limit, 100)

        # Validate sort_by
        valid_sort_columns = ["created_at", "pr_number", "status", "api_latency_ms"]
        if sort_by not in valid_sort_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sort column. Must be one of: {', '.join(valid_sort_columns)}",
                headers={"code": "INVALID_REQUEST"}
            )

        # Validate sort_order
        if sort_order not in ["asc", "desc"]:
            raise HTTPException(
                status_code=400,
                detail="sort_order must be 'asc' or 'desc'",
                headers={"code": "INVALID_REQUEST"}
            )

        # Build query
        query = db.query(ReviewRecord)

        # Apply filters
        if repo_name:
            query = query.filter(ReviewRecord.repo_name.ilike(f"%{repo_name}%"))

        if status:
            # Map uppercase status to lowercase database format
            status_map = {
                "SUCCESS": "success",
                "PARTIAL_FAILURE": "partial_failure",
                "FAILURE": "failure",
            }
            db_status = status_map.get(status, status)
            query = query.filter(ReviewRecord.review_status == db_status)

        if date_from:
            parsed_date_from = parse_iso_date(date_from)
            if not parsed_date_from:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date_from format. Use ISO format (YYYY-MM-DD or ISO 8601)",
                    headers={"code": "INVALID_REQUEST"}
                )
            query = query.filter(ReviewRecord.created_at >= parsed_date_from)

        if date_to:
            parsed_date_to = parse_iso_date(date_to)
            if not parsed_date_to:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date_to format. Use ISO format (YYYY-MM-DD or ISO 8601)",
                    headers={"code": "INVALID_REQUEST"}
                )
            query = query.filter(ReviewRecord.created_at <= parsed_date_to)

        # Check date range validity
        if date_from and date_to:
            parsed_from = parse_iso_date(date_from)
            parsed_to = parse_iso_date(date_to)
            if parsed_from and parsed_to and parsed_from > parsed_to:
                raise HTTPException(
                    status_code=400,
                    detail="date_from must be before date_to",
                    headers={"code": "INVALID_REQUEST"}
                )

        # Get total count before pagination
        total_count = query.count()

        # Apply sorting
        if sort_by == "created_at":
            if sort_order == "asc":
                query = query.order_by(ReviewRecord.created_at.asc())
            else:
                query = query.order_by(ReviewRecord.created_at.desc())
        elif sort_by == "pr_number":
            if sort_order == "asc":
                query = query.order_by(ReviewRecord.pr_number.asc())
            else:
                query = query.order_by(ReviewRecord.pr_number.desc())
        elif sort_by == "status":
            if sort_order == "asc":
                query = query.order_by(ReviewRecord.review_status.asc())
            else:
                query = query.order_by(ReviewRecord.review_status.desc())
        elif sort_by == "api_latency_ms":
            if sort_order == "asc":
                query = query.order_by(ReviewRecord.api_latency_ms.asc())
            else:
                query = query.order_by(ReviewRecord.api_latency_ms.desc())

        # Apply pagination
        offset = (page - 1) * limit
        reviews = query.offset(offset).limit(limit).all()

        # Build response
        data = [
            ReviewListItemResponse(
                review_id=review.id,
                repo_name=review.repo_name,
                pr_number=review.pr_number,
                status=normalize_status(review.review_status.value),
                files_reviewed=review.files_reviewed,
                api_latency_ms=review.api_latency_ms,
                cache_hit=review.cache_hit,
                created_at=review.created_at.isoformat() + "Z",
            )
            for review in reviews
        ]

        pagination = PaginationInfo(
            total_count=total_count,
            page=page,
            limit=limit,
            total_pages=(total_count + limit - 1) // limit,  # Ceiling division
        )

        logger.info(f"Listed {len(reviews)} reviews", page=page, limit=limit, total=total_count)

        return ReviewListResponse(data=data, pagination=pagination)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list reviews: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve reviews", headers={"code": "INTERNAL_ERROR"})


@router.get("/api/reviews/{review_id}", response_model=ReviewDetailResponse)
async def get_review_detail(
    review_id: str,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db_session),
):
    """
    Get single review with all comments and feedback.

    Path Parameters:
    - review_id: UUID of the review

    Returns:
    - Full review details with comments grouped by file and feedback
    """
    try:
        # Validate API key
        if authorization:
            validate_api_key(authorization)
        else:
            raise HTTPException(status_code=401, detail="Missing Authorization header")

        # Validate review_id format (basic UUID check)
        if not review_id or len(review_id) < 36:
            raise HTTPException(
                status_code=400,
                detail="Invalid review ID format",
                headers={"code": "INVALID_REQUEST"}
            )

        # Get review
        review = db.query(ReviewRecord).filter_by(id=review_id).first()
        if not review:
            raise HTTPException(
                status_code=404,
                detail="Review not found",
                headers={"code": "NOT_FOUND"}
            )

        # Get comments sorted by file_path then line_number
        comments_query = (
            db.query(ReviewComment)
            .filter_by(review_record_id=review_id)
            .order_by(ReviewComment.file_path.asc(), ReviewComment.line_number.asc())
            .all()
        )

        comments = [
            CommentResponse(
                file_path=comment.file_path,
                line_number=comment.line_number,
                severity=comment.severity.value.upper(),
                comment_text=comment.comment_text,
            )
            for comment in comments_query
        ]

        # Get feedback (most recent if multiple)
        feedback_record = (
            db.query(ReviewFeedback)
            .filter_by(review_record_id=review_id)
            .order_by(ReviewFeedback.created_at.desc())
            .first()
        )

        feedback = None
        if feedback_record:
            feedback = FeedbackResponse(
                rating=feedback_record.rating,
                is_helpful=feedback_record.is_helpful,
                user_comment=feedback_record.comment,
                created_at=feedback_record.created_at.isoformat() + "Z",
            )

        logger.info(f"Retrieved review detail", review_id=review_id)

        return ReviewDetailResponse(
            review_id=review.id,
            repo_name=review.repo_name,
            pr_number=review.pr_number,
            status=normalize_status(review.review_status.value),
            files_reviewed=review.files_reviewed,
            api_latency_ms=review.api_latency_ms,
            cache_hit=review.cache_hit,
            created_at=review.created_at.isoformat() + "Z",
            comments=comments,
            feedback=feedback,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get review detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve review", headers={"code": "INTERNAL_ERROR"})


@router.get("/api/analytics/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    authorization: Optional[str] = Depends(lambda: None),
    db: Session = Depends(get_db_session),
):
    """
    Get overall metrics summary across all reviews.

    Returns:
    - Overall success rate, average latency, feedback metrics, and comment distribution
    """
    try:
        # Validate API key
        if authorization:
            validate_api_key(authorization)
        else:
            raise HTTPException(status_code=401, detail="Missing Authorization header")

        # Get counts
        total_reviews = db.query(ReviewRecord).count()

        if total_reviews == 0:
            return AnalyticsSummaryResponse(
                total_reviews=0,
                success_rate=0.0,
                average_latency_ms=0.0,
                average_rating=None,
                cache_hit_rate=0.0,
                total_comments=0,
                comments_by_severity={"CRITICAL": 0, "WARNING": 0, "INFO": 0},
                helpful_feedback_rate=None,
            )

        # Success rate
        success_reviews = db.query(ReviewRecord).filter_by(review_status="success").count()
        success_rate = (success_reviews / total_reviews * 100) if total_reviews > 0 else 0

        # Average latency
        avg_latency = db.query(func.avg(ReviewRecord.api_latency_ms)).scalar() or 0

        # Cache hit rate
        cache_hits = db.query(ReviewRecord).filter_by(cache_hit=True).count()
        cache_hit_rate = (cache_hits / total_reviews * 100) if total_reviews > 0 else 0

        # Total comments
        total_comments = db.query(ReviewComment).count()

        # Comments by severity
        severity_counts = {}
        for severity in ["critical", "warning", "info"]:
            count = db.query(ReviewComment).filter_by(severity=severity).count()
            severity_counts[severity.upper()] = count

        # Average rating and helpful feedback rate
        feedback_count = db.query(ReviewFeedback).count()
        average_rating = None
        helpful_feedback_rate = None

        if feedback_count > 0:
            avg_rating_result = db.query(func.avg(ReviewFeedback.rating)).scalar()
            average_rating = float(avg_rating_result) if avg_rating_result else None

            helpful_count = db.query(ReviewFeedback).filter_by(is_helpful=True).count()
            helpful_feedback_rate = (helpful_count / feedback_count * 100) if feedback_count > 0 else 0

        logger.info("Generated analytics summary", total_reviews=total_reviews)

        return AnalyticsSummaryResponse(
            total_reviews=total_reviews,
            success_rate=round(success_rate, 2),
            average_latency_ms=round(float(avg_latency), 2),
            average_rating=round(average_rating, 2) if average_rating else None,
            cache_hit_rate=round(cache_hit_rate, 2),
            total_comments=total_comments,
            comments_by_severity=severity_counts,
            helpful_feedback_rate=round(helpful_feedback_rate, 2) if helpful_feedback_rate is not None else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analytics summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics", headers={"code": "INTERNAL_ERROR"})


@router.get("/api/analytics/by-repo", response_model=AnalyticsByRepoResponse)
async def get_analytics_by_repo(
    authorization: Optional[str] = Depends(lambda: None),
    date_from: Optional[str] = Query(None, description="ISO format date, filter reviews >= this date"),
    date_to: Optional[str] = Query(None, description="ISO format date, filter reviews <= this date"),
    db: Session = Depends(get_db_session),
):
    """
    Get metrics aggregated by repository.

    Query Parameters:
    - date_from: ISO format date, filter reviews >= this date
    - date_to: ISO format date, filter reviews <= this date

    Returns:
    - Per-repo metrics sorted by review count (descending)
    """
    try:
        # Validate API key
        if authorization:
            validate_api_key(authorization)
        else:
            raise HTTPException(status_code=401, detail="Missing Authorization header")

        # Parse and validate dates
        parsed_date_from = None
        parsed_date_to = None

        if date_from:
            parsed_date_from = parse_iso_date(date_from)
            if not parsed_date_from:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date_from format",
                    headers={"code": "INVALID_REQUEST"}
                )

        if date_to:
            parsed_date_to = parse_iso_date(date_to)
            if not parsed_date_to:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date_to format",
                    headers={"code": "INVALID_REQUEST"}
                )

        if parsed_date_from and parsed_date_to and parsed_date_from > parsed_date_to:
            raise HTTPException(
                status_code=400,
                detail="date_from must be before date_to",
                headers={"code": "INVALID_REQUEST"}
            )

        # Build base query
        base_query = db.query(ReviewRecord)
        if parsed_date_from:
            base_query = base_query.filter(ReviewRecord.created_at >= parsed_date_from)
        if parsed_date_to:
            base_query = base_query.filter(ReviewRecord.created_at <= parsed_date_to)

        # Get unique repos
        repos = db.query(ReviewRecord.repo_name).distinct()
        if parsed_date_from:
            repos = repos.filter(ReviewRecord.created_at >= parsed_date_from)
        if parsed_date_to:
            repos = repos.filter(ReviewRecord.created_at <= parsed_date_to)
        repos = repos.all()

        repo_metrics = []

        for (repo_name,) in repos:
            repo_query = base_query.filter(ReviewRecord.repo_name == repo_name)

            review_count = repo_query.count()
            if review_count == 0:
                continue

            # Success rate
            success_count = repo_query.filter_by(review_status="success").count()
            success_rate = (success_count / review_count * 100) if review_count > 0 else 0

            # Average latency
            avg_latency = db.query(func.avg(ReviewRecord.api_latency_ms)).filter(
                ReviewRecord.repo_name == repo_name,
                ReviewRecord.api_latency_ms.isnot(None),
            )
            if parsed_date_from:
                avg_latency = avg_latency.filter(ReviewRecord.created_at >= parsed_date_from)
            if parsed_date_to:
                avg_latency = avg_latency.filter(ReviewRecord.created_at <= parsed_date_to)
            avg_latency = avg_latency.scalar() or 0

            # Cache hit rate
            cache_hits = repo_query.filter_by(cache_hit=True).count()
            cache_hit_rate = (cache_hits / review_count * 100) if review_count > 0 else 0

            # Total comments for this repo
            total_comments = db.query(ReviewComment).join(ReviewRecord).filter(
                ReviewRecord.repo_name == repo_name
            )
            if parsed_date_from:
                total_comments = total_comments.filter(ReviewRecord.created_at >= parsed_date_from)
            if parsed_date_to:
                total_comments = total_comments.filter(ReviewRecord.created_at <= parsed_date_to)
            total_comments = total_comments.count()

            # Comments by severity for this repo
            severity_counts = {}
            for severity in ["critical", "warning", "info"]:
                count = db.query(ReviewComment).join(ReviewRecord).filter(
                    ReviewRecord.repo_name == repo_name,
                    ReviewComment.severity == severity,
                )
                if parsed_date_from:
                    count = count.filter(ReviewRecord.created_at >= parsed_date_from)
                if parsed_date_to:
                    count = count.filter(ReviewRecord.created_at <= parsed_date_to)
                severity_counts[severity.upper()] = count.count()

            # Average rating for this repo
            average_rating = None
            feedback_subquery = db.query(ReviewFeedback).join(ReviewRecord).filter(
                ReviewRecord.repo_name == repo_name
            )
            if parsed_date_from:
                feedback_subquery = feedback_subquery.filter(ReviewRecord.created_at >= parsed_date_from)
            if parsed_date_to:
                feedback_subquery = feedback_subquery.filter(ReviewRecord.created_at <= parsed_date_to)
            feedback_records = feedback_subquery.all()

            if feedback_records:
                avg_rating = sum(f.rating for f in feedback_records) / len(feedback_records)
                average_rating = round(avg_rating, 2)

            # Last review date
            last_review = repo_query.order_by(ReviewRecord.created_at.desc()).first()
            last_review_date = last_review.created_at.isoformat() + "Z" if last_review else None

            repo_metrics.append(
                RepoMetricsResponse(
                    repo_name=repo_name,
                    review_count=review_count,
                    success_rate=round(success_rate, 2),
                    average_latency_ms=round(float(avg_latency), 2),
                    average_rating=average_rating,
                    cache_hit_rate=round(cache_hit_rate, 2),
                    total_comments=total_comments,
                    comments_by_severity=severity_counts,
                    last_review_date=last_review_date,
                )
            )

        # Sort by review_count descending (most active repos first)
        repo_metrics.sort(key=lambda x: x.review_count, reverse=True)

        logger.info(f"Generated analytics for {len(repo_metrics)} repos")

        return AnalyticsByRepoResponse(data=repo_metrics)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analytics by repo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics", headers={"code": "INTERNAL_ERROR"})
