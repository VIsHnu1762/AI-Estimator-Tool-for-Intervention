"""
Analysis service - orchestrates document processing, intervention extraction,
IRC mapping, pricing, and cost calculation
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path

from app.db.models import Intervention, CostItem, Analysis
from app.services.extractor_service import DocumentExtractor
from app.services.ai_service import AIService
from app.services.rag_service import RAGService
from app.services.pricing_service import PricingService
from app.services.document_service import DocumentService
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)


class AnalysisService:
    """Service for complete document analysis"""
    
    def __init__(
        self, 
        db: Session,
        ai_service: Optional[AIService] = None,
        rag_service: Optional[RAGService] = None
    ):
        self.db = db
        self.ai_service = ai_service
        self.rag_service = rag_service
        self.extractor = DocumentExtractor()
        self.pricing_service = PricingService(db)
        self.doc_service = DocumentService(db)
        self.report_service = ReportService()
    
    async def process_document(self, document_id: int):
        """
        Complete processing pipeline for a document
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting analysis for document {document_id}")
            
            # Get document
            document = self.doc_service.get_document(document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Create analysis record
            analysis = Analysis(
                document_id=document_id,
                analysis_started_at=start_time
            )
            self.db.add(analysis)
            self.db.commit()
            
            # Step 1: Extract text
            logger.info("Step 1: Extracting text from document")
            text = await self.extractor.extract_text(document.file_path)
            self.doc_service.update_extracted_text(document_id, text)
            
            if not text or len(text.strip()) < 50:
                raise ValueError("Insufficient text extracted from document")
            
            # Step 2: Extract interventions using AI
            logger.info("Step 2: Extracting interventions using AI/NLP")
            interventions = await self.ai_service.extract_interventions(text)
            logger.info(f"Found {len(interventions)} interventions")
            
            if not interventions:
                raise ValueError("No interventions found in document")
            
            # Step 3: Process each intervention
            total_cost = 0.0
            assumptions = []
            warnings = []
            
            for idx, intervention_data in enumerate(interventions):
                logger.info(f"Processing intervention {idx+1}/{len(interventions)}: {intervention_data['intervention_type']}")
                
                # Find relevant IRC standards
                irc_standards = await self.rag_service.find_relevant_standards(intervention_data)
                irc_codes = [std['code'] for std in irc_standards]
                irc_clauses = []
                for std in irc_standards:
                    if std.get('matched_clause'):
                        irc_clauses.append(f"{std['code']} - Clause {std['matched_clause']}")
                
                # Create intervention record
                intervention = Intervention(
                    document_id=document_id,
                    intervention_type=intervention_data['intervention_type'],
                    description=intervention_data['description'],
                    location=intervention_data.get('location'),
                    chainage=intervention_data.get('chainage'),
                    specifications=intervention_data.get('specifications'),
                    irc_standards=irc_codes,
                    irc_clauses=irc_clauses,
                    confidence_score=intervention_data.get('confidence_score'),
                    extraction_method=intervention_data.get('extraction_method')
                )
                self.db.add(intervention)
                self.db.flush()  # Get intervention ID
                
                # Step 4: Calculate costs
                cost_data = await self._calculate_intervention_cost(
                    intervention_data,
                    intervention.id
                )
                
                if cost_data:
                    total_cost += cost_data['total_cost']
                    assumptions.extend(cost_data.get('assumptions', []))
                    warnings.extend(cost_data.get('warnings', []))
            
            # Update analysis record prior to report generation
            analysis.analysis_completed_at = datetime.now()
            analysis.analysis_duration_seconds = (
                analysis.analysis_completed_at - start_time
            ).total_seconds()
            analysis.total_interventions = len(interventions)
            analysis.total_cost = total_cost
            analysis.assumptions = assumptions
            analysis.warnings = warnings
            analysis.summary_data = {
                'interventions_by_type': self._summarize_by_type(interventions),
                'total_interventions': len(interventions),
                'total_cost': total_cost
            }

            # Step 5: Generate report with enriched analysis data
            logger.info("Step 5: Generating report")
            report_path = await self.report_service.generate_report(
                document_id=document_id,
                document=document,
                interventions=self.db.query(Intervention).filter(
                    Intervention.document_id == document_id
                ).all(),
                total_cost=total_cost,
                analysis=analysis
            )
            analysis.report_path = report_path
            analysis.report_generated_at = datetime.now()
            
            self.db.commit()
            
            logger.info(f"Analysis completed for document {document_id}. Total cost: ₹{total_cost:,.2f}")
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}", exc_info=True)
            self.db.rollback()
            raise
    
    async def _calculate_intervention_cost(
        self, 
        intervention_data: Dict,
        intervention_id: int
    ) -> Optional[Dict[str, Any]]:
        """Calculate cost for an intervention"""
        
        total_cost = 0.0
        assumptions = []
        warnings = []
        
        # Determine materials needed based on intervention type
        materials = self._identify_materials(intervention_data)
        
        if not materials:
            logger.warning(f"No materials identified for intervention: {intervention_data['intervention_type']}")
            assumptions.append(f"Material estimation required for {intervention_data['intervention_type']}")
            return None
        
        # Get pricing for each material
        for material in materials:
            try:
                price_data = await self.pricing_service.get_material_price(
                    material_name=material['name'],
                    quantity=material['quantity'],
                    unit=material['unit']
                )
                
                # Create cost item
                cost_item = CostItem(
                    intervention_id=intervention_id,
                    material_name=material['name'],
                    material_category=material.get('category'),
                    specification=material.get('specification'),
                    quantity=material['quantity'],
                    unit=material['unit'],
                    unit_rate=price_data['unit_rate'],
                    total_cost=price_data['total_cost'],
                    price_source=price_data['source'],
                    price_source_reference=price_data.get('source_reference'),
                    price_fetched_at=price_data['fetched_at']
                )
                self.db.add(cost_item)
                
                total_cost += price_data['total_cost']
                
                # Track assumptions and warnings
                if price_data.get('is_estimate'):
                    assumptions.append(f"Estimated rate used for {material['name']}")
                if price_data.get('requires_verification'):
                    warnings.append(f"Price verification required for {material['name']}")
                
            except Exception as e:
                logger.error(f"Error getting price for {material['name']}: {str(e)}")
                warnings.append(f"Failed to get price for {material['name']}")
        
        return {
            'total_cost': total_cost,
            'assumptions': assumptions,
            'warnings': warnings
        }
    
    def _identify_materials(self, intervention_data: Dict) -> List[Dict[str, Any]]:
        """Identify required materials based on intervention type and quantities"""
        
        materials = []
        intervention_type = intervention_data['intervention_type']
        quantities = intervention_data.get('quantities', [])
        
        # Material mapping based on intervention type
        material_rules = {
            'Safety Barrier': [
                {'name': 'Steel Crash Barrier', 'unit': 'm', 'ratio': 1.0},
                {'name': 'Guardrail Post', 'unit': 'nos', 'ratio': 0.33},  # One post per 3m
            ],
            'Road Marking': [
                {'name': 'Thermoplastic Paint', 'unit': 'kg', 'ratio': 0.5},  # 0.5 kg per m
                {'name': 'Glass Beads', 'unit': 'kg', 'ratio': 0.1},
            ],
            'Traffic Calming': [
                {'name': 'Rumble Strip', 'unit': 'm', 'ratio': 1.0},
            ],
            'Signage': [
                {'name': 'Traffic Sign Board', 'unit': 'sqm', 'ratio': 1.0},
                {'name': 'Sign Post', 'unit': 'nos', 'ratio': 1.0},
            ],
            'Pedestrian Facility': [
                {'name': 'Footpath Paving', 'unit': 'sqm', 'ratio': 1.0},
                {'name': 'Pedestrian Railing', 'unit': 'm', 'ratio': 1.0},
            ],
            'Illumination': [
                {'name': 'LED Street Light', 'unit': 'nos', 'ratio': 1.0},
                {'name': 'Light Pole', 'unit': 'nos', 'ratio': 1.0},
            ],
            'Delineation': [
                {'name': 'Cat Eye Road Stud', 'unit': 'nos', 'ratio': 1.0},
                {'name': 'Flexible Delineator', 'unit': 'nos', 'ratio': 1.0},
            ],
        }
        
        # Get material rules for this intervention type
        rules = material_rules.get(intervention_type, [])
        
        if not rules:
            # Generic intervention - try to infer from description
            rules = [{'name': intervention_type, 'unit': 'nos', 'ratio': 1.0}]
        
        # Calculate material quantities
        for rule in rules:
            # Use extracted quantities if available
            if quantities:
                for qty in quantities:
                    # Match unit
                    if qty['unit'] in [rule['unit'], 'm', 'meter', 'metre'] and rule['unit'] in ['m', 'meter']:
                        materials.append({
                            'name': rule['name'],
                            'quantity': qty['value'] * rule['ratio'],
                            'unit': rule['unit'],
                            'category': intervention_type
                        })
                        break
                else:
                    # Use first quantity as fallback
                    materials.append({
                        'name': rule['name'],
                        'quantity': quantities[0]['value'] * rule['ratio'],
                        'unit': rule['unit'],
                        'category': intervention_type
                    })
            else:
                # No quantities extracted - use default
                materials.append({
                    'name': rule['name'],
                    'quantity': 100.0 * rule['ratio'],  # Default quantity
                    'unit': rule['unit'],
                    'category': intervention_type,
                    'is_estimate': True
                })
        
        return materials
    
    def _summarize_by_type(self, interventions: List[Dict]) -> Dict[str, int]:
        """Summarize interventions by type"""
        summary = {}
        for intervention in interventions:
            itype = intervention['intervention_type']
            summary[itype] = summary.get(itype, 0) + 1
        return summary
    
    def get_analysis(self, document_id: int) -> Optional[Analysis]:
        """Get analysis for a document"""
        return self.db.query(Analysis).filter(
            Analysis.document_id == document_id
        ).first()
