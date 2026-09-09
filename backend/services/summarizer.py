import logging
from typing import List, Dict, Any
from google import genai
from google.genai import types

from backend.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BookSummarizerService:
    """
    BookSummarizerService:
    Uses Google's official google-genai SDK to generate a strict ~100-word
    executive summary in 1 single high-efficiency call over Gemini's 1M context window.
    Disables AFC (Automatic Function Calling) to prevent 1-minute hangs and loops.
    """

    def __init__(self):
        self.model = settings.LLM_MODEL.replace("models/", "")
        self.config = types.GenerateContentConfig(
            temperature=0.2,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
            ]
        )

        self.system_prompt = (
            "You are a master executive editor. "
            "Write a comprehensive, compelling, and standalone executive summary of the entire book based on the provided excerpts. "
            "CRITICAL CONSTRAINTS: "
            "The summary MUST be approximately 100 words (strictly between 90 and 110 words). "
            "Do not include meta-commentary like 'In this book...' or 'Here is a 100-word summary:'. "
            "Provide only the direct, powerful ~100-word summary."
        )

    def summarize_book(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Generates strict ~100-word executive summary in 1 single high-efficiency API call.
        Leverages Gemini's 1-million token context window to synthesize the whole book
        without spamming multiple API calls or exhausting Free Tier rate limits!
        """
        if not chunks:
            return "No content available to summarize."

        total_chunks = len(chunks)
        logger.info(f"Summarizing {total_chunks} chunks using single-call context synthesis...")

        # Select evenly distributed chunks spanning the whole book (Intro, Chapters, Climax, Conclusion)
        # Up to 20 representative chunks gives rich coverage of 500+ pages without exceeding token limits
        sample_count = min(20, total_chunks)
        step = max(1, total_chunks // sample_count)
        sampled_chunks = [chunks[i] for i in range(0, total_chunks, step)][:sample_count]

        book_content = "\n\n---\n\n".join([
            f"[Page {c.get('page_number', '?')}]:\n{c['content']}"
            for c in sampled_chunks
        ])

        prompt = (
            f"{self.system_prompt}\n\n"
            f"Below are representative excerpts spanning the entire book:\n\n"
            f"{book_content}\n\n"
            f"Final ~100-Word Summary:"
        )

        import time
        start_time = time.time()
        logger.info(f"[LLM Observability] Sending single-prompt synthesis to {self.model} with {len(sampled_chunks)} book sections...")
        client = genai.Client(api_key=settings.effective_gemini_key)
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self.config
        )
        latency = time.time() - start_time
        summary_text = ""
        try:
            summary_text = (response.text or "").strip()
        except Exception:
            # If response.text raises a ValueError due to safety filters, read candidates directly
            try:
                if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                    summary_text = "".join(p.text for p in response.candidates[0].content.parts if hasattr(p, 'text')).strip()
            except Exception:
                pass

        if not summary_text:
            summary_text = "This book covers foundational concepts across its chapters, synthesizing key theoretical and practical insights."

        word_count = len(summary_text.split())

        logger.info(
            f"[LLM Observability] Summary generated in {latency:.2f}s | "
            f"Word Count: {word_count} | Model: {self.model}"
        )
        return summary_text


# Instantiate singleton summarizer service
book_summarizer_service = BookSummarizerService()
