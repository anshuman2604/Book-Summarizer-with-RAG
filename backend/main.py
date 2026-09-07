import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.db.init_db import init_db
from backend.api.auth import router as auth_router
from backend.api.books import router as books_router

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan Event:
    Runs automatically when the server starts up and shuts down.
    Ensures pgvector extension and all database tables exist in Supabase before handling traffic.
    """
    logger.info('=' * 60)
    logger.info(f'Starting up: {settings.PROJECT_NAME}...')
    try:
        init_db()
        logger.info('Database tables & pgvector extension initialized successfully.')
    except Exception as e:
        logger.error(f'Database initialization failed on startup: {str(e)}')
    logger.info('=' * 60)

    yield  # Application is now live and accepting requests

    logger.info(f'Shutting down {settings.PROJECT_NAME}...')


# Initialize FastAPI Application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description='''
## AI Agentic Book Summarizer and Query System
Takes entire books (500+ page PDFs/DOCs) as input and outputs a strict ~100-word executive summary.
Allows users to ask questions about the book with grounded page citations using RAG and pgvector.
''',
    version='1.0.0',
    docs_url='/docs',        # Interactive Swagger UI documentation
    redoc_url='/redoc',      # ReDoc alternative documentation
    lifespan=lifespan
)

# Configure CORS (Cross-Origin Resource Sharing)
# Allows the Next.js frontend to communicate seamlessly with this backend
origins = [
    'http://localhost:3000',      # Local Next.js dev server
    'http://localhost:3001',
    'https://*.vercel.app',       # Production Vercel deployments
    '*'                           # Allow all during prototyping/grading
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Mount API Routers under /api/v1 prefix
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(books_router, prefix=settings.API_V1_STR)


@app.get('/', tags=['Health'])
def root():
    '''Root endpoint: returns system status and documentation link.'''
    return {
        'message': f'Welcome to {settings.PROJECT_NAME} API',
        'docs': '/docs',
        'health': '/health'
    }


@app.get('/health', tags=['Health'])
def health_check():
    '''Health check endpoint used by cloud hosts (like Render) to verify uptime.'''
    return {
        'status': 'healthy',
        'project': settings.PROJECT_NAME,
        'llm_model': settings.LLM_MODEL,
        'embedding_model': settings.EMBEDDING_MODEL
    }
