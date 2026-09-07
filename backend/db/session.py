from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import NullPool
from backend.core.config import settings

# 1. Supabase-Dedicated Database Engine
# Supabase uses PgBouncer on port 6543 (Transaction Pooler Mode).
# We configure NullPool so SQLAlchemy doesn't conflict with Supabase's pooler.
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
    connect_args={
        'connect_timeout': 15,
        'options': '-c statement_timeout=60000'  # 60s timeout protection
    },
    echo=False
)

# 2. SessionLocal factory
# Creates an isolated session for each incoming request
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# 3. Base class for all ORM models (Users, Books, BookChunks, ChatHistory)
Base = declarative_base()


# 4. Dependency function for FastAPI routes
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that opens a database session for a request
    and guarantees that the session is closed when the request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
