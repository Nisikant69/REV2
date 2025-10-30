"""
User feedback collection and analytics for review quality improvement.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException

from backend.database import get_db_session
from backend.db_models import ReviewRecord, ReviewFeedback
from backend.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class FeedbackRequest:
    """Request model for feedback submission."""

    def __init__(self, rating: int, is_helpful: bool, comment: Optional[str] = None):
        """
        Initialize feedback request.

        Args:
            rating: Rating from 1-5
            is_helpful: Whether the review was helpful
            comment: Optional feedback comment
        """
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")

        self.rating = rating
        self.is_helpful = is_helpful
        self.comment = comment


@router.post("/api/reviews/{review_id}/feedback")
async def submit_feedback(
    review_id: str,
    rating: int,
    is_helpful: bool,
    comment: Optional[str] = None,
    db: Session = Depends(get_db_session),
):
    """
    Submit feedback for a review.

    Args:
        review_id: ID of the review
        rating: Rating from 1-5
        is_helpful: Whether review was helpful
        comment: Optional feedback comment
    """
    try:
        # Validate review exists
        review = db.query(ReviewRecord).filter_by(id=review_id).first()
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        # Validate feedback
        try:
            feedback_request = FeedbackRequest(
                rating=rating,
                is_helpful=is_helpful,
                comment=comment,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Create feedback record
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
            rating=rating,
            helpful=is_helpful,
        )

        return {
            "status": "success",
            "feedback_id": feedback.id,
            "created_at": feedback.created_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to submit feedback")


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
