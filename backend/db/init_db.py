import logging
from sqlalchemy import text
from backend.db.session import engine, Base
from backend.models.models import User, Book, BookChunk, ChatHistory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db() -> None:
    """
    Initializes the Supabase PostgreSQL database:
    1. Enables the 'vector' extension (mandatory for pgvector RAG).
    2. Automatically creates all 4 tables (users, books, book_chunks, chat_history)
       if they do not already exist.
    """
    logger.info("Connecting to Supabase PostgreSQL...")

    with engine.connect() as connection:
        # Step 1: Enable the pgvector extension in PostgreSQL
        logger.info("Enabling 'vector' extension in PostgreSQL (if not already enabled)...")
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        connection.commit()
        logger.info("pgvector extension verified successfully!")

    # Step 2: Create all database tables defined in models.py
    logger.info("Creating database tables if they do not exist...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created successfully!")


if __name__ == "__main__":
    init_db()
