from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


# ==========================================
# 1. User & Authentication Schemas
# ==========================================

class UserRegisterRequest(BaseModel):
    """Schema for registering a new user."""
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")


class UserLoginRequest(BaseModel):
    """Schema for user login with email and password."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for returning the JWT access token to the browser."""
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    email: str


class UserResponse(BaseModel):
    """Schema for returning user details."""
    id: UUID
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# 2. Book Schemas
# ==========================================

class BookResponse(BaseModel):
    """Schema for returning book metadata and the 100-word summary."""
    id: UUID
    title: str
    filename: str
    file_type: str
    total_pages: int
    summary_100_words: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BookListResponse(BaseModel):
    """Schema for returning the history list of books for the logged-in user."""
    books: List[BookResponse]
    total_count: int


# ==========================================
# 3. Chat & Q&A Schemas
# ==========================================

class QuestionRequest(BaseModel):
    """Schema for asking a question about an uploaded book."""
    question: str = Field(..., min_length=2, description="The question text to ask about the book")


class SourceSnippet(BaseModel):
    """Schema for a cited source page snippet."""
    page_number: Optional[int]
    snippet: str


class AnswerResponse(BaseModel):
    """Schema for returning the RAG answer with page citations."""
    book_id: UUID
    question: str
    answer: str
    sources: List[SourceSnippet]


class ChatMessageResponse(BaseModel):
    """Schema for returning past conversation messages for a book."""
    id: UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
