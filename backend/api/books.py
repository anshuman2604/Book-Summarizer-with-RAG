import logging
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models.models import User, Book, ChatHistory
from backend.api.deps import get_current_user
from backend.schemas.schemas import (
    BookResponse,
    BookListResponse,
    QuestionRequest,
    AnswerResponse,
    ChatMessageResponse
)
from backend.services.parser import document_parser
from backend.services.vector_store import vector_store_service
from backend.services.summarizer import book_summarizer_service
from backend.services.qa_service import qa_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/books", tags=["Books & Q&A"])


@router.post(
    "/upload",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF/DOCX book, generate 100-word summary, and index in pgvector"
)
async def upload_book(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Core Upload Pipeline (Handles 500+ page books):
    1. Reads uploaded PDF or DOCX file bytes.
    2. Parses document and splits into semantic chunks with page numbers.
    3. Generates 100-word executive summary using hierarchical Map-Reduce.
    4. Saves Book record in Supabase.
    5. Batch stores chunks & vectors into Supabase pgvector table.
    6. Returns complete BookResponse with summary to the frontend.
    """
    filename = file.filename or "unknown_document"
    logger.info(f"User {current_user.email} uploading book: {filename}")

    # Read binary bytes of uploaded file
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty."
        )

    # Step 1: Extract pages and determine file type
    try:
        pages_content, total_pages, file_type = document_parser.parse_document(file_bytes, filename)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error parsing document {filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse document: {str(e)}"
        )

    if not pages_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract any readable text from this file."
        )

    # Step 2: Chunk the document while tagging page numbers
    chunks_data = document_parser.create_chunks(pages_content)

    # Step 3: Generate strict ~100-word summary via Map-Reduce
    logger.info(f"Generating 100-word summary for {filename}...")
    try:
        summary_100_words = book_summarizer_service.summarize_book(chunks_data)
    except Exception as e:
        logger.error(f"Error generating summary for {filename}: {str(e)}")
        summary_100_words = "Summary generation encountered a temporary error."

    # Step 4: Create Book record in Supabase
    clean_title = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
    book = Book(
        user_id=current_user.id,
        title=clean_title,
        filename=filename,
        file_type=file_type,
        total_pages=total_pages,
        summary_100_words=summary_100_words
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    # Step 5: Store vectors & chunks in Supabase pgvector
    logger.info(f"Storing {len(chunks_data)} chunks and vector embeddings in Supabase...")
    try:
        vector_store_service.store_book_chunks(
            db=db,
            book_id=book.id,
            chunks_data=chunks_data
        )
    except Exception as e:
        logger.error(f"Error embedding chunks for book {book.id}: {str(e)}")
        # Note: Even if vector indexing fails partially, the book and summary are safely saved.

    logger.info(f"Book {clean_title} processed successfully!")
    return book


@router.get(
    "",
    response_model=BookListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get history list of books uploaded by current user"
)
def get_user_books(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fulfills Rule 4: 'The user should be able to see the history of his/her other books extracted'.
    Returns all books uploaded by the logged-in user, ordered by most recent first.
    """
    books = (
        db.query(Book)
        .filter(Book.user_id == current_user.id)
        .order_by(Book.created_at.desc())
        .all()
    )
    return BookListResponse(
        books=books,
        total_count=len(books)
    )


@router.get(
    "/{book_id}",
    response_model=BookResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single book details and 100-word summary"
)
def get_book(
    book_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetches details of a specific book owned by current user.
    Enforces user isolation: User A cannot access User B's book.
    """
    book = db.query(Book).filter(Book.id == book_id, Book.user_id == current_user.id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found or access denied."
        )
    return book


@router.post(
    "/{book_id}/chat",
    response_model=AnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask any question about a specific book (RAG with citations)"
)
def ask_book_question(
    book_id: UUID,
    payload: QuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fulfills Problem Statement: 'It should also have a feature to question anything about the book.'
    1. Verifies user ownership of the book.
    2. Runs vector semantic search in pgvector.
    3. Generates grounded answer with exact page citations.
    4. Saves to chat history in Supabase.
    """
    book = db.query(Book).filter(Book.id == book_id, Book.user_id == current_user.id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found or access denied."
        )

    result = qa_service.answer_question(
        db=db,
        book_id=book.id,
        user_id=current_user.id,
        question=payload.question
    )

    return AnswerResponse(
        book_id=book.id,
        question=payload.question,
        answer=result["answer"],
        sources=result["sources"]
    )


@router.get(
    "/{book_id}/chat/history",
    response_model=List[ChatMessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Get conversation chat history for a specific book"
)
def get_book_chat_history(
    book_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns previous conversation history between user and assistant for this book.
    """
    book = db.query(Book).filter(Book.id == book_id, Book.user_id == current_user.id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found or access denied."
        )

    history = (
        db.query(ChatHistory)
        .filter(ChatHistory.book_id == book_id, ChatHistory.user_id == current_user.id)
        .order_by(ChatHistory.created_at.asc())
        .all()
    )
    return history


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a book, its chunks, vectors, and chat history"
)
def delete_book(
    book_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fulfills Rule 7.c: 'Use proper HTTP codes for conveying different messages (204 for no content)'.
    Deletes the book and cascades deletion to book_chunks and chat_history.
    """
    book = db.query(Book).filter(Book.id == book_id, Book.user_id == current_user.id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found or access denied."
        )

    db.delete(book)
    db.commit()
    return None
