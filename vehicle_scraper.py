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
from bs4 import BeautifulSoup
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
                # First, debug what's actually on the page
                page_text = self.driver.page_source
                logger.info(f"MOT page contains: {len(page_text)} characters")
                
                # Check if page shows "No MOT History Available"
                if "No MOT History Available" in page_text or "No MOT test records" in page_text:
                    logger.info("Page explicitly shows no MOT history available")
                else:
                    logger.info("Page may contain MOT data, attempting extraction")
                    
                # Debug: Look for any MOT-related class names in the page
                soup = BeautifulSoup(page_text, 'html.parser')
                mot_elements = soup.find_all(class_=lambda x: x and 'mot' in x.lower())
                logger.info(f"Found {len(mot_elements)} elements with 'mot' in class name")
                for elem in mot_elements[:3]:  # Show first 3
                    logger.info(f"MOT element class: {elem.get('class')} - tag: {elem.name}")
                
                # Check for various MOT wrapper types (including new user-provided)
                wrapper_variants = [
                    'mot-history-wrapper-pass',
                    'mot-history-wrapper-fail', 
                    'mot-history-wrapper',
                    'mot-history-summary',  # User-provided summary
                    'mot-wrapper',
                    'mot-summary',
                    'history-wrapper',
                    'history-summary'
                ]
                
                for variant in wrapper_variants:
                    found = soup.find_all(class_=lambda x: x and variant in str(x).lower())
                    if found:
                        logger.info(f"Found {len(found)} elements with class containing '{variant}'")
                
                # Also check nth-child(6) specifically
                container_divs = soup.select("body > div.container > div")
                if len(container_divs) >= 6:
                    logger.info(f"Found container with {len(container_divs)} child divs, checking 6th child")
                    sixth_child = container_divs[5]  # 0-indexed
                    all_children = sixth_child.find_all()
                    logger.info(f"6th child div has {len(all_children)} total descendant elements")
                
                # Enhanced MOT extraction based on actual HTML structure
                # First, look for the specific structure we know exists
                mot_timeline_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.mot-history-timeline")
                
                if mot_timeline_elements:
                    logger.info(f"Found {len(mot_timeline_elements)} mot-history-timeline elements")
                    
                    for timeline_elem in mot_timeline_elements:
                        timeline_text = timeline_elem.text.strip()
                        logger.info(f"Timeline content preview: {timeline_text[:100]}")
                        
                        # Extract MOT test data from timeline
                        if timeline_text and len(timeline_text) > 20:
                            # Look for date patterns and results in timeline
                            if any(word in timeline_text.lower() for word in ['pass', 'fail', 'advisory', '20']):
                                logger.info(f"Found potential MOT data in timeline: {timeline_text[:150]}")
                                
                                # Extract dates and results
                                date_patterns = [
                                    r'\b(\d{2}/\d{2}/\d{4})\b',  # DD/MM/YYYY
                                    r'\b(\d{1,2}/\d{1,2}/\d{4})\b',  # D/M/YYYY
                                    r'\b(\d{1,2}\s+\w+\s+\d{4})\b'  # D Month YYYY
                                ]
                                
                                for pattern in date_patterns:
                                    date_matches = re.findall(pattern, timeline_text)
                                    if date_matches:
                                        for date_str in date_matches:
                                            # Find result for this date
                                            result = 'FAIL' if 'fail' in timeline_text.lower() else 'PASS'
                                            
                                            # Extract mileage if present
                                            mileage_patterns = [
                                                r'(\d{1,3}(?:,\d{3})*)\s*mile',
                                                r'(\d{1,6})\s*mile',
                                            ]
                                            
                                            mileage = None
                                            for mileage_pattern in mileage_patterns:
                                                mileage_match = re.search(mileage_pattern, timeline_text, re.IGNORECASE)
                                                if mileage_match:
                                                    mileage = int(mileage_match.group(1).replace(',', ''))
                                                    break
                                            
                                            mot_tests.append({
                                                'date': date_str,
                                                'result': result,
                                                'mileage': mileage,
                                                'raw_text': timeline_text[:200]
                                            })
                                            logger.info(f"Extracted MOT from timeline: {date_str} - {result} - {mileage} miles")
                                        break
                
                # Also try the specific selectors for backup
                backup_selectors = [
                    "div.mot-history-wrapper-pass div.mot-history-timeline",
                    "div.mot-history-wrapper-fail div.mot-history-timeline", 
                    ".total-tests",
                    "div.mot-history-summary",
                    "body > div.container > div:nth-child(6) *"
                ]
                
                # Continue with backup selectors if timeline didn't work
                for selector in backup_selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Backup selector '{selector}' found {len(elements)} elements")
                    
                    for element in elements:
                        try:
                            text = element.text.strip()
                            if text and len(text) > 10:  # Only check substantial text
                                # Look for date patterns and MOT-related keywords
                                if any(word in text.lower() for word in ['pass', 'fail', 'advisory', 'mot', '202', '201']):
                                    logger.info(f"Found potential MOT text: {text[:100]}")
                                    
                                    # Extract date pattern (DD/MM/YYYY or similar)
                                    date_patterns = [
                                        r'\b(\d{2}/\d{2}/\d{4})\b',  # DD/MM/YYYY
                                        r'\b(\d{1,2}/\d{1,2}/\d{4})\b',  # D/M/YYYY
                                        r'\b(\d{4}-\d{2}-\d{2})\b',  # YYYY-MM-DD
                                        r'\b(\d{1,2}\s+\w+\s+\d{4})\b'  # D Month YYYY
                                    ]
                                    
                                    for pattern in date_patterns:
                                        date_match = re.search(pattern, text)
                                        if date_match:
                                            test_date = date_match.group(1)
                                            
                                            # Determine result
                                            result = 'FAIL' if 'fail' in text.lower() else 'PASS'
                                            
                                            # Extract mileage if present  
                                            mileage_patterns = [
                                                r'(\d{1,3}(?:,\d{3})*)\s*mile',
                                                r'(\d{1,6})\s*mile',
                                                r'mileage[:\s]*(\d{1,3}(?:,\d{3})*)',
                                            ]
                                            
                                            mileage = None
                                            for mileage_pattern in mileage_patterns:
                                                mileage_match = re.search(mileage_pattern, text, re.IGNORECASE)
                                                if mileage_match:
                                                    mileage = int(mileage_match.group(1).replace(',', ''))
                                                    break
                                            
                                            mot_tests.append({
                                                'date': test_date,
                                                'result': result,
                                                'mileage': mileage,
                                                'raw_text': text[:100]  # Keep first 100 chars for reference
                                            })
                                            logger.info(f"Extracted MOT test: {test_date} - {result}")
                                            break  # Found date, move to next element
                        except Exception as e:
                            logger.debug(f"Error processing element: {e}")
                            continue
                
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
                # First, debug what's actually on the page
                page_text = self.driver.page_source
                logger.info(f"Mileage page contains: {len(page_text)} characters")
                
                # Check if page shows "No Mileage Analysis Available"
                if "No Mileage Analysis Available" in page_text or "No mileage data" in page_text:
                    logger.info("Page explicitly shows no mileage data available")
                else:
                    logger.info("Page may contain mileage data, attempting extraction")
                
                # Try comprehensive selectors for mileage data
                mileage_selectors = [
                    "table tr",
                    ".mileage-reading", 
                    ".reading",
                    ".mileage-history-item",
                    ".history-item",
                    "div[class*='mileage']",
                    "div[class*='reading']", 
                    "*[class*='history']",
                    "tbody tr",
                    ".row"
                ]
                
                all_elements = []
                for selector in mileage_selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    all_elements.extend(elements)
                    logger.info(f"Mileage selector '{selector}' found {len(elements)} elements")
                
                logger.info(f"Total mileage elements to scan: {len(all_elements)}")
                
                for element in all_elements:
                    try:
                        text = element.text.strip()
                        if text and len(text) > 5:  # Only check substantial text
                            # Look for mileage patterns: numbers followed by miles/km
                            mileage_patterns = [
                                r'(\d{1,3}(?:,\d{3})*)\s*mile',
                                r'(\d{1,6})\s*mile',
                                r'mileage[:\s]*(\d{1,3}(?:,\d{3})*)',
                            ]
                            
                            # Look for date patterns
                            date_patterns = [
                                r'\b(\d{2}/\d{2}/\d{4})\b',  # DD/MM/YYYY
                                r'\b(\d{1,2}/\d{1,2}/\d{4})\b',  # D/M/YYYY
                                r'\b(\d{1,2}\s+\w+\s+\d{4})\b'  # D Month YYYY
                            ]
                            
                            mileage_match = None
                            for pattern in mileage_patterns:
                                mileage_match = re.search(pattern, text, re.IGNORECASE)
                                if mileage_match:
                                    break
                            
                            date_match = None
                            for pattern in date_patterns:
                                date_match = re.search(pattern, text)
                                if date_match:
                                    break
                            
                            if mileage_match and date_match:
                                mileage = int(mileage_match.group(1).replace(',', ''))
                                date = date_match.group(1)
                                
                                mileage_readings.append({
                                    'date': date,
                                    'mileage': mileage,
                                    'source': 'MOT_test_record'
                                })
                                logger.info(f"Extracted mileage reading: {date} - {mileage} miles")
                            elif mileage_match:
                                logger.info(f"Found mileage without date: {text[:50]}")
                            elif any(word in text.lower() for word in ['mile', 'mileage']):
                                logger.info(f"Found mileage-related text: {text[:50]}")
                    except Exception as e:
                        logger.debug(f"Error processing mileage element: {e}")
                        continue
                
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
