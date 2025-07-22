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
        """Navigate directly to vehicle-specific URL"""
        try:
            # Navigate directly to vehicle details page - this works reliably
            direct_url = f"https://www.checkcardetails.co.uk/cardetails/{registration.lower()}"
            self.driver.get(direct_url)
            logger.info(f"Navigated directly to: {direct_url}")
            
            # Wait for vehicle details page to load
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
            
            logger.info("Vehicle page loaded successfully")
            return True
            
        except TimeoutException:
            logger.error("Timeout waiting for vehicle page to load")
            return False
        except Exception as e:
            logger.error(f"Error navigating to vehicle page: {e}")
            return False
    
    def scrape_vehicle_data(self, registration):
        """Main method to scrape vehicle data with MOT and mileage history"""
        try:
            self._setup_driver()
            
            # Navigate and search for basic data
            if not self._navigate_to_search(registration):
                return None
            
            # Wait a bit for page to fully load
            time.sleep(2)
            
            # Debug: Save page source to see what we're working with
            page_source = self.driver.page_source
            logger.info(f"Page title: {self.driver.title}")
            
            # Look for Ferrari in page source  
            if "Ferrari" in page_source:
                logger.info("Ferrari found in page source - data extraction should work")
            else:
                logger.warning("Ferrari not found in page source - may need different extraction approach")
            
            # Extract basic vehicle data using the working extractor
            vehicle_data = self.data_extractor.extract_all_data(self.driver)
            
            # Debug: Log what we extracted
            if vehicle_data:
                basic_info = vehicle_data.get('basic_info', {})
                vehicle_details = vehicle_data.get('vehicle_details', {})
                logger.info(f"Basic info extracted: {basic_info}")
                logger.info(f"Vehicle details extracted: {vehicle_details}")
            
            if vehicle_data:
                logger.info(f"Successfully extracted basic data for {registration}")
                
                # Now add MOT history - navigate directly to MOT page
                self._add_mot_history(registration, vehicle_data)
                
                # Add mileage history 
                self._add_mileage_history(registration, vehicle_data)
                
                return vehicle_data
            else:
                logger.warning(f"No basic data extracted for {registration}")
                return None
                
        except Exception as e:
            logger.error(f"Error scraping vehicle data: {e}")
            return None
            
        finally:
            self._cleanup()
    
    def _add_mot_history(self, registration, vehicle_data):
        """Add MOT history to existing vehicle data"""
        try:
            # Navigate directly to MOT history page
            mot_url = f"https://www.checkcardetails.co.uk/cardetails/{registration.lower()}/mot-history"
            logger.info(f"Getting MOT history from: {mot_url}")
            
            self.driver.get(mot_url)
            time.sleep(3)
            
            # Extract MOT tests
            mot_tests = []
            
            # Look for MOT test rows in the page
            try:
                # Try different selectors for MOT history tables
                test_rows = self.driver.find_elements(By.CSS_SELECTOR, "table tr, .mot-test, .test-result")
                
                for row in test_rows:
                    text = row.text.strip()
                    if text and any(word in text.lower() for word in ['pass', 'fail', 'advisory', '20']):
                        # Extract date pattern (DD/MM/YYYY)
                        date_match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', text)
                        
                        if date_match:
                            test_date = date_match.group(1)
                            
                            # Determine result
                            result = 'FAIL' if 'fail' in text.lower() else 'PASS'
                            
                            # Extract mileage if present  
                            mileage_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*mile', text, re.IGNORECASE)
                            mileage = int(mileage_match.group(1).replace(',', '')) if mileage_match else None
                            
                            mot_tests.append({
                                'date': test_date,
                                'result': result,
                                'mileage': mileage,
                                'raw_text': text[:100]  # Keep first 100 chars for reference
                            })
                
                if mot_tests:
                    vehicle_data['mot_history'] = {
                        'tests': mot_tests,
                        'total_tests': len(mot_tests)
                    }
                    logger.info(f"Extracted {len(mot_tests)} MOT tests")
                else:
                    logger.info("No MOT tests found")
                    
            except Exception as e:
                logger.error(f"Error extracting MOT tests: {e}")
                
        except Exception as e:
            logger.error(f"Error getting MOT history: {e}")
    
    def _add_mileage_history(self, registration, vehicle_data):
        """Add mileage history to existing vehicle data"""
        try:
            # Navigate directly to mileage history page  
            mileage_url = f"https://www.checkcardetails.co.uk/cardetails/{registration.lower()}/mileage-history"
            logger.info(f"Getting mileage history from: {mileage_url}")
            
            self.driver.get(mileage_url)
            time.sleep(3)
            
            # Extract mileage readings
            mileage_readings = []
            
            try:
                # Look for mileage data in various formats
                elements = self.driver.find_elements(By.CSS_SELECTOR, "table tr, .mileage-reading, .reading")
                
                for element in elements:
                    text = element.text.strip()
                    
                    # Look for mileage patterns: numbers followed by miles/km
                    mileage_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*mile', text, re.IGNORECASE)
                    date_match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', text)
                    
                    if mileage_match and date_match:
                        mileage = int(mileage_match.group(1).replace(',', ''))
                        date = date_match.group(1)
                        
                        mileage_readings.append({
                            'date': date,
                            'mileage': mileage,
                            'source': 'MOT_test_record'
                        })
                
                if mileage_readings:
                    # Sort by date (convert to proper date format for sorting)
                    mileage_readings.sort(key=lambda x: datetime.strptime(x['date'], '%d/%m/%Y'))
                    
                    vehicle_data['mileage_history'] = {
                        'readings': mileage_readings,
                        'total_readings': len(mileage_readings),
                        'latest_mileage': mileage_readings[-1]['mileage'] if mileage_readings else None
                    }
                    logger.info(f"Extracted {len(mileage_readings)} mileage readings")
                else:
                    logger.info("No mileage readings found")
                    
            except Exception as e:
                logger.error(f"Error extracting mileage readings: {e}")
                
        except Exception as e:
            logger.error(f"Error getting mileage history: {e}")
    
    def _cleanup(self):
        """Clean up WebDriver resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")
