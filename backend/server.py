from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import uuid
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
import asyncio
import time
import json
import re


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define Models
class Property(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    region: str
    location: str
    property_type: str  # apartment, house, plot
    price: Optional[float] = None
    price_per_sqm: Optional[float] = None
    area: Optional[float] = None
    operation_type: str  # sale, rent
    url: str
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PropertyCreate(BaseModel):
    region: str
    location: str
    property_type: str
    price: Optional[float] = None
    price_per_sqm: Optional[float] = None
    area: Optional[float] = None
    operation_type: str
    url: str

class ScrapingSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str  # running, completed, failed
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    total_properties: int = 0
    regions_scraped: List[str] = []
    error_message: Optional[str] = None

class RegionStats(BaseModel):
    region: str
    location: str
    avg_sale_price: Optional[float] = None
    avg_rent_price: Optional[float] = None
    total_properties: int = 0
    avg_price_per_sqm_sale: Optional[float] = None
    avg_price_per_sqm_rent: Optional[float] = None

# Portuguese regions and major cities for scraping
PORTUGUESE_REGIONS = {
    'lisboa': ['lisboa', 'cascais', 'sintra', 'almada', 'amadora', 'loures'],
    'porto': ['porto', 'vila-nova-de-gaia', 'matosinhos', 'gondomar', 'maia'],
    'faro': ['faro', 'olhao', 'albufeira', 'portimao', 'tavira', 'lagoa'],
    'braga': ['braga', 'guimaraes', 'barcelos', 'famalicao', 'esposende'],
    'aveiro': ['aveiro', 'ovar', 'ilhavo', 'agueda', 'estarreja'],
    'coimbra': ['coimbra', 'figueira-da-foz', 'cantanhede', 'montemor-o-velho'],
    'leiria': ['leiria', 'marinha-grande', 'batalha', 'pombal', 'alcobaca'],
    'setubal': ['setubal', 'barreiro', 'almada', 'seixal', 'moita'],
    'santarem': ['santarem', 'torres-novas', 'entroncamento', 'tomar'],
    'viseu': ['viseu', 'lamego', 'sao-pedro-do-sul', 'tondela'],
    'castelo-branco': ['castelo-branco', 'covilha', 'fundao', 'belmonte'],
    'guarda': ['guarda', 'seia', 'gouveia', 'pinhel'],
    'braganca': ['braganca', 'mirandela', 'macedo-de-cavaleiros'],
    'vila-real': ['vila-real', 'chaves', 'peso-da-regua', 'montalegre'],
    'viana-do-castelo': ['viana-do-castelo', 'ponte-de-lima', 'valenca'],
    'beja': ['beja', 'serpa', 'moura', 'odemira'],
    'evora': ['evora', 'estremoz', 'montemor-o-novo', 'vendas-novas'],
    'portalegre': ['portalegre', 'elvas', 'campo-maior', 'nisa']
}

class IdealistaScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-PT,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
    def extract_price(self, price_text):
        """Extract numeric price from text"""
        if not price_text:
            return None
        # Remove currency symbols and spaces, extract numbers
        price_clean = re.sub(r'[€\s.]', '', price_text.replace(',', '.'))
        numbers = re.findall(r'\d+', price_clean)
        if numbers:
            return float(''.join(numbers))
        return None
    
    def extract_area(self, area_text):
        """Extract area in square meters"""
        if not area_text:
            return None
        numbers = re.findall(r'\d+', area_text)
        if numbers:
            return float(numbers[0])
        return None
    
    async def scrape_location(self, region, location, operation_type='sale', property_type=None):
        """Scrape properties from a specific location"""
        properties = []
        
        # Construct URL for idealista.pt
        if operation_type == 'sale':
            op_type = 'venda'
        else:
            op_type = 'arrendamento'
            
        # Property type mapping
        prop_types = []
        if property_type is None:
            prop_types = ['casas', 'apartamentos', 'terrenos']
        elif property_type == 'house':
            prop_types = ['casas']
        elif property_type == 'apartment':
            prop_types = ['apartamentos']
        elif property_type == 'plot':
            prop_types = ['terrenos']
            
        for prop_type in prop_types:
            try:
                url = f"https://www.idealista.pt/{op_type}/{prop_type}/{location}/"
                logger.info(f"Scraping: {url}")
                
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find property listings (this is a simplified selector - may need adjustment)
                listings = soup.find_all('article', class_=['item', 'item-multimedia'])
                
                for listing in listings[:10]:  # Limit to first 10 properties per page
                    try:
                        # Extract price
                        price_elem = listing.find(['span', 'div'], class_=['item-price', 'price'])
                        price = self.extract_price(price_elem.get_text() if price_elem else None)
                        
                        # Extract area
                        area_elem = listing.find(['span', 'div'], string=re.compile(r'm²|m2'))
                        area = self.extract_area(area_elem.get_text() if area_elem else None)
                        
                        # Calculate price per sqm
                        price_per_sqm = None
                        if price and area and area > 0:
                            price_per_sqm = price / area
                        
                        # Extract property URL
                        link_elem = listing.find('a')
                        property_url = f"https://www.idealista.pt{link_elem['href']}" if link_elem else url
                        
                        property_data = {
                            'region': region,
                            'location': location,
                            'property_type': prop_type.replace('apartamentos', 'apartment').replace('casas', 'house').replace('terrenos', 'plot'),
                            'price': price,
                            'price_per_sqm': price_per_sqm,
                            'area': area,
                            'operation_type': operation_type,
                            'url': property_url
                        }
                        
                        properties.append(property_data)
                        
                    except Exception as e:
                        logger.error(f"Error processing listing: {e}")
                        continue
                
                # Add delay to be respectful
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                continue
        
        return properties

scraper = IdealistaScraper()

@api_router.post("/scrape/start")
async def start_scraping(background_tasks: BackgroundTasks):
    """Start a new scraping session"""
    session = ScrapingSession(status="running")
    session_dict = session.dict()
    await db.scraping_sessions.insert_one(session_dict)
    
    background_tasks.add_task(run_scraping_task, session.id)
    
    return {"message": "Scraping started", "session_id": session.id}

async def run_scraping_task(session_id: str):
    """Background task to run the scraping"""
    try:
        # Update session status
        await db.scraping_sessions.update_one(
            {"id": session_id},
            {"$set": {"status": "running"}}
        )
        
        total_properties = 0
        regions_scraped = []
        
        # Scrape all regions
        for region, locations in PORTUGUESE_REGIONS.items():
            regions_scraped.append(region)
            
            for location in locations:
                # Scrape sales
                sale_properties = await scraper.scrape_location(region, location, 'sale')
                for prop_data in sale_properties:
                    property_obj = Property(**prop_data)
                    await db.properties.insert_one(property_obj.dict())
                    total_properties += 1
                
                # Scrape rentals
                rent_properties = await scraper.scrape_location(region, location, 'rent')
                for prop_data in rent_properties:
                    property_obj = Property(**prop_data)
                    await db.properties.insert_one(property_obj.dict())
                    total_properties += 1
        
        # Update session as completed
        await db.scraping_sessions.update_one(
            {"id": session_id},
            {"$set": {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc),
                "total_properties": total_properties,
                "regions_scraped": regions_scraped
            }}
        )
        
        logger.info(f"Scraping completed: {total_properties} properties")
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        await db.scraping_sessions.update_one(
            {"id": session_id},
            {"$set": {
                "status": "failed",
                "completed_at": datetime.now(timezone.utc),
                "error_message": str(e)
            }}
        )

