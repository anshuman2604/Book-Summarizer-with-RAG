import logging
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy.orm import Session
from google import genai
from google.genai import types
from langsmith import traceable

from backend.core.config import settings
from backend.services.vector_store import vector_store_service
from backend.models.models import ChatHistory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QAService:
    """
    QAService:
    Implements the Retrieval-Augmented Generation (RAG) Question-Answering agent.
    1. Uses pgvector to retrieve the top relevant book chunks.
    2. Builds a grounded prompt with exact page citations.
    3. Generates accurate, non-hallucinated answers using Google's modern google-genai SDK.
    4. Persists the conversation in the Supabase 'chat_history' table.
    """

    def __init__(self):
        self.client = genai.Client(api_key=settings.effective_gemini_key)
        self.model = settings.LLM_MODEL.replace("models/", "")
        self.config = types.GenerateContentConfig(
            temperature=0.3,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        )

    @traceable(name="rag_qa_agent", run_type="chain")
    def answer_question(
        self,
        db: Session,
        book_id: UUID,
        user_id: UUID,
        question: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Executes the full RAG pipeline for a user question on a specific book:
        - Vector search in pgvector
        - LLM response generation with page citations
        - Saves user query and assistant response to Supabase chat_history
        """
        logger.info(f"Processing question for book {book_id}: '{question}'")

        # Step 1: Semantic search in pgvector
        relevant_chunks = vector_store_service.search_similar_chunks(
            db=db,
            book_id=book_id,
            query=question,
            top_k=top_k
        )

        if not relevant_chunks:
            return {
                "answer": "No relevant content found in this book to answer your question.",
                "sources": []
            }

        # Step 2: Format context with page numbers for the LLM
        formatted_context_list = []
        sources = []
        for c in relevant_chunks:
            page_str = f"Page {c['page_number']}" if c.get('page_number') else "Unknown Page"
            formatted_context_list.append(f"[{page_str}]:\n{c['content']}")
            sources.append({
                "page_number": c.get("page_number"),
                "snippet": c["content"][:150] + "..."
            })

        combined_context = "\n\n".join(formatted_context_list)

        # Step 3: Call Google GenAI SDK
        prompt = (
            "You are a helpful, knowledgeable AI assistant for analyzing books.\n"
            "Use the following retrieved excerpts from the book to answer the user's question.\n\n"
            "STRICT INSTRUCTIONS:\n"
            "1. Base your answer ONLY on the provided context excerpts below. Do not make up information.\n"
            "2. ALWAYS cite the exact page numbers from which you retrieved your information (e.g., 'According to Page 14...', or '[Page 88]').\n"
            "3. If the provided context does not contain enough information to answer the question, clearly state: 'The provided book text does not contain sufficient information to answer this question.'\n\n"
            f"--- RETRIEVED BOOK CONTEXT ---\n{combined_context}\n\n"
            f"--- USER QUESTION ---\n{question}\n\n"
            "--- HELPFUL ANSWER WITH PAGE CITATIONS ---"
        )

        import time
        start_time = time.time()
        logger.info(f"[LLM Observability] Querying {self.model} with {len(top_chunks)} retrieved context chunks...")

        client = genai.Client(api_key=settings.effective_gemini_key)
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self.config
        )
        latency = time.time() - start_time
        answer_text = response.text.strip()

        logger.info(
            f"[LLM Observability] Answer generated in {latency:.2f}s | "
            f"Context Chunks: {len(top_chunks)} | Model: {self.model}"
        )

        # Step 4: Persist chat messages to Supabase database
        user_msg = ChatHistory(
            book_id=book_id,
            user_id=user_id,
            role="user",
            content=question
        )
        assistant_msg = ChatHistory(
            book_id=book_id,
            user_id=user_id,
            role="assistant",
            content=answer_text
        )
        db.add_all([user_msg, assistant_msg])
        db.commit()

        logger.info(f"Q&A completed and saved to history for book {book_id}.")
        return {
            "answer": answer_text,
            "sources": sources
        }


# Instantiate singleton QA service
qa_service = QAService()
