"""
RAG (Retrieval-Augmented Generation) Service for IRC Standards
Implements vector search and semantic matching
"""
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from pathlib import Path
import json

from app.core.config import settings

logger = logging.getLogger(__name__)


class RAGService:
    """RAG service for IRC standards retrieval"""
    
    def __init__(self):
        self.client = None
        self.collection = None
        self.irc_standards_db = {}
        
    async def initialize(self):
        """Initialize ChromaDB and load IRC standards"""
        try:
            logger.info("Initializing RAG service...")
            
            # Create ChromaDB client
            persist_dir = Path(settings.CHROMA_PERSIST_DIRECTORY)
            persist_dir.mkdir(parents=True, exist_ok=True)
            
            self.client = chromadb.Client(ChromaSettings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=str(persist_dir)
            ))
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(
                    name=settings.VECTOR_COLLECTION_NAME
                )
                logger.info(f"Loaded existing collection: {settings.VECTOR_COLLECTION_NAME}")
            except:
                self.collection = self.client.create_collection(
                    name=settings.VECTOR_COLLECTION_NAME,
                    metadata={"description": "IRC Standards for Road Safety"}
                )
                logger.info(f"Created new collection: {settings.VECTOR_COLLECTION_NAME}")
                
                # Load and index IRC standards
                await self._load_irc_standards()
            
            logger.info("RAG service initialized successfully")
        
        except Exception as e:
            logger.error(f"Error initializing RAG service: {str(e)}", exc_info=True)
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            self.client.persist()
        self.client = None
        self.collection = None
    
    async def _load_irc_standards(self):
        """Load IRC standards into vector database"""
        logger.info("Loading IRC standards...")
        
        # IRC Standards data (in production, load from files/database)
        irc_standards = [
            {
                'code': 'IRC 35',
                'title': 'Code of Practice for Road Markings',
                'description': 'Covers specifications for road markings including pavement markings, object markers, delineators, and hazard markers. Specifies materials, colors, dimensions, and retroreflectivity requirements.',
                'clauses': {
                    '4.1': 'White and yellow thermoplastic paint for road markings',
                    '4.2': 'Retroreflective road studs and cat eyes',
                    '5.1': 'Center line markings specifications',
                    '5.2': 'Edge line markings',
                    '6.1': 'Pedestrian crossing markings (zebra crossings)',
                    '7.1': 'Stop lines and give way markings'
                },
                'applications': ['road marking', 'pavement marking', 'line marking', 'pedestrian crossing', 'zebra crossing']
            },
            {
                'code': 'IRC 67',
                'title': 'Code of Practice for Road Signs',
                'description': 'Guidelines for design, placement, and specifications of road traffic signs including regulatory, warning, and informatory signs. Covers materials, reflectivity, and mounting requirements.',
                'clauses': {
                    '4.1': 'Regulatory signs (mandatory, prohibitory)',
                    '4.2': 'Warning signs for hazards',
                    '4.3': 'Informatory signs (route guidance)',
                    '5.1': 'Sign dimensions and letter sizes',
                    '6.1': 'Retroreflective sheeting specifications',
                    '7.1': 'Sign placement and mounting heights'
                },
                'applications': ['traffic sign', 'warning sign', 'mandatory sign', 'regulatory sign', 'guide sign', 'signage']
            },
            {
                'code': 'IRC 99',
                'title': 'Tentative Guidelines on the Provision of Facilities for Pedestrians',
                'description': 'Guidelines for pedestrian infrastructure including footpaths, crossings, overpasses, underpasses, and pedestrian safety measures.',
                'clauses': {
                    '5.1': 'Footpath width and design requirements',
                    '5.2': 'Surface requirements for footpaths',
                    '6.1': 'At-grade pedestrian crossings',
                    '6.2': 'Pedestrian signals and refuge islands',
                    '7.1': 'Pedestrian overpasses and underpasses',
                    '8.1': 'Ramps and tactile paving for accessibility'
                },
                'applications': ['footpath', 'footway', 'sidewalk', 'pedestrian crossing', 'pedestrian facility']
            },
            {
                'code': 'IRC SP:84',
                'title': 'Manual for Road Safety Audits',
                'description': 'Comprehensive manual for conducting road safety audits at all stages of road projects. Covers audit procedures, safety checkpoints, and intervention recommendations.',
                'clauses': {
                    '4.1': 'Safety audit at feasibility stage',
                    '4.2': 'Safety audit at design stage',
                    '5.1': 'Pre-opening safety audit',
                    '6.1': 'Road safety inspections',
                    '7.1': 'Black spot identification and treatment',
                    '8.1': 'Safety interventions and countermeasures'
                },
                'applications': ['safety audit', 'black spot', 'hazard', 'safety intervention', 'crash analysis']
            },
            {
                'code': 'IRC SP:87',
                'title': 'Manual of Specifications and Standards for Four Laning of Highways',
                'description': 'Standards for widening and upgrading highways to four lanes, including safety features, barriers, medians, and auxiliary facilities.',
                'clauses': {
                    '8.1': 'Median design and barriers',
                    '8.2': 'Crash barriers and guardrails',
                    '9.1': 'Road furniture and safety appurtenances',
                    '10.1': 'Street lighting and illumination',
                    '11.1': 'Traffic signs and road markings',
                    '12.1': 'Drainage and road safety'
                },
                'applications': ['median', 'crash barrier', 'guardrail', 'safety barrier', 'illumination', 'street light']
            },
            {
                'code': 'IRC 19',
                'title': 'Geometric Design Standards for Rural (Non-Urban) Highways',
                'description': 'Standards for geometric design including alignment, cross-section, sight distance, and safety features for rural highways.',
                'clauses': {
                    '7.1': 'Road shoulder specifications',
                    '7.2': 'Roadside safety and clear zones',
                    '8.1': 'Horizontal and vertical curves',
                    '9.1': 'Sight distance requirements',
                    '10.1': 'Junction and intersection design'
                },
                'applications': ['shoulder', 'verge', 'alignment', 'junction', 'intersection', 'roundabout']
            },
            {
                'code': 'IRC 103',
                'title': 'Guidelines for Pedestrian Facilities',
                'description': 'Detailed guidelines for providing safe pedestrian facilities including walkways, crossings, and grade-separated facilities.',
                'clauses': {
                    '4.1': 'Pedestrian facility planning',
                    '5.1': 'Footpath design standards',
                    '6.1': 'At-grade crossing design',
                    '7.1': 'Grade-separated crossings'
                },
                'applications': ['pedestrian', 'footpath', 'crossing', 'walkway']
            },
            {
                'code': 'IRC 11',
                'title': 'Recommended Practice for the Design of At-Grade Extra-Urban Intersections',
                'description': 'Design guidelines for intersections including channelization, traffic islands, and safety measures.',
                'clauses': {
                    '5.1': 'Intersection types and selection',
                    '6.1': 'Channelization design',
                    '7.1': 'Traffic islands and medians',
                    '8.1': 'Sight distance at intersections'
                },
                'applications': ['intersection', 'junction', 'channelization', 'traffic island']
            }
        ]
        
        # Prepare documents for indexing
        documents = []
        metadatas = []
        ids = []
        
        for std in irc_standards:
            self.irc_standards_db[std['code']] = std
            
            # Main standard document
            doc_text = f"{std['code']}: {std['title']}\n{std['description']}"
            documents.append(doc_text)
            metadatas.append({
                'code': std['code'],
                'title': std['title'],
                'type': 'standard'
            })
            ids.append(std['code'])
            
            # Index individual clauses
            for clause_num, clause_text in std.get('clauses', {}).items():
                clause_doc = f"{std['code']} Clause {clause_num}: {clause_text}"
                documents.append(clause_doc)
                metadatas.append({
                    'code': std['code'],
                    'clause': clause_num,
                    'type': 'clause'
                })
                ids.append(f"{std['code']}_clause_{clause_num}")
        
        # Add to collection
        if documents:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Indexed {len(documents)} IRC standard documents")
    
    async def find_relevant_standards(
        self, 
        intervention: Dict[str, Any],
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find relevant IRC standards for an intervention using semantic search
        """
        try:
            # Create search query from intervention
            query_parts = [
                intervention.get('intervention_type', ''),
                intervention.get('description', ''),
                ' '.join(intervention.get('keywords_matched', []))
            ]
            query = ' '.join([p for p in query_parts if p]).strip()
            
            if not query:
                return []
            
            # Search in ChromaDB
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k * 2  # Get more results to filter
            )
            
            # Process results
            relevant_standards = []
            seen_codes = set()
            
            if results and results['ids'] and len(results['ids']) > 0:
                for i, doc_id in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i] if 'distances' in results else 1.0
                    
                    code = metadata.get('code')
                    if code and code not in seen_codes:
                        seen_codes.add(code)
                        
                        standard_info = self.irc_standards_db.get(code, {})
                        relevant_standards.append({
                            'code': code,
                            'title': standard_info.get('title', ''),
                            'description': standard_info.get('description', ''),
                            'relevance_score': 1.0 - min(distance, 1.0),
                            'matched_clause': metadata.get('clause')
                        })
                        
                        if len(relevant_standards) >= top_k:
                            break
            
            return relevant_standards
        
        except Exception as e:
            logger.error(f"Error finding relevant standards: {str(e)}", exc_info=True)
            return []
    
    async def get_standard_details(self, code: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific IRC standard"""
        return self.irc_standards_db.get(code)
    
    async def search_by_keyword(self, keyword: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search standards by keyword"""
        try:
            results = self.collection.query(
                query_texts=[keyword],
                n_results=top_k
            )
            
            standards = []
            seen = set()
            
            if results and results['ids'] and len(results['ids']) > 0:
                for i, doc_id in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i]
                    code = metadata.get('code')
                    
                    if code and code not in seen:
                        seen.add(code)
                        standard_info = self.irc_standards_db.get(code, {})
                        if standard_info:
                            standards.append(standard_info)
            
            return standards
        
        except Exception as e:
            logger.error(f"Error searching by keyword: {str(e)}", exc_info=True)
            return []
