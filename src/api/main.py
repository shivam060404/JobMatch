import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.exceptions import AppException
from src.api.routes import candidates, feedback, jobs, recommendations, weights
from src.database import Database
from src.embedding import EmbeddingService
from src.ranking import RankingEngine
from src.recommendation import RecommendationGenerator
from src.vector_store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

db: Optional[Database] = None
vector_store: Optional[VectorStore] = None
embedding_service: Optional[EmbeddingService] = None
ranking_engine: Optional[RankingEngine] = None
recommendation_generator: Optional[RecommendationGenerator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db, vector_store, embedding_service, ranking_engine, recommendation_generator
    
    logger.info("Starting up Job Recommender API...")
    
    # Initialize services
    db = Database()
    vector_store = VectorStore(path="data/qdrant")
    embedding_service = EmbeddingService()
    ranking_engine = RankingEngine()
    recommendation_generator = RecommendationGenerator()
    
    logger.info(f"Database initialized with {db.count_jobs()} jobs")
    logger.info(f"Vector store initialized with {vector_store.count()} vectors")
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down Job Recommender API...")
    if db:
        db.close()


# Create FastAPI application
app = FastAPI(
    title="Tech Job Recommender API",
    description="""
    AI-powered job recommendation system specialized for software engineering,
    data science, and DevOps roles.
    
    ## Features
    
    - **Candidate Profiles**: Create and manage candidate profiles with skills, experience, and preferences
    - **Job Search**: Browse and filter tech job postings with pagination
    - **Smart Recommendations**: Get personalized job recommendations with explainable AI
    - **Weight Customization**: Adjust ranking weights with preset profiles or custom values
    - **Feedback Collection**: Like/dislike jobs to improve recommendations
    
    ## Preset Weight Profiles
    
    - **Skill-Focused**: Prioritizes skill match (50% weight)
    - **Career-Growth**: Emphasizes experience alignment (35% weight)
    - **Compensation-First**: Focuses on salary fit (35% weight)
    - **Remote-Priority**: Prioritizes location/remote match (30% weight)
    - **Balanced**: Equal consideration of all factors
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    timestamp = datetime.utcnow().isoformat()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000
    
    # Log request details
    logger.info(
        f"[{timestamp}] {request.method} {request.url.path} "
        f"- Status: {response.status_code} - Duration: {duration_ms:.2f}ms"
    )
    
    # Add timing header
    response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
    
    return response


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.warning(f"AppException: {exc.detail} (status: {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "detail": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


app.include_router(candidates.router, prefix="/api", tags=["Candidates"])
app.include_router(jobs.router, prefix="/api", tags=["Jobs"])
app.include_router(recommendations.router, prefix="/api", tags=["Recommendations"])
app.include_router(weights.router, prefix="/api", tags=["Weights"])
app.include_router(feedback.router, prefix="/api", tags=["Feedback"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "name": "Tech Job Recommender API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    job_count = db.count_jobs() if db else 0
    vector_count = vector_store.count() if vector_store else 0
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "connected" if db else "disconnected",
            "vector_store": "connected" if vector_store else "disconnected",
            "embedding_service": "ready" if embedding_service else "not_ready",
        },
        "stats": {
            "jobs_count": job_count,
            "vectors_count": vector_count,
        },
    }


def get_db() -> Database:
    if db is None:
        raise AppException(
            status_code=503,
            error_code="service_unavailable",
            detail="Database not initialized",
        )
    return db


def get_vector_store() -> VectorStore:
    if vector_store is None:
        raise AppException(
            status_code=503,
            error_code="service_unavailable",
            detail="Vector store not initialized",
        )
    return vector_store


def get_embedding_service() -> EmbeddingService:
    if embedding_service is None:
        raise AppException(
            status_code=503,
            error_code="service_unavailable",
            detail="Embedding service not initialized",
        )
    return embedding_service


def get_ranking_engine() -> RankingEngine:
    if ranking_engine is None:
        raise AppException(
            status_code=503,
            error_code="service_unavailable",
            detail="Ranking engine not initialized",
        )
    return ranking_engine


def get_recommendation_generator() -> RecommendationGenerator:
    if recommendation_generator is None:
        raise AppException(
            status_code=503,
            error_code="service_unavailable",
            detail="Recommendation generator not initialized",
        )
    return recommendation_generator
