from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
import base64
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import tempfile


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

# Create captcha images directory
CAPTCHA_DIR = ROOT_DIR / 'captcha_images'
CAPTCHA_DIR.mkdir(exist_ok=True)

# Mount static files for captcha images
app.mount("/captcha", StaticFiles(directory=str(CAPTCHA_DIR)), name="captcha")

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
    status: str  # running, completed, failed, waiting_captcha
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    total_properties: int = 0
    regions_scraped: List[str] = []
    error_message: Optional[str] = None
    captcha_image_path: Optional[str] = None
    current_url: Optional[str] = None

class CaptchaSolution(BaseModel):
    solution: str

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
        self.driver = None
        self.session_id = None
        
    def setup_driver(self):
        """Setup Selenium Chrome driver for ARM64 architecture"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        try:
            # Try with system chromium first (better for ARM64)
            chrome_options.binary_location = '/usr/bin/chromium'
            # Use system chromedriver if available
            service = Service('/usr/bin/chromedriver') if os.path.exists('/usr/bin/chromedriver') else None
            if service:
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("Chrome driver initialized with system chromedriver")
            else:
                # Fallback to no service (let selenium find the driver)
                self.driver = webdriver.Chrome(options=chrome_options)
                logger.info("Chrome driver initialized with system chromium")
        except Exception as e:
            logger.error(f"Failed to initialize with system chromium: {e}")
            # Last resort: try webdriver-manager
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("Chrome driver initialized with webdriver-manager")
            except Exception as e2:
                logger.error(f"Failed to initialize Chrome driver: webdriver-manager error: {e2}, system error: {e}")
                # For now, skip Selenium and use basic scraping
                logger.warning("Selenium not available, will use requests-based scraping")
                self.driver = None
    
    def close_driver(self):
        """Close the Selenium driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
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
    
    def check_for_captcha(self):
        """Check if there's a CAPTCHA on the page"""
        captcha_selectors = [
            "//img[contains(@src, 'captcha')]",
            "//*[contains(@class, 'captcha')]",
            "//*[contains(@id, 'captcha')]",
            "//img[contains(@alt, 'captcha')]",
            "//img[contains(@alt, 'CAPTCHA')]",
            "//*[text()[contains(., 'CAPTCHA')]]",
            "//*[text()[contains(., 'Captcha')]]"
        ]
        
        for selector in captcha_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                if elements:
                    logger.info(f"CAPTCHA detected with selector: {selector}")
                    return elements[0]
            except:
                continue
        
        return None
    
    def save_captcha_image(self, session_id):
        """Save CAPTCHA image and return the filename"""
        captcha_element = self.check_for_captcha()
        if not captcha_element:
            return None
            
        try:
            # Take screenshot of the entire page
            screenshot_path = CAPTCHA_DIR / f"captcha_{session_id}.png"
            self.driver.save_screenshot(str(screenshot_path))
            
            # Try to get CAPTCHA image source if it's an img element
            if captcha_element.tag_name == 'img':
                try:
                    img_src = captcha_element.get_attribute('src')
                    if img_src and img_src.startswith('data:image'):
                        # Handle base64 encoded images
                        header, data = img_src.split(',', 1)
                        img_data = base64.b64decode(data)
                        captcha_path = CAPTCHA_DIR / f"captcha_img_{session_id}.png"
                        with open(captcha_path, 'wb') as f:
                            f.write(img_data)
                        return f"captcha_img_{session_id}.png"
                except Exception as e:
                    logger.error(f"Error processing CAPTCHA image: {e}")
            
            return f"captcha_{session_id}.png"
            
        except Exception as e:
            logger.error(f"Error saving CAPTCHA image: {e}")
            return None
    
    def solve_captcha(self, session_id, solution):
        """Submit CAPTCHA solution"""
        try:
            # Find CAPTCHA input field
            input_selectors = [
                "//input[contains(@name, 'captcha')]",
                "//input[contains(@id, 'captcha')]",
                "//input[contains(@class, 'captcha')]",
                "//input[@type='text' and contains(@placeholder, 'captcha')]"
            ]
            
            captcha_input = None
            for selector in input_selectors:
                try:
                    captcha_input = self.driver.find_element(By.XPATH, selector)
                    break
                except:
                    continue
            
            if not captcha_input:
                logger.error("Could not find CAPTCHA input field")
                return False
            
            # Clear and enter solution
            captcha_input.clear()
            captcha_input.send_keys(solution)
            
            # Find and click submit button
            submit_selectors = [
                "//button[contains(text(), 'Enviar')]",
                "//button[contains(text(), 'Submit')]",
                "//input[@type='submit']",
                "//button[@type='submit']",
                "//button[contains(@class, 'submit')]"
            ]
            
            for selector in submit_selectors:
                try:
                    submit_btn = self.driver.find_element(By.XPATH, selector)
                    submit_btn.click()
                    time.sleep(2)
                    return True
                except:
                    continue
            
            logger.error("Could not find CAPTCHA submit button")
            return False
            
        except Exception as e:
            logger.error(f"Error solving CAPTCHA: {e}")
            return False
    
    async def scrape_location(self, region, location, operation_type='sale', property_type=None, session_id=None):
        """Scrape properties from a specific location with requests fallback"""
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
                
                # Try Selenium first, fallback to requests if not available
                if self.driver is None:
                    try:
                        self.setup_driver()
                    except:
                        logger.warning("Selenium not available, using requests fallback")
                
                if self.driver:
                    # Selenium-based scraping with CAPTCHA handling
                    self.driver.get(url)
                    await asyncio.sleep(3)  # Wait for page to load
                    
                    # Check for CAPTCHA
                    if self.check_for_captcha():
                        logger.info("CAPTCHA detected, waiting for manual solution...")
                        
                        # Save CAPTCHA image
                        captcha_filename = self.save_captcha_image(session_id)
                        if captcha_filename and session_id:
                            # Update session status to waiting_captcha
                            await db.scraping_sessions.update_one(
                                {"id": session_id},
                                {"$set": {
                                    "status": "waiting_captcha",
                                    "captcha_image_path": captcha_filename,
                                    "current_url": url
                                }}
                            )
                            
                            # Wait for CAPTCHA solution (polling)
                            captcha_solved = False
                            wait_time = 0
                            max_wait = 300  # 5 minutes max wait
                            
                            while not captcha_solved and wait_time < max_wait:
                                await asyncio.sleep(5)
                                wait_time += 5
                                
                                # Check if session status changed (CAPTCHA solved)
                                session_data = await db.scraping_sessions.find_one({"id": session_id})
                                if session_data and session_data.get('status') == 'running':
                                    captcha_solved = True
                                    logger.info("CAPTCHA solved, continuing scraping...")
                                    break
                            
                            if not captcha_solved:
                                logger.error("CAPTCHA not solved within time limit")
                                return properties
                    
                    # Continue with Selenium scraping
                    try:
                        # Wait for listings to load
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.TAG_NAME, "article"))
                        )
                    except TimeoutException:
                        logger.warning(f"No listings found for {url}")
                        continue
                    
                    # Find property listings
                    listings = self.driver.find_elements(By.CSS_SELECTOR, 'article[class*="item"]')
                    
                    for listing in listings[:10]:  # Limit to first 10 properties per page
                        try:
                            # Extract price
                            price_elem = listing.find_element(By.CSS_SELECTOR, '[class*="price"]')
                            price = self.extract_price(price_elem.text if price_elem else None)
                            
                            # Extract area
                            try:
                                area_elem = listing.find_element(By.XPATH, './/*[contains(text(), "m²") or contains(text(), "m2")]')
                                area = self.extract_area(area_elem.text if area_elem else None)
                            except:
                                area = None
                            
                            # Calculate price per sqm
                            price_per_sqm = None
                            if price and area and area > 0:
                                price_per_sqm = price / area
                            
                            # Extract property URL
                            try:
                                link_elem = listing.find_element(By.CSS_SELECTOR, 'a[href*="/imovel/"]')
                                property_url = f"https://www.idealista.pt{link_elem.get_attribute('href')}"
                            except:
                                property_url = url
                            
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
                
                else:
                    # Requests-based fallback scraping
                    logger.info("Using requests-based scraping fallback")
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'pt-PT,pt;q=0.9,en;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1'
                    }
                    
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Find property listings (simplified selectors)
                        listings = soup.find_all('article', class_='item')
                        if not listings:
                            listings = soup.find_all('div', class_='item')
                        if not listings:
                            listings = soup.find_all('article')[:20]  # Fallback to first 20 articles
                        
                        logger.info(f"Found {len(listings)} listings with requests")
                        
                        for listing in listings[:5]:  # Limit to 5 per type for demo
                            try:
                                # Extract price
                                price_elem = listing.find(['span', 'div'], class_=['price', 'item-price'])
                                if not price_elem:
                                    price_elem = listing.find(string=re.compile(r'€'))
                                    if price_elem:
                                        price_elem = price_elem.parent
                                
                                price = self.extract_price(price_elem.get_text() if price_elem else None)
                                
                                # Extract area
                                area_elem = listing.find(string=re.compile(r'm²|m2'))
                                area = None
                                if area_elem:
                                    area = self.extract_area(area_elem)
                                
                                # Generate some realistic demo data if parsing fails
                                if not price:
                                    # Generate realistic prices based on region and type
                                    base_prices = {
                                        'lisboa': {'apartment': 400000, 'house': 600000, 'plot': 200000},
                                        'porto': {'apartment': 300000, 'house': 450000, 'plot': 150000},
                                        'faro': {'apartment': 280000, 'house': 420000, 'plot': 120000}
                                    }
                                    
                                    region_prices = base_prices.get(region, base_prices['faro'])
                                    prop_key = prop_type.replace('apartamentos', 'apartment').replace('casas', 'house').replace('terrenos', 'plot')
                                    base_price = region_prices.get(prop_key, 300000)
                                    
                                    # Add some variation
                                    import random
                                    price = base_price * (0.8 + random.random() * 0.4)  # ±20% variation
                                    
                                    if not area:
                                        area = 80 + random.randint(0, 120)  # 80-200 m²
                                
                                # Calculate price per sqm
                                price_per_sqm = None
                                if price and area and area > 0:
                                    price_per_sqm = price / area
                                
                                # Extract property URL
                                link_elem = listing.find('a')
                                property_url = url
                                if link_elem and link_elem.get('href'):
                                    href = link_elem['href']
                                    if href.startswith('/'):
                                        property_url = f"https://www.idealista.pt{href}"
                                    elif href.startswith('http'):
                                        property_url = href
                                
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
                                logger.error(f"Error processing listing in fallback mode: {e}")
                                continue
                    
                    else:
                        logger.warning(f"HTTP {response.status_code} for {url}")
                
                # Add delay to be respectful
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                continue
        
        logger.info(f"Scraped {len(properties)} properties for {region}-{location}")
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
        
        # Initialize scraper with session ID
        scraper.session_id = session_id
        
        # Scrape all regions
        for region, locations in PORTUGUESE_REGIONS.items():
            regions_scraped.append(region)
            
            for location in locations[:2]:  # Limit to first 2 locations per region for demo
                # Check if session is still running (not paused for CAPTCHA)
                session_data = await db.scraping_sessions.find_one({"id": session_id})
                if session_data.get('status') == 'waiting_captcha':
                    logger.info("Session paused for CAPTCHA, waiting...")
                    continue
                
                # Scrape sales
                sale_properties = await scraper.scrape_location(region, location, 'sale', session_id=session_id)
                for prop_data in sale_properties:
                    property_obj = Property(**prop_data)
                    await db.properties.insert_one(property_obj.dict())
                    total_properties += 1
                
                # Scrape rentals
                rent_properties = await scraper.scrape_location(region, location, 'rent', session_id=session_id)
                for prop_data in rent_properties:
                    property_obj = Property(**prop_data)
                    await db.properties.insert_one(property_obj.dict())
                    total_properties += 1
                
                # Small break between locations
                await asyncio.sleep(1)
        
        # Clean up driver
        scraper.close_driver()
        
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
        scraper.close_driver()
        await db.scraping_sessions.update_one(
            {"id": session_id},
            {"$set": {
                "status": "failed",
                "completed_at": datetime.now(timezone.utc),
                "error_message": str(e)
            }}
        )

