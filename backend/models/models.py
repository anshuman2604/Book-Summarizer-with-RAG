import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from backend.db.session import Base

# Note: Cohere embed-english-v3.0 produces high-accuracy 1024-dimensional vector embeddings.
# pgvector stores these vectors in a dedicated column for cosine similarity search.
EMBEDDING_DIMENSION = 1024


class User(Base):
    """
    User Table: Stores registered user credentials and login sessions.
    Guarantees user isolation so each user can only see their own books & chats.
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship: A user can upload many books
    books = relationship("Book", back_populates="owner", cascade="all, delete-orphan")


class Book(Base):
    """
    Book Table: Stores extracted books, file metadata, and the final 100-word summary.
    Allows users to see their complete history of past uploaded books.
    """
    __tablename__ = "books"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    filename = Column(String(500), nullable=False)
    file_type = Column(String(10), nullable=False)  # 'pdf' or 'docx'
    total_pages = Column(Integer, default=0, nullable=False)
    summary_100_words = Column(Text, nullable=True)  # Strictly ~100-word executive summary
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    owner = relationship("User", back_populates="books")
    chunks = relationship("BookChunk", back_populates="book", cascade="all, delete-orphan")
    chat_history = relationship("ChatHistory", back_populates="book", cascade="all, delete-orphan")


class BookChunk(Base):
    """
    BookChunk Table: Stores chunked fragments of large 500+ page books along with
    their pgvector numerical embeddings for fast similarity retrieval (RAG).
    """
    __tablename__ = "book_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)  # Page number for citation in answers
    content = Column(Text, nullable=False)         # The raw text snippet

    # Vector Embedding Column (768 numbers for text-embedding-004)
    embedding = Column(Vector(EMBEDDING_DIMENSION), nullable=True)

    # Relationship
    book = relationship("Book", back_populates="chunks")


class ChatHistory(Base):
    """
    ChatHistory Table: Stores all user queries and agent answers for each book.
    Ensures users can revisit past questions and conversations.
    """
    __tablename__ = "chat_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)       # 'user' or 'assistant'
    content = Column(Text, nullable=False)          # Message text
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    book = relationship("Book", back_populates="chat_history")
