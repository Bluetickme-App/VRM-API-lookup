"""
Enhanced Cloudflare bypass scraper using undetected-chromedriver
Specifically designed to bypass Cloudflare protection for vehicle data extraction
"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import logging
import re
from data_extractor import DataExtractor

logger = logging.getLogger(__name__)

class CloudflareBypassScraper:
    """Advanced scraper with Cloudflare bypass capabilities"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.data_extractor = DataExtractor()
        
    def _setup_driver(self):
        """Initialize undetected Chrome driver for Cloudflare bypass"""
        try:
            options = uc.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = uc.Chrome(options=options, version_main=None)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 30)
            logger.info("Undetected Chrome driver initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize undetected Chrome driver: {e}")
            raise
    
    def scrape_vehicle_data(self, registration):
        """Main scraping method with advanced Cloudflare bypass"""
        try:
            self._setup_driver()
            
            # Multi-step bypass strategy
            logger.info("Starting advanced Cloudflare bypass...")
            
            # Step 1: Visit main site first
            self.driver.get("https://www.checkcardetails.co.uk/")
            time.sleep(5)  # Allow initial load
            
            # Step 2: Navigate to vehicle page
            direct_url = f"https://www.checkcardetails.co.uk/cardetails/{registration.lower()}"
            self.driver.get(direct_url)
            logger.info(f"Navigated to: {direct_url}")
            
            # Step 3: Wait for Cloudflare bypass
            max_wait = 45
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                page_title = self.driver.title.lower()
                page_source = self.driver.page_source.lower()
                
                if ("just a moment" not in page_title and 
                    "cloudflare" not in page_source and
                    len(page_source) > 5000):
                    logger.info("Cloudflare bypass successful!")
                    break
                    
                logger.info("Waiting for Cloudflare bypass...")
                time.sleep(3)
            
            # Extract vehicle data
            vehicle_data = self.data_extractor.extract_all_data(self.driver)
            
            if vehicle_data:
                logger.info(f"Successfully extracted data for {registration}")
                return vehicle_data
            else:
                logger.warning(f"No data extracted for {registration}")
                return None
                
        except Exception as e:
            logger.error(f"Error in Cloudflare bypass scraper: {e}")
            return None
            
        finally:
            if self.driver:
                self.driver.quit()