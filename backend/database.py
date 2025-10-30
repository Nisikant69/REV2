"""
Database initialization and session management for REV2.
Supports SQLite (development) and PostgreSQL (production).
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from typing import Generator

# Import models
from backend.db_models import Base

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./rev2.db"
)

# Create engine
if "postgresql" in DATABASE_URL or "postgres" in DATABASE_URL:
    # PostgreSQL
    engine = create_engine(
        DATABASE_URL,
        pool_size=int(os.getenv("DATABASE_POOL_SIZE", 10)),
        max_overflow=20,
        echo=os.getenv("DATABASE_ECHO", "False").lower() == "true",
    )
else:
    # SQLite
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=os.getenv("DATABASE_ECHO", "False").lower() == "true",
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session() -> Generator:
    """
    Dependency for FastAPI to get database session.
    Usage in routes:
        def my_route(db: Session = Depends(get_db_session)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def drop_db():
    """Drop all database tables (for testing)."""
    Base.metadata.drop_all(bind=engine)
