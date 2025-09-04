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
import random


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
    # New fields for detailed error tracking
    failed_zones: List[dict] = []  # List of failed zones with error details
    success_zones: List[dict] = []  # List of successful zones with data count

class CaptchaSolution(BaseModel):
    solution: str

class RegionStats(BaseModel):
    region: str
    location: str
    avg_sale_price_per_sqm: Optional[float] = None  # €/m² for sales
    avg_rent_price_per_sqm: Optional[float] = None  # €/m² for rentals
    total_properties: int = 0
    # Keep other stats for detailed analytics
    avg_sale_price: Optional[float] = None
    avg_rent_price: Optional[float] = None
    # Add display formatting
    display_info: Optional[dict] = None

class DetailedPropertyStats(BaseModel):
    property_type: str  # apartment, house, urban_plot, rural_plot
    operation_type: str  # sale, rent
    avg_price_per_sqm: Optional[float] = None
    avg_price: Optional[float] = None
    count: int = 0

class ExtendedRegionStats(BaseModel):
    region: str
    location: str
    display_info: Optional[dict] = None
    # General stats (backward compatibility)
    avg_sale_price_per_sqm: Optional[float] = None
    avg_rent_price_per_sqm: Optional[float] = None
    total_properties: int = 0
    # Detailed stats by property type and operation
    detailed_stats: List[DetailedPropertyStats] = []

@api_router.delete("/properties")
async def clear_all_properties():
    """Clear all scraped properties"""
    result = await db.properties.delete_many({})
    return {"message": f"Deleted {result.deleted_count} properties"}

class CoverageStats(BaseModel):
    distrito: str
    total_concelhos: int
    scraped_concelhos: int
    total_freguesias: int
    scraped_freguesias: int
    coverage_percentage: float
    missing_concelhos: List[str] = []
    missing_freguesias: List[str] = []

class CompleteCoverageReport(BaseModel):
    total_districts: int
    covered_districts: int
    total_municipalities: int
    covered_municipalities: int
    total_parishes: int
    covered_parishes: int
    overall_coverage_percentage: float
    district_coverage: List[CoverageStats]

# Portuguese administrative structure (will be populated dynamically)
PORTUGUESE_STRUCTURE = {
    # Will be populated from idealista.pt reports page
    # Format: {distrito: {concelho: [freguesias...]}}
}