@api_router.get("/scraping-sessions", response_model=List[ScrapingSession])
async def get_scraping_sessions():
    """Get all scraping sessions"""
    sessions = await db.scraping_sessions.find().sort("started_at", -1).to_list(100)
    return [ScrapingSession(**session) for session in sessions]

@api_router.get("/scraping-sessions/{session_id}", response_model=ScrapingSession)
async def get_scraping_session(session_id: str):
    """Get specific scraping session"""
    session = await db.scraping_sessions.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return ScrapingSession(**session)

@api_router.get("/properties", response_model=List[Property])
async def get_properties(
    region: Optional[str] = None,
    operation_type: Optional[str] = None,
    property_type: Optional[str] = None,
    limit: int = 100
):
    """Get properties with optional filters"""
    filter_query = {}
    if region:
        filter_query["region"] = region
    if operation_type:
        filter_query["operation_type"] = operation_type
    if property_type:
        filter_query["property_type"] = property_type
    
    properties = await db.properties.find(filter_query).sort("scraped_at", -1).limit(limit).to_list(limit)
    return [Property(**prop) for prop in properties]

@api_router.get("/stats/regions", response_model=List[RegionStats])
async def get_region_stats():
    """Get aggregated statistics by region"""
    pipeline = [
        {
            "$group": {
                "_id": {"region": "$region", "location": "$location", "operation_type": "$operation_type"},
                "avg_price": {"$avg": "$price"},
                "avg_price_per_sqm": {"$avg": "$price_per_sqm"},
                "count": {"$sum": 1}
            }
        }
    ]
    
    results = await db.properties.aggregate(pipeline).to_list(1000)
    
    # Process results into RegionStats format
    stats_dict = {}
    for result in results:
        key = f"{result['_id']['region']}-{result['_id']['location']}"
        if key not in stats_dict:
            stats_dict[key] = {
                'region': result['_id']['region'],
                'location': result['_id']['location'],
                'total_properties': 0,
                'avg_sale_price': None,
                'avg_rent_price': None,
                'avg_price_per_sqm_sale': None,
                'avg_price_per_sqm_rent': None
            }
        
        op_type = result['_id']['operation_type']
        stats_dict[key]['total_properties'] += result['count']
        
        if op_type == 'sale':
            stats_dict[key]['avg_sale_price'] = result['avg_price']
            stats_dict[key]['avg_price_per_sqm_sale'] = result['avg_price_per_sqm']
        else:
            stats_dict[key]['avg_rent_price'] = result['avg_price']
            stats_dict[key]['avg_price_per_sqm_rent'] = result['avg_price_per_sqm']
    
    return [RegionStats(**stats) for stats in stats_dict.values()]

@api_router.get("/export/php")
async def export_php_format():
    """Export data in PHP array format like the original file"""
    stats = await get_region_stats()
    
    php_array = {}
    for stat in stats:
        region = stat.region
        if region not in php_array:
            php_array[region] = {
                'average': stat.avg_sale_price or 0,
                'average_rent': stat.avg_rent_price or 0
            }
        
        # Add location data
        if stat.location != region:
            location_key = stat.location.replace('-', '_')
            php_array[region][location_key] = {
                'name': stat.location.title(),
                'average': stat.avg_sale_price or 0,
                'average_rent': stat.avg_rent_price or 0
            }
    
    return {"php_array": php_array}

@api_router.delete("/properties")
async def clear_all_properties():
    """Clear all scraped properties"""
    result = await db.properties.delete_many({})
    return {"message": f"Deleted {result.deleted_count} properties"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()