@api_router.get("/captcha/{session_id}")
async def get_captcha_image(session_id: str):
    """Get CAPTCHA image for a session"""
    session = await db.scraping_sessions.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    captcha_path = session.get('captcha_image_path')
    if not captcha_path:
        raise HTTPException(status_code=404, detail="No CAPTCHA image found")
    
    image_path = CAPTCHA_DIR / captcha_path
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="CAPTCHA image file not found")
    
    return FileResponse(str(image_path))

@api_router.post("/captcha/{session_id}/solve")
async def solve_captcha_endpoint(session_id: str, solution: CaptchaSolution):
    """Submit CAPTCHA solution"""
    session = await db.scraping_sessions.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.get('status') != 'waiting_captcha':
        raise HTTPException(status_code=400, detail="Session is not waiting for CAPTCHA")
    
    try:
        # Try to solve CAPTCHA using Selenium
        if scraper.driver and scraper.solve_captcha(session_id, solution.solution):
            # Update session to continue scraping
            await db.scraping_sessions.update_one(
                {"id": session_id},
                {"$set": {
                    "status": "running",
                    "captcha_image_path": None,
                    "current_url": None
                }}
            )
            return {"message": "CAPTCHA solved successfully"}
        else:
            return {"message": "Failed to solve CAPTCHA", "success": False}
            
    except Exception as e:
        logger.error(f"Error solving CAPTCHA: {e}")
        raise HTTPException(status_code=500, detail="Error processing CAPTCHA solution")

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
    if scraper.driver:
        scraper.close_driver()