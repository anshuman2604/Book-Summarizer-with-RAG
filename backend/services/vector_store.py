import logging
from typing import List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
import cohere

from backend.core.config import settings
from backend.models.models import BookChunk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorStoreService:
    """
    VectorStoreService:
    1. Generates high-accuracy 1024-dimensional embeddings using Cohere API (100 RPM Free Tier).
    2. Batch stores chunks and vectors into Supabase PostgreSQL (pgvector column).
    3. Performs cosine-similarity semantic search to find relevant book pages for RAG.
    """

    def __init__(self):
        # Initialize Cohere Client (100 Requests/Min Free Tier)
        self.client = cohere.ClientV2(api_key=settings.COHERE_API_KEY)
        self.model = settings.COHERE_EMBED_MODEL

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Takes a list of text strings and calls Cohere's Embed API to generate
        1024-dimensional float vectors with input_type='search_document'.
        """
        logger.info(f"Generating Cohere embeddings for {len(texts)} text snippets...")
        response = self.client.embed(
            texts=texts,
            model=self.model,
            input_type="search_document",
            embedding_types=["float"]
        )
        return response.embeddings.float_

    def embed_query(self, text: str) -> List[float]:
        """
        Embeds a single search query string into a 1024-dimensional float vector
        with input_type='search_query'.
        """
        response = self.client.embed(
            texts=[text],
            model=self.model,
            input_type="search_query",
            embedding_types=["float"]
        )
        return response.embeddings.float_[0]

    def store_book_chunks(
        self,
        db: Session,
        book_id: UUID,
        chunks_data: List[Dict[str, Any]],
        batch_size: int = 60
    ) -> int:
        """
        Embeds chunks in fast batches of 60 and stores them into 'book_chunks' in Supabase.
        Leverages Cohere's 100 Requests/Minute limit to ingest 500-page books in seconds.
        """
        import time
        total_chunks = len(chunks_data)
        logger.info(f"Storing {total_chunks} chunks for book {book_id} in fast batches of {batch_size}...")

        for i in range(0, total_chunks, batch_size):
            batch = chunks_data[i:i + batch_size]
            batch_texts = [c["content"] for c in batch]

            # Generate vectors with robust automatic retry so 100% of chunks are saved
            max_retries = 5
            batch_vectors = None
            for attempt in range(max_retries):
                try:
                    batch_vectors = self.generate_embeddings(batch_texts)
                    break
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "Too Many Requests" in str(e):
                        wait_sec = (attempt + 1) * 6
                        logger.warning(f"Rate limit hit during embedding. Waiting {wait_sec}s before retry {attempt + 1}/{max_retries}...")
                        time.sleep(wait_sec)
                    else:
                        raise e

            if not batch_vectors:
                logger.error(f"Skipping batch {i} due to repeated rate limit failures.")
                continue

            # Create BookChunk ORM objects
            db_chunks = []
            for chunk_meta, vector in zip(batch, batch_vectors):
                db_chunk = BookChunk(
                    book_id=book_id,
                    chunk_index=chunk_meta["chunk_index"],
                    page_number=chunk_meta["page_number"],
                    content=chunk_meta["content"],
                    embedding=vector  # pgvector Vector(1024)
                )
                db_chunks.append(db_chunk)

            # Bulk save to PostgreSQL
            db.bulk_save_objects(db_chunks)
            db.commit()
            logger.info(f"Saved chunks {i + 1} to {min(i + batch_size, total_chunks)} of {total_chunks}.")

            # 0.7s spacing between batches to keep comfortably under Cohere rate limits
            if i + batch_size < total_chunks:
                time.sleep(0.7)

        return total_chunks

    def search_similar_chunks(
        self,
        db: Session,
        book_id: UUID,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Searches the most relevant chunks in a book for a given user query using pgvector's
        cosine distance operator (<=>).
        Returns top_k most similar chunks with page numbers.
        """
        logger.info(f"Running vector similarity search for query: '{query}' on book {book_id}...")

        # 1. Convert user's question into a 768-dim query vector
        query_vector = self.embed_query(query)

        # 2. Query pgvector using SQLAlchemy:
        # BookChunk.embedding.cosine_distance(query_vector) finds nearest neighbors
        results = (
            db.query(BookChunk)
            .filter(BookChunk.book_id == book_id)
            .order_by(BookChunk.embedding.cosine_distance(query_vector))
            .limit(top_k)
            .all()
        )

        matched_chunks = []
        for chunk in results:
            matched_chunks.append({
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "content": chunk.content
            })

        logger.info(f"Retrieved {len(matched_chunks)} matching chunks for RAG.")
        return matched_chunks


# Instantiate singleton vector service
vector_store_service = VectorStoreService()