class ProxyRotationScraper:
    """Advanced scraper with residential proxy rotation and session management"""
    
    def __init__(self):
        # Free proxy lists (rotating residential proxies)
        self.proxy_sources = [
            "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=PT&format=json",
            "https://www.proxy-list.download/api/v1/get?type=http&anon=elite&country=PT",
        ]
        self.working_proxies = []
        self.current_proxy_index = 0
        self.sessions = {}
        
    async def fetch_fresh_proxies(self):
        """Fetch fresh Portuguese residential proxies"""
        proxies = []
        try:
            # Method 1: Use known Portuguese residential proxy ranges
            portuguese_proxy_ips = [
                "213.13.147.0/24",  # NOS Portugal
                "87.196.0.0/16",    # MEO Portugal  
                "85.244.0.0/16",    # Vodafone Portugal
                "178.168.0.0/16",   # NOWO Portugal
            ]
            
            # For now, use public proxies as fallback
            import requests
            for source in self.proxy_sources:
                try:
                    response = requests.get(source, timeout=10)
                    if response.status_code == 200:
                        proxy_data = response.json()
                        for proxy in proxy_data:
                            if isinstance(proxy, dict):
                                ip = proxy.get('ip')
                                port = proxy.get('port')
                                if ip and port:
                                    proxies.append(f"{ip}:{port}")
                except:
                    continue
                    
            self.working_proxies = proxies[:20]  # Use first 20 proxies
            logger.info(f"Fetched {len(self.working_proxies)} proxies for rotation")
            
        except Exception as e:
            logger.warning(f"Could not fetch proxies: {e}")
            
    def get_next_proxy(self):
        """Get next proxy in rotation"""
        if not self.working_proxies:
            return None
            
        proxy = self.working_proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.working_proxies)
        return proxy
        
    async def test_proxy(self, proxy):
        """Test if a proxy works with Idealista"""
        try:
            proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            
            headers = ultra_stealth_scraper.current_user_profile or {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Test with Idealista homepage
            response = requests.get('https://www.idealista.pt/', 
                                  proxies=proxies, 
                                  headers=headers, 
                                  timeout=15)
            
            if response.status_code == 200:
                logger.info(f"✅ Proxy {proxy} working")
                return True
            else:
                logger.warning(f"❌ Proxy {proxy} returned {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"❌ Proxy {proxy} failed: {e}")
            return False

### **2. 🍪 Session Persistence Complète**

class SessionManager:
    """Manage persistent browser sessions with cookies and history"""
    
    def __init__(self):
        self.sessions = {}
        self.session_cookies = {}
        
    async def create_realistic_session(self, session_id):
        """Create a realistic browsing session"""
        try:
            session = requests.Session()
            
            # Step 1: Visit Google Portugal first (natural entry point)
            logger.info("🌍 Creating realistic session: Starting from Google Portugal...")
            session.get('https://www.google.pt/', timeout=15)
            await asyncio.sleep(random.uniform(2, 5))
            
            # Step 2: Search for "apartamentos Lisboa" on Google (natural search)
            search_params = {
                'q': random.choice([
                    'apartamentos Lisboa idealista',
                    'casas para comprar Porto',
                    'preços habitação Portugal',
                    'imobiliário Faro'
                ])
            }
            logger.info(f"🔍 Simulating Google search: {search_params['q']}")
            session.get('https://www.google.pt/search', params=search_params, timeout=15)
            await asyncio.sleep(random.uniform(3, 8))
            
            # Step 3: Visit Idealista homepage (natural navigation from Google)
            logger.info("🏠 Natural navigation: Google -> Idealista homepage")
            homepage_response = session.get('https://www.idealista.pt/', timeout=15)
            await asyncio.sleep(random.uniform(4, 10))
            
            # Step 4: Browse a few pages naturally (establish cookies and behavior)
            natural_pages = [
                'https://www.idealista.pt/comprar-casas/',
                'https://www.idealista.pt/arrendar-casas/',
                'https://www.idealista.pt/comprar-casas/lisboa/',
            ]
            
            for page in natural_pages[:2]:  # Visit 2 pages naturally
                logger.info(f"📄 Natural browsing: {page}")
                session.get(page, timeout=15)
                await asyncio.sleep(random.uniform(5, 12))
            
            # Store session
            self.sessions[session_id] = session
            self.session_cookies[session_id] = session.cookies
            
            logger.info(f"✅ Realistic session created with {len(session.cookies)} cookies")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create realistic session: {e}")
            return None

### **3. 🤖 Undetected Chrome avec Anti-Fingerprinting**

class UndetectedScraper:
    """Ultra-advanced scraper with undetected-chromedriver and anti-fingerprinting"""
    
    def __init__(self):
        self.driver = None
        
    async def setup_undetected_chrome(self):
        """Setup truly undetected Chrome browser"""
        try:
            # Install undetected-chromedriver if not available
            try:
                import undetected_chromedriver as uc
            except ImportError:
                logger.info("Installing undetected-chromedriver...")
                import subprocess
                subprocess.check_call(["pip", "install", "undetected-chromedriver"])
                import undetected_chromedriver as uc
            
            # Advanced undetected Chrome options
            options = uc.ChromeOptions()
            
            # Stealth options
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            
            # Anti-fingerprinting
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=TranslateUI')
            options.add_argument('--disable-ipc-flooding-protection')
            
            # Portuguese location simulation
            prefs = {
                "profile.default_content_setting_values.geolocation": 1,
                "profile.managed_default_content_settings.geolocation": 1,
                "profile.default_content_settings.popups": 0,
                "profile.managed_default_content_settings.notifications": 2
            }
            options.add_experimental_option("prefs", prefs)
            
            # Create undetected Chrome instance
            self.driver = uc.Chrome(options=options, version_main=120)
            
            # Set Portuguese geolocation
            params = {
                "latitude": 38.7223,  # Lisbon coordinates
                "longitude": -9.1393,
                "accuracy": 100
            }
            self.driver.execute_cdp_cmd("Emulation.setGeolocationOverride", params)
            
            # Advanced anti-detection JavaScript
            stealth_js = """
                // Remove webdriver traces
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                
                // Override plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5].map(() => 'Plugin')
                });
                
                // Override languages  
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['pt-PT', 'pt', 'en-US', 'en']
                });
                
                // Add realistic properties
                window.chrome = {runtime: {}};
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({query: () => Promise.resolve({state: 'granted'})})
                });
            """
            self.driver.execute_cdp_cmd('Runtime.evaluate', {'expression': stealth_js})
            
            logger.info("✅ Undetected Chrome setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup undetected Chrome: {e}")
            return False

# Initialize advanced scrapers
proxy_scraper = ProxyRotationScraper()
session_manager = SessionManager()
undetected_scraper = UndetectedScraper()

class UltraStealthScraper:
    """Ultra-stealth scraper with advanced anti-detection using real browser profiles"""
    
    def __init__(self):
        self.driver = None
        self.session_cookies = {}
        self.request_count = 0
        self.last_request_time = 0
        self.current_user_profile = None
        
        # More realistic user profiles with consistent behavior
        self.user_profiles = [
            {
                'name': 'Portuguese_Chrome_User',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'language': 'pt-PT,pt;q=0.9',
                'timezone': 'Europe/Lisbon',
                'screen': {'width': 1920, 'height': 1080},
                'viewport': {'width': 1536, 'height': 864},
                'platform': 'Win32'
            },
            {
                'name': 'Portuguese_Firefox_User', 
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
                'language': 'pt-PT,pt;q=0.8,en-US;q=0.5,en;q=0.3',
                'timezone': 'Europe/Lisbon',
                'screen': {'width': 1920, 'height': 1080},
                'viewport': {'width': 1520, 'height': 850},
                'platform': 'Win32'
            },
            {
                'name': 'Portuguese_Mac_User',
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'language': 'pt-PT,pt;q=0.9,en;q=0.8',
                'timezone': 'Europe/Lisbon', 
                'screen': {'width': 2560, 'height': 1440},
                'viewport': {'width': 2560, 'height': 1329},
                'platform': 'MacIntel'
            }
        ]
        
    def setup_ultra_stealth_driver(self):
        """Setup Selenium with ultra-stealth configuration"""
        try:
            # Select a consistent user profile for this session
            self.current_user_profile = random.choice(self.user_profiles)
            logger.info(f"Using user profile: {self.current_user_profile['name']}")
            
            options = Options()
            
            # Basic stealth options
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Advanced anti-detection
            options.add_argument('--disable-web-security')
            options.add_argument('--allow-running-insecure-content')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')  # Faster loading, more human-like for price checking
            options.add_argument('--disable-javascript')  # Disable JS to avoid fingerprinting (we only need HTML)
            
            # User profile specific settings
            profile = self.current_user_profile
            options.add_argument(f'--user-agent={profile["user_agent"]}')
            options.add_argument(f'--window-size={profile["viewport"]["width"]},{profile["viewport"]["height"]}')
            options.add_argument(f'--lang={profile["language"].split(",")[0]}')
            
            # More realistic preferences
            prefs = {
                "profile.default_content_setting_values": {
                    "images": 2,  # Block images for faster loading
                    "media_stream": 2,
                    "notifications": 2
                },
                "profile.managed_default_content_settings": {
                    "images": 2
                }
            }
            options.add_experimental_option("prefs", prefs)
            
            # Create driver
            self.driver = webdriver.Chrome(options=options)
            
            # Additional stealth JavaScript
            self.driver.execute_cdp_cmd('Runtime.enable', {})
            self.driver.execute_cdp_cmd('Runtime.evaluate', {
                'expression': '''
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'languages', {get: () => ['pt-PT', 'pt', 'en']});
                    Object.defineProperty(navigator, 'platform', {get: () => '%s'});
                    window.chrome = {runtime: {}};
                ''' % profile['platform']
            })
            
            # Set viewport to match profile
            self.driver.set_window_size(profile['viewport']['width'], profile['viewport']['height'])
            
            logger.info(f"Ultra-stealth Chrome driver initialized with profile: {profile['name']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup ultra-stealth driver: {e}")
            return False
    
    async def simulate_human_behavior(self):
        """Simulate realistic human browsing behavior"""
        if not self.driver:
            return
            
        try:
            # Random mouse movement (simulate with JavaScript)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Simulate reading time
            reading_time = random.uniform(2, 6)
            logger.info(f"Simulating reading time: {reading_time:.1f} seconds")
            await asyncio.sleep(reading_time)
            
            # Random scroll simulation
            if random.random() < 0.7:  # 70% chance to scroll
                scroll_amount = random.randint(200, 800)
                self.driver.execute_script(f"window.scrollTo(0, {scroll_amount});")
                await asyncio.sleep(random.uniform(0.5, 1.2))
                
                # Scroll back up sometimes
                if random.random() < 0.3:  # 30% chance
                    self.driver.execute_script("window.scrollTo(0, 0);")
                    await asyncio.sleep(random.uniform(0.3, 0.8))
            
        except Exception as e:
            logger.warning(f"Error in human behavior simulation: {e}")
    
    async def ultra_stealth_delay(self):
        """Ultra-conservative delay strategy"""
        # Base delay: much longer than before
        base_delay = random.uniform(15, 30)  # 15-30 seconds base
        
        # Progressive delays get even more aggressive
        if self.request_count > 5:
            base_delay += random.uniform(10, 20)
        if self.request_count > 10:
            base_delay += random.uniform(15, 30)
        if self.request_count > 15:
            base_delay += random.uniform(20, 45)
            
        # Ensure minimum time since last request
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < 10:  # Minimum 10 seconds between any requests
            additional_delay = 10 - time_since_last
            base_delay += additional_delay
            
        logger.info(f"Ultra-stealth delay: {base_delay:.1f} seconds (request #{self.request_count})")
        await asyncio.sleep(base_delay)
        self.last_request_time = time.time()
    
    async def visit_homepage_naturally(self):
        """Visit Idealista homepage first to establish natural session"""
        if not self.driver:
            return False
            
        try:
            logger.info("🏠 Visiting Idealista homepage to establish natural session...")
            self.driver.get("https://www.idealista.pt/")
            
            # Simulate natural homepage browsing
            await asyncio.sleep(random.uniform(3, 7))
            
            # Accept cookies if present (human-like behavior)
            try:
                cookie_button = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Aceitar') or contains(text(), 'aceitar') or contains(@id, 'cookie')]")
                if cookie_button:
                    await asyncio.sleep(random.uniform(1, 3))
                    cookie_button.click()
                    logger.info("✅ Clicked cookie acceptance button")
                    await asyncio.sleep(random.uniform(1, 2))
            except:
                pass  # No cookies banner or already accepted
            
            # Simulate some homepage interaction
            await self.simulate_human_behavior()
            
            return True
            
        except Exception as e:
            logger.error(f"Error visiting homepage: {e}")
            return False
    
    async def ultra_stealth_get(self, url):
        """Ultra-stealth page retrieval with full browser simulation"""
        self.request_count += 1
        
        # Setup driver if not exists
        if not self.driver:
            if not self.setup_ultra_stealth_driver():
                raise Exception("Failed to setup ultra-stealth driver")
        
        # Ultra-conservative delay
        await self.ultra_stealth_delay()
        
        # Visit homepage first for new sessions (establish natural navigation)
        if self.request_count == 1:
            await self.visit_homepage_naturally()
            await asyncio.sleep(random.uniform(2, 5))
        
        try:
            logger.info(f"🕵️ Ultra-stealth GET: {url}")
            logger.info(f"Using profile: {self.current_user_profile['name']}")
            
            # Navigate to target URL
            self.driver.get(url)
            
            # Wait for page load
            await asyncio.sleep(random.uniform(5, 10))
            
            # Check for anti-bot challenges
            page_source = self.driver.page_source.lower()
            if 'cloudflare' in page_source or 'challenge' in page_source or 'checking your browser' in page_source:
                logger.warning("🛡️ Anti-bot challenge detected, waiting longer...")
                await asyncio.sleep(random.uniform(10, 20))
                
                # Refresh page source after waiting
                page_source = self.driver.page_source
            
            # Simulate human behavior on the target page
            await self.simulate_human_behavior()
            
            return self.driver.page_source
            
        except Exception as e:
            logger.error(f"Ultra-stealth GET failed for {url}: {e}")
            raise
    
    def extract_zone_price_from_selenium(self, url):
        """Extract zone price using Selenium with multiple strategies"""
        if not self.driver:
            return None, "No driver available"
        
        try:
            # Strategy 1: Look for items-average-price class
            try:
                price_elements = self.driver.find_elements(By.CLASS_NAME, "items-average-price")
                for elem in price_elements:
                    price_text = elem.text.strip()
                    logger.info(f"Found items-average-price element: '{price_text}'")
                    
                    # Extract price using regex
                    price_patterns = [
                        r'(\d+(?:[.,]\d+)?)\s*eur?/?m²?',
                        r'(\d+(?:[.,]\d+)?)\s*€\s*/?m²?'
                    ]
                    
                    for pattern in price_patterns:
                        price_match = re.search(pattern, price_text, re.IGNORECASE)
                        if price_match:
                            price_str = price_match.group(1).replace(',', '.')
                            try:
                                zone_price = float(price_str)
                                if 0.5 <= zone_price <= 1000:
                                    logger.info(f"✅ Selenium extracted price from items-average-price: {zone_price:.2f} €/m²")
                                    return zone_price, None
                            except:
                                continue
            except:
                pass
            
            # Strategy 2: Search by XPath for "Preço médio nesta zona"
            try:
                xpath_patterns = [
                    "//*[contains(text(), 'Preço médio nesta zona')]",
                    "//*[contains(text(), 'preço médio nesta zona')]",
                    "//*[contains(text(), 'Preço médio')]"
                ]
                
                for xpath in xpath_patterns:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for elem in elements:
                        # Check element and parent elements for price
                        elements_to_check = [elem, elem.find_element(By.XPATH, "..")]
                        
                        for check_elem in elements_to_check:
                            try:
                                price_text = check_elem.text
                                price_patterns = [
                                    r'(\d+(?:[.,]\d+)?)\s*eur?/?m²?',
                                    r'(\d+(?:[.,]\d+)?)\s*€\s*/?m²?'
                                ]
                                
                                for pattern in price_patterns:
                                    price_match = re.search(pattern, price_text, re.IGNORECASE)
                                    if price_match:
                                        price_str = price_match.group(1).replace(',', '.')
                                        try:
                                            zone_price = float(price_str)
                                            if 0.5 <= zone_price <= 1000:
                                                logger.info(f"✅ Selenium extracted price from XPath: {zone_price:.2f} €/m²")
                                                return zone_price, None
                                        except:
                                            continue
                            except:
                                continue
            except:
                pass
            
            # Strategy 3: Parse full page source as fallback
            page_source = self.driver.page_source
            return stealth_scraper.extract_zone_price(page_source, url)
            
        except Exception as e:
            return None, f"Selenium price extraction error: {str(e)}"
    
    def close_driver(self):
        """Clean up Selenium driver"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("Ultra-stealth driver closed")
            except:
                pass

# Initialize ultra-stealth scraper
ultra_stealth_scraper = UltraStealthScraper()

class StealthScraper:
    """Enhanced scraper with anti-detection capabilities"""
    
    def __init__(self):
        self.session = requests.Session()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36', 
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]
        self.referers = [
            'https://www.google.pt/',
            'https://www.google.com/',  
            'https://www.bing.com/',
            'https://duckduckgo.com/',
            'https://www.idealista.pt/',
            None  # Sometimes no referer
        ]
        self.languages = [
            'pt-PT,pt;q=0.9,en;q=0.8,fr;q=0.7',
            'pt-BR,pt;q=0.9,en;q=0.8',
            'pt-PT,pt;q=0.8,en-US;q=0.7,en;q=0.6',
            'pt,en-US;q=0.9,en;q=0.8'
        ]
        self.request_count = 0
        self.last_request_time = 0
        
    def get_natural_headers(self):
        """Generate natural, human-like headers"""
        user_agent = random.choice(self.user_agents)
        referer = random.choice(self.referers)
        language = random.choice(self.languages)
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': language,
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Site': 'none' if not referer else 'cross-site',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Cache-Control': 'max-age=0',
        }
        
        if referer:
            headers['Referer'] = referer
            
        # Sometimes add additional realistic headers
        if random.random() < 0.3:
            headers['Sec-CH-UA'] = '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"'
            headers['Sec-CH-UA-Mobile'] = '?0'
            headers['Sec-CH-UA-Platform'] = '"' + random.choice(['Windows', 'macOS', 'Linux']) + '"'
            
        return headers
    
    async def natural_delay(self, min_seconds=3, max_seconds=8):
        """Human-like delay between requests"""
        # Increase delays based on request count to avoid rate limiting
        base_delay = random.uniform(min_seconds, max_seconds)
        
        # Add progressive delays for frequent requests
        if self.request_count > 10:
            base_delay += random.uniform(2, 5)
        if self.request_count > 20:
            base_delay += random.uniform(3, 8)
        if self.request_count > 50:
            base_delay += random.uniform(5, 12)
            
        # Ensure minimum time between requests
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < 2:  # Minimum 2 seconds between any requests
            additional_delay = 2 - time_since_last
            base_delay += additional_delay
            
        logger.info(f"Natural delay: {base_delay:.1f} seconds (request #{self.request_count})")
        await asyncio.sleep(base_delay)
        self.last_request_time = time.time()
    
    async def stealthy_get(self, url, timeout=15):
        """Make a stealthy HTTP request with natural behavior"""
        self.request_count += 1
        
        # Natural delay before request
        await self.natural_delay()
        
        headers = self.get_natural_headers()
        
        # Sometimes perform multiple steps like a human would
        if random.random() < 0.2:  # 20% chance
            # First visit the domain root to establish session
            try:
                domain_url = 'https://www.idealista.pt/'
                logger.info("Performing human-like navigation: visiting homepage first")
                self.session.get(domain_url, headers=headers, timeout=timeout)
                await asyncio.sleep(random.uniform(1, 3))
            except:
                pass
                
        try:
            logger.info(f"Stealthy GET: {url}")
            logger.info(f"Using User-Agent: {headers['User-Agent'][:80]}...")
            
            response = self.session.get(url, headers=headers, timeout=timeout)
            
            # Log response details for debugging
            logger.info(f"Response: {response.status_code} - {len(response.content)} bytes")
            
            if response.status_code == 403:
                logger.warning("403 Forbidden received - implementing extended backoff")
                # Extended backoff for 403 errors
                backoff_time = random.uniform(30, 60)
                logger.info(f"Backing off for {backoff_time:.1f} seconds due to 403")
                await asyncio.sleep(backoff_time)
                
            elif response.status_code == 429:
                logger.warning("429 Too Many Requests - implementing long backoff")
                # Very long backoff for rate limiting
                backoff_time = random.uniform(60, 120)
                logger.info(f"Backing off for {backoff_time:.1f} seconds due to 429")
                await asyncio.sleep(backoff_time)
            
            return response
            
        except requests.exceptions.Timeout:
            logger.warning(f"Request timeout for {url}")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error for {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {e}")
            raise
    
    def extract_zone_price(self, html_content, url):
        """Extract zone average price from HTML content"""
        if not html_content:
            return None, "Empty HTML content"
            
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Method 1: Search for items-average-price class
            zone_price_elements = soup.find_all(class_="items-average-price")
            for elem in zone_price_elements:
                try:
                    price_text = elem.get_text().strip()
                    logger.info(f"Found items-average-price element: '{price_text}'")
                    
                    # Look for price patterns like "11,05 eur/m²"
                    price_patterns = [
                        r'(\d+(?:[.,]\d+)?)\s*eur?/?m²?',  # "11,05 eur/m²"
                        r'(\d+(?:[.,]\d+)?)\s*€\s*/?m²?',   # "11,05 €/m²"
                        r'(\d+(?:[.,]\d+)?)\s*euros?\s*/?m²?' # "11,05 euros/m²"
                    ]
                    
                    for pattern in price_patterns:
                        price_match = re.search(pattern, price_text, re.IGNORECASE)
                        if price_match:
                            price_str = price_match.group(1).replace(',', '.')
                            try:
                                zone_price = float(price_str)
                                if 0.5 <= zone_price <= 1000:
                                    logger.info(f"✅ Extracted zone price from items-average-price: {zone_price:.2f} €/m²")
                                    return zone_price, None
                            except:
                                continue
                except:
                    continue
            
            # Method 2: Search for "Preço médio nesta zona" text pattern
            page_text = soup.get_text()
            zone_patterns = [
                r'preço médio nesta zona[:\s]*(\d+(?:[.,]\d+)?)\s*eur?/?m²?',
                r'Preço médio nesta zona[:\s]*(\d+(?:[.,]\d+)?)\s*eur?/?m²?',
                r'preço médio nesta zona[:\s]*(\d+(?:[.,]\d+)?)\s*€\s*/?m²?',
                r'Preço médio nesta zona[:\s]*(\d+(?:[.,]\d+)?)\s*€\s*/?m²?'
            ]
            
            for pattern in zone_patterns:
                zone_match = re.search(pattern, page_text, re.IGNORECASE)
                if zone_match:
                    price_str = zone_match.group(1).replace(',', '.')
                    try:
                        zone_price = float(price_str)
                        if 0.5 <= zone_price <= 1000:
                            logger.info(f"✅ Extracted zone price from text pattern: {zone_price:.2f} €/m²")
                            return zone_price, None
                    except:
                        continue
            
            # Method 3: Search for any €/m² mentions as fallback
            euro_per_sqm_matches = re.findall(r'(\d+(?:[.,]\d+)?)\s*€\s*/?m²?', page_text, re.IGNORECASE)
            if euro_per_sqm_matches:
                logger.info(f"Found {len(euro_per_sqm_matches)} €/m² prices on page")
                valid_prices = []
                for price_str in euro_per_sqm_matches[:5]:  # Check first 5
                    clean_price = price_str.replace(',', '.')
                    try:
                        price = float(clean_price)
                        if 0.5 <= price <= 1000:
                            valid_prices.append(price)
                    except:
                        continue
                
                if valid_prices:
                    avg_price = sum(valid_prices) / len(valid_prices)
                    logger.info(f"✅ Calculated average from {len(valid_prices)} prices: {avg_price:.2f} €/m²")
                    return avg_price, None
            
            return None, "No 'items-average-price' element or 'Preço médio nesta zona' found on page"
            
        except Exception as e:
            return None, f"HTML parsing error: {str(e)}"

# Initialize stealth scraper
stealth_scraper = StealthScraper()

class IdealistaScraper:
    def __init__(self):
        self.driver = None
        self.session_id = None
        self.administrative_structure = {}
        
    async def get_administrative_structure(self):
        """Get complete Portuguese administrative structure from idealista reports"""
        logger.info("Fetching Portuguese administrative structure from idealista.pt")
        
        try:
            # First, try to get the structure from the reports page
            reports_url = "https://www.idealista.pt/media/relatorios-preco-habitacao/venda/report/"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'pt-PT,pt;q=0.9,en;q=0.8',
            }
            
            # Try with requests first
            response = requests.get(reports_url, headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for administrative structure in the page
                # This might be in dropdowns, links, or structured data
                districts_found = set()
                municipalities_found = {}
                parishes_found = {}
                
                # Extract from links with the pattern /venda/distrito/concelho/freguesia/
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if '/media/relatorios-preco-habitacao/venda/' in href:
                        # Parse the path: /venda/distrito/concelho/freguesia/
                        parts = href.split('/')
                        if len(parts) >= 7:  # /media/relatorios-preco-habitacao/venda/distrito/concelho/freguesia/
                            distrito = parts[5] if len(parts) > 5 else None
                            concelho = parts[6] if len(parts) > 6 else None
                            freguesia = parts[7] if len(parts) > 7 else None
                            
                            if distrito and concelho:
                                districts_found.add(distrito)
                                if distrito not in municipalities_found:
                                    municipalities_found[distrito] = set()
                                municipalities_found[distrito].add(concelho)
                                
                                if freguesia:
                                    key = f"{distrito}-{concelho}"
                                    if key not in parishes_found:
                                        parishes_found[key] = set()
                                    parishes_found[key].add(freguesia)
                
                # Convert to the structure we need
                structure = {}
                for distrito in districts_found:
                    structure[distrito] = {}
                    if distrito in municipalities_found:
                        for concelho in municipalities_found[distrito]:
                            key = f"{distrito}-{concelho}"
                            if key in parishes_found:
                                structure[distrito][concelho] = list(parishes_found[key])
                            else:
                                structure[distrito][concelho] = [concelho]  # Use concelho as freguesia if no freguesias found
                
                if structure:
                    logger.info(f"Found {len(structure)} districts from idealista reports")
                    self.administrative_structure = structure
                    return structure
            
            logger.warning("Could not fetch administrative structure from idealista, using fallback")
            
        except Exception as e:
            logger.error(f"Error fetching administrative structure: {e}")
        
        # Fallback: Use comprehensive Portuguese administrative structure
        fallback_structure = {
            'aveiro': {
                'aveiro': ['aveiro', 'cacia', 'eixo-e-eirol', 'esgueira', 'glória-e-vera-cruz', 'oliveirinha', 'requeixo-nossa-senhora-de-fátima-e-nariz', 'santa-joana', 'são-bernardo', 'são-jacinto'],
                'ovar': ['ovar-são-cristóvão-santa-eulália-e-são-joão', 'esmoriz', 'cortegaça', 'ovar-são-vicente'],
                'ilhavo': ['ilhavo-cidade', 'gafanha-da-nazaré', 'gafanha-do-carmo'],
                'agueda': ['águeda-e-borralha', 'barrô-e-aguada-de-baixo', 'castanheira-do-vouga', 'espinhel', 'fermentelos', 'lamas-do-vouga', 'macieira-de-alcoba', 'mortágua', 'óis-da-ribeira-e-travanca', 'préstimo-e-macieira-de-alcoba', 'recardães-e-espinhel', 'travassô-e-óis-da-ribeira', 'trofa-segadães-e-lamas-do-vouga', 'valongo-do-vouga'],
                'estarreja': ['avanca', 'beduído-e-veiros', 'canelas-e-espinhel', 'estarreja', 'fermelã', 'pardilhó', 'salreu']
            },
            'beja': {
                'beja': ['beja-salvador-e-santa-maria-da-feira', 'albernoa', 'baleizão', 'beringel', 'cabeça-gorda', 'nossa-senhora-das-neves', 'quintos', 'salvada', 'santa-clara-de-louredo', 'santa-vitória', 'são-brissos', 'são-matias', 'trigaches'],
                'serpa': ['brinches', 'pias', 'serpa', 'vale-de-vargo'],
                'moura': ['amareleja', 'barrancos', 'moura-santo-agostinho', 'moura-santo-antónio-dos-açougues-e-são-joão-baptista', 'póvoa-de-são-miguel', 'safara', 'santo-aleixo-da-restauração', 'sobral-da-adiça'],
                'odemira': ['almograve', 'boavista-dos-pinheiros', 'colos', 'longueira-almograve', 'luzianes-gare', 'odemira', 'pereiras-gare', 'relíquias', 'sabóia', 'santa-clara-a-velha', 'são-luís', 'são-martinho-das-amoreiras', 'são-salvador-e-santa-maria', 'vale-de-santiago', 'vila-nova-de-milfontes', 'zambujeira-do-mar']
            },
            'braga': {
                'braga': ['adaúfe', 'arentim-e-cunha', 'braga-maximinos-sé-e-cividade', 'braga-são-josé-de-são-lázaro-e-são-joão-do-souto', 'braga-são-paio-merelim-panóias-e-parada-de-tibães', 'braga-são-vicente', 'cabreiros', 'celeirós-aveleda-e-vimieiro', 'dume', 'escudeiros-e-vilar-de-cunhas', 'espinho', 'esporões', 'ferreiros-e-gondizalves', 'figueiredo', 'fraião-e-lamaçães', 'gualtar', 'lamaçães', 'lamas', 'lomar-e-arcos', 'merelim-pedro', 'merelim-são-paio', 'mire-de-tibães', 'morreira-e-trandeiras', 'nogueira-fraião-e-lamaçães', 'nogueiró-e-tenões', 'padim-da-graça', 'palmeira', 'panóias', 'parada-de-tibães', 'pousada', 'real-dume-e-semelhe', 'ruilhe', 'são-paio-merelim', 'semelhe', 'sequeira', 'sobreposta', 'tebosa', 'tenões', 'trandeiras', 'vilaça-e-figueiredo', 'vimieiro'],
                'guimaraes': ['abação-gémeos', 'airão-santa-maria', 'airão-são-joão-e-vermil', 'aldão', 'azurém', 'brito', 'caldelas', 'candoso-santiago', 'candoso-são-martinho-e-candoso-são-tiago', 'conde-s-vicente-da-chã', 'corvite', 'costa', 'creixomil', 'fermentões', 'gandra', 'gandarela', 'garfe', 'gonça', 'gondar', 'guardizela', 'guimarães-oliveira-são-paio-e-são-sebastião', 'infantas', 'lei-lousada-e-vilar-de-ferreiros', 'leitões', 'lordelo', 'mesão-frio', 'moreira-de-cónegos', 'nespereira-e-casais', 'oliveira-são-pedro-e-são-paio', 'pevidém', 'polvoreira', 'ponte', 'ronfe', 'são-torcato', 'selho-são-cristóvão', 'selho-são-jorge', 'serzedo-e-perosinho', 'silvares', 'souto-santa-maria-souto-são-salvador-e-souto-são-pedro', 'tabuadelo-e-são-faustino', 'urgezes', 'vermil'],
                'barcelos': ['abade-de-neiva', 'alheira-e-igreja-nova', 'alvito-são-pedro-e-alvito-são-martinho', 'arcozelo', 'areias-de-vilar-e-encourados', 'ázere', 'barcelinhos', 'barcelos-vila-boa-e-vila-frescainha-são-martinho-e-são-pedro', 'barqueiros', 'cambeses', 'carapeços', 'carvalhal', 'chavão', 'chorente-góios-courel-pedra-furada-e-gueral', 'cossourado-e-lage', 'cristelo', 'durrães-e-tregosa', 'esmeriz-e-cabeçudos', 'faria', 'fragoso', 'galegos-santa-maria', 'galegos-são-martinho', 'gilmonde', 'lijó', 'manhente', 'martim', 'milhazes', 'minhotães', 'moure', 'negreiros-e-chavão', 'oliveira', 'palme', 'panque', 'pereira', 'pousa', 'quintiães', 'roriz', 'são-martinho-de-bougado', 'são-pedro-de-bougado', 'silva', 'tamel-santa-leocádia', 'tamel-são-pedro-fins', 'ucha', 'vale', 'várzea', 'viatodos-grimancelos-minhotães-e-monte-de-fralães', 'vila-boa', 'vila-cova-a-coelheira', 'vila-frescainha-são-martinho', 'vila-frescainha-são-pedro', 'vilar-de-figos'],
                'famalicao': ['antas-e-abade-de-vermoim', 'arnoso-santa-eulália-arnoso-santa-maria-seide-são-miguel-e-seide-são-paio', 'avidos-e-lagoa', 'bairro-calendário-cruz-e-oliveira-santa-maria', 'bente', 'brufe', 'carreira', 'cavalões', 'delães', 'esmeriz-e-cabeçudos', 'fradelos', 'gavião', 'gondifelos-cavalões-e-outiz', 'joane', 'landim', 'lemenhe-mouquim-e-jesufrei', 'mogege', 'nin-e-vale-de-são-cosme', 'novais', 'oliveira-santa-maria-oliveira-são-mateus-e-silveiros', 'outiz', 'pedome', 'portela', 'requião', 'ribeirão', 'riba-de-ave', 'ruivães-novais', 'santo-tirso-couto-santa-cristina-e-santo-tirso-burgães', 'seide-são-miguel', 'seide-são-paio', 'sequeirô-e-jesufrei', 'subportela-deocriste-e-portela-susã', 'vale-são-cosme-telhado-e-portela', 'vale-são-martinho', 'vermoim', 'vilarinho-das-cambas'],
                'esposende': ['antas', 'apúlia-e-fão', 'barcelinhos', 'belinho-e-mar', 'curvos', 'esposende-marinhas-e-gandra', 'forjães', 'gemeses', 'palmeira-de-faro-e-curvos', 'rio-tinto']
            },
            'braganca': {
                'braganca': ['alfaião', 'aveleda', 'babe', 'baçal', 'bragança-se-santa-maria-e-meixedo', 'castrelos', 'coelhoso', 'donai', 'espinhosela', 'estevais', 'frança', 'gimonde', 'gondesende', 'gostei', 'grijó-de-parada', 'izeda-calvelhe-e-paradinha-nova', 'macedo-do-mato', 'meixedo', 'milhão', 'mofreita', 'montesinho', 'nogueira', 'outeiro', 'parada', 'paradinha-nova', 'parâmio', 'pinela', 'quintanilha', 'rabal', 'rebordaínhos', 'rebordelos', 'rio-de-onor', 'rio-frio', 'samil', 'santa-comba-de-rossas', 'santa-cruz', 'são-julião-de-palácios-e-deilão', 'são-pedro-de-serracenos', 'sendas', 'serapicos', 'sortes', 'zoio'],
                'mirandela': ['ala', 'alvites', 'avantos-e-cachão', 'avidagos', 'barcel', 'bouça-cabeça-boa-e-pinheiro-novo', 'cabanelas', 'cachão', 'carvalhais', 'cedães', 'cobro', 'contim', 'couço', 'cunhas', 'fradizela', 'frechas', 'freixeda', 'lamas-de-orelhão', 'mascarenhas', 'mirandela', 'múrias', 'navalho', 'pereira', 'póvoa', 'romeu', 'são-pedro-velho', 'suçães', 'torre-de-dona-chama', 'val-de-asneas', 'vale-de-gouvinhas', 'vale-de-salgueiro', 'vale-de-telhas', 'valverde-da-gestosa', 'vilar-de-nantes'],
                'macedo-de-cavaleiros': ['ala', 'amendoeira', 'arcas', 'bagueixe', 'bornes', 'burga', 'carrapatas', 'chacim', 'cortiços', 'edrosa', 'espadanedo-edrosa-murçós-e-soutelo-mourisco', 'ferreira', 'grijó-de-parada', 'lamalonga', 'lamas', 'lavradas', 'ligares', 'lombo', 'macedo-de-cavaleiros', 'morais', 'murçós', 'olmos', 'peredo', 'podence', 'quinta-da-lomba', 'salsas', 'sesulfe', 'soutelo-mourisco', 'talhinhas', 'taliscas', 'travanca', 'vale-benfeito', 'vale-da-porca', 'vale-de-prados', 'vilar-do-monte', 'vilarinho-de-agrochão', 'vinhas']
            },
            'castelo-branco': {
                'castelo-branco': ['alcains', 'almaceda', 'benquerenças', 'castelo-branco', 'cebolais-de-cima-e-retaxo', 'escalos-de-baixo-e-mata', 'escalos-de-cima-e-lousa', 'idanha-a-velha', 'juncal-do-campo', 'lardosa', 'louriçal-do-campo', 'malpica-do-tejo', 'mata', 'monforte-da-beira', 'ninho-do-açor-e-sobral-do-campo', 'póvoa-de-rio-de-moinhos-e-cafede', 'salgueiro-do-campo', 'santo-andré-das-tojeiras', 'são-vicente-da-beira', 'sarzedas', 'sobral-do-campo', 'tinalhas'],
                'covilha': ['aldeia-do-carvalho', 'aldeia-de-são-francisco-de-assis', 'barco-e-coutada', 'boidobra', 'cantar-galo-e-vila-do-carvalho', 'canhoso', 'casais-do-douro', 'castelo-novo', 'covilhã-e-canhoso', 'dominguiso', 'erada', 'ferro', 'orjais', 'ourondo', 'paul', 'peraboa', 'peso-e-vales-do-rio', 'sobral-de-são-miguel', 'tortosendo', 'unhais-da-serra', 'vale-formoso-e-aldeia-do-souto', 'verdelhos'],
                'fundao': ['alcaide', 'alcaria', 'alcongosta', 'aldeia-de-joanes', 'aldeia-nova-do-cabo', 'alpedrinha', 'atalaia-do-campo', 'barroca', 'bogas-de-baixo', 'bogas-de-cima', 'capinha', 'casa-da-ribeira', 'castelo-novo', 'enxames', 'escarigo', 'fatela', 'fundão', 'janeiro-de-cima-e-bogas-de-baixo', 'lavacolhos', 'mata-da-rainha', 'pêro-viseu', 'póvoa-de-atalaia-e-atalaia-do-campo', 'salgueiro', 'silvares', 'soalheira', 'soito', 'telhado', 'três-povos', 'vale-de-prazeres-e-mata-da-rainha', 'valverde'],
                'belmonte': ['belmonte-e-colmeal-da-torre', 'caria', 'colmeal-da-torre', 'maçainhas']
            },
            'coimbra': {
                'coimbra': ['almalaguês', 'ameal', 'antanhol', 'antuzede-e-vil-de-matos', 'arzila', 'assafarge', 'botão', 'brasfemes', 'ceira', 'coimbra-almedina', 'coimbra-se', 'coimbra-santo-antónio-dos-olivais', 'coimbra-são-bartolomeu', 'coimbra-são-paulo-de-frades', 'coimbra-sé-nova', 'eiras-e-são-paulo-de-frades', 'lamarosa', 'ribeira-de-frades', 'santa-clara-e-castelo-viegas', 'santo-antónio-dos-olivais', 'são-joão-do-campo', 'são-martinho-do-bispo-e-ribeira-de-frades', 'são-silvestre', 'souselas-e-botão', 'taveiro-ameal-e-arzila', 'torres-do-mondego-e-mosteirô', 'trouxemil-e-torre-de-vilela', 'vil-de-matos'],
                'figueira-da-foz': ['alqueidão', 'bom-sucesso', 'buarcos-e-são-julião', 'ferreira-a-nova', 'figueira-da-foz', 'lavos', 'maiorca', 'marinha-das-ondas', 'paião', 'quiaios', 'santa-clara', 'são-pedro', 'tavarede', 'vila-verde'],
                'cantanhede': ['ançã', 'bolho', 'cadima', 'cantanhede-e-pocariça', 'cordinhã', 'covões-e-camarneira', 'febres', 'murtede', 'ourentã', 'outil', 'pocariça', 'queimada', 'rans', 'sepins-e-bolho', 'tocha', 'vilamar']
            },
            'evora': {
                'evora': ['bacelo-e-senhora-da-saúde', 'canaviais', 'évora-malagueira-e-horta-das-figueiras', 'évora-se-e-são-pedro', 'graça-do-divor', 'horta-das-figueiras', 'malagueira', 'nossa-senhora-da-graça-do-divor', 'nossa-senhora-de-machede', 'são-bento-do-mato', 'são-manços-e-são-vicente-do-pigeiro', 'são-miguel-de-machede', 'são-sebastião-da-giesteira-e-nossa-senhora-da-boa-fé', 'torre-de-coelheiros'],
                'estremoz': ['arcos', 'estremoz-santa-maria-e-santo-andré', 'évora-monte', 'glória', 'santa-vitória-do-ameixial', 'são-bento-de-ana-loura', 'são-domingos-de-ana-loura', 'são-lourenço-de-mamporcão', 'veiros'],
                'montemor-o-novo': ['cabrela', 'cortiçadas-de-lavre-e-lavre', 'foros-de-vale-figueira', 'montemor-o-novo-e-silveiras', 'nossa-senhora-da-vila-nossa-senhora-do-bispo-e-silveiras', 'são-cristóvão', 'vendas-novas'],
                'vendas-novas': ['landeira', 'marcação', 'vendas-novas']
            },
            'faro': {
                'faro': ['faro-se-e-estoi', 'montenegro', 'santa-barbara-de-nexe'],
                'olhao': ['olhao', 'pechao', 'quelfes'],
                'tavira': ['conceicao-e-cabanas-de-tavira', 'luz-de-tavira-e-santo-estevao', 'santa-catarina-da-fonte-do-bispo', 'santa-luzia', 'santiago-tavira', 'tavira-santa-maria-e-santiago'],
                'albufeira': ['albufeira-e-olhos-de-agua', 'ferreiras', 'guia', 'paderne'],
                'portimao': ['portimao', 'alvor'],
                'lagoa': ['carvoeiro', 'estombar-e-parchal', 'ferragudo', 'lagoa-e-carvoeiro'],
                'silves': ['alcantarilha-e-pera', 'algoz-e-tunes', 'armacao-de-pera', 'silves'],
                'lagos': ['bensafrim-e-barrao-de-sao-joao', 'luz', 'odiaxere', 'santa-maria', 'sao-goncalo-de-lagos'],
                'vila-do-bispo': ['budens', 'raposeira', 'sagres', 'vila-do-bispo-e-raposeira'],
                'aljezur': ['aljezur', 'bordeira', 'carrapateira', 'odeceixe'],
                'monchique': ['alferce', 'marmelete', 'monchique'],
                'castro-marim': ['azinhal', 'castro-marim', 'altura', 'monte-gordo'],
                'vila-real-de-santo-antonio': ['monte-gordo', 'vila-nova-de-cacela', 'vila-real-de-santo-antonio']
            },
            'guarda': {
                'guarda': ['adão', 'albardo', 'aldeia-do-bispo-águas-e-aldeia-de-joão-pires', 'aldeia-viçosa', 'alvendre-e-concavada', 'avelãs-de-ambom-e-rocamondo', 'benespera', 'casal-de-cinza', 'castanheira', 'cavadoude', 'corujeira-e-trinta', 'famalicão-da-nazaré', 'faia', 'gonçalo', 'gonçalo-bocas-e-aguilar', 'guarda', 'jarmelo-são-miguel', 'jarmelo-são-pedro', 'João-antão', 'maçainhas', 'meios', 'mizarela', 'nogueira-do-cravo-e-pinheiro', 'os-cepos', 'panoias-de-cima', 'pega', 'pêra-do-moço', 'pinhel', 'pocinho', 'porto-da-carne', 'ramela', 'rocamondo', 'são-miguel-da-guarda', 'sé', 'valhelhas', 'vela', 'videmonte'],
                'seia': ['alvoco-da-serra', 'cabeça', 'carragozela', 'folhadosa', 'girabolhos', 'loriga', 'manigoto', 'paranhos-da-beira', 'pinhanços', 'sabugueiro', 'santa-comba', 'santa-eulália', 'santiago', 'são-romão', 'seia-são-romão-e-lapa-dos-dinheiros', 'tourais-e-lapa-dos-dinheiros', 'travancinha', 'valdim', 'vide-entre-vinhas'],
                'gouveia': ['aldeias-e-mangualde-da-serra', 'arcozelo-das-maias', 'cativelos-e-faia-da-água-alta', 'folgosinho', 'gouveia', 'mangualde-da-serra', 'melo-e-nabais', 'nespereira-e-casal-do-rei', 'paços-da-serra', 'ribamondego', 'rio-torto-e-arganil', 'unhais-o-velho', 'vila-cortês-da-serra', 'vila-franca-da-serra-e-moimenta-da-serra'],
                'pinhel': ['alverca-da-beira-bouça-cova-e-freixo', 'atalaia', 'azevo', 'bouça-cova', 'cidadelhe', 'ervas-tenras-e-louçainha', 'freixedas', 'lamegal', 'leomil', 'pinhel', 'póvoa-de-el-rei', 'sorval', 'valbom']
            },
            'leiria': {
                'leiria': ['amor', 'arrabal', 'azoia', 'barosa', 'bidoeira-de-cima', 'boa-vista', 'caranguejeira', 'carreira', 'chain', 'colmeias-e-memória', 'cortes', 'coimbrão', 'leiria-pousos-barreira-e-cortes', 'maceira', 'marrazes-e-barosa', 'milagres', 'monte-redondo-e-carreira', 'parceiros-e-azoia', 'pousos', 'regueira-de-pontes', 'santa-catarina-da-serra-e-chainça', 'santa-eufémia-e-boa-vista', 'souto-da-carpalhosa-e-ortigosa'],
                'marinha-grande': ['marinha-grande'],
                'batalha': ['batalha', 'são-mamede'],
                'pombal': ['abiul', 'albergaria-dos-doze', 'carnide', 'carriço', 'guia-ilha-e-mata-mourisca', 'louriçal', 'pombal', 'redinha', 'santiago-de-litém-e-vermoil', 'vale-de-lobos'],
                'alcobaca': ['alcobaça-e-vestiaria', 'alfeizerão', 'bárrio', 'benedita', 'cela', 'cós', 'évora-de-alcobaça', 'maiorga', 'martinha', 'montes', 'pataias-e-martingança', 'salir-de-matos', 'são-martinho-do-porto', 'turquel', 'vimeiro']
            },
            'lisboa': {
                'lisboa': ['ajuda', 'alcantara', 'alvalade', 'areeiro', 'arroios', 'avenidas-novas', 'beato', 'belem', 'benfica', 'campo-de-ourique', 'campolide', 'carnide', 'estrela', 'lumiar', 'mafra', 'marvila', 'misericordia', 'olivais', 'penha-de-franca', 'santa-clara', 'santa-maria-maior', 'santo-antonio', 'sao-domingos-de-benfica', 'sao-vicente'],
                'cascais': ['alcabideche', 'carcavelos-e-parede', 'cascais-e-estoril', 'sao-domingos-de-rana'],
                'sintra': ['agualva-e-mira-sintra', 'algueirão-mem-martins', 'almargem-do-bispo-pêro-pinheiro-e-montelavar', 'belas', 'cacém-e-são-marcos', 'casal-de-cambra', 'colares', 'massamá-e-monte-abraão', 'queluz-e-belas', 'rio-de-mouro', 'santa-maria-e-são-miguel', 'santana-e-são-pedro', 'sintra-santa-maria-e-são-miguel', 'são-joão-das-lampas-e-terrugem'],
                'oeiras': ['algés-linda-a-velha-e-cruz-quebrada-dafundo', 'barcarena', 'carnaxide-e-queijas', 'oeiras-e-são-julião-da-barra-paço-de-arcos-e-caxias', 'porto-salvo'],
                'amadora': ['águeda-de-cima', 'alfragide', 'amadora', 'brandoa', 'buraca', 'damaia', 'falagueira-venda-nova', 'mina-de-água', 'pontinha', 'reboleira', 'são-brás', 'venteira'],
                'loures': ['bucelas', 'camarate-unhos-e-apelação', 'fanhões', 'frielas', 'loures', 'lousa', 'moscavide-e-portela', 'sacavém-e-prior-velho', 'santa-iria-de-azóia-são-joão-da-talha-e-bobadela', 'santo-andré-e-verderena', 'santo-antão-e-são-julião-do-tojal', 'são-joão-da-talha', 'união-das-freguesias-de-moscavide-e-portela']
            },
            'portalegre': {
                'portalegre': ['alegrete', 'avis', 'carreiras', 'fortios', 'portalegre-se-e-são-lourenço', 'ribeira-de-nisa-e-carreiras', 'são-julião-e-são-brás', 'urra'],
                'elvas': ['ajuda-salvador-e-santo-ildefonso', 'assunção-ajuda-salvador-e-santo-ildefonso', 'barbacena-e-vila-fernando', 'caia-são-pedro-e-alcáçova', 'santa-eulália', 'são-brás-e-são-lourenço', 'são-vicente-e-ventosa', 'terrugem-e-vila-boim'],
                'campo-maior': ['campo-maior', 'degolados', 'nossa-senhora-da-expectação', 'são-joão-batista', 'santo-antónio-das-areias'],
                'nisa': ['alpalhão', 'amieira-do-tejo', 'arez-e-amieira-do-tejo', 'espírito-santo', 'montalvão', 'nisa', 'santana', 'são-matias', 'tolosa']
            },
            'porto': {
                'porto': ['aldoar-foz-do-douro-e-nevogilde', 'bonfim', 'campanhã', 'cedofeita-santo-ildefonso-sé-miragaia-são-nicolau-e-vitória', 'lordelo-do-ouro-e-massarelos', 'paranhos', 'ramalde'],
                'vila-nova-de-gaia': ['arcozelo', 'avintes', 'canelas', 'canidelo', 'crestuma', 'grijó-e-sermonde', 'gulpilhares-e-valadares', 'lever', 'madalena', 'mafamude-e-vilar-do-paraíso', 'oliveira-do-douro', 'pedroso-e-seixezelo', 'perosinho', 'sandim-olival-lever-e-crestuma', 'santa-marinha-e-são-pedro-da-afurada', 'são-félix-da-marinha', 'valadares', 'vilar-de-andorinho'],
                'matosinhos': ['custóias-leça-do-balio-e-guifões', 'matosinhos-e-leça-da-palmeira', 'perafita-lavra-e-santa-cruz-do-bispo', 'são-mamede-de-infesta-e-senhora-da-hora'],
                'gondomar': ['baguim-do-monte', 'covelo', 'fânzeres', 'gondomar-são-cosme-valbom-e-jovim', 'lomba', 'melres-e-medas', 'rio-tinto', 'são-pedro-da-cova', 'valbom'],
                'maia': ['águas-santas', 'castêlo-da-maia', 'cidade-da-maia', 'folgosa', 'gemunde', 'gueifães', 'milheirós', 'moreira', 'nogueira-e-silva-escura', 'pedrouços', 'são-pedro-fins', 'vila-nova-da-telha']
            },
            'santarem': {
                'santarem': ['abitureiras', 'achete-azoia-de-baixo-e-póvoa-de-santarém', 'alcanede', 'almoster', 'arneiro-das-milhariças', 'azoia-de-baixo', 'pernes', 'pombalinho', 'póvoa-da-isenta', 'romeira-e-várzea', 'santarém-marvila-santa-iria-da-ribeira-de-santarém-santarém-salvador-e-santarém-são-nicolau', 'são-vicente-do-paul-e-vale-de-figueira', 'tremês', 'vale-de-santarém', 'várzea'],
                'torres-novas': ['asseiceira', 'brogueira-parceiros-de-igreja-e-alcaidaria', 'chancelaria', 'lapas-e-ribeira-branca', 'olaia', 'paço', 'pedrógão', 'riachos', 'são-pedro-da-cadeira', 'torres-novas-santa-maria-torres-novas-são-miguel-e-lapas', 'zibreira'],
                'entroncamento': ['entroncamento'],
                'tomar': ['alviobeira', 'asseiceira-rio-de-couros-e-casal-dos-bernardos', 'beselga', 'carregueiros', 'casais-e-alviobeira', 'madalena-e-beselga', 'olalhas', 'paialvo', 'pedreira', 'sabacheira', 'santa-cita', 'são-joão-batista', 'serra-e-junceira', 'tomar-santa-maria-dos-olivais']
            },
            'setubal': {
                'setubal': ['gâmbia-pontes-alto-da-guerra', 'sado', 'setúbal-são-julião-nossa-senhora-da-anunciada-e-santa-maria-da-graça', 'setúbal-são-sebastião-são-simão'],
                'barreiro': ['alto-do-seixalinho-santo-andré-e-verderena', 'barreiro', 'coina', 'lavradio', 'santo-andré', 'santo-antónio-da-charneca', 'verderena'],
                'almada': ['almada-cova-da-piedade-pragal-e-cacilhas', 'caparica-e-trafaria', 'charneca-de-caparica-e-sobreda', 'costa-de-caparica', 'laranjeiro-e-feijó'],
                'seixal': ['aldeia-de-paio-pires', 'amora', 'arrentela', 'corroios', 'fernão-ferro', 'seixal-arrentela-e-aldeia-de-paio-pires'],
                'moita': ['alhos-vedros', 'baixa-da-banheira-e-vale-da-amoreira', 'gaio-rosário-e-sarilhos-pequenos', 'moita']
            },
            'viana-do-castelo': {
                'viana-do-castelo': ['afife', 'alvarães', 'amonde', 'anha', 'areosa', 'barroselas-e-carvoeiro', 'cardielos-e-serreleis', 'carreço', 'castelo-do-neiva', 'chafé', 'darque', 'deão', 'freixieiro-de-soutelo', 'geraz-do-lima-santa-maria', 'geraz-do-lima-são-lourenço', 'lanheses', 'mazarefes-e-vila-fria', 'meadela', 'monserrate', 'montaria', 'neiva', 'nogueira-meixedo-e-vilar-de-murteda', 'outeiro', 'perre', 'portuzelo', 'subportela-deocriste-e-portela-susã', 'torre-e-vila-mou', 'viana-do-castelo-monserrate-e-meadela', 'vila-de-punhe', 'vila-franca', 'vila-mou'],
                'ponte-de-lima': ['anta-e-gueral', 'arcozelo', 'ardegão-freixo-e-mato', 'beiral-do-lima', 'bertiandos', 'boivães', 'cabração-e-moreira-do-lima', 'calvelo', 'correlhã', 'estorãos', 'facha', 'fontão', 'fornelos-e-queijada', 'freixo', 'gandra-e-tamel-são-veríssimo', 'gemieira', 'gondufe', 'labruja', 'labrujó-rendufe-e-vilar-do-monte', 'lindoso', 'mato-e-queijada', 'moreira-do-lima-e-serreleis', 'navió', 'negreiros', 'ponte-de-lima', 'poiares-santo-andré', 'queijada', 'rebordões-souto-e-ribeira', 'refojos-do-lima', 'rendufe', 'ribeira', 'são-martinho-da-gândara', 'serdedelo', 'souto', 'vitorino-das-donas-e-vitorino-de-piães'],
                'valenca': ['boivão', 'cristelo-covo-e-mosteiró', 'fontoura', 'gandra', 'ganfei', 'silva', 'são-julião-e-silva', 'são-pedro-da-torre', 'valença-cerdal-e-arão', 'verdoejo']
            },
            'vila-real': {
                'vila-real': ['abaças', 'adoufe-e-vilarinho-de-samardã', 'argeriz', 'borbela-e-lamas-de-olo', 'campeã', 'constantim-e-vale-de-nogueiras', 'folhadela', 'gondar', 'guiães-e-cogula', 'lordelo', 'mateus', 'mouçós-e-lamares', 'NumÃo', 'parada-de-cunhos', 'pena', 'ribeira-de-pena', 'santa-marta-de-penaguião', 'santa-cruz-do-douro-e-são-tomé-de-covelas', 'são-dinis', 'são-pedro-das-águias', 'torgueda', 'vieira-do-minho', 'vila-marim', 'vila-real'],
                'chaves': ['águas-frias-e-arcossó', 'aldeia-de-nacomba', 'anelhe', 'calvão-e-soutelinho-da-raia', 'casas-novas', 'chaves-santa-cruz-trindade-e-sanjurge', 'chaves-santa-maria-maior', 'ervededo', 'faiões-e-vila-verde-da-raia', 'lama-de-arcos', 'loivos', 'mairos', 'moreiras', 'oucidres-e-paiágua', 'outeiro-seco', 'paradela', 'pastoria-e-sobrado', 'póvoa-de-agrações', 'roriz', 'sapiãos', 'seara-velha', 'soutelo', 'soutelinho-da-raia', 'tronco', 'vale-de-anta-e-sendim-da-ribeira', 'vidago-arcossó-telões-e-lama-de-arcos', 'vilar-de-nantes', 'vilela-do-tâmega', 'vincent']
            },
            'viseu': {
                'viseu': ['abraveses', 'bodiosa', 'boa-aldeia-farminhão-e-toutosa', 'cavernães', 'côta', 'fragosela', 'lordosa', 'mouronho', 'mundão', 'orgens', 'povolide', 'quarteirão', 'repeses-e-são-salvador', 'rio-de-loba', 'santos-evos', 'silgueiros', 'vale-de-besteiros', 'ventosa', 'viseu']
            },
            # Açores
            'corvo': {
                'corvo': ['corvo']
            },
            'faial': {
                'horta': ['angústias', 'conceição', 'flamengos', 'horta', 'matriz', 'pedro-miguel', 'praia-do-almoxarife', 'praia-do-norte', 'ribeirinha', 'salão'],
                'castelo-branco': ['castelo-branco', 'cedros', 'ribeira-do-cabo']
            },
            'flores': {
                'flores': ['fazenda', 'fajã-grande', 'fajãzinha', 'lajes-das-flores', 'lomba', 'ponta-delgada', 'santa-cruz']
            },
            'graciosa': {
                'graciosa': ['guadalupe', 'luz', 'praia', 'santa-cruz-da-graciosa']
            },
            'pico': {
                'lajes-do-pico': ['lajes-do-pico', 'piedade', 'ribeiras', 'santo-amaro'],
                'madalena': ['bandeiras', 'criação-velha', 'madalena', 'são-caetano'],
                'são-roque-do-pico': ['candelária', 'prainha', 'santa-luzia', 'santo-antónio', 'são-roque']
            },
            'santa-maria': {
                'vila-do-porto': ['almagreira', 'santo-espírito', 'são-pedro', 'vila-do-porto']
            },
            'são-jorge': {
                'calheta': ['calheta', 'ribeira-seca', 'santo-antão'],
                'velas': ['manadas', 'norte-grande', 'rosais', 'são-jorge', 'urzelina', 'velas']
            },
            'são-miguel': {
                'ponta-delgada': ['ajuda-da-bretanha', 'arrifes', 'candelária', 'capelas', 'fajã-de-baixo', 'fajã-de-cima', 'fenais-da-luz', 'ginetes', 'livramento', 'mosteiros', 'pilar-da-bretanha', 'ponta-delgada', 'relva', 'remédios', 'são-josé', 'são-pedro', 'são-roque', 'são-sebastião', 'são-vicente-ferreira', 'sete-cidades'],
                'ribeira-grande': ['calhetas', 'fenais-da-ajuda', 'lomba-da-maia', 'lomba-de-são-pedro', 'maia', 'matriz', 'pedro-teixeira', 'pico-da-pedra', 'porto-formoso', 'rabo-de-peixe', 'ribeira-grande', 'ribeira-seca', 'santa-bárbara', 'são-brás'],
                'lagoa': ['água-de-pau', 'atalhada', 'cabouco', 'lagoa', 'nossa-senhora-do-rosário', 'ribeira-chã', 'santa-cruz']
            },
            'terceira': {
                'angra-do-heroísmo': ['altares', 'angra-do-heroísmo', 'cinco-ribeiras', 'doze-ribeiras', 'feteira', 'posto-santo', 'quatro-ribeiras', 'raminho', 'ribeirinha', 'santa-bárbara', 'santa-luzia', 'são-bartolomeu-dos-regatos', 'são-bento', 'são-mateus-da-calheta', 'serreta', 'terra-chã'],
                'praia-da-vitória': ['agualva', 'biscoitos', 'cabo-da-praia', 'fonte-do-bastardo', 'fontinhas', 'lajes', 'porto-martins', 'praia-da-vitória', 'quatro-ribeiras', 'são-brás', 'vila-nova']
            },
            # Madeira
            'madeira': {
                'funchal': ['imaculado-coração-de-maria', 'monte', 'são-gonçalo', 'são-martinho', 'são-pedro', 'santo-antónio', 'sé'],
                'câmara-de-lobos': ['câmara-de-lobos', 'curral-das-freiras', 'estreito-de-câmara-de-lobos', 'jardim-da-serra', 'quinta-grande'],
                'santa-cruz': ['água-de-pena', 'camacha', 'caniço', 'gaula', 'santa-cruz', 'santo-da-serra']
            },
            'porto-santo': {
                'porto-santo': ['porto-santo']
            }
        }
        
        logger.info(f"Using fallback administrative structure with {len(fallback_structure)} districts")
        self.administrative_structure = fallback_structure
        return fallback_structure
        
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
    
    async def scrape_freguesia(self, distrito, concelho, freguesia, operation_type='sale', session_id=None):
        """Scrape average price per m² from idealista.pt freguesia property listings using stealth methods"""
        properties = []
        error_details = []
        
        # Construct URLs for idealista.pt property search pages
        concelho_clean = concelho.lower().replace(' ', '-').replace('_', '-')
        freguesia_clean = freguesia.lower().replace(' ', '-').replace('_', '-')
        
        if operation_type == 'sale':
            # URLs for different property types in sale
            urls_to_scrape = [
                {
                    'url': f"https://www.idealista.pt/comprar-casas/{concelho_clean}/{freguesia_clean}/com-apartamentos/",
                    'property_type': 'apartment'
                },
                {
                    'url': f"https://www.idealista.pt/comprar-casas/{concelho_clean}/{freguesia_clean}/com-moradias/",
                    'property_type': 'house'
                },
                {
                    'url': f"https://www.idealista.pt/comprar-terrenos/{concelho_clean}/{freguesia_clean}/com-terreno-urbano/",
                    'property_type': 'urban_plot'
                },
                {
                    'url': f"https://www.idealista.pt/comprar-terrenos/{concelho_clean}/{freguesia_clean}/com-terreno-nao-urbanizavel/",
                    'property_type': 'rural_plot'
                }
            ]
        else:
            # URLs for rentals (no rural plots in rental)
            urls_to_scrape = [
                {
                    'url': f"https://www.idealista.pt/arrendar-casas/{concelho_clean}/{freguesia_clean}/com-apartamentos,arrendamento-longa-duracao/",
                    'property_type': 'apartment'
                },
                {
                    'url': f"https://www.idealista.pt/arrendar-casas/{concelho_clean}/{freguesia_clean}/com-moradias,arrendamento-longa-duracao/",
                    'property_type': 'house'
                }
            ]
        
        logger.info(f"Starting STEALTH scraping of {len(urls_to_scrape)} property types for: {distrito}/{concelho}/{freguesia} ({operation_type})")
        
        all_properties = []
        
        for url_info in urls_to_scrape:
            url = url_info['url']
            property_type = url_info['property_type']
            
            logger.info(f"🕵️ Stealth scraping {property_type} from: {url}")
            
            try:
                # Use ULTRA-STEALTH scraper instead of basic stealth
                average_price_per_sqm = None
                real_data_found = False
                scraping_error = None
                
                logger.info(f"🛡️ Attempting ULTRA-STEALTH scraping for {property_type}")
                
                try:
                    # Use ultra-stealth Selenium approach
                    page_source = await ultra_stealth_scraper.ultra_stealth_get(url)
                    
                    if page_source:
                        # Extract price using Selenium-specific methods
                        zone_price, extraction_error = ultra_stealth_scraper.extract_zone_price_from_selenium(url)
                        
                        if zone_price:
                            average_price_per_sqm = zone_price
                            real_data_found = True
                            logger.info(f"✅ ULTRA-STEALTH SUCCESS: {average_price_per_sqm:.2f} €/m² for {property_type}")
                        else:
                            scraping_error = extraction_error or "No price data found with ultra-stealth method"
                            logger.warning(f"⚠️ Ultra-stealth extraction failed: {scraping_error}")
                    else:
                        scraping_error = "Ultra-stealth page retrieval failed"
                        
                except Exception as ultra_e:
                    scraping_error = f"Ultra-stealth method failed: {str(ultra_e)}"
                    logger.warning(f"Ultra-stealth attempt failed: {ultra_e}")
                    
                    # Fallback to basic stealth scraper if ultra-stealth fails
                    logger.info("Falling back to basic stealth scraper...")
                    try:
                        response = await stealth_scraper.stealthy_get(url)
                        
                        if response.status_code == 200:
                            # Extract price using basic stealth scraper
                            zone_price, extraction_error = stealth_scraper.extract_zone_price(response.text, url)
                            
                            if zone_price:
                                average_price_per_sqm = zone_price
                                real_data_found = True
                                logger.info(f"✅ BASIC STEALTH SUCCESS: {average_price_per_sqm:.2f} €/m² for {property_type}")
                            else:
                                scraping_error = extraction_error or "No price data found on page"
                                
                        elif response.status_code == 403:
                            scraping_error = "HTTP 403 Forbidden - Site is blocking requests (both ultra and basic stealth failed)"
                        elif response.status_code == 429:
                            scraping_error = "HTTP 429 Too Many Requests - Rate limited (need longer delays)"
                        elif response.status_code == 404:
                            scraping_error = "HTTP 404 Not Found - URL might be invalid for this location"
                        else:
                            scraping_error = f"HTTP {response.status_code} - Request failed"
                            
                    except Exception as basic_e:
                        scraping_error = f"Both ultra-stealth and basic stealth failed: {str(basic_e)}"
                
                # Create property entry ONLY if we have real scraped data
                if real_data_found and average_price_per_sqm and average_price_per_sqm > 0:
                    property_data = {
                        'region': distrito,
                        'location': f"{concelho}_{freguesia}",
                        'property_type': property_type,  # Specific property type (apartment, house, urban_plot, rural_plot)
                        'price': None,  # Individual property prices not available from zone averages
                        'price_per_sqm': average_price_per_sqm,  # REAL scraped price from "Preço médio nesta zona"
                        'area': None,  # Not applicable for zone averages
                        'operation_type': operation_type,
                        'url': url
                    }
                    
                    all_properties.append(property_data)
                    logger.info(f"✅ Added STEALTH SCRAPED {property_type} {operation_type}: {average_price_per_sqm:.2f} €/m² for {distrito}/{concelho}/{freguesia}")
                else:
                    # Record detailed error for this property type
                    error_info = {
                        'property_type': property_type,
                        'operation_type': operation_type,
                        'url': url,
                        'error': scraping_error or "No real price data found",
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    error_details.append(error_info)
                    logger.warning(f"❌ Failed to stealth scrape {property_type} {operation_type} at {distrito}/{concelho}/{freguesia}: {scraping_error or 'No price data'}")
                
                # Additional delay between property types for ultra-stealth
                logger.info(f"Ultra-stealth waiting before next property type...")
                await asyncio.sleep(random.uniform(10, 20))  # Even longer delays
                
            except Exception as e:
                error_info = {
                    'property_type': property_type,
                    'operation_type': operation_type,
                    'url': url,
                    'error': f"Unexpected error: {str(e)}",
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                error_details.append(error_info)
                logger.error(f"Error in ultra-stealth scraping {property_type} from {url}: {e}")
                continue
        
        # Clean up ultra-stealth driver after all property types are processed
        ultra_stealth_scraper.close_driver()
        logger.info("Ultra-stealth driver cleaned up")
        
        # Update session with detailed results
        if session_id:
            zone_key = f"{distrito}/{concelho}/{freguesia}"
            if all_properties:
                # Success - add to success zones
                await db.scraping_sessions.update_one(
                    {"id": session_id},
                    {"$push": {
                        "success_zones": {
                            "zone": zone_key,
                            "operation_type": operation_type,
                            "properties_count": len(all_properties),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    }}
                )
            
            if error_details:
                # Errors occurred - add to failed zones
                await db.scraping_sessions.update_one(
                    {"id": session_id},
                    {"$push": {
                        "failed_zones": {
                            "zone": zone_key,
                            "operation_type": operation_type,
                            "errors": error_details,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    }}
                )
        
        return all_properties
        """Scrape average price per m² from idealista.pt freguesia property listings"""
        properties = []
        error_details = []
        
        # Construct URLs for idealista.pt property search pages
        concelho_clean = concelho.lower().replace(' ', '-').replace('_', '-')
        freguesia_clean = freguesia.lower().replace(' ', '-').replace('_', '-')
        
        if operation_type == 'sale':
            # URLs for different property types in sale
            urls_to_scrape = [
                {
                    'url': f"https://www.idealista.pt/comprar-casas/{concelho_clean}/{freguesia_clean}/com-apartamentos/",
                    'property_type': 'apartment'
                },
                {
                    'url': f"https://www.idealista.pt/comprar-casas/{concelho_clean}/{freguesia_clean}/com-moradias/",
                    'property_type': 'house'
                },
                {
                    'url': f"https://www.idealista.pt/comprar-terrenos/{concelho_clean}/{freguesia_clean}/com-terreno-urbano/",
                    'property_type': 'urban_plot'
                },
                {
                    'url': f"https://www.idealista.pt/comprar-terrenos/{concelho_clean}/{freguesia_clean}/com-terreno-nao-urbanizavel/",
                    'property_type': 'rural_plot'
                }
            ]
        else:
            # URLs for rentals (no rural plots in rental)
            urls_to_scrape = [
                {
                    'url': f"https://www.idealista.pt/arrendar-casas/{concelho_clean}/{freguesia_clean}/com-apartamentos,arrendamento-longa-duracao/",
                    'property_type': 'apartment'
                },
                {
                    'url': f"https://www.idealista.pt/arrendar-casas/{concelho_clean}/{freguesia_clean}/com-moradias,arrendamento-longa-duracao/",
                    'property_type': 'house'
                }
            ]
        
        logger.info(f"Scraping {len(urls_to_scrape)} property types for: {distrito}/{concelho}/{freguesia} ({operation_type})")
        
        all_properties = []
        
        for url_info in urls_to_scrape:
            url = url_info['url']
            property_type = url_info['property_type']
            
            logger.info(f"Scraping {property_type} from: {url}")
            
            try:
                # Simulate scraping delay (realistic timing)
                await asyncio.sleep(2)
                
                # Try real scraping first
                average_price_per_sqm = None
                real_data_found = False
                scraping_error = None
                
                # Try Selenium if available
                if self.driver is None:
                    try:
                        self.setup_driver()
                    except Exception as e:
                        scraping_error = f"Selenium setup failed: {str(e)}"
                        logger.warning(scraping_error)
                
                if self.driver and not scraping_error:
                    try:
                        self.driver.get(url)
                        await asyncio.sleep(3)
                        
                        # Check for CAPTCHA (realistic CAPTCHA simulation)
                        if random.random() < 0.15:  # 15% chance of CAPTCHA
                            scraping_error = "CAPTCHA detected - manual intervention required"
                            logger.info(f"CAPTCHA detected during {property_type} scraping")
                            
                            # Save a mock CAPTCHA image for testing
                            captcha_filename = self.save_mock_captcha_image(session_id)
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
                                
                                logger.info("Session paused for CAPTCHA resolution...")
                                await asyncio.sleep(8)
                                
                                # Auto-continue simulation
                                await db.scraping_sessions.update_one(
                                    {"id": session_id},
                                    {"$set": {
                                        "status": "running",
                                        "captcha_image_path": None,
                                        "current_url": None
                                    }}
                                )
                                scraping_error = None  # Reset error after CAPTCHA resolution
                        
                        # Look for price information in the property listings
                        if not scraping_error:
                            try:
                                # Search specifically for the "items-average-price" element
                                zone_price_elements = self.driver.find_elements(By.CLASS_NAME, "items-average-price")
                                
                                zone_price_found = False
                                for elem in zone_price_elements:
                                    try:
                                        price_text = elem.get_attribute('textContent') or elem.text
                                        logger.info(f"Found items-average-price element: {price_text}")
                                        
                                        # Look for price pattern like "11,05 eur/m²" or "11.05 €/m²"
                                        price_patterns = [
                                            r'(\d+(?:[.,]\d+)?)\s*eur?/?m²?',  # "11,05 eur/m²"
                                            r'(\d+(?:[.,]\d+)?)\s*€\s*/?m²?',   # "11,05 €/m²"
                                            r'(\d+(?:[.,]\d+)?)\s*euros?\s*/?m²?' # "11,05 euros/m²"
                                        ]
                                        
                                        for pattern in price_patterns:
                                            price_match = re.search(pattern, price_text, re.IGNORECASE)
                                            if price_match:
                                                price_str = price_match.group(1).replace(',', '.')
                                                try:
                                                    zone_price = float(price_str)
                                                    if 0.5 <= zone_price <= 1000:  # Reasonable range for €/m² zone averages
                                                        average_price_per_sqm = zone_price
                                                        real_data_found = True
                                                        zone_price_found = True
                                                        logger.info(f"✅ REAL SCRAPED PRICE from items-average-price: {average_price_per_sqm:.2f} €/m²")
                                                        break
                                                except:
                                                    continue
                                        if zone_price_found:
                                            break
                                    except:
                                        continue
                                
                                # If no items-average-price found, try alternative search for "Preço médio nesta zona"
                                if not zone_price_found:
                                    logger.info("items-average-price not found, trying text search for 'Preço médio nesta zona'...")
                                    zone_text_elements = self.driver.find_elements(By.XPATH, 
                                        "//*[contains(text(), 'Preço médio nesta zona') or contains(text(), 'preço médio nesta zona')]")
                                    
                                    for elem in zone_text_elements:
                                        try:
                                            # Check the element and its parent/siblings for price
                                            elements_to_check = [elem]
                                            parent = elem.find_element(By.XPATH, "..")
                                            elements_to_check.append(parent)
                                            siblings = parent.find_elements(By.XPATH, "./*")
                                            elements_to_check.extend(siblings)
                                            
                                            for check_elem in elements_to_check:
                                                price_text = check_elem.get_attribute('textContent') or check_elem.text
                                                
                                                # Look for price pattern
                                                price_patterns = [
                                                    r'(\d+(?:[.,]\d+)?)\s*eur?/?m²?',
                                                    r'(\d+(?:[.,]\d+)?)\s*€\s*/?m²?',
                                                    r'(\d+(?:[.,]\d+)?)\s*euros?\s*/?m²?'
                                                ]
                                                
                                                for pattern in price_patterns:
                                                    price_match = re.search(pattern, price_text, re.IGNORECASE)
                                                    if price_match:
                                                        price_str = price_match.group(1).replace(',', '.')
                                                        try:
                                                            zone_price = float(price_str)
                                                            if 0.5 <= zone_price <= 1000:
                                                                average_price_per_sqm = zone_price
                                                                real_data_found = True
                                                                zone_price_found = True
                                                                logger.info(f"✅ REAL SCRAPED PRICE from text search: {average_price_per_sqm:.2f} €/m²")
                                                                break
                                                        except:
                                                            continue
                                                if zone_price_found:
                                                    break
                                            if zone_price_found:
                                                break
                                        except:
                                            continue
                                        if zone_price_found:
                                            break
                                
                                if not real_data_found:
                                    scraping_error = "No 'items-average-price' element or 'Preço médio nesta zona' found on page"
                                            
                            except Exception as e:
                                scraping_error = f"Selenium price extraction failed: {str(e)}"
                                logger.warning(scraping_error)
                            
                    except Exception as e:
                        scraping_error = f"Selenium page load failed: {str(e)}"
                        logger.warning(scraping_error)
                
                # If Selenium failed, try requests fallback
                if not real_data_found and not scraping_error:
                    try:
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                            'Accept-Language': 'pt-PT,pt;q=0.9,en;q=0.8',
                        }
                        
                        response = requests.get(url, headers=headers, timeout=10)
                        
                        if response.status_code == 200:
                            # Look for price information in the HTML
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # First, search for the specific "items-average-price" class
                            zone_price_elements = soup.find_all(class_="items-average-price")
                            zone_price_found = False
                            
                            for elem in zone_price_elements:
                                try:
                                    price_text = elem.get_text()
                                    logger.info(f"Found items-average-price element: {price_text}")
                                    
                                    # Look for price patterns like "11,05 eur/m²"
                                    price_patterns = [
                                        r'(\d+(?:[.,]\d+)?)\s*eur?/?m²?',  # "11,05 eur/m²"
                                        r'(\d+(?:[.,]\d+)?)\s*€\s*/?m²?',   # "11,05 €/m²"
                                        r'(\d+(?:[.,]\d+)?)\s*euros?\s*/?m²?' # "11,05 euros/m²"
                                    ]
                                    
                                    for pattern in price_patterns:
                                        price_match = re.search(pattern, price_text, re.IGNORECASE)
                                        if price_match:
                                            price_str = price_match.group(1).replace(',', '.')
                                            try:
                                                zone_price = float(price_str)
                                                if 0.5 <= zone_price <= 1000:  # Reasonable range
                                                    average_price_per_sqm = zone_price
                                                    real_data_found = True
                                                    zone_price_found = True
                                                    logger.info(f"✅ REAL SCRAPED PRICE via requests from items-average-price: {average_price_per_sqm:.2f} €/m²")
                                                    break
                                            except:
                                                continue
                                        if zone_price_found:
                                            break
                                except:
                                    continue
                            
                            # If no items-average-price found, search by text content
                            if not zone_price_found:
                                logger.info("items-average-price class not found, searching page text...")
                                page_text = soup.get_text()
                                
                                # Look for "Preço médio nesta zona" pattern in text
                                zone_patterns = [
                                    r'preço médio nesta zona[:\s]*(\d+(?:[.,]\d+)?)\s*eur?/?m²?',
                                    r'Preço médio nesta zona[:\s]*(\d+(?:[.,]\d+)?)\s*eur?/?m²?',
                                    r'preço médio nesta zona[:\s]*(\d+(?:[.,]\d+)?)\s*€\s*/?m²?',
                                    r'Preço médio nesta zona[:\s]*(\d+(?:[.,]\d+)?)\s*€\s*/?m²?'
                                ]
                                
                                for pattern in zone_patterns:
                                    zone_match = re.search(pattern, page_text, re.IGNORECASE)
                                    if zone_match:
                                        price_str = zone_match.group(1).replace(',', '.')
                                        try:
                                            zone_price = float(price_str)
                                            if 0.5 <= zone_price <= 1000:
                                                average_price_per_sqm = zone_price
                                                real_data_found = True
                                                zone_price_found = True
                                                logger.info(f"✅ REAL SCRAPED PRICE via requests from text pattern: {average_price_per_sqm:.2f} €/m²")
                                                break
                                        except:
                                            continue
                                    if zone_price_found:
                                        break
                            
                            if not real_data_found:
                                scraping_error = "HTTP 200 received but no price data found on page"
                                
                        elif response.status_code == 403:
                            scraping_error = "HTTP 403 Forbidden - Site is blocking requests"
                        elif response.status_code == 429:
                            scraping_error = "HTTP 429 Too Many Requests - Rate limited"
                        elif response.status_code == 404:
                            scraping_error = "HTTP 404 Not Found - URL might be invalid for this location"
                        else:
                            scraping_error = f"HTTP {response.status_code} - Request failed"
                            
                    except requests.exceptions.Timeout:
                        scraping_error = "Request timeout - Site too slow to respond"
                    except requests.exceptions.ConnectionError:
                        scraping_error = "Connection error - Cannot reach idealista.pt"
                    except Exception as e:
                        scraping_error = f"Requests scraping failed: {str(e)}"
                
                # Create property entry ONLY if we have real scraped data
                if real_data_found and average_price_per_sqm and average_price_per_sqm > 0:
                    property_data = {
                        'region': distrito,
                        'location': f"{concelho}_{freguesia}",
                        'property_type': property_type,  # Specific property type (apartment, house, urban_plot, rural_plot)
                        'price': None,  # Individual property prices not available from zone averages
                        'price_per_sqm': average_price_per_sqm,  # REAL scraped price from "Preço médio nesta zona"
                        'area': None,  # Not applicable for zone averages
                        'operation_type': operation_type,
                        'url': url
                    }
                    
                    all_properties.append(property_data)
                    logger.info(f"✅ Added REAL SCRAPED {property_type} {operation_type}: {average_price_per_sqm:.2f} €/m² for {distrito}/{concelho}/{freguesia}")
                else:
                    # Record detailed error for this property type
                    error_info = {
                        'property_type': property_type,
                        'operation_type': operation_type,
                        'url': url,
                        'error': scraping_error or "No real price data found",
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    error_details.append(error_info)
                    logger.warning(f"❌ Failed to scrape {property_type} {operation_type} at {distrito}/{concelho}/{freguesia}: {scraping_error or 'No price data'}")
                
                # Add delay between property types to be respectful
                await asyncio.sleep(1)
                
            except Exception as e:
                error_info = {
                    'property_type': property_type,
                    'operation_type': operation_type,
                    'url': url,
                    'error': f"Unexpected error: {str(e)}",
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                error_details.append(error_info)
                logger.error(f"Error scraping {property_type} from {url}: {e}")
                continue
        
        # Update session with detailed results
        if session_id:
            zone_key = f"{distrito}/{concelho}/{freguesia}"
            if all_properties:
                # Success - add to success zones
                await db.scraping_sessions.update_one(
                    {"id": session_id},
                    {"$push": {
                        "success_zones": {
                            "zone": zone_key,
                            "operation_type": operation_type,
                            "properties_count": len(all_properties),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    }}
                )
            
            if error_details:
                # Errors occurred - add to failed zones
                await db.scraping_sessions.update_one(
                    {"id": session_id},
                    {"$push": {
                        "failed_zones": {
                            "zone": zone_key,
                            "operation_type": operation_type,
                            "errors": error_details,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    }}
                )
        
        return all_properties
        """Scrape average price per m² from idealista.pt freguesia property listings"""
        properties = []
        
        # Construct URLs for idealista.pt property search pages
        concelho_clean = concelho.lower().replace(' ', '-').replace('_', '-')
        freguesia_clean = freguesia.lower().replace(' ', '-').replace('_', '-')
        
        if operation_type == 'sale':
            # URLs for different property types in sale
            urls_to_scrape = [
                {
                    'url': f"https://www.idealista.pt/comprar-casas/{concelho_clean}/{freguesia_clean}/com-apartamentos/",
                    'property_type': 'apartment'
                },
                {
                    'url': f"https://www.idealista.pt/comprar-casas/{concelho_clean}/{freguesia_clean}/com-moradias/",
                    'property_type': 'house'
                },
                {
                    'url': f"https://www.idealista.pt/comprar-terrenos/{concelho_clean}/{freguesia_clean}/com-terreno-urbano/",
                    'property_type': 'urban_plot'
                },
                {
                    'url': f"https://www.idealista.pt/comprar-terrenos/{concelho_clean}/{freguesia_clean}/com-terreno-nao-urbanizavel/",
                    'property_type': 'rural_plot'
                }
            ]
        else:
            # URLs for rentals (no rural plots in rental)
            urls_to_scrape = [
                {
                    'url': f"https://www.idealista.pt/arrendar-casas/{concelho_clean}/{freguesia_clean}/com-apartamentos,arrendamento-longa-duracao/",
                    'property_type': 'apartment'
                },
                {
                    'url': f"https://www.idealista.pt/arrendar-casas/{concelho_clean}/{freguesia_clean}/com-moradias,arrendamento-longa-duracao/",
                    'property_type': 'house'
                }
            ]
        
        logger.info(f"Scraping {len(urls_to_scrape)} property types for: {distrito}/{concelho}/{freguesia} ({operation_type})")
        
        all_properties = []
        
        for url_info in urls_to_scrape:
            url = url_info['url']
            property_type = url_info['property_type']
            
            logger.info(f"Scraping {property_type} from: {url}")
            
            try:
                # Simulate scraping delay (realistic timing)
                await asyncio.sleep(2)
                
                # Try real scraping first
                average_price_per_sqm = None
                real_data_found = False
                
                # Try Selenium if available
                if self.driver is None:
                    try:
                        self.setup_driver()
                    except:
                        logger.warning("Selenium not available")
                
                if self.driver:
                    try:
                        self.driver.get(url)
                        await asyncio.sleep(3)
                        
                        # Check for CAPTCHA (realistic CAPTCHA simulation)
                        if random.random() < 0.15:  # 15% chance of CAPTCHA
                            logger.info(f"CAPTCHA detected during {property_type} scraping")
                            
                            # Save a mock CAPTCHA image for testing
                            captcha_filename = self.save_mock_captcha_image(session_id)
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
                                
                                logger.info("Session paused for CAPTCHA resolution...")
                                await asyncio.sleep(8)
                                
                                # Auto-continue simulation
                                await db.scraping_sessions.update_one(
                                    {"id": session_id},
                                    {"$set": {
                                        "status": "running",
                                        "captcha_image_path": None,
                                        "current_url": None
                                    }}
                                )
                        
                        # Look for price information in the property listings
                        try:
                            # Search specifically for the "items-average-price" element
                            zone_price_elements = self.driver.find_elements(By.CLASS_NAME, "items-average-price")
                            
                            zone_price_found = False
                            for elem in zone_price_elements:
                                try:
                                    price_text = elem.get_attribute('textContent') or elem.text
                                    logger.info(f"Found items-average-price element: {price_text}")
                                    
                                    # Look for price pattern like "11,05 eur/m²" or "11.05 €/m²"
                                    price_patterns = [
                                        r'(\d+(?:[.,]\d+)?)\s*eur?/?m²?',  # "11,05 eur/m²"
                                        r'(\d+(?:[.,]\d+)?)\s*€\s*/?m²?',   # "11,05 €/m²"
                                        r'(\d+(?:[.,]\d+)?)\s*euros?\s*/?m²?' # "11,05 euros/m²"
                                    ]
                                    
                                    for pattern in price_patterns:
                                        price_match = re.search(pattern, price_text, re.IGNORECASE)
                                        if price_match:
                                            price_str = price_match.group(1).replace(',', '.')
                                            try:
                                                zone_price = float(price_str)
                                                if 0.5 <= zone_price <= 1000:  # Reasonable range for €/m² zone averages
                                                    average_price_per_sqm = zone_price
                                                    real_data_found = True
                                                    zone_price_found = True
                                                    logger.info(f"✅ REAL SCRAPED PRICE from items-average-price: {average_price_per_sqm:.2f} €/m²")
                                                    break
                                            except:
                                                continue
                                    if zone_price_found:
                                        break
                                except:
                                    continue
                            
                            # If no items-average-price found, try alternative search for "Preço médio nesta zona"
                            if not zone_price_found:
                                logger.info("items-average-price not found, trying text search for 'Preço médio nesta zona'...")
                                zone_text_elements = self.driver.find_elements(By.XPATH, 
                                    "//*[contains(text(), 'Preço médio nesta zona') or contains(text(), 'preço médio nesta zona')]")
                                
                                for elem in zone_text_elements:
                                    try:
                                        # Check the element and its parent/siblings for price
                                        elements_to_check = [elem]
                                        parent = elem.find_element(By.XPATH, "..")
                                        elements_to_check.append(parent)
                                        siblings = parent.find_elements(By.XPATH, "./*")
                                        elements_to_check.extend(siblings)
                                        
                                        for check_elem in elements_to_check:
                                            price_text = check_elem.get_attribute('textContent') or check_elem.text
                                            
                                            # Look for price pattern
                                            price_patterns = [
                                                r'(\d+(?:[.,]\d+)?)\s*eur?/?m²?',
                                                r'(\d+(?:[.,]\d+)?)\s*€\s*/?m²?',
                                                r'(\d+(?:[.,]\d+)?)\s*euros?\s*/?m²?'
                                            ]
                                            
                                            for pattern in price_patterns:
                                                price_match = re.search(pattern, price_text, re.IGNORECASE)
                                                if price_match:
                                                    price_str = price_match.group(1).replace(',', '.')
                                                    try:
                                                        zone_price = float(price_str)
                                                        if 0.5 <= zone_price <= 1000:
                                                            average_price_per_sqm = zone_price
                                                            real_data_found = True
                                                            zone_price_found = True
                                                            logger.info(f"✅ REAL SCRAPED PRICE from text search: {average_price_per_sqm:.2f} €/m²")
                                                            break
                                                    except:
                                                        continue
                                            if zone_price_found:
                                                break
                                        if zone_price_found:
                                            break
                                    except:
                                        continue
                                    if zone_price_found:
                                        break
                                        
                        except Exception as e:
                            logger.warning(f"Could not extract real average price: {e}")
                            
                    except Exception as e:
                        logger.warning(f"Selenium scraping failed: {e}")
                
                if not real_data_found:
                    # Use requests fallback
                    try:
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                            'Accept-Language': 'pt-PT,pt;q=0.9,en;q=0.8',
                        }
                        
                        response = requests.get(url, headers=headers, timeout=10)
                        if response.status_code == 200:
                            # Look for price information in the HTML
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # First, search for the specific "items-average-price" class
                            zone_price_elements = soup.find_all(class_="items-average-price")
                            zone_price_found = False
                            
                            for elem in zone_price_elements:
                                try:
                                    price_text = elem.get_text()
                                    logger.info(f"Found items-average-price element: {price_text}")
                                    
                                    # Look for price patterns like "11,05 eur/m²"
                                    price_patterns = [
                                        r'(\d+(?:[.,]\d+)?)\s*eur?/?m²?',  # "11,05 eur/m²"
                                        r'(\d+(?:[.,]\d+)?)\s*€\s*/?m²?',   # "11,05 €/m²"
                                        r'(\d+(?:[.,]\d+)?)\s*euros?\s*/?m²?' # "11,05 euros/m²"
                                    ]
                                    
                                    for pattern in price_patterns:
                                        price_match = re.search(pattern, price_text, re.IGNORECASE)
                                        if price_match:
                                            price_str = price_match.group(1).replace(',', '.')
                                            try:
                                                zone_price = float(price_str)
                                                if 0.5 <= zone_price <= 1000:  # Reasonable range
                                                    average_price_per_sqm = zone_price
                                                    real_data_found = True
                                                    zone_price_found = True
                                                    logger.info(f"✅ REAL SCRAPED PRICE via requests from items-average-price: {average_price_per_sqm:.2f} €/m²")
                                                    break
                                            except:
                                                continue
                                    if zone_price_found:
                                        break
                                except:
                                    continue
                            
                            # If no items-average-price found, search by text content
                            if not zone_price_found:
                                logger.info("items-average-price class not found, searching page text...")
                                page_text = soup.get_text()
                                
                                # Look for "Preço médio nesta zona" pattern in text
                                zone_patterns = [
                                    r'preço médio nesta zona[:\s]*(\d+(?:[.,]\d+)?)\s*eur?/?m²?',
                                    r'Preço médio nesta zona[:\s]*(\d+(?:[.,]\d+)?)\s*eur?/?m²?',
                                    r'preço médio nesta zona[:\s]*(\d+(?:[.,]\d+)?)\s*€\s*/?m²?',
                                    r'Preço médio nesta zona[:\s]*(\d+(?:[.,]\d+)?)\s*€\s*/?m²?'
                                ]
                                
                                for pattern in zone_patterns:
                                    zone_match = re.search(pattern, page_text, re.IGNORECASE)
                                    if zone_match:
                                        price_str = zone_match.group(1).replace(',', '.')
                                        try:
                                            zone_price = float(price_str)
                                            if 0.5 <= zone_price <= 1000:
                                                average_price_per_sqm = zone_price
                                                real_data_found = True
                                                zone_price_found = True
                                                logger.info(f"✅ REAL SCRAPED PRICE via requests from text pattern: {average_price_per_sqm:.2f} €/m²")
                                                break
                                        except:
                                            continue
                                    if zone_price_found:
                                        break
                    except Exception as e:
                        logger.warning(f"Requests scraping failed: {e}")
                
                # Create property entry ONLY if we have real scraped data
                if real_data_found and average_price_per_sqm and average_price_per_sqm > 0:
                    property_data = {
                        'region': distrito,
                        'location': f"{concelho}_{freguesia}",
                        'property_type': property_type,  # Specific property type (apartment, house, urban_plot, rural_plot)
                        'price': None,  # Individual property prices not available from zone averages
                        'price_per_sqm': average_price_per_sqm,  # REAL scraped price from "Preço médio nesta zona"
                        'area': None,  # Not applicable for zone averages
                        'operation_type': operation_type,
                        'url': url
                    }
                    
                    all_properties.append(property_data)
                    logger.info(f"✅ Added REAL SCRAPED {property_type} {operation_type}: {average_price_per_sqm:.2f} €/m² for {distrito}/{concelho}/{freguesia}")
                else:
                    logger.warning(f"❌ No real price data found for {property_type} {operation_type} at {distrito}/{concelho}/{freguesia} - SKIPPING (no simulated data)")
                
                # Add delay between property types to be respectful
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error scraping {property_type} from {url}: {e}")
                continue
        
        return all_properties
    
    def save_mock_captcha_image(self, session_id):
        """Save a mock CAPTCHA image for testing purposes"""
        if not session_id:
            return None
            
        try:
            import base64
            from PIL import Image, ImageDraw, ImageFont
            import io
            
            # Create a simple mock CAPTCHA image
            img = Image.new('RGB', (200, 80), color='white')
            draw = ImageDraw.Draw(img)
            
            # Add some simple text as mock CAPTCHA
            captcha_text = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=5))
            
            try:
                # Try to use a default font
                font = ImageFont.load_default()
            except:
                font = None
            
            # Draw the CAPTCHA text
            draw.text((50, 30), captcha_text, fill='black', font=font)
            
            # Add some noise lines
            for _ in range(5):
                x1, y1 = random.randint(0, 200), random.randint(0, 80)
                x2, y2 = random.randint(0, 200), random.randint(0, 80)
                draw.line([(x1, y1), (x2, y2)], fill='gray', width=1)
            
            # Save the image
            captcha_path = CAPTCHA_DIR / f"mock_captcha_{session_id}.png"
            img.save(captcha_path)
            
            logger.info(f"Mock CAPTCHA saved: {captcha_path}")
            return f"mock_captcha_{session_id}.png"
            
        except Exception as e:
            logger.error(f"Error creating mock CAPTCHA: {e}")
            # Fallback: create a simple text file
            try:
                captcha_path = CAPTCHA_DIR / f"mock_captcha_{session_id}.txt"
                with open(captcha_path, 'w') as f:
                    f.write("MOCK CAPTCHA - Enter any text to continue")
                return f"mock_captcha_{session_id}.txt"
            except:
                return None

scraper = IdealistaScraper()

@api_router.post("/scrape/targeted")
async def start_targeted_scraping(
    background_tasks: BackgroundTasks,
    distrito: Optional[str] = None,
    concelho: Optional[str] = None, 
    freguesia: Optional[str] = None
):
    """Start a targeted scraping session for specific administrative level"""
    if not distrito:
        raise HTTPException(status_code=400, detail="Distrito is required")
    
    session = ScrapingSession(status="running")
    session_dict = session.dict()
    await db.scraping_sessions.insert_one(session_dict)
    
    background_tasks.add_task(run_targeted_scraping_task, session.id, distrito, concelho, freguesia)
    
    target_description = distrito
    if concelho:
        target_description += f" > {concelho}"
    if freguesia:
        target_description += f" > {freguesia}"
    
    return {
        "message": f"Scraping ciblé démarré pour: {target_description}", 
        "session_id": session.id,
        "target": {"distrito": distrito, "concelho": concelho, "freguesia": freguesia}
    }

async def run_targeted_scraping_task(session_id: str, distrito: str, concelho: Optional[str] = None, freguesia: Optional[str] = None):
    """Background task for targeted scraping"""
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
        
        # Get the administrative structure
        logger.info("Fetching administrative structure for targeted scraping...")
        structure = await scraper.get_administrative_structure()
        
        if not structure or distrito not in structure:
            await db.scraping_sessions.update_one(
                {"id": session_id},
                {"$set": {
                    "status": "failed",
                    "completed_at": datetime.now(timezone.utc),
                    "error_message": f"Distrito '{distrito}' not found in administrative structure"
                }}
            )
            return
        
        distrito_data = structure[distrito]
        
        if freguesia and concelho:
            # Scrape specific freguesia
            if concelho in distrito_data and freguesia in distrito_data[concelho]:
                logger.info(f"Scraping specific freguesia: {distrito}/{concelho}/{freguesia}")
                
                # Scrape sales data
                sale_properties = await scraper.scrape_freguesia(distrito, concelho, freguesia, 'sale', session_id=session_id)
                for prop_data in sale_properties:
                    property_obj = Property(**prop_data)
                    await db.properties.insert_one(property_obj.dict())
                    total_properties += 1
                
                # Scrape rental data
                rent_properties = await scraper.scrape_freguesia(distrito, concelho, freguesia, 'rent', session_id=session_id)
                for prop_data in rent_properties:
                    property_obj = Property(**prop_data)
                    await db.properties.insert_one(property_obj.dict())
                    total_properties += 1
                
                regions_scraped.append(f"{distrito}/{concelho}/{freguesia}")
            else:
                raise Exception(f"Freguesia '{freguesia}' not found in {distrito}/{concelho}")
                
        elif concelho:
            # Scrape all freguesias in concelho
            if concelho in distrito_data:
                logger.info(f"Scraping all freguesias in concelho: {distrito}/{concelho}")
                freguesias_list = distrito_data[concelho]
                
                for freguesia_name in freguesias_list:
                    try:
                        logger.info(f"Processing: {distrito}/{concelho}/{freguesia_name}")
                        
                        # Scrape sales and rental data for this freguesia
                        sale_properties = await scraper.scrape_freguesia(distrito, concelho, freguesia_name, 'sale', session_id=session_id)
                        for prop_data in sale_properties:
                            property_obj = Property(**prop_data)
                            await db.properties.insert_one(property_obj.dict())
                            total_properties += 1
                        
                        rent_properties = await scraper.scrape_freguesia(distrito, concelho, freguesia_name, 'rent', session_id=session_id)
                        for prop_data in rent_properties:
                            property_obj = Property(**prop_data)
                            await db.properties.insert_one(property_obj.dict())
                            total_properties += 1
                        
                        regions_scraped.append(f"{distrito}/{concelho}/{freguesia_name}")
                        
                        # Small delay between freguesias
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error scraping freguesia {freguesia_name}: {e}")
                        continue
            else:
                raise Exception(f"Concelho '{concelho}' not found in distrito '{distrito}'")
                
        else:
            # Scrape all concelhos and freguesias in distrito
            logger.info(f"Scraping all concelhos in distrito: {distrito}")
            
            for concelho_name, freguesias_list in distrito_data.items():
                logger.info(f"Processing concelho: {distrito}/{concelho_name} ({len(freguesias_list)} freguesias)")
                
                for freguesia_name in freguesias_list:
                    try:
                        logger.info(f"Processing: {distrito}/{concelho_name}/{freguesia_name}")
                        
                        # Scrape sales and rental data
                        sale_properties = await scraper.scrape_freguesia(distrito, concelho_name, freguesia_name, 'sale', session_id=session_id)
                        for prop_data in sale_properties:
                            property_obj = Property(**prop_data)
                            await db.properties.insert_one(property_obj.dict())
                            total_properties += 1
                        
                        rent_properties = await scraper.scrape_freguesia(distrito, concelho_name, freguesia_name, 'rent', session_id=session_id)
                        for prop_data in rent_properties:
                            property_obj = Property(**prop_data)
                            await db.properties.insert_one(property_obj.dict())
                            total_properties += 1
                        
                        regions_scraped.append(f"{distrito}/{concelho_name}/{freguesia_name}")
                        
                        # Small delay between freguesias
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error scraping freguesia {freguesia_name}: {e}")
                        continue
                
                # Delay between concelhos
                await asyncio.sleep(2)
        
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
        
        logger.info(f"Targeted scraping completed: {total_properties} properties from {len(regions_scraped)} regions")
        
    except Exception as e:
        logger.error(f"Targeted scraping failed: {e}")
        scraper.close_driver()
        await db.scraping_sessions.update_one(
            {"id": session_id},
            {"$set": {
                "status": "failed",
                "completed_at": datetime.now(timezone.utc),
                "error_message": str(e)
            }}
        )

@api_router.get("/coverage/detailed")
async def get_detailed_coverage():
    """Get detailed coverage statistics by administrative levels"""
    
    # Get administrative structure
    if not scraper.administrative_structure:
        await scraper.get_administrative_structure()
    
    structure = scraper.administrative_structure
    
    # Get all scraped locations from database
    scraped_locations = await db.properties.distinct("location")
    scraped_regions = await db.properties.distinct("region")
    
    detailed_coverage = {
        "overview": {
            "total_distritos": len(structure),
            "scraped_distritos": len(scraped_regions),
            "total_concelhos": sum(len(concelhos) for concelhos in structure.values()),
            "total_freguesias": sum(len(freguesias) for distrito_data in structure.values() for freguesias in distrito_data.values()),
            "scraped_locations": len(scraped_locations)
        },
        "by_distrito": []
    }
    
    for distrito, concelhos_data in structure.items():
        distrito_info = {
            "distrito": distrito,
            "distrito_display": distrito.replace('-', ' ').title(),
            "total_concelhos": len(concelhos_data),
            "total_freguesias": sum(len(freguesias) for freguesias in concelhos_data.values()),
            "scraped": distrito in scraped_regions,
            "concelhos": []
        }
        
        scraped_concelhos = 0
        scraped_freguesias_total = 0
        
        for concelho, freguesias_list in concelhos_data.items():
            # Check which freguesias in this concelho are scraped
            scraped_freguesias_in_concelho = []
            for freguesia in freguesias_list:
                location_pattern = f"{concelho}_{freguesia}"
                if location_pattern in scraped_locations:
                    scraped_freguesias_in_concelho.append(freguesia)
            
            concelho_scraped = len(scraped_freguesias_in_concelho) > 0
            if concelho_scraped:
                scraped_concelhos += 1
            
            scraped_freguesias_total += len(scraped_freguesias_in_concelho)
            
            concelho_info = {
                "concelho": concelho,
                "concelho_display": concelho.replace('-', ' ').title(),
                "total_freguesias": len(freguesias_list),
                "scraped_freguesias": len(scraped_freguesias_in_concelho),
                "scraped": concelho_scraped,
                "coverage_percentage": (len(scraped_freguesias_in_concelho) / len(freguesias_list)) * 100 if freguesias_list else 0,
                "missing_freguesias": [f for f in freguesias_list if f not in [sf for sf in scraped_freguesias_in_concelho]]
            }
            
            distrito_info["concelhos"].append(concelho_info)
        
        distrito_info["scraped_concelhos"] = scraped_concelhos
        distrito_info["scraped_freguesias"] = scraped_freguesias_total
        distrito_info["concelho_coverage_percentage"] = (scraped_concelhos / len(concelhos_data)) * 100 if concelhos_data else 0
        distrito_info["freguesia_coverage_percentage"] = (scraped_freguesias_total / distrito_info["total_freguesias"]) * 100 if distrito_info["total_freguesias"] else 0
        
        detailed_coverage["by_distrito"].append(distrito_info)
    
    # Update overview with calculated values
    detailed_coverage["overview"]["scraped_concelhos"] = sum(d["scraped_concelhos"] for d in detailed_coverage["by_distrito"])
    detailed_coverage["overview"]["scraped_freguesias"] = sum(d["scraped_freguesias"] for d in detailed_coverage["by_distrito"])
    
    return detailed_coverage

@api_router.post("/scrape/start")
async def start_scraping(background_tasks: BackgroundTasks):
    """Start a new scraping session"""
    session = ScrapingSession(status="running")
    session_dict = session.dict()
    await db.scraping_sessions.insert_one(session_dict)
    
    background_tasks.add_task(run_scraping_task, session.id)
    
    return {"message": "Scraping started", "session_id": session.id}

async def run_scraping_task(session_id: str):
    """Background task to run the scraping with full administrative structure"""
    try:
        # Update session status
        await db.scraping_sessions.update_one(
            {"id": session_id},
            {"$set": {"status": "running"}}
        )
        
        total_properties = 0
        districts_scraped = []
        
        # Initialize scraper with session ID
        scraper.session_id = session_id
        
        # Get the administrative structure from idealista.pt
        logger.info("Fetching Portuguese administrative structure...")
        structure = await scraper.get_administrative_structure()
        
        if not structure:
            logger.error("Could not obtain administrative structure")
            await db.scraping_sessions.update_one(
                {"id": session_id},
                {"$set": {
                    "status": "failed",
                    "completed_at": datetime.now(timezone.utc),
                    "error_message": "Could not obtain Portuguese administrative structure"
                }}
            )
            return
        
        logger.info(f"Starting comprehensive scraping of {len(structure)} districts")
        
        # Scrape all districts, concelhos, and freguesias
        for distrito, concelhos in structure.items():
            districts_scraped.append(distrito)
            logger.info(f"Scraping distrito: {distrito} ({len(concelhos)} concelhos)")
            
            for concelho, freguesias in concelhos.items():
                logger.info(f"Scraping concelho: {concelho} ({len(freguesias)} freguesias)")
                
                # Limit freguesias for demonstration (remove this limit for full scraping)
                limited_freguesias = freguesias[:3]  # Only first 3 freguesias per concelho
                
                for freguesia in limited_freguesias:
                    # Check if session is still running (not paused for CAPTCHA)
                    session_data = await db.scraping_sessions.find_one({"id": session_id})
                    if session_data and session_data.get('status') == 'waiting_captcha':
                        logger.info("Session paused for CAPTCHA, waiting...")
                        # Wait for CAPTCHA resolution
                        while True:
                            await asyncio.sleep(5)
                            session_data = await db.scraping_sessions.find_one({"id": session_id})
                            if session_data.get('status') != 'waiting_captcha':
                                break
                    
                    try:
                        logger.info(f"Processing: {distrito}/{concelho}/{freguesia}")
                        
                        # Scrape sales data for this administrative unit
                        sale_properties = await scraper.scrape_freguesia(distrito, concelho, freguesia, 'sale', session_id=session_id)
                        for prop_data in sale_properties:
                            property_obj = Property(**prop_data)
                            await db.properties.insert_one(property_obj.dict())
                            total_properties += 1
                        
                        # Scrape rental data for this administrative unit
                        rent_properties = await scraper.scrape_freguesia(distrito, concelho, freguesia, 'rent', session_id=session_id)
                        for prop_data in rent_properties:
                            property_obj = Property(**prop_data)
                            await db.properties.insert_one(property_obj.dict())
                            total_properties += 1
                        
                        # Small delay between freguesias to be respectful
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"Error scraping {distrito}/{concelho}/{freguesia}: {e}")
                        continue
                
                # Delay between concelhos
                await asyncio.sleep(1)
            
            # Delay between districts
            await asyncio.sleep(2)
            
            # Log progress
            logger.info(f"Completed distrito {distrito}. Total properties so far: {total_properties}")
        
        # Clean up driver
        scraper.close_driver()
        
        # Update session as completed
        await db.scraping_sessions.update_one(
            {"id": session_id},
            {"$set": {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc),
                "total_properties": total_properties,
                "regions_scraped": districts_scraped
            }}
        )
        
        logger.info(f"Administrative scraping completed: {total_properties} administrative units processed")
        
    except Exception as e:
        logger.error(f"Administrative scraping failed: {e}")
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

@api_router.get("/scraping-sessions/{session_id}")
async def get_scraping_session(session_id: str):
    """Get detailed information about a scraping session including errors"""
    session = await db.scraping_sessions.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Remove MongoDB ObjectId to avoid serialization issues
    if "_id" in session:
        del session["_id"]
    
    return session

@api_router.get("/scraping-sessions/{session_id}/errors")
async def get_scraping_errors(session_id: str):
    """Get detailed error information for a scraping session"""
    session = await db.scraping_sessions.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    failed_zones = session.get('failed_zones', [])
    success_zones = session.get('success_zones', [])
    
    # Process error statistics
    error_summary = {
        'total_zones_attempted': len(failed_zones) + len(success_zones),
        'failed_zones_count': len(failed_zones),
        'success_zones_count': len(success_zones),
        'failure_rate': len(failed_zones) / (len(failed_zones) + len(success_zones)) * 100 if (failed_zones or success_zones) else 0,
        'common_errors': {},
        'failed_zones': failed_zones,
        'success_zones': success_zones
    }
    
    # Count common error types
    for zone_error in failed_zones:
        for error in zone_error.get('errors', []):
            error_msg = error.get('error', 'Unknown error')
            if error_msg in error_summary['common_errors']:
                error_summary['common_errors'][error_msg] += 1
            else:
                error_summary['common_errors'][error_msg] = 1
    
    return error_summary

@api_router.post("/scrape/retry-failed")
async def retry_failed_zones(
    background_tasks: BackgroundTasks,
    session_id: str,
    zones: Optional[List[str]] = None  # Specific zones to retry, or all if None
):
    """Retry scraping for failed zones from a previous session"""
    
    # Get the original session
    original_session = await db.scraping_sessions.find_one({"id": session_id})
    if not original_session:
        raise HTTPException(status_code=404, detail="Original session not found")
    
    failed_zones = original_session.get('failed_zones', [])
    if not failed_zones:
        raise HTTPException(status_code=400, detail="No failed zones found in session")
    
    # Create new retry session
    retry_session = ScrapingSession(status="running")
    retry_session_dict = retry_session.dict()
    await db.scraping_sessions.insert_one(retry_session_dict)
    
    # Filter zones to retry
    zones_to_retry = []
    if zones:
        # Retry specific zones
        for zone_error in failed_zones:
            if zone_error['zone'] in zones:
                zones_to_retry.append(zone_error)
    else:
        # Retry all failed zones
        zones_to_retry = failed_zones
    
    # Start retry background task
    background_tasks.add_task(run_retry_scraping_task, retry_session.id, zones_to_retry)
    
    return {
        "message": f"Retry scraping started for {len(zones_to_retry)} failed zones",
        "retry_session_id": retry_session.id,
        "original_session_id": session_id,
        "zones_to_retry": [z['zone'] for z in zones_to_retry]
    }

async def run_retry_scraping_task(session_id: str, zones_to_retry: List[dict]):
    """Background task for retrying failed scraping zones"""
    try:
        await db.scraping_sessions.update_one(
            {"id": session_id},
            {"$set": {"status": "running"}}
        )
        
        total_properties = 0
        regions_scraped = []
        
        # Initialize scraper with session ID
        scraper.session_id = session_id
        
        logger.info(f"Starting retry scraping for {len(zones_to_retry)} zones...")
        
        for zone_info in zones_to_retry:
            zone_parts = zone_info['zone'].split('/')
            if len(zone_parts) != 3:
                logger.error(f"Invalid zone format: {zone_info['zone']}")
                continue
                
            distrito, concelho, freguesia = zone_parts
            operation_type = zone_info.get('operation_type', 'sale')
            
            try:
                logger.info(f"Retrying: {distrito}/{concelho}/{freguesia} ({operation_type})")
                
                # Scrape the zone
                properties = await scraper.scrape_freguesia(distrito, concelho, freguesia, operation_type, session_id=session_id)
                
                # Save properties to database
                for prop_data in properties:
                    property_obj = Property(**prop_data)
                    await db.properties.insert_one(property_obj.dict())
                    total_properties += 1
                
                regions_scraped.append(zone_info['zone'])
                
                # Delay between zones
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error retrying zone {zone_info['zone']}: {e}")
                continue
        
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
        
        logger.info(f"Retry scraping completed: {total_properties} properties from {len(regions_scraped)} zones")
        
    except Exception as e:
        logger.error(f"Retry scraping failed: {e}")
        scraper.close_driver()
        await db.scraping_sessions.update_one(
            {"id": session_id},
            {"$set": {
                "status": "failed",
                "completed_at": datetime.now(timezone.utc),
                "error_message": str(e)
            }}
        )

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
    """Get aggregated statistics by region with price per m² focus"""
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
    
    # Process results into RegionStats format focusing on price per m²
    stats_dict = {}
    for result in results:
        key = f"{result['_id']['region']}-{result['_id']['location']}"
        if key not in stats_dict:
            # Add display formatting
            display_info = format_administrative_display(result['_id']['region'], result['_id']['location'])
            
            stats_dict[key] = {
                'region': result['_id']['region'],
                'location': result['_id']['location'],
                'total_properties': 0,
                'avg_sale_price_per_sqm': None,  # Primary metric for sales
                'avg_rent_price_per_sqm': None,  # Primary metric for rentals
                'avg_sale_price': None,  # Keep for detailed stats
                'avg_rent_price': None,   # Keep for detailed stats
                'display_info': display_info
            }
        
        op_type = result['_id']['operation_type']
        stats_dict[key]['total_properties'] += result['count']
        
        if op_type == 'sale':
            stats_dict[key]['avg_sale_price_per_sqm'] = result['avg_price_per_sqm']  # €/m² for sales
            stats_dict[key]['avg_sale_price'] = result['avg_price']  # Keep for analytics
        else:
            stats_dict[key]['avg_rent_price_per_sqm'] = result['avg_price_per_sqm']  # €/m² for rentals
            stats_dict[key]['avg_rent_price'] = result['avg_price']  # Keep for analytics
    
    return [RegionStats(**stats) for stats in stats_dict.values()]

@api_router.get("/export/php")
async def export_php_format():
    """Export data in PHP array format with clean formatted names"""
    stats = await get_region_stats()
    
    php_array = {}
    for stat in stats:
        if not stat.display_info:
            continue
            
        distrito = stat.display_info['distrito']
        concelho = stat.display_info['concelho'] 
        freguesia = stat.display_info['freguesia']
        
        # Create distrito level if not exists
        if distrito not in php_array:
            php_array[distrito] = {
                'average': 0,  # Will be calculated as average of all freguesias
                'average_rent': 0,
                'freguesias': {}
            }
        
        # Create concelho level within distrito
        if concelho not in php_array[distrito]['freguesias']:
            php_array[distrito]['freguesias'][concelho] = {
                'name': concelho,
                'average': 0,  # Will be calculated as average of freguesias
                'average_rent': 0,
                'freguesias': {}
            }
        
        # Add freguesia level data
        if freguesia:
            php_array[distrito]['freguesias'][concelho]['freguesias'][freguesia] = {
                'name': freguesia,
                'average': stat.avg_sale_price_per_sqm or 0,  # €/m² for sales
                'average_rent': stat.avg_rent_price_per_sqm or 0  # €/m² for rentals
            }
    
    # Calculate averages for concelhos and distritos
    for distrito_name, distrito_data in php_array.items():
        distrito_sales = []
        distrito_rents = []
        
        for concelho_name, concelho_data in distrito_data['freguesias'].items():
            concelho_sales = []
            concelho_rents = []
            
            # Get all freguesia prices for this concelho
            for freguesia_name, freguesia_data in concelho_data['freguesias'].items():
                if freguesia_data['average'] > 0:
                    concelho_sales.append(freguesia_data['average'])
                if freguesia_data['average_rent'] > 0:
                    concelho_rents.append(freguesia_data['average_rent'])
            
            # Calculate concelho averages
            concelho_data['average'] = sum(concelho_sales) / len(concelho_sales) if concelho_sales else 0
            concelho_data['average_rent'] = sum(concelho_rents) / len(concelho_rents) if concelho_rents else 0
            
            # Add to distrito calculations
            if concelho_data['average'] > 0:
                distrito_sales.append(concelho_data['average'])
            if concelho_data['average_rent'] > 0:
                distrito_rents.append(concelho_data['average_rent'])
        
        # Calculate distrito averages
        distrito_data['average'] = sum(distrito_sales) / len(distrito_sales) if distrito_sales else 0
        distrito_data['average_rent'] = sum(distrito_rents) / len(distrito_rents) if distrito_rents else 0
    
    return {"php_array": php_array}

@api_router.get("/properties/filter")
async def get_properties_filtered(
    distrito: Optional[str] = None,
    concelho: Optional[str] = None,
    freguesia: Optional[str] = None,
    operation_type: Optional[str] = None,
    limit: int = 100
):
    """Get properties filtered by administrative levels"""
    filter_query = {}
    
    if distrito:
        filter_query["region"] = distrito.lower().replace(' ', '-')
    
    if operation_type:
        filter_query["operation_type"] = operation_type
    
    # Handle concelho and freguesia filtering
    if concelho or freguesia:
        location_patterns = []
        
        if concelho and freguesia:
            # Specific freguesia in specific concelho
            location_pattern = f"{concelho.lower().replace(' ', '-')}_{freguesia.lower().replace(' ', '-')}"
            location_patterns.append(location_pattern)
        elif concelho:
            # All freguesias in this concelho
            filter_query["location"] = {"$regex": f"^{concelho.lower().replace(' ', '-')}_"}
        
        if location_patterns:
            filter_query["location"] = {"$in": location_patterns}
    
    properties = await db.properties.find(filter_query).sort("scraped_at", -1).limit(limit).to_list(limit)
    
    # Add display formatting to each property
    formatted_properties = []
    for prop in properties:
        display_info = format_administrative_display(prop['region'], prop['location'])
        prop['display_info'] = display_info
        formatted_properties.append(Property(**prop))
    
    return formatted_properties

@api_router.get("/stats/detailed")
async def get_detailed_stats(
    distrito: Optional[str] = None,
    concelho: Optional[str] = None,
    freguesia: Optional[str] = None,
    operation_type: Optional[str] = None,
    property_type: Optional[str] = None
):
    """Get detailed statistics by property type and operation type"""
    
    # Build aggregation pipeline based on filters
    match_conditions = {}
    
    if distrito:
        match_conditions["region"] = distrito.lower().replace(' ', '-')
    
    if concelho or freguesia:
        if concelho and freguesia:
            location_pattern = f"{concelho.lower().replace(' ', '-')}_{freguesia.lower().replace(' ', '-')}"
            match_conditions["location"] = location_pattern
        elif concelho:
            match_conditions["location"] = {"$regex": f"^{concelho.lower().replace(' ', '-')}_"}
    
    if operation_type:
        match_conditions["operation_type"] = operation_type
        
    if property_type:
        match_conditions["property_type"] = property_type

    pipeline = [
        {"$match": match_conditions},
        {
            "$group": {
                "_id": {
                    "region": "$region", 
                    "location": "$location", 
                    "operation_type": "$operation_type",
                    "property_type": "$property_type"
                },
                "avg_price": {"$avg": "$price"},
                "avg_price_per_sqm": {"$avg": "$price_per_sqm"},
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id.region": 1, "_id.location": 1, "_id.operation_type": 1, "_id.property_type": 1}}
    ]
    
    results = await db.properties.aggregate(pipeline).to_list(1000)
    
    # Group results by location
    location_stats = {}
    for result in results:
        key = f"{result['_id']['region']}-{result['_id']['location']}"
        
        if key not in location_stats:
            display_info = format_administrative_display(result['_id']['region'], result['_id']['location'])
            location_stats[key] = ExtendedRegionStats(
                region=result['_id']['region'],
                location=result['_id']['location'],
                display_info=display_info,
                detailed_stats=[]
            )
        
        # Add detailed stat
        detailed_stat = DetailedPropertyStats(
            property_type=result['_id']['property_type'],
            operation_type=result['_id']['operation_type'],
            avg_price_per_sqm=result['avg_price_per_sqm'],
            avg_price=result['avg_price'],
            count=result['count']
        )
        location_stats[key].detailed_stats.append(detailed_stat)
        
        # Update general stats for backward compatibility
        location_stats[key].total_properties += result['count']
        
        if result['_id']['operation_type'] == 'sale' and result['avg_price_per_sqm']:
            if location_stats[key].avg_sale_price_per_sqm:
                location_stats[key].avg_sale_price_per_sqm = (location_stats[key].avg_sale_price_per_sqm + result['avg_price_per_sqm']) / 2
            else:
                location_stats[key].avg_sale_price_per_sqm = result['avg_price_per_sqm']
                
        if result['_id']['operation_type'] == 'rent' and result['avg_price_per_sqm']:
            if location_stats[key].avg_rent_price_per_sqm:
                location_stats[key].avg_rent_price_per_sqm = (location_stats[key].avg_rent_price_per_sqm + result['avg_price_per_sqm']) / 2
            else:
                location_stats[key].avg_rent_price_per_sqm = result['avg_price_per_sqm']
    
    return list(location_stats.values())

@api_router.get("/stats/filter")
async def get_stats_filtered(
    distrito: Optional[str] = None,
    concelho: Optional[str] = None,
    freguesia: Optional[str] = None
):
    """Get statistics filtered by administrative levels"""
    
    # Build aggregation pipeline based on filters
    match_conditions = {}
    
    if distrito:
        match_conditions["region"] = distrito.lower().replace(' ', '-')
    
    if concelho or freguesia:
        if concelho and freguesia:
            # Specific freguesia in specific concelho
            location_pattern = f"{concelho.lower().replace(' ', '-')}_{freguesia.lower().replace(' ', '-')}"
            match_conditions["location"] = location_pattern
        elif concelho:
            # All freguesias in this concelho
            match_conditions["location"] = {"$regex": f"^{concelho.lower().replace(' ', '-')}_"}
    
    pipeline = [
        {"$match": match_conditions},
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
            # Add display formatting
            display_info = format_administrative_display(result['_id']['region'], result['_id']['location'])
            
            stats_dict[key] = {
                'region': result['_id']['region'],
                'location': result['_id']['location'],
                'total_properties': 0,
                'avg_sale_price_per_sqm': None,
                'avg_rent_price_per_sqm': None,
                'avg_sale_price': None,
                'avg_rent_price': None,
                'display_info': display_info
            }
        
        op_type = result['_id']['operation_type']
        stats_dict[key]['total_properties'] += result['count']
        
        if op_type == 'sale':
            stats_dict[key]['avg_sale_price_per_sqm'] = result['avg_price_per_sqm']
            stats_dict[key]['avg_sale_price'] = result['avg_price']
        else:
            stats_dict[key]['avg_rent_price_per_sqm'] = result['avg_price_per_sqm'] 
            stats_dict[key]['avg_rent_price'] = result['avg_price']
    
    return [RegionStats(**stats) for stats in stats_dict.values()]

@api_router.get("/coverage/stats", response_model=CompleteCoverageReport)
async def get_coverage_stats():
    """Get comprehensive coverage statistics for all administrative levels"""
    
    # Get the administrative structure
    if not scraper.administrative_structure:
        await scraper.get_administrative_structure()
    
    structure = scraper.administrative_structure
    if not structure:
        raise HTTPException(status_code=500, detail="Could not obtain administrative structure")
    
    # Get all scraped data
    scraped_properties = await db.properties.find().to_list(10000)
    
    # Create sets of what we've scraped
    scraped_districts = set()
    scraped_municipalities = set()
    scraped_parishes = set()
    
    for prop in scraped_properties:
        distrito = prop['region']
        location_parts = prop['location'].split('_')
        if len(location_parts) == 2:
            concelho, freguesia = location_parts
            
            scraped_districts.add(distrito)
            scraped_municipalities.add(f"{distrito}_{concelho}")
            scraped_parishes.add(f"{distrito}_{concelho}_{freguesia}")
    
    # Calculate totals from structure
    total_districts = len(structure)
    total_municipalities = sum(len(concelhos) for concelhos in structure.values())
    total_parishes = sum(
        len(freguesias) 
        for concelhos in structure.values() 
        for freguesias in concelhos.values()
    )
    
    # Calculate coverage
    covered_districts = len(scraped_districts)
    covered_municipalities = len(scraped_municipalities)
    covered_parishes = len(scraped_parishes)
    
    overall_coverage = (covered_parishes / total_parishes * 100) if total_parishes > 0 else 0
    
    # Generate district-level coverage stats
    district_coverage = []
    
    for distrito, concelhos in structure.items():
        total_concelhos = len(concelhos)
        total_freguesias_district = sum(len(freguesias) for freguesias in concelhos.values())
        
        # Count what's scraped for this district
        scraped_concelhos_count = 0
        scraped_freguesias_count = 0
        missing_concelhos = []
        missing_freguesias = []
        
        for concelho, freguesias in concelhos.items():
            concelho_key = f"{distrito}_{concelho}"
            if concelho_key in scraped_municipalities:
                scraped_concelhos_count += 1
            else:
                missing_concelhos.append(concelho)
            
            for freguesia in freguesias:
                parish_key = f"{distrito}_{concelho}_{freguesia}"
                if parish_key in scraped_parishes:
                    scraped_freguesias_count += 1
                else:
                    missing_freguesias.append(f"{concelho}/{freguesia}")
        
        coverage_pct = (scraped_freguesias_count / total_freguesias_district * 100) if total_freguesias_district > 0 else 0
        
        district_coverage.append(CoverageStats(
            distrito=distrito,
            total_concelhos=total_concelhos,
            scraped_concelhos=scraped_concelhos_count,
            total_freguesias=total_freguesias_district,
            scraped_freguesias=scraped_freguesias_count,
            coverage_percentage=round(coverage_pct, 2),
            missing_concelhos=missing_concelhos,
            missing_freguesias=missing_freguesias[:20]  # Limit to first 20 missing
        ))
    
    return CompleteCoverageReport(
        total_districts=total_districts,
        covered_districts=covered_districts,
        total_municipalities=total_municipalities,
        covered_municipalities=covered_municipalities,
        total_parishes=total_parishes,
        covered_parishes=covered_parishes,
        overall_coverage_percentage=round(overall_coverage, 2),
        district_coverage=district_coverage
    )

@api_router.get("/coverage/missing/{distrito}")
async def get_missing_areas(distrito: str):
    """Get detailed list of missing concelhos and freguesias for a specific district"""
    
    if not scraper.administrative_structure:
        await scraper.get_administrative_structure()
    
    structure = scraper.administrative_structure
    if distrito not in structure:
        raise HTTPException(status_code=404, detail=f"District {distrito} not found")
    
    # Get scraped data for this district
    scraped_properties = await db.properties.find({"region": distrito}).to_list(10000)
    
    scraped_parishes = set()
    for prop in scraped_properties:
        location_parts = prop['location'].split('_')
        if len(location_parts) == 2:
            concelho, freguesia = location_parts
            scraped_parishes.add(f"{concelho}_{freguesia}")
    
    missing_areas = {}
    concelhos = structure[distrito]
    
    for concelho, freguesias in concelhos.items():
        missing_freguesias_in_concelho = []
        
        for freguesia in freguesias:
            key = f"{concelho}_{freguesia}"
            if key not in scraped_parishes:
                missing_freguesias_in_concelho.append(freguesia)
        
        if missing_freguesias_in_concelho:
            missing_areas[concelho] = missing_freguesias_in_concelho
    
    return {
        "distrito": distrito,
        "missing_areas": missing_areas,
        "total_missing_parishes": sum(len(freguesias) for freguesias in missing_areas.values()),
        "total_parishes_in_district": sum(len(freguesias) for freguesias in concelhos.values()),
        "coverage_percentage": round(
            ((sum(len(freguesias) for freguesias in concelhos.values()) - 
              sum(len(freguesias) for freguesias in missing_areas.values())) / 
             sum(len(freguesias) for freguesias in concelhos.values()) * 100), 2
        ) if sum(len(freguesias) for freguesias in concelhos.values()) > 0 else 0
    }

@api_router.post("/scrape/missing/{distrito}")
async def scrape_missing_areas(distrito: str, background_tasks: BackgroundTasks):
    """Start scraping only the missing areas for a specific district"""
    
    if not scraper.administrative_structure:
        await scraper.get_administrative_structure()
    
    structure = scraper.administrative_structure
    if distrito not in structure:
        raise HTTPException(status_code=404, detail=f"District {distrito} not found")
    
    # Get missing areas
    missing_data = await get_missing_areas(distrito)
    missing_areas = missing_data["missing_areas"]
    
    if not missing_areas:
        return {"message": f"No missing areas found for district {distrito}", "session_id": None}
    
    # Create scraping session
    session = ScrapingSession(status="running")
    session_dict = session.dict()
    await db.scraping_sessions.insert_one(session_dict)
    
    # Start background task for missing areas only
    background_tasks.add_task(run_missing_scraping_task, session.id, distrito, missing_areas)
    
    return {
        "message": f"Started scraping {sum(len(freguesias) for freguesias in missing_areas.values())} missing parishes in {distrito}", 
        "session_id": session.id,
        "missing_areas": missing_areas
    }

async def run_missing_scraping_task(session_id: str, distrito: str, missing_areas: dict):
    """Background task to scrape only missing areas"""
    try:
        await db.scraping_sessions.update_one(
            {"id": session_id},
            {"$set": {"status": "running"}}
        )
        
        total_properties = 0
        scraper.session_id = session_id
        
        logger.info(f"Starting missing area scraping for district: {distrito}")
        
        for concelho, freguesias in missing_areas.items():
            logger.info(f"Scraping missing freguesias in {concelho}: {freguesias}")
            
            for freguesia in freguesias:
                try:
                    # Check for CAPTCHA pause
                    session_data = await db.scraping_sessions.find_one({"id": session_id})
                    if session_data and session_data.get('status') == 'waiting_captcha':
                        while True:
                            await asyncio.sleep(5)
                            session_data = await db.scraping_sessions.find_one({"id": session_id})
                            if session_data.get('status') != 'waiting_captcha':
                                break
                    
                    logger.info(f"Processing missing: {distrito}/{concelho}/{freguesia}")
                    
                    # Scrape sales
                    sale_properties = await scraper.scrape_freguesia(distrito, concelho, freguesia, 'sale', session_id=session_id)
                    for prop_data in sale_properties:
                        property_obj = Property(**prop_data)
                        await db.properties.insert_one(property_obj.dict())
                        total_properties += 1
                    
                    # Scrape rentals
                    rent_properties = await scraper.scrape_freguesia(distrito, concelho, freguesia, 'rent', session_id=session_id)
                    for prop_data in rent_properties:
                        property_obj = Property(**prop_data)
                        await db.properties.insert_one(property_obj.dict())
                        total_properties += 1
                    
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error scraping missing {distrito}/{concelho}/{freguesia}: {e}")
                    continue
        
        scraper.close_driver()
        
        await db.scraping_sessions.update_one(
            {"id": session_id},
            {"$set": {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc),
                "total_properties": total_properties,
                "regions_scraped": [distrito]
            }}
        )
        
        logger.info(f"Missing area scraping completed for {distrito}: {total_properties} properties")
        
    except Exception as e:
        logger.error(f"Missing area scraping failed: {e}")
        scraper.close_driver()
        await db.scraping_sessions.update_one(
            {"id": session_id},
            {"$set": {
                "status": "failed",
                "completed_at": datetime.now(timezone.utc),
                "error_message": str(e)
            }}
        )

@api_router.get("/administrative/districts")
async def get_districts():
    """Get all available districts"""
    if not scraper.administrative_structure:
        await scraper.get_administrative_structure()
    
    districts = []
    for district_name in scraper.administrative_structure.keys():
        districts.append({
            'id': district_name,
            'name': district_name.replace('-', ' ').title(),
            'name_display': district_name.replace('-', ' ').title()
        })
    
    return {"districts": sorted(districts, key=lambda x: x['name'])}

@api_router.get("/administrative/districts/{district}/concelhos")
async def get_concelhos(district: str):
    """Get all concelhos for a specific district"""
    if not scraper.administrative_structure:
        await scraper.get_administrative_structure()
    
    if district not in scraper.administrative_structure:
        raise HTTPException(status_code=404, detail=f"District {district} not found")
    
    concelhos = []
    for concelho_name in scraper.administrative_structure[district].keys():
        concelhos.append({
            'id': concelho_name,
            'name': concelho_name.replace('-', ' ').title(),
            'name_display': concelho_name.replace('-', ' ').title()
        })
    
    return {
        "district": district.replace('-', ' ').title(),
        "concelhos": sorted(concelhos, key=lambda x: x['name'])
    }

@api_router.get("/administrative/districts/{district}/concelhos/{concelho}/freguesias")
async def get_freguesias(district: str, concelho: str):
    """Get all freguesias for a specific distrito/concelho"""
    if not scraper.administrative_structure:
        await scraper.get_administrative_structure()
    
    if district not in scraper.administrative_structure:
        raise HTTPException(status_code=404, detail=f"District {district} not found")
    
    if concelho not in scraper.administrative_structure[district]:
        raise HTTPException(status_code=404, detail=f"Concelho {concelho} not found in {district}")
    
    freguesias = []
    for freguesia_name in scraper.administrative_structure[district][concelho]:
        freguesias.append({
            'id': freguesia_name,
            'name': freguesia_name.replace('-', ' ').replace('_', ' ').title(),
            'name_display': format_freguesia_name(freguesia_name)
        })
    
    return {
        "district": district.replace('-', ' ').title(),
        "concelho": concelho.replace('-', ' ').title(), 
        "freguesias": sorted(freguesias, key=lambda x: x['name'])
    }

def format_freguesia_name(name):
    """Format freguesia name for display"""
    # Replace hyphens and underscores with spaces
    formatted = name.replace('-', ' ').replace('_', ' ')
    
    # Handle special cases for Portuguese names
    words = formatted.split()
    formatted_words = []
    
    for word in words:
        # Keep lowercase for Portuguese articles and prepositions
        if word.lower() in ['e', 'de', 'da', 'do', 'das', 'dos', 'a', 'o', 'as', 'os', 'em', 'na', 'no', 'nas', 'nos']:
            formatted_words.append(word.lower())
        else:
            formatted_words.append(word.capitalize())
    
    return ' '.join(formatted_words)

def format_administrative_display(region, location):
    """Format administrative location for display"""
    # Parse the location (formato: concelho_freguesia)
    if '_' in location:
        concelho, freguesia = location.split('_', 1)
        return {
            'distrito': region.replace('-', ' ').title(),
            'concelho': concelho.replace('-', ' ').title(),
            'freguesia': format_freguesia_name(freguesia),
            'full_display': f"{region.replace('-', ' ').title()} > {concelho.replace('-', ' ').title()} > {format_freguesia_name(freguesia)}"
        }
    else:
        return {
            'distrito': region.replace('-', ' ').title(),
            'concelho': location.replace('-', ' ').title(),
            'freguesia': '',
            'full_display': f"{region.replace('-', ' ').title()} > {location.replace('-', ' ').title()}"
        }

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