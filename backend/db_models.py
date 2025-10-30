"""
SQLAlchemy data models for REV2.
Tracks review history, comments, cache metadata, and user feedback.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Float,
    Text,
    DateTime,
    ForeignKey,
    Enum,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship
from enum import Enum as PyEnum

Base = declarative_base()


class ReviewStatus(PyEnum):
    """Status of a review."""
    SUCCESS = "success"
    PARTIAL_FAILURE = "partial_failure"
    FAILURE = "failure"


class CommentSeverity(PyEnum):
    """Severity level of a review comment."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class ReviewRecord(Base):
    """
    Record of a code review performed by REV2.
    Tracks metrics and status for analytics and debugging.
    """

    __tablename__ = "review_records"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    installation_id = Column(String(50), nullable=False, index=True)
    repo_name = Column(String(255), nullable=False, index=True)
    pr_number = Column(Integer, nullable=False)
    pr_url = Column(String(512), nullable=False)
    commit_sha = Column(String(40), nullable=False, index=True)
    files_reviewed = Column(Integer, default=0)
    review_status = Column(
        Enum(ReviewStatus),
        default=ReviewStatus.SUCCESS,
        nullable=False,
    )
    total_comments = Column(Integer, default=0)
    api_latency_ms = Column(Integer, nullable=True)
    cache_hit = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    comments = relationship("ReviewComment", back_populates="review_record")
    feedback = relationship("ReviewFeedback", back_populates="review_record")

    __table_args__ = (
        Index("idx_repo_created", "repo_name", "created_at"),
        Index("idx_installation_created", "installation_id", "created_at"),
    )


class ReviewComment(Base):
    """
    Individual comment from a code review.
    Linked to a specific file and line in the PR.
    """

    __tablename__ = "review_comments"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    review_record_id = Column(
        String(36),
        ForeignKey("review_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path = Column(String(512), nullable=False)
    line_number = Column(Integer, nullable=True)  # Can be null for file-level comments
    severity = Column(
        Enum(CommentSeverity),
        default=CommentSeverity.INFO,
        nullable=False,
    )
    comment_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    review_record = relationship("ReviewRecord", back_populates="comments")


class IndexCache(Base):
    """
    Metadata about cached FAISS indexes.
    Used for TTL management and cleanup.
    """

    __tablename__ = "index_cache"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    repo_name = Column(String(255), nullable=False, index=True)
    commit_sha = Column(String(40), nullable=False, index=True)
    index_file_path = Column(String(512), nullable=False, unique=True)
    file_count = Column(Integer, default=0)
    total_size_bytes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_accessed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ttl_days = Column(Integer, default=30)

    __table_args__ = (
        Index("idx_repo_commit", "repo_name", "commit_sha", unique=True),
        Index("idx_created_at", "created_at"),
    )


class ReviewFeedback(Base):
    """
    User feedback on review quality.
    Used to improve review prompts and quality over time.
    """

    __tablename__ = "review_feedback"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    review_record_id = Column(
        String(36),
        ForeignKey("review_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rating = Column(Integer, nullable=False)  # 1-5 rating
    is_helpful = Column(Boolean, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    review_record = relationship("ReviewRecord", back_populates="feedback")
