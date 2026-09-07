import io
import logging
from typing import List, Dict, Any, Tuple
from pypdf import PdfReader
import docx
from langchain_text_splitters import RecursiveCharacterTextSplitter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentParser:
    """
    DocumentParser:
    Extracts text and page numbers from large PDF and DOCX files (500+ pages)
    and splits them into semantically meaningful chunks with metadata for RAG.
    """

    def __init__(self, chunk_size: int = 2500, chunk_overlap: int = 250):
        """
        chunk_size: Maximum characters in each chunk (~500 words).
        chunk_overlap: Shared characters between consecutive chunks so context isn't lost.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def extract_from_pdf(self, file_bytes: bytes) -> Tuple[List[Dict[str, Any]], int]:
        """
        Reads a PDF page-by-page from memory.
        Returns:
            - List of dicts: [{'page_number': int, 'text': str}, ...]
            - Total page count
        """
        logger.info("Parsing PDF document...")
        pages_content = []
        total_pages = 0

        # Try ultra-fast C-based PyMuPDF first
        try:
            import pymupdf
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
            total_pages = len(doc)
            for page_idx in range(total_pages):
                page = doc[page_idx]
                text = page.get_text()
                if text and text.strip():
                    pages_content.append({
                        "page_number": page_idx + 1,  # 1-indexed page number
                        "text": text.strip()
                    })
            doc.close()
            logger.info(f"PyMuPDF parsed {len(pages_content)} text pages from {total_pages} total pages in milliseconds.")
            return pages_content, total_pages
        except Exception as e:
            logger.warning(f"PyMuPDF parsing encountered an issue ({e}). Falling back to pypdf...")

        # Fallback to pypdf if fitz encounters an unexpected format
        pdf_file = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_file)
        total_pages = len(reader.pages)
        pages_content = []

        for page_idx, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                pages_content.append({
                    "page_number": page_idx + 1,  # 1-indexed page number
                    "text": text.strip()
                })

        logger.info(f"Successfully extracted {len(pages_content)} text pages from {total_pages} total pages via pypdf.")
        return pages_content, total_pages

    def extract_from_docx(self, file_bytes: bytes) -> Tuple[List[Dict[str, Any]], int]:
        """
        Reads a Word .docx document from memory.
        Returns:
            - List of dicts grouped into virtual pages/sections
            - Estimated total page count
        """
        logger.info("Parsing DOCX document...")
        docx_file = io.BytesIO(file_bytes)
        doc = docx.Document(docx_file)

        full_text = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                full_text.append(paragraph.text.strip())

        combined_text = "\n\n".join(full_text)
        
        # In DOCX there are no hard page breaks, so we estimate 1 page ~= 3,000 characters
        chars_per_page = 3000
        total_pages = max(1, len(combined_text) // chars_per_page + (1 if len(combined_text) % chars_per_page else 0))
        
        pages_content = []
        for i in range(total_pages):
            start = i * chars_per_page
            end = start + chars_per_page
            page_snippet = combined_text[start:end]
            if page_snippet.strip():
                pages_content.append({
                    "page_number": i + 1,
                    "text": page_snippet.strip()
                })

        logger.info(f"Successfully extracted {len(pages_content)} sections from DOCX (estimated {total_pages} pages).")
        return pages_content, total_pages

    def parse_document(self, file_bytes: bytes, filename: str) -> Tuple[List[Dict[str, Any]], int, str]:
        """
        Master method: Automatically detects whether the file is PDF or DOCX,
        routes it to the correct extractor, and returns:
            - pages_content: List of extracted pages with text and page numbers
            - total_pages: Total or estimated page count
            - file_type: 'pdf' or 'docx'
        """
        fname_lower = filename.lower()
        if fname_lower.endswith(".pdf"):
            pages_content, total_pages = self.extract_from_pdf(file_bytes)
            return pages_content, total_pages, "pdf"
        elif fname_lower.endswith(".docx") or fname_lower.endswith(".doc"):
            pages_content, total_pages = self.extract_from_docx(file_bytes)
            return pages_content, total_pages, "docx"
        else:
            raise ValueError("Unsupported file format. Please upload a PDF (.pdf) or Word document (.doc/.docx).")

    def create_chunks(self, pages_content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Splits extracted pages into smaller chunks while preserving page number citations.
        Returns:
            - List of dicts: [{'chunk_index': int, 'page_number': int, 'content': str}, ...]
        """
        all_chunks = []
        chunk_idx = 0

        for page_data in pages_content:
            page_num = page_data["page_number"]
            page_text = page_data["text"]

            # Split text of this page using LangChain splitter
            splits = self.splitter.split_text(page_text)
            for split_content in splits:
                if split_content.strip():
                    all_chunks.append({
                        "chunk_index": chunk_idx,
                        "page_number": page_num,
                        "content": split_content.strip()
                    })
                    chunk_idx += 1

        logger.info(f"Created {len(all_chunks)} semantic chunks for vector storage.")
        return all_chunks


# Instantiate a parser for reuse across the app
document_parser = DocumentParser()
