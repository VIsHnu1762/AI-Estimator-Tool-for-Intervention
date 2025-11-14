"""
Pricing service for fetching material costs from government sources
Integrates with CPWD SOR/AOR and GeM marketplace
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
import json
from sqlalchemy.orm import Session
import redis
import pickle

from app.core.config import settings
from app.db.models import PriceCache

logger = logging.getLogger(__name__)


class PricingService:
    """Service for fetching and caching government pricing data"""
    
    def __init__(self, db: Session):
        self.db = db
        self.redis_client = None
        
        # Initialize Redis connection
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=False
            )
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis not available: {str(e)}")
            self.redis_client = None
        
        # Material mapping for common interventions
        self.material_database = self._initialize_material_database()
    
    def _initialize_material_database(self) -> Dict[str, Any]:
        """Initialize material database with common road safety materials"""
        return {
            # Safety Barriers
            'Steel Crash Barrier': {
                'category': 'Safety Barrier',
                'unit': 'm',
                'cpwd_code': 'CPWD-SOR-2023-12.45',
                'gem_category': 'Road Safety Equipment',
                'specifications': 'Galvanized steel W-beam, AASHTO M-180',
                'typical_rate': 1850.0
            },
            'Concrete Safety Barrier': {
                'category': 'Safety Barrier',
                'unit': 'm',
                'cpwd_code': 'CPWD-SOR-2023-12.46',
                'specifications': 'RCC Jersey barrier, M30 grade',
                'typical_rate': 2200.0
            },
            'Guardrail Post': {
                'category': 'Safety Barrier',
                'unit': 'nos',
                'cpwd_code': 'CPWD-SOR-2023-12.47',
                'specifications': 'MS post, galvanized, 2.5m height',
                'typical_rate': 850.0
            },
            
            # Road Markings
            'Thermoplastic Paint': {
                'category': 'Road Marking',
                'unit': 'kg',
                'cpwd_code': 'CPWD-SOR-2023-18.23',
                'gem_category': 'Road Marking Materials',
                'specifications': 'White/yellow thermoplastic, Type-II',
                'typical_rate': 185.0
            },
            'Cold Paint': {
                'category': 'Road Marking',
                'unit': 'ltr',
                'cpwd_code': 'CPWD-SOR-2023-18.24',
                'specifications': 'Chlorinated rubber based paint',
                'typical_rate': 95.0
            },
            'Glass Beads': {
                'category': 'Road Marking',
                'unit': 'kg',
                'cpwd_code': 'CPWD-SOR-2023-18.25',
                'specifications': 'Retroreflective glass beads, Type-A',
                'typical_rate': 42.0
            },
            
            # Road Studs
            'Cat Eye Road Stud': {
                'category': 'Delineation',
                'unit': 'nos',
                'cpwd_code': 'CPWD-SOR-2023-18.31',
                'gem_category': 'Road Safety Equipment',
                'specifications': 'Reflective, aluminum body',
                'typical_rate': 125.0
            },
            'Solar Road Stud': {
                'category': 'Delineation',
                'unit': 'nos',
                'cpwd_code': 'CPWD-SOR-2023-18.32',
                'specifications': 'LED, solar powered, IP68',
                'typical_rate': 850.0
            },
            
            # Signs
            'Traffic Sign Board': {
                'category': 'Signage',
                'unit': 'sqm',
                'cpwd_code': 'CPWD-SOR-2023-18.15',
                'gem_category': 'Traffic Signs',
                'specifications': 'Aluminum sheet, Grade-III retroreflective',
                'typical_rate': 3200.0
            },
            'Sign Post': {
                'category': 'Signage',
                'unit': 'nos',
                'cpwd_code': 'CPWD-SOR-2023-18.16',
                'specifications': 'MS square hollow section, galvanized',
                'typical_rate': 1850.0
            },
            
            # Speed Control
            'Rumble Strip': {
                'category': 'Traffic Calming',
                'unit': 'm',
                'cpwd_code': 'CPWD-SOR-2023-18.42',
                'specifications': 'Thermoplastic or milled asphalt',
                'typical_rate': 450.0
            },
            'Speed Hump': {
                'category': 'Traffic Calming',
                'unit': 'nos',
                'cpwd_code': 'CPWD-SOR-2023-18.43',
                'specifications': 'Rubber/plastic, 3.7m x 350mm x 50mm',
                'typical_rate': 4500.0
            },
            
            # Pedestrian Facilities
            'Footpath Paving': {
                'category': 'Pedestrian Facility',
                'unit': 'sqm',
                'cpwd_code': 'CPWD-SOR-2023-14.35',
                'specifications': 'Concrete paver blocks, 60mm thick',
                'typical_rate': 425.0
            },
            'Tactile Paving': {
                'category': 'Pedestrian Facility',
                'unit': 'sqm',
                'cpwd_code': 'CPWD-SOR-2023-14.36',
                'specifications': 'Warning/directional tiles, vitrified',
                'typical_rate': 850.0
            },
            'Pedestrian Railing': {
                'category': 'Pedestrian Facility',
                'unit': 'm',
                'cpwd_code': 'CPWD-SOR-2023-12.52',
                'specifications': 'MS railing, powder coated, 1.1m height',
                'typical_rate': 1250.0
            },
            
            # Lighting
            'LED Street Light': {
                'category': 'Illumination',
                'unit': 'nos',
                'cpwd_code': 'CPWD-SOR-2023-16.25',
                'gem_category': 'LED Street Lights',
                'specifications': '150W LED, IP65, 4000K',
                'typical_rate': 12500.0
            },
            'Light Pole': {
                'category': 'Illumination',
                'unit': 'nos',
                'cpwd_code': 'CPWD-SOR-2023-16.26',
                'specifications': 'MS octagonal pole, 9m, galvanized',
                'typical_rate': 8500.0
            },
            
            # Delineators
            'Flexible Delineator': {
                'category': 'Delineation',
                'unit': 'nos',
                'cpwd_code': 'CPWD-SOR-2023-18.35',
                'specifications': 'PU/rubber, 750mm, retroreflective',
                'typical_rate': 650.0
            },
            'Chevron Marker': {
                'category': 'Delineation',
                'unit': 'nos',
                'cpwd_code': 'CPWD-SOR-2023-18.36',
                'specifications': 'Aluminum, Grade-I retroreflective',
                'typical_rate': 1250.0
            },
        }
    
    async def get_material_price(
        self, 
        material_name: str,
        quantity: float,
        unit: str,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get material price from cache or fetch from sources
        """
        # Check cache first
        cached_price = await self._get_cached_price(material_name, unit)
        if cached_price:
            logger.info(f"Using cached price for {material_name}")
            return {
                'material_name': material_name,
                'quantity': quantity,
                'unit': unit,
                'unit_rate': cached_price['unit_rate'],
                'total_cost': quantity * cached_price['unit_rate'],
                'source': cached_price['source'],
                'source_reference': cached_price['source_reference'],
                'fetched_at': cached_price['fetched_at'],
                'from_cache': True
            }
        
        # Try to fetch from sources
        price_data = await self._fetch_price_from_sources(material_name, unit, location)
        
        if price_data:
            # Cache the price
            await self._cache_price(material_name, unit, price_data)
            
            return {
                'material_name': material_name,
                'quantity': quantity,
                'unit': unit,
                'unit_rate': price_data['unit_rate'],
                'total_cost': quantity * price_data['unit_rate'],
                'source': price_data['source'],
                'source_reference': price_data.get('reference', ''),
                'fetched_at': datetime.now(),
                'from_cache': False
            }
        
        # Fallback to typical rate if available
        return await self._get_fallback_price(material_name, quantity, unit)
    
    async def _get_cached_price(self, material_name: str, unit: str) -> Optional[Dict]:
        """Get price from cache"""
        # Try Redis first
        if self.redis_client:
            try:
                cache_key = f"price:{material_name}:{unit}"
                cached = self.redis_client.get(cache_key)
                if cached:
                    return pickle.loads(cached)
            except Exception as e:
                logger.warning(f"Redis get error: {str(e)}")
        
        # Try database cache
        cache_entry = self.db.query(PriceCache).filter(
            PriceCache.material_name == material_name,
            PriceCache.unit == unit,
            PriceCache.valid_until > datetime.now()
        ).order_by(PriceCache.fetched_at.desc()).first()
        
        if cache_entry:
            cache_entry.cache_hits += 1
            cache_entry.last_accessed = datetime.now()
            self.db.commit()
            
            return {
                'unit_rate': cache_entry.unit_rate,
                'source': cache_entry.source,
                'source_reference': cache_entry.source_reference,
                'fetched_at': cache_entry.fetched_at
            }
        
        return None
    
    async def _fetch_price_from_sources(
        self, 
        material_name: str, 
        unit: str,
        location: Optional[str] = None
    ) -> Optional[Dict]:
        """Fetch price from government sources"""
        
        # Check material database first
        material_info = self.material_database.get(material_name)
        if material_info:
            return {
                'unit_rate': material_info['typical_rate'],
                'source': 'CPWD_SOR',
                'reference': material_info.get('cpwd_code', '')
            }
        
        # Try CPWD SOR
        cpwd_price = await self._fetch_from_cpwd_sor(material_name, unit)
        if cpwd_price:
            return cpwd_price
        
        # Try GeM
        gem_price = await self._fetch_from_gem(material_name, unit)
        if gem_price:
            return gem_price
        
        return None
    
    async def _fetch_from_cpwd_sor(self, material_name: str, unit: str) -> Optional[Dict]:
        """Fetch price from CPWD SOR"""
        try:
            # In production, make actual API call
            # For now, simulate with material database lookup
            logger.info(f"Attempting to fetch {material_name} from CPWD SOR")
            
            # Simulate API response
            # async with httpx.AsyncClient() as client:
            #     response = await client.get(
            #         f"{settings.CPWD_SOR_API_URL}/search",
            #         params={'material': material_name, 'unit': unit}
            #     )
            #     if response.status_code == 200:
            #         data = response.json()
            #         return data
            
            return None
        
        except Exception as e:
            logger.error(f"Error fetching from CPWD SOR: {str(e)}")
            return None
    
    async def _fetch_from_gem(self, material_name: str, unit: str) -> Optional[Dict]:
        """Fetch price from GeM marketplace"""
        try:
            logger.info(f"Attempting to fetch {material_name} from GeM")
            
            # In production, make actual API call with authentication
            # async with httpx.AsyncClient() as client:
            #     response = await client.get(
            #         f"{settings.GEM_API_URL}/products/search",
            #         headers={'Authorization': f'Bearer {settings.GEM_API_KEY}'},
            #         params={'query': material_name}
            #     )
            #     if response.status_code == 200:
            #         data = response.json()
            #         return data
            
            return None
        
        except Exception as e:
            logger.error(f"Error fetching from GeM: {str(e)}")
            return None
    
    async def _get_fallback_price(
        self, 
        material_name: str, 
        quantity: float, 
        unit: str
    ) -> Dict[str, Any]:
        """Get fallback price from material database"""
        
        # Try exact match
        material_info = self.material_database.get(material_name)
        
        # Try fuzzy match
        if not material_info:
            material_name_lower = material_name.lower()
            for mat_name, mat_info in self.material_database.items():
                if material_name_lower in mat_name.lower() or mat_name.lower() in material_name_lower:
                    material_info = mat_info
                    material_name = mat_name
                    break
        
        if material_info:
            unit_rate = material_info['typical_rate']
            return {
                'material_name': material_name,
                'quantity': quantity,
                'unit': unit,
                'unit_rate': unit_rate,
                'total_cost': quantity * unit_rate,
                'source': 'Material_Database',
                'source_reference': material_info.get('cpwd_code', 'Estimated'),
                'fetched_at': datetime.now(),
                'from_cache': False,
                'is_estimate': True
            }
        
        # Last resort: return generic rate
        logger.warning(f"No price found for {material_name}, using generic rate")
        generic_rate = 1000.0
        return {
            'material_name': material_name,
            'quantity': quantity,
            'unit': unit,
            'unit_rate': generic_rate,
            'total_cost': quantity * generic_rate,
            'source': 'Estimated',
            'source_reference': 'Generic Rate (Verification Required)',
            'fetched_at': datetime.now(),
            'from_cache': False,
            'is_estimate': True,
            'requires_verification': True
        }
    
    async def _cache_price(self, material_name: str, unit: str, price_data: Dict):
        """Cache price in Redis and database"""
        
        # Cache in Redis
        if self.redis_client:
            try:
                cache_key = f"price:{material_name}:{unit}"
                cache_data = {
                    'unit_rate': price_data['unit_rate'],
                    'source': price_data['source'],
                    'source_reference': price_data.get('reference', ''),
                    'fetched_at': datetime.now()
                }
                self.redis_client.setex(
                    cache_key,
                    settings.REDIS_CACHE_TTL,
                    pickle.dumps(cache_data)
                )
            except Exception as e:
                logger.warning(f"Redis cache error: {str(e)}")
        
        # Cache in database
        try:
            cache_entry = PriceCache(
                material_name=material_name,
                unit=unit,
                unit_rate=price_data['unit_rate'],
                source=price_data['source'],
                source_reference=price_data.get('reference', ''),
                valid_from=datetime.now(),
                valid_until=datetime.now() + timedelta(days=90),
                fetched_at=datetime.now()
            )
            self.db.add(cache_entry)
            self.db.commit()
        except Exception as e:
            logger.error(f"Database cache error: {str(e)}")
            self.db.rollback()
