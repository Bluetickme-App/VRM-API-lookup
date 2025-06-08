"""
Vehicle data scraper for checkcardetails.co.uk
Uses Selenium WebDriver to extract comprehensive vehicle information
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.firefox import GeckoDriverManager
from data_extractor import DataExtractor
from config import SCRAPER_CONFIG
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VehicleScraper:
    """Main scraper class for vehicle data extraction"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.data_extractor = DataExtractor()
        
    def _setup_driver(self):
        """Initialize Firefox WebDriver with appropriate options"""
        try:
            firefox_options = Options()
            firefox_options.add_argument('--headless')  # Run in background
            firefox_options.add_argument('--no-sandbox')
            firefox_options.add_argument('--disable-dev-shm-usage')
            firefox_options.add_argument('--disable-gpu')
            firefox_options.add_argument('--window-size=1920,1080')
            firefox_options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0")
            
            # Use webdriver-manager to automatically manage GeckoDriver
            service = Service(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=firefox_options)
            self.wait = WebDriverWait(self.driver, SCRAPER_CONFIG['timeout'])
            logger.info("WebDriver initialized successfully")
            
        except WebDriverException as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise
    
    def _navigate_to_search(self, registration):
        """Navigate to the search page and perform vehicle lookup"""
        try:
            # Navigate to main page
            self.driver.get(SCRAPER_CONFIG['base_url'])
            logger.info(f"Navigated to {SCRAPER_CONFIG['base_url']}")
            
            # Wait for and find the search input
            search_input = self.wait.until(
                EC.presence_of_element_located((By.ID, "vrm"))
            )
            
            # Clear and enter registration
            search_input.clear()
            search_input.send_keys(registration)
            logger.info(f"Entered registration: {registration}")
            
            # Find and click search button
            search_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            search_button.click()
            
            # Wait for results page to load
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".vehicle-details, .car-details, h1, h2"))
            )
            
            logger.info("Search completed successfully")
            return True
            
        except TimeoutException:
            logger.error("Timeout waiting for search elements")
            return False
        except NoSuchElementException as e:
            logger.error(f"Search element not found: {e}")
            return False
    
    def scrape_vehicle_data(self, registration):
        """Main method to scrape vehicle data"""
        try:
            self._setup_driver()
            
            # Navigate and search
            if not self._navigate_to_search(registration):
                return None
            
            # Wait a bit for page to fully load
            time.sleep(2)
            
            # Extract all vehicle data
            vehicle_data = self.data_extractor.extract_all_data(self.driver)
            
            if vehicle_data:
                logger.info(f"Successfully extracted data for {registration}")
                return vehicle_data
            else:
                logger.warning(f"No data extracted for {registration}")
                return None
                
        except Exception as e:
            logger.error(f"Error scraping vehicle data: {e}")
            return None
            
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Clean up WebDriver resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")
