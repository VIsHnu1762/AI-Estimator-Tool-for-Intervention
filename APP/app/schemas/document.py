"""
Pydantic schemas for API requests and responses
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DocumentStatusEnum(str, Enum):
    """Document processing status"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentUploadResponse(BaseModel):
    """Response for document upload"""
    id: int
    filename: str
    original_filename: str
    status: DocumentStatusEnum
    message: str


class DocumentResponse(BaseModel):
    """Document details response"""
    id: int
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    status: DocumentStatusEnum
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class InterventionResponse(BaseModel):
    """Intervention details"""
    id: int
    intervention_type: str
    description: str
    location: Optional[str] = None
    chainage: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    irc_standards: Optional[List[str]] = None
    irc_clauses: Optional[List[str]] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    confidence_score: Optional[float] = None
    
    class Config:
        from_attributes = True


class CostItemResponse(BaseModel):
    """Cost item details"""
    id: int
    material_name: str
    material_category: Optional[str] = None
    specification: Optional[str] = None
    quantity: float
    unit: str
    unit_rate: float
    total_cost: float
    price_source: str
    price_source_reference: Optional[str] = None
    price_fetched_at: datetime
    
    class Config:
        from_attributes = True


class AnalysisResponse(BaseModel):
    """Complete analysis response"""
    id: int
    document_id: int
    total_interventions: int
    total_cost: float
    report_path: Optional[str] = None
    report_format: str
    report_generated_at: Optional[datetime] = None
    analysis_started_at: datetime
    analysis_completed_at: Optional[datetime] = None
    analysis_duration_seconds: Optional[float] = None
    summary_data: Optional[Dict[str, Any]] = None
    assumptions: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    
    class Config:
        from_attributes = True
