"""
Database models for the application
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.db.database import Base


class DocumentStatus(str, enum.Enum):
    """Document processing status"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    """Document upload and processing record"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED, nullable=False)
    
    # Processing info
    extracted_text = Column(Text, nullable=True)
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    processing_error = Column(Text, nullable=True)
    
    # Metadata
    uploaded_by = Column(String(100), nullable=True)
    upload_ip = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    interventions = relationship("Intervention", back_populates="document", cascade="all, delete-orphan")
    analysis = relationship("Analysis", back_populates="document", uselist=False, cascade="all, delete-orphan")


class Intervention(Base):
    """Extracted road safety intervention"""
    __tablename__ = "interventions"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Intervention details
    intervention_type = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String(500), nullable=True)
    chainage = Column(String(100), nullable=True)
    
    # Specifications
    specifications = Column(JSON, nullable=True)  # Detailed specs as JSON
    
    # IRC standards
    irc_standards = Column(JSON, nullable=True)  # List of relevant IRC standards
    irc_clauses = Column(JSON, nullable=True)  # Specific clause references
    
    # Quantities
    quantity = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)
    
    # Extracted metadata
    confidence_score = Column(Float, nullable=True)
    extraction_method = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="interventions")
    cost_items = relationship("CostItem", back_populates="intervention", cascade="all, delete-orphan")


class CostItem(Base):
    """Cost calculation for materials"""
    __tablename__ = "cost_items"
    
    id = Column(Integer, primary_key=True, index=True)
    intervention_id = Column(Integer, ForeignKey("interventions.id", ondelete="CASCADE"), nullable=False)
    
    # Material details
    material_name = Column(String(300), nullable=False)
    material_category = Column(String(100), nullable=True)
    specification = Column(Text, nullable=True)
    
    # Quantity
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    
    # Pricing
    unit_rate = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    
    # Price source
    price_source = Column(String(100), nullable=False)  # CPWD_SOR, CPWD_AOR, GEM
    price_source_reference = Column(String(200), nullable=True)
    price_fetched_at = Column(DateTime, nullable=False)
    price_valid_until = Column(DateTime, nullable=True)
    
    # Metadata
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    intervention = relationship("Intervention", back_populates="cost_items")


class Analysis(Base):
    """Complete analysis and report generation"""
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Summary
    total_interventions = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    
    # Report
    report_path = Column(String(512), nullable=True)
    report_format = Column(String(20), default="pdf")
    report_generated_at = Column(DateTime, nullable=True)
    
    # Analysis metadata
    analysis_started_at = Column(DateTime, nullable=False)
    analysis_completed_at = Column(DateTime, nullable=True)
    analysis_duration_seconds = Column(Float, nullable=True)
    
    # Additional data
    summary_data = Column(JSON, nullable=True)
    assumptions = Column(JSON, nullable=True)
    warnings = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="analysis")


class IRCStandard(Base):
    """IRC standard reference data"""
    __tablename__ = "irc_standards"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Content
    full_text = Column(Text, nullable=True)
    clauses = Column(JSON, nullable=True)  # Structured clause data
    
    # Metadata
    version = Column(String(50), nullable=True)
    published_year = Column(Integer, nullable=True)
    last_updated = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class PriceCache(Base):
    """Cache for government pricing data"""
    __tablename__ = "price_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Material identification
    material_name = Column(String(300), nullable=False, index=True)
    material_code = Column(String(100), nullable=True, index=True)
    specification = Column(Text, nullable=True)
    unit = Column(String(50), nullable=False)
    
    # Price
    unit_rate = Column(Float, nullable=False)
    
    # Source
    source = Column(String(100), nullable=False, index=True)  # CPWD_SOR, CPWD_AOR, GEM
    source_reference = Column(String(200), nullable=True)
    location = Column(String(200), nullable=True)  # For location-specific pricing
    
    # Validity
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=True)
    
    # Metadata
    fetched_at = Column(DateTime, default=func.now(), nullable=False)
    cache_hits = Column(Integer, default=0)
    last_accessed = Column(DateTime, default=func.now(), onupdate=func.now())
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
