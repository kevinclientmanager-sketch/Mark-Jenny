from sqlalchemy import inspect
from app.db.base import engine, Base
from app.models import *
from app.core.config import get_settings

settings = get_settings()


def init_db() -> None:
    """Initialize database tables (creates any missing ones, keeps existing data)."""
    # create_all with checkfirst=True only adds missing tables — safe on existing DBs
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("Database tables ensured successfully!")


def drop_db() -> None:
    """Drop all database tables."""
    print("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    print("Database tables dropped!")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "drop":
        drop_db()
    else:
        init_db()