"""
Main FastAPI application for Road Safety Intervention Analysis System
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
from typing import List, Optional
import os
from pathlib import Path

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.api import routes
from app.db.database import engine, Base, get_db
from app.services.ai_service import AIService
from app.services.rag_service import RAGService

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("Starting Road Safety Intervention Analysis System...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize AI services
    logger.info("Initializing AI services...")
    ai_service = AIService()
    await ai_service.initialize()
    
    rag_service = RAGService()
    await rag_service.initialize()
    
    # Store in app state
    app.state.ai_service = ai_service
    app.state.rag_service = rag_service
    
    logger.info("Application startup complete")
    
    yield
    
    # Cleanup
    logger.info("Shutting down application...")
    await ai_service.cleanup()
    await rag_service.cleanup()
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered road safety intervention analysis and cost estimation system",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# Mount static files
static_path = Path("static")
if static_path.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(routes.router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Road Safety Intervention Analysis System API",
        "version": settings.APP_VERSION,
        "docs": "/api/docs" if settings.DEBUG else "Disabled in production"
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred. Please try again later.",
            "error_id": str(id(exc))
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.WORKERS
    )
