"""
API Routes for the application
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import shutil
from pathlib import Path
from datetime import datetime

from app.db.database import get_db
from app.db.models import Document, DocumentStatus, Analysis
from app.core.config import settings
from app.schemas.document import DocumentResponse, AnalysisResponse, DocumentUploadResponse
from app.services.document_service import DocumentService
from app.services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Upload a document for processing
    """
    # Validate file size
    file_size = 0
    temp_path = Path(settings.TEMP_UPLOAD_DIR) / f"temp_{datetime.now().timestamp()}_{file.filename}"
    
    try:
        with temp_path.open("wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # Read 1MB chunks
                file_size += len(chunk)
                if file_size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB}MB"
                    )
                buffer.write(chunk)
        
        # Validate file extension
        file_ext = Path(file.filename).suffix.lower().lstrip('.')
        if file_ext not in settings.allowed_extensions_list:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {', '.join(settings.allowed_extensions_list)}"
            )
        
        # Create document service
        doc_service = DocumentService(db)
        
        # Save document
        document = await doc_service.save_document(
            file_path=str(temp_path),
            original_filename=file.filename,
            mime_type=file.content_type or "application/octet-stream",
            file_size=file_size,
            upload_ip=request.client.host if request else None
        )
        
        # Schedule background processing
        if background_tasks:
            background_tasks.add_task(
                process_document_background,
                document.id,
                request.app.state
            )
        
        return DocumentUploadResponse(
            id=document.id,
            filename=document.filename,
            original_filename=document.original_filename,
            status=document.status,
            message="Document uploaded successfully. Processing will begin shortly."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error uploading document")
    finally:
        # Cleanup temp file if it exists
        if temp_path.exists():
            try:
                temp_path.unlink()
            except:
                pass


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: int, db: Session = Depends(get_db)):
    """
    Get document details and processing status
    """
    doc_service = DocumentService(db)
    document = doc_service.get_document(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse.from_orm(document)


@router.get("/documents/{document_id}/analysis", response_model=AnalysisResponse)
async def get_analysis(document_id: int, db: Session = Depends(get_db)):
    """
    Get analysis results for a document
    """
    analysis_service = AnalysisService(db)
    analysis = analysis_service.get_analysis(document_id)
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return AnalysisResponse.from_orm(analysis)


@router.get("/documents/{document_id}/report")
async def download_report(document_id: int, db: Session = Depends(get_db)):
    """
    Download the generated report
    """
    analysis_service = AnalysisService(db)
    analysis = analysis_service.get_analysis(document_id)
    
    if not analysis or not analysis.report_path:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report_path = Path(analysis.report_path)
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")
    
    return FileResponse(
        path=str(report_path),
        filename=f"cost_analysis_report_{document_id}.pdf",
        media_type="application/pdf"
    )


@router.post("/documents/{document_id}/analyze")
async def analyze_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Trigger analysis for an uploaded document
    """
    doc_service = DocumentService(db)
    document = doc_service.get_document(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.status != DocumentStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Document must be in COMPLETED status. Current status: {document.status}"
        )
    
    # Schedule analysis
    background_tasks.add_task(
        process_document_background,
        document.id,
        request.app.state
    )
    
    return {"message": "Analysis started", "document_id": document_id}


@router.get("/documents")
async def list_documents(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    List all documents
    """
    doc_service = DocumentService(db)
    documents = doc_service.list_documents(skip=skip, limit=limit)
    return [DocumentResponse.from_orm(doc) for doc in documents]


async def process_document_background(document_id: int, app_state):
    """
    Background task to process document and generate analysis
    """
    from app.db.database import SessionLocal
    
    db = SessionLocal()
    try:
        logger.info(f"Starting background processing for document {document_id}")
        
        # Get services from app state
        ai_service = app_state.ai_service
        rag_service = app_state.rag_service
        
        # Create service instances
        doc_service = DocumentService(db)
        analysis_service = AnalysisService(db, ai_service, rag_service)
        
        # Update status
        doc_service.update_status(document_id, DocumentStatus.PROCESSING)
        
        # Process document
        await analysis_service.process_document(document_id)
        
        # Update status
        doc_service.update_status(document_id, DocumentStatus.COMPLETED)
        
        logger.info(f"Completed processing for document {document_id}")
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}", exc_info=True)
        doc_service.update_status(document_id, DocumentStatus.FAILED, error=str(e))
    finally:
        db.close()
