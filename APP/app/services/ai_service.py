"""
AI Service for NLP and intervention extraction
Combines spaCy NER with transformer models
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
import spacy
import torch
from transformers import pipeline, AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer
import re
import json

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """AI service for document analysis and entity extraction"""
    
    def __init__(self):
        self.nlp = None
        self.transformer_model = None
        self.ner_pipeline = None
        self.embedding_model = None
        
        # Intervention patterns
        self.intervention_keywords = [
            'guardrail', 'crash barrier', 'rumble strip', 'speed bump', 'traffic sign',
            'road marking', 'pedestrian crossing', 'footpath', 'footway', 'sidewalk',
            'street light', 'road light', 'illumination', 'delineator', 'chevron',
            'road hump', 'speed table', 'roundabout', 'junction improvement',
            'median', 'divider', 'kerb', 'pavement', 'shoulder', 'verge',
            'drainage', 'culvert', 'catch pit', 'gutter', 'safety barrier',
            'parapet', 'railing', 'fence', 'cattle guard', 'road stud', 'cat eye',
            'reflector', 'signage', 'information board', 'milestone', 'km stone',
            'warning sign', 'mandatory sign', 'regulatory sign', 'guide sign'
        ]
        
        # Quantity patterns
        self.quantity_patterns = [
            r'(\d+(?:\.\d+)?)\s*(km|kilometer|metre|meter|m|sqm|square\s*meter|cubic\s*meter|cum|ton|tonne|nos?\.?|number|unit|set)',
            r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*(m|meter|metre)',
            r'length[:\s]+(\d+(?:\.\d+)?)\s*(m|meter|metre|km)',
            r'width[:\s]+(\d+(?:\.\d+)?)\s*(m|meter|metre)',
            r'height[:\s]+(\d+(?:\.\d+)?)\s*(m|meter|metre)',
            r'area[:\s]+(\d+(?:\.\d+)?)\s*(sqm|square\s*meter)',
            r'volume[:\s]+(\d+(?:\.\d+)?)\s*(cum|cubic\s*meter)',
        ]
        
        # IRC standard patterns
        self.irc_patterns = [
            r'IRC[:\s-]*(\d+)[:\s-]*(\d{4})?',
            r'IRC[:\s]*SP[:\s-]*(\d+)',
            r'Indian\s+Roads\s+Congress[:\s]+(\d+)',
        ]
    
    async def initialize(self):
        """Initialize AI models"""
        try:
            logger.info("Loading spaCy model...")
            self.nlp = spacy.load(settings.NER_MODEL)
            
            logger.info("Loading embedding model...")
            self.embedding_model = SentenceTransformer(settings.TRANSFORMER_MODEL)
            
            logger.info("AI models loaded successfully")
        
        except Exception as e:
            logger.error(f"Error initializing AI models: {str(e)}", exc_info=True)
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        # Clear models from memory
        self.nlp = None
        self.transformer_model = None
        self.ner_pipeline = None
        self.embedding_model = None
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    async def extract_interventions(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract road safety interventions from text using hybrid NLP approach
        """
        interventions = []
        
        # Process with spaCy
        doc = self.nlp(text)
        
        # Split into sentences
        sentences = [sent.text.strip() for sent in doc.sents]
        
        for i, sentence in enumerate(sentences):
            # Check if sentence contains intervention keywords
            sentence_lower = sentence.lower()
            matched_keywords = [kw for kw in self.intervention_keywords if kw in sentence_lower]
            
            if matched_keywords:
                intervention = await self._extract_intervention_details(
                    sentence, 
                    matched_keywords,
                    context_sentences=sentences[max(0, i-1):min(len(sentences), i+2)]
                )
                if intervention:
                    interventions.append(intervention)
        
        # Merge similar interventions
        interventions = self._merge_similar_interventions(interventions)
        
        return interventions
    
    async def _extract_intervention_details(
        self, 
        sentence: str, 
        keywords: List[str],
        context_sentences: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Extract detailed information about an intervention"""
        
        # Combine context
        full_text = sentence
        if context_sentences:
            full_text = " ".join(context_sentences)
        
        # Extract entities with spaCy
        doc = self.nlp(full_text)
        
        # Extract locations
        locations = [ent.text for ent in doc.ents if ent.label_ in ['GPE', 'LOC', 'FAC']]
        
        # Extract chainages
        chainage_pattern = r'(?:km|chainage|ch\.?)[:\s]*(\d+(?:\.\d+)?)[+\s]*(\d+)?'
        chainages = re.findall(chainage_pattern, sentence.lower())
        chainage_str = None
        if chainages:
            km, plus = chainages[0]
            chainage_str = f"Km {km}" + (f"+{plus}" if plus else "")
        
        # Extract quantities
        quantities = await self._extract_quantities(full_text)
        
        # Determine intervention type
        intervention_type = self._classify_intervention_type(sentence, keywords)
        
        # Extract specifications
        specifications = await self._extract_specifications(full_text)
        
        # Calculate confidence score
        confidence = self._calculate_confidence(sentence, keywords, quantities)
        
        intervention = {
            'intervention_type': intervention_type,
            'description': sentence.strip(),
            'location': locations[0] if locations else None,
            'chainage': chainage_str,
            'specifications': specifications,
            'quantities': quantities,
            'confidence_score': confidence,
            'keywords_matched': keywords,
            'extraction_method': 'hybrid_nlp'
        }
        
        return intervention
    
    def _classify_intervention_type(self, text: str, keywords: List[str]) -> str:
        """Classify the type of intervention"""
        text_lower = text.lower()
        
        # Category mapping
        categories = {
            'Safety Barrier': ['guardrail', 'crash barrier', 'safety barrier', 'parapet', 'railing'],
            'Traffic Calming': ['rumble strip', 'speed bump', 'road hump', 'speed table'],
            'Signage': ['traffic sign', 'signage', 'warning sign', 'mandatory sign', 'guide sign', 'information board'],
            'Road Marking': ['road marking', 'pavement marking', 'line marking'],
            'Pedestrian Facility': ['pedestrian crossing', 'footpath', 'footway', 'sidewalk', 'zebra crossing'],
            'Illumination': ['street light', 'road light', 'illumination', 'lighting'],
            'Delineation': ['delineator', 'chevron', 'road stud', 'cat eye', 'reflector'],
            'Drainage': ['drainage', 'culvert', 'catch pit', 'gutter'],
            'Junction Improvement': ['roundabout', 'junction', 'intersection'],
            'Road Furniture': ['milestone', 'km stone', 'cattle guard'],
        }
        
        for category, category_keywords in categories.items():
            if any(kw in text_lower for kw in category_keywords):
                return category
        
        # Default
        return 'General Safety Intervention'
    
    async def _extract_quantities(self, text: str) -> List[Dict[str, Any]]:
        """Extract quantities and units from text"""
        quantities = []
        
        for pattern in self.quantity_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    if len(match) == 2:
                        value, unit = match
                        quantities.append({
                            'value': float(value),
                            'unit': unit.lower().strip(),
                            'raw_text': f"{value} {unit}"
                        })
                    elif len(match) == 3:
                        # e.g., "10 x 20 m"
                        val1, val2, unit = match
                        quantities.append({
                            'value': float(val1) * float(val2),
                            'unit': unit.lower().strip(),
                            'raw_text': f"{val1} x {val2} {unit}",
                            'dimensions': [float(val1), float(val2)]
                        })
        
        return quantities
    
    async def _extract_specifications(self, text: str) -> Dict[str, Any]:
        """Extract technical specifications"""
        specs = {}
        
        # Common specification patterns
        spec_patterns = {
            'material': r'(?:made of|material|using)\s+([a-zA-Z\s]+?)(?:\s|,|\.)',
            'grade': r'grade[:\s]+([A-Z0-9]+)',
            'class': r'class[:\s]+([A-Z0-9]+)',
            'type': r'type[:\s]+([A-Z0-9\s]+?)(?:\s|,|\.)',
            'thickness': r'thickness[:\s]+(\d+(?:\.\d+)?)\s*(mm|cm|m)',
            'diameter': r'diameter[:\s]+(\d+(?:\.\d+)?)\s*(mm|cm|m)',
            'height': r'height[:\s]+(\d+(?:\.\d+)?)\s*(mm|cm|m)',
            'width': r'width[:\s]+(\d+(?:\.\d+)?)\s*(mm|cm|m)',
        }
        
        for spec_name, pattern in spec_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                if isinstance(matches[0], tuple):
                    specs[spec_name] = ' '.join(matches[0])
                else:
                    specs[spec_name] = matches[0].strip()
        
        return specs
    
    def _calculate_confidence(
        self, 
        sentence: str, 
        keywords: List[str], 
        quantities: List[Dict]
    ) -> float:
        """Calculate confidence score for extraction"""
        score = 0.5  # Base score
        
        # Keywords matched
        score += min(len(keywords) * 0.1, 0.3)
        
        # Has quantities
        if quantities:
            score += 0.2
        
        # Sentence length (not too short, not too long)
        words = len(sentence.split())
        if 10 <= words <= 100:
            score += 0.1
        
        return min(score, 1.0)
    
    def _merge_similar_interventions(self, interventions: List[Dict]) -> List[Dict]:
        """Merge similar interventions to avoid duplicates"""
        if not interventions:
            return []
        
        # Simple deduplication based on intervention type and location
        unique = []
        seen = set()
        
        for intervention in interventions:
            key = (
                intervention['intervention_type'],
                intervention.get('location'),
                intervention.get('chainage')
            )
            if key not in seen:
                seen.add(key)
                unique.append(intervention)
        
        return unique
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        if not texts:
            return []
        
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    async def find_irc_standards(self, text: str) -> List[str]:
        """Extract IRC standard references from text"""
        standards = set()
        
        for pattern in self.irc_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    standard_num = match[0]
                    year = match[1] if len(match) > 1 else ''
                    std = f"IRC {standard_num}"
                    if year:
                        std += f":{year}"
                    standards.add(std)
                else:
                    standards.add(f"IRC {match}")
        
        return list(standards)
