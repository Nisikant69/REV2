"""
User feedback collection and analytics for review quality improvement.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Header

from backend.database import get_db_session
from backend.db_models import ReviewRecord, ReviewFeedback
from backend.logger import get_logger
from backend.auth import validate_api_key

logger = get_logger(__name__)
router = APIRouter()


class FeedbackRequest(BaseModel):
    """Request model for feedback submission."""
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    is_helpful: bool
    comment: Optional[str] = Field(None, max_length=500, description="Optional feedback comment (max 500 chars)")


class FeedbackResponse(BaseModel):
    """Response model for feedback submission."""
    feedback_id: str
    created_at: str
    updated_at: Optional[str] = None


@router.post("/api/reviews/{review_id}/feedback")
async def submit_feedback(
    review_id: str,
    feedback_request: FeedbackRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db_session),
) -> dict:
    """
    Submit or update user feedback on a review.

    Path Parameters:
        review_id: ID of the review

    Request Body:
        rating: Rating from 1-5
        is_helpful: Whether review was helpful
        comment: Optional feedback comment (max 500 chars)

    Returns:
        - 201 if new feedback created
        - 200 if existing feedback updated
    """
    try:
        # Validate API key if provided
        if authorization:
            validate_api_key(authorization)
        else:
            raise HTTPException(status_code=401, detail="Missing Authorization header")

        # Validate review exists
        review = db.query(ReviewRecord).filter_by(id=review_id).first()
        if not review:
            raise HTTPException(
                status_code=404,
                detail="Review not found",
                headers={"code": "NOT_FOUND"}
            )

        # Check if feedback already exists for this review
        existing_feedback = db.query(ReviewFeedback).filter_by(review_record_id=review_id).first()

        if existing_feedback:
            # Update existing feedback
            existing_feedback.rating = feedback_request.rating
            existing_feedback.is_helpful = feedback_request.is_helpful
            existing_feedback.comment = feedback_request.comment
            db.commit()

            logger.info(
                "Feedback updated",
                review_id=review_id,
                rating=feedback_request.rating,
                helpful=feedback_request.is_helpful,
            )

            return {
                "feedback_id": existing_feedback.id,
                "created_at": existing_feedback.created_at.isoformat() + "Z",
                "updated_at": existing_feedback.updated_at.isoformat() + "Z" if hasattr(existing_feedback, 'updated_at') else None,
                "status": "updated"
            }
        else:
            # Create new feedback
            feedback = ReviewFeedback(
                review_record_id=review_id,
                rating=feedback_request.rating,
                is_helpful=feedback_request.is_helpful,
                comment=feedback_request.comment,
            )

            db.add(feedback)
            db.commit()

            logger.info(
                "Feedback submitted",
                review_id=review_id,
                rating=feedback_request.rating,
                helpful=feedback_request.is_helpful,
            )

            return {
                "feedback_id": feedback.id,
                "created_at": feedback.created_at.isoformat() + "Z",
                "status": "created"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to submit feedback",
            headers={"code": "INTERNAL_ERROR"}
        )


@router.get("/api/reviews/{review_id}/feedback")
async def get_review_feedback(
    review_id: str,
    db: Session = Depends(get_db_session),
):
    """
    Get all feedback for a review.

    Args:
        review_id: ID of the review

    Returns:
        List of feedback records
    """
    try:
        feedback_list = db.query(ReviewFeedback).filter_by(
            review_record_id=review_id
        ).all()

        return {
            "review_id": review_id,
            "feedback_count": len(feedback_list),
            "feedback": [
                {
                    "id": f.id,
                    "rating": f.rating,
                    "is_helpful": f.is_helpful,
                    "comment": f.comment,
                    "created_at": f.created_at.isoformat(),
                }
                for f in feedback_list
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get feedback")


@router.get("/api/reviews/analytics/feedback")
async def feedback_analytics(
    db: Session = Depends(get_db_session),
):
    """
    Get feedback analytics across all reviews.

    Returns:
        Analytics summary
    """
    try:
        # Get all feedback
        all_feedback = db.query(ReviewFeedback).all()

        if not all_feedback:
            return {
                "total_feedback": 0,
                "average_rating": 0,
                "helpful_percentage": 0,
                "feedback_by_rating": {},
            }

        # Calculate statistics
        ratings = [f.rating for f in all_feedback]
        helpful_count = sum(1 for f in all_feedback if f.is_helpful)

        average_rating = sum(ratings) / len(ratings) if ratings else 0
        helpful_percentage = (helpful_count / len(all_feedback)) * 100 if all_feedback else 0

        # Feedback by rating
        feedback_by_rating = {}
        for i in range(1, 6):
            feedback_by_rating[i] = sum(1 for f in all_feedback if f.rating == i)

        logger.info(
            "Feedback analytics generated",
            total_feedback=len(all_feedback),
            avg_rating=average_rating,
        )

        return {
            "total_feedback": len(all_feedback),
            "average_rating": round(average_rating, 2),
            "helpful_percentage": round(helpful_percentage, 2),
            "feedback_by_rating": feedback_by_rating,
        }

    except Exception as e:
        logger.error(f"Failed to generate feedback analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate analytics")


@router.get("/api/reviews/analytics/quality")
async def review_quality_analytics(
    db: Session = Depends(get_db_session),
):
    """
    Analyze review quality based on feedback.

    Returns:
        Quality metrics and trends
    """
    try:
        from sqlalchemy import func

        # Calculate metrics
        total_reviews = db.query(ReviewRecord).count()
        successful_reviews = db.query(ReviewRecord).filter_by(
            review_status="success"
        ).count()

        # Average latency
        avg_latency = db.query(func.avg(ReviewRecord.api_latency_ms)).scalar() or 0

        # Cache hit rate
        cache_hits = db.query(ReviewRecord).filter_by(cache_hit=True).count()
        cache_hit_rate = (cache_hits / total_reviews * 100) if total_reviews > 0 else 0

        # Feedback correlation
        reviews_with_feedback = (
            db.query(ReviewRecord)
            .join(ReviewFeedback)
            .distinct()
            .count()
        )

        logger.info(
            "Quality analytics generated",
            total_reviews=total_reviews,
            success_rate=successful_reviews / total_reviews if total_reviews > 0 else 0,
        )

        return {
            "total_reviews": total_reviews,
            "successful_reviews": successful_reviews,
            "success_rate": (
                successful_reviews / total_reviews if total_reviews > 0 else 0
            ),
            "average_latency_ms": round(avg_latency, 2),
            "cache_hit_rate": round(cache_hit_rate, 2),
            "reviews_with_feedback": reviews_with_feedback,
        }

    except Exception as e:
        logger.error(f"Failed to generate quality analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate analytics")
