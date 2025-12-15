"""Database session management."""
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base
from ..config.settings import settings

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=settings.DEBUG,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """
    Initialize database tables.
    
    Creates all tables defined in models.py if they don't exist.
    """
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """
    Get database session.
    
    Usage:
        db = get_db()
        try:
            # use db
        finally:
            db.close()
    """
    db = SessionLocal()
    return db


@contextmanager
def get_db_context():
    """
    Database session context manager.
    
    Usage:
        with get_db_context() as db:
            # use db
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def get_db_async():
    """
    Async database session dependency for FastAPI.
    
    Usage in FastAPI:
        @app.get("/items")
        async def get_items(db: Session = Depends(get_db_async)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
