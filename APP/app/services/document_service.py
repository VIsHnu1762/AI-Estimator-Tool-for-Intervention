"""
Document processing service
"""
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentStatus
from app.core.config import settings
from app.utils.file_utils import generate_unique_filename

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for document management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def save_document(
        self,
        file_path: str,
        original_filename: str,
        mime_type: str,
        file_size: int,
        upload_ip: Optional[str] = None
    ) -> Document:
        """
        Save uploaded document to persistent storage
        """
        try:
            # Generate unique filename
            unique_filename = generate_unique_filename(original_filename)
            
            # Create destination path
            dest_dir = Path(settings.TEMP_UPLOAD_DIR)
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / unique_filename
            
            # Move file
            shutil.move(file_path, dest_path)
            
            # Create database record
            document = Document(
                filename=unique_filename,
                original_filename=original_filename,
                file_path=str(dest_path),
                file_size=file_size,
                mime_type=mime_type,
                status=DocumentStatus.UPLOADED,
                upload_ip=upload_ip
            )
            
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            
            logger.info(f"Document saved: {document.id} - {original_filename}")
            return document
            
        except Exception as e:
            logger.error(f"Error saving document: {str(e)}", exc_info=True)
            self.db.rollback()
            raise
    
    def get_document(self, document_id: int) -> Optional[Document]:
        """Get document by ID"""
        return self.db.query(Document).filter(Document.id == document_id).first()
    
    def list_documents(self, skip: int = 0, limit: int = 50) -> List[Document]:
        """List documents"""
        return self.db.query(Document).order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
    
    def update_status(
        self,
        document_id: int,
        status: DocumentStatus,
        error: Optional[str] = None
    ):
        """Update document status"""
        document = self.get_document(document_id)
        if document:
            document.status = status
            if error:
                document.processing_error = error
            if status == DocumentStatus.PROCESSING:
                document.processing_started_at = datetime.now()
            elif status in [DocumentStatus.COMPLETED, DocumentStatus.FAILED]:
                document.processing_completed_at = datetime.now()
            
            self.db.commit()
            logger.info(f"Document {document_id} status updated to {status}")
    
    def update_extracted_text(self, document_id: int, text: str):
        """Update extracted text"""
        document = self.get_document(document_id)
        if document:
            document.extracted_text = text
            self.db.commit()
