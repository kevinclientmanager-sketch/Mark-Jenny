from sqlalchemy import inspect
from app.db.base import engine, Base
from app.models import *
from app.core.config import get_settings

settings = get_settings()


def init_db() -> None:
    """Initialize database tables."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    if not existing_tables:
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully!")
    else:
        print(f"Database already exists with tables: {existing_tables}")


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