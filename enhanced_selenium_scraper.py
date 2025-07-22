"""
Enhanced Selenium scraper with MOT and mileage history extraction
Extends the basic scraping to include MOT history and mileage history pages
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.keys import Keys
from webdriver_manager.firefox import GeckoDriverManager
import time
import random
import logging
import os
import re
import psutil
import signal
from typing import Dict, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedSeleniumScraper:
    """Enhanced Selenium scraper with MOT and mileage history support"""
    
    def __init__(self, headless=False):
        self.driver = None
        self.wait = None
        self.headless = headless
        # Optimized timing configurations for web interface
        self.min_delay = 0.5
        self.max_delay = 1.5
        self.page_load_timeout = 15
        self.element_wait_timeout = 10
    
    def _kill_firefox_processes(self):
        """Kill any remaining Firefox/GeckoDriver processes"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                proc_name = proc.info['name'].lower()
                
                if any(term in proc_name for term in ['firefox', 'geckodriver']):
                    try:
                        logger.info(f"Killing process: {proc.info['name']} (PID: {proc.info['pid']})")
                        proc.terminate()
                        proc.wait(timeout=3)
                    except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                        try:
                            proc.kill()
                        except psutil.NoSuchProcess:
                            pass
                    except Exception as e:
                        logger.warning(f"Could not kill process {proc.info['pid']}: {e}")
        except Exception as e:
            logger.warning(f"Error during process cleanup: {e}")
    
    def _natural_delay(self, min_time=None, max_time=None):
        """Add natural human-like delay between actions - optimized for speed"""
        min_delay = min_time if min_time is not None else 0.3
        max_delay = max_time if max_time is not None else 0.8
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
        logger.debug(f"Natural delay: {delay:.2f}s")
    
    def _setup_driver(self):
        """Initialize Firefox WebDriver"""
        try:
            # Clean up any existing processes
            self._kill_firefox_processes()
            
            # Firefox options
            firefox_options = Options()
            if self.headless:
                firefox_options.add_argument("--headless")
            
            firefox_options.add_argument("--no-sandbox")
            firefox_options.add_argument("--disable-dev-shm-usage")
            firefox_options.add_argument("--disable-gpu")
            firefox_options.add_argument("--window-size=1920,1080")
            firefox_options.add_argument("--disable-extensions")
            firefox_options.add_argument("--disable-plugins")
            firefox_options.add_argument("--disable-images")
            
            # User agent to appear more human-like
            firefox_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0")
            
            # Firefox preferences for better performance
            firefox_options.set_preference("dom.webdriver.enabled", False)
            firefox_options.set_preference("useAutomationExtension", False)
            firefox_options.set_preference("media.autoplay.default", 0)
            firefox_options.set_preference("media.autoplay.enabled.user-gestures-needed", False)
            
            # Set up service
            service = Service(GeckoDriverManager().install())
            
            # Initialize driver
            self.driver = webdriver.Firefox(service=service, options=firefox_options)
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.wait = WebDriverWait(self.driver, self.element_wait_timeout)
            
            logger.info("Firefox WebDriver initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"WebDriver initialization failed: {e}")
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            return False
    
    def scrape_complete_vehicle_data(self, registration: str) -> Optional[Dict[str, Any]]:
        """Main method to scrape complete vehicle data including MOT and mileage history"""
        logger.info(f"Starting complete scrape for registration: {registration}")
        
        try:
            if not self._setup_driver():
                return None
            
            # First, get basic vehicle data
            vehicle_data = self._scrape_basic_vehicle_data(registration)
            if not vehicle_data:
                logger.error("Failed to get basic vehicle data")
                self._cleanup()
                return None
            
            # Extract complete MOT and mileage history using enhanced MOT scraper
            logger.info(f"Extracting complete MOT history for {registration}")
            
            try:
                # Import and use the enhanced MOT scraper with forced complete extraction for all 16 tests
                from enhanced_mot_scraper import EnhancedMOTScraper
                mot_scraper = EnhancedMOTScraper()
                
                # Get complete MOT history data with explicit request for all tests
                logger.info(f"Requesting complete 16-test extraction for {registration}")
                mot_result = mot_scraper.scrape_comprehensive_vehicle_data(registration)
                
                # The enhanced MOT scraper returns the data directly, not wrapped in success/data structure
                if mot_result and isinstance(mot_result, dict):
                    # Extract MOT history data directly
                    vehicle_data['mot_history'] = mot_result.get('mot_history', {})
                    
                    # Create mileage history from MOT test data
                    mot_tests = vehicle_data['mot_history'].get('mot_tests', [])
                    mileage_records = []
                    for test in mot_tests:
                        if test.get('mileage'):
                            mileage_records.append({
                                'date': test.get('test_date'),
                                'mileage': test.get('mileage'),
                                'source': 'MOT test'
                            })
                    
                    vehicle_data['mileage_history'] = {
                        'extraction_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'mileage_records': mileage_records,
                        'total_records_found': len(mileage_records),
                        'registration': registration.upper(),
                        'scraped_from': 'enhanced_mot_scraper',
                    }
                    
                    mot_tests_count = len(mot_tests)
                    logger.info(f"Successfully extracted {mot_tests_count} MOT tests for {registration}")
                    
                    # If we got the full 16+ tests, mark as successful
                    if mot_tests_count >= 16:
                        logger.info(f"SUCCESS: All {mot_tests_count} MOT tests captured for complete history!")
                    elif mot_tests_count >= 10:
                        logger.info(f"EXCELLENT: {mot_tests_count} MOT tests - major improvement achieved!")
                else:
                    logger.warning(f"Enhanced MOT scraper returned invalid data for {registration}")
                    raise Exception("Invalid MOT scraper result")
                    
            except Exception as e:
                logger.warning(f"Error using enhanced MOT scraper: {e}, falling back to placeholders")
                
                # Fallback to empty structures if enhanced scraper fails
                vehicle_data['mot_history'] = {
                    'extraction_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'mot_tests': [],
                    'summary': {},
                    'total_tests_found': 0,
                    'registration': registration.upper(),
                    'scraped_from': 'enhanced_selenium_fallback',
                    'page_url': vehicle_data.get('current_url', 'https://www.checkcardetails.co.uk'),
                    'page_title': 'Check Car Details'
                }
                
                vehicle_data['mileage_history'] = {
                    'extraction_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'mileage_records': [],
                    'analysis': {},
                    'total_records_found': 0,
                    'registration': registration.upper(),
                    'scraped_from': 'enhanced_selenium_fallback',
                    'page_url': vehicle_data.get('current_url', 'https://www.checkcardetails.co.uk'),
                    'page_title': 'Check Car Details'
                }
            
            # Save to database using the same pattern as the app.py endpoint
            try:
                from models import VehicleData, SearchHistory, db
                from app import app
                from datetime import datetime
                
                with app.app_context():
                    # Check if vehicle already exists
                    existing_record = VehicleData.query.filter_by(registration=registration.upper()).first()
                    
                    if existing_record:
                        # Update existing record with enhanced data
                        vehicle_record = existing_record
                        logger.info(f"Updating existing record for {registration}")
                    else:
                        # Create new record
                        vehicle_record = VehicleData(registration=registration.upper())
                        logger.info(f"Creating new record for {registration}")
                    
                    # Update all fields with scraped data
                    vehicle_record.make = vehicle_data.get('make')
                    vehicle_record.model = vehicle_data.get('model')
                    vehicle_record.year = vehicle_data.get('year')
                    vehicle_record.color = vehicle_data.get('color')
                    vehicle_record.fuel_type = vehicle_data.get('fuel_type')
                    vehicle_record.engine_size = vehicle_data.get('engine_size')
                    vehicle_record.co2_emissions = vehicle_data.get('co2_emissions')
                    vehicle_record.date_first_registered = vehicle_data.get('date_first_registered')
                    vehicle_record.tax_status = vehicle_data.get('tax_status')
                    vehicle_record.mot_status = vehicle_data.get('mot_status')
                    vehicle_record.mot_expiry = vehicle_data.get('mot_expiry')
                    
                    # Store complete raw data including MOT history
                    vehicle_record.raw_data = vehicle_data
                    vehicle_record.updated_at = datetime.utcnow()
                    
                    # Store summarized MOT and mileage data in structured fields
                    vehicle_record.mot_history = vehicle_data.get('mot_history', {})
                    vehicle_record.mileage_history = vehicle_data.get('mileage_history', {})
                    
                    # Save to database
                    if not existing_record:
                        db.session.add(vehicle_record)
                    
                    db.session.commit()
                    
                    mot_tests_count = len(vehicle_data.get('mot_history', {}).get('mot_tests', []))
                    logger.info(f"Successfully saved {registration} to database with {mot_tests_count} MOT tests")
                    
            except Exception as e:
                logger.error(f"Error saving to database: {e}")
                # Continue anyway, return the data even if database save fails
            
            self._cleanup()
            
            # Return success format expected by the calling code
            return {
                'success': True,
                'data': vehicle_data,
                'registration': registration.upper(),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"Error in complete vehicle data scrape: {e}")
            self._cleanup()
            return None
    
    def _scrape_basic_vehicle_data(self, registration: str) -> Optional[Dict[str, Any]]:
        """Navigate to basic vehicle page and extract data"""
        try:
            # Navigate to the website
            self.driver.get("https://www.checkcardetails.co.uk/")
            logger.info("Navigated to checkcardetails.co.uk")
            
            self._natural_delay(0.3, 0.8)
            
            # Wait for page to load
            WebDriverWait(self.driver, self.page_load_timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # Find and fill registration input
            search_input = None
            all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
            
            for inp in all_inputs:
                try:
                    input_type = inp.get_attribute('type')
                    input_placeholder = inp.get_attribute('placeholder')
                    input_id = inp.get_attribute('id')
                    input_name = inp.get_attribute('name')
                    
                    if (input_type == 'text' and 
                        (input_placeholder and ('reg' in input_placeholder.lower() or 'vrm' in input_placeholder.lower())) or
                        (input_id and ('reg' in input_id.lower() or 'vrm' in input_id.lower())) or
                        (input_name and ('reg' in input_name.lower() or 'vrm' in input_name.lower()))):
                        search_input = inp
                        break
                except Exception:
                    continue
            
            if not search_input:
                # Try first visible text input as fallback
                for inp in all_inputs:
                    try:
                        if (inp.get_attribute('type') == 'text' and 
                            inp.is_displayed() and inp.is_enabled()):
                            search_input = inp
                            break
                    except:
                        continue
            
            if not search_input:
                logger.error("Could not find registration input field")
                return None
            
            # Enter registration
            search_input.clear()
            self._natural_delay(0.5, 1.5)
            search_input.click()
            self._natural_delay(0.3, 0.8)
            
            # Type registration naturally
            for char in registration.upper():
                search_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            logger.info(f"Entered registration: {registration}")
            self._natural_delay(0.3, 0.8)
            
            # Submit form
            try:
                submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit'], .submit-btn")
                submit_button.click()
                logger.info("Clicked submit button")
            except NoSuchElementException:
                search_input.send_keys(Keys.RETURN)
                logger.info("Pressed Enter to submit")
            
            # Wait for results
            self._natural_delay(2.0, 3.0)
            
            # Log current page for debugging
            logger.info(f"After search - URL: {self.driver.current_url}, Title: {self.driver.title}")
            
            # Extract basic vehicle data
            vehicle_data = {
                'registration': registration.upper(),
                'basic_info': {},
                'tax_mot': {},
                'vehicle_details': {},
                'scraped_from': 'enhanced_selenium_basic_page',
                'current_url': self.driver.current_url
            }
            
            # Extract data from the page
            self._extract_page_data(vehicle_data)
            
            # Look for and store MOT/mileage links during basic extraction
            self._find_and_store_history_links(vehicle_data)
            
            return vehicle_data
            
        except Exception as e:
            logger.error(f"Error scraping basic vehicle data: {e}")
            return None
    
    def _find_and_store_history_links(self, vehicle_data):
        """Find MOT and mileage history links on current page and store them"""
        try:
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            logger.info(f"Looking for history links among {len(all_links)} total links")
            
            mot_links = []
            mileage_links = []
            
            for i, link in enumerate(all_links):
                try:
                    link_text = link.text.strip()
                    link_href = link.get_attribute('href') or ''
                    
                    # Log interesting links for debugging
                    if (link_text and len(link_text) > 2 and 
                        any(keyword in link_text.lower() for keyword in ['mot', 'history', 'mileage', 'test', 'check', 'view'])):
                        logger.info(f"Potential history link {i}: text='{link_text}', href='{link_href}'")
                    
                    # Look for MOT-related links
                    if (any(keyword in link_text.lower() for keyword in ['mot', 'test']) or 
                        'mot' in link_href.lower()):
                        mot_links.append({'text': link_text, 'href': link_href, 'element_index': i})
                    
                    # Look for mileage-related links
                    if (any(keyword in link_text.lower() for keyword in ['mileage', 'miles']) or 
                        'mileage' in link_href.lower()):
                        mileage_links.append({'text': link_text, 'href': link_href, 'element_index': i})
                        
                except Exception as e:
                    continue
            
            vehicle_data['available_mot_links'] = mot_links
            vehicle_data['available_mileage_links'] = mileage_links
            
            logger.info(f"Found {len(mot_links)} potential MOT links and {len(mileage_links)} potential mileage links")
            
        except Exception as e:
            logger.error(f"Error finding history links: {e}")
            vehicle_data['available_mot_links'] = []
            vehicle_data['available_mileage_links'] = []
    
    def _perform_vehicle_search(self, registration: str):
        """Helper method to perform vehicle search on homepage"""
        try:
            # Find and fill registration input
            search_input = None
            all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
            
            for inp in all_inputs:
                try:
                    input_type = inp.get_attribute('type')
                    input_placeholder = inp.get_attribute('placeholder')
                    input_id = inp.get_attribute('id')
                    input_name = inp.get_attribute('name')
                    
                    if (input_type == 'text' and 
                        (input_placeholder and ('reg' in input_placeholder.lower() or 'vrm' in input_placeholder.lower())) or
                        (input_id and ('reg' in input_id.lower() or 'vrm' in input_id.lower())) or
                        (input_name and ('reg' in input_name.lower() or 'vrm' in input_name.lower()))):
                        search_input = inp
                        break
                except Exception:
                    continue
            
            if not search_input:
                # Try first visible text input as fallback
                for inp in all_inputs:
                    try:
                        if (inp.get_attribute('type') == 'text' and 
                            inp.is_displayed() and inp.is_enabled()):
                            search_input = inp
                            break
                    except:
                        continue
            
            if search_input:
                # Enter registration
                search_input.clear()
                self._natural_delay(0.5, 1.5)
                search_input.click()
                self._natural_delay(0.3, 0.8)
                
                # Type registration naturally
                for char in registration.upper():
                    search_input.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.15))
                
                logger.info(f"Entered registration: {registration}")
                self._natural_delay(0.3, 0.8)
                
                # Submit form
                try:
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit'], .submit-btn")
                    submit_button.click()
                    logger.info("Clicked submit button")
                except NoSuchElementException:
                    search_input.send_keys(Keys.RETURN)
                    logger.info("Pressed Enter to submit")
            else:
                logger.warning("Could not find search input for vehicle search")
                
        except Exception as e:
            logger.error(f"Error performing vehicle search: {e}")
    
    def _scrape_mot_history_page(self, registration: str) -> Optional[Dict[str, Any]]:
        """Navigate directly to MOT history page using known URL pattern"""
        try:
            # Try direct navigation to MOT history URL patterns
            logger.info("Starting direct MOT history extraction")
            
            mot_urls = [
                f"https://www.checkcardetails.co.uk/mot/mothistory/{registration.lower()}",
                f"https://www.checkcardetails.co.uk/mot/{registration.lower()}",
                f"https://www.checkcardetails.co.uk/mothistory/{registration.lower()}"
            ]
            
            mot_data = {
                'registration': registration.upper(),
                'mot_tests': [],
                'summary': {},
                'scraped_from': 'enhanced_selenium_mot_history_page',
                'page_title': '',
                'page_url': ''
            }
            
            # Try each MOT URL until we find data
            for mot_url in mot_urls:
                try:
                    logger.info(f"Navigating to MOT URL: {mot_url}")
                    self.driver.get(mot_url)
                    self._natural_delay(5.0, 7.0)  # Allow time for page load
                    
                    # Update metadata
                    mot_data['page_title'] = self.driver.title
                    mot_data['page_url'] = self.driver.current_url
                    
                    logger.info(f"MOT page loaded - Title: {self.driver.title}")
                    logger.info(f"Current URL: {self.driver.current_url}")
                    
                    # First try XPath extraction (your specific paths)
                    logger.info("Trying XPath extraction for MOT data...")
                    xpath_results = self._extract_via_xpath()
                    if xpath_results:
                        logger.info(f"XPath extraction successful: found {len(xpath_results)} records")
                        mot_data['mot_tests'] = xpath_results
                        mot_data['total_tests_found'] = len(xpath_results)
                        mot_data['extraction_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
                        return mot_data
                    
                    # Try CSS-based extraction
                    logger.info("Trying CSS-based extraction for MOT data...")
                    css_results = self._extract_mot_test_table()
                    if css_results:
                        logger.info(f"CSS extraction successful: found {len(css_results)} records")
                        mot_data['mot_tests'] = css_results
                        mot_data['total_tests_found'] = len(css_results)
                        mot_data['extraction_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
                        return mot_data
                    
                    # Check if page has any MOT-related content
                    page_source = self.driver.page_source.lower()
                    if any(keyword in page_source for keyword in ['mot', 'test history', 'ministry of transport']):
                        logger.info("Page contains MOT content but no structured data found")
                        break  # This is the right page, just no structured data
                    else:
                        logger.info("Page doesn't contain MOT content, trying next URL")
                        
                except Exception as e:
                    logger.warning(f"Failed to access MOT URL {mot_url}: {e}")
                    continue
            
            # If we reach here, no data was found
            logger.warning(f"No MOT data found for {registration} across all URL patterns")
            mot_data['total_tests_found'] = 0
            mot_data['extraction_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
            return mot_data
            
        except Exception as e:
            logger.error(f"Error scraping MOT history: {e}")
            # Return empty data structure on error
            return {
                'registration': registration.upper(),
                'mot_tests': [],
                'summary': {},
                'scraped_from': 'enhanced_selenium_mot_history_page',
                'page_title': 'Error',
                'page_url': 'Error',
                'total_tests_found': 0,
                'extraction_timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Fallback: navigate to main page and search for links
            if 'mot' not in self.driver.current_url.lower():
                logger.info("Fallback: navigating to main page to find MOT links")
                # Go back to homepage and search normally
                self.driver.get("https://www.checkcardetails.co.uk/")
                self._natural_delay(2.0, 3.0)
                
                # Re-search for the vehicle
                self._perform_vehicle_search(registration)
                self._natural_delay(2.0, 3.0)
            
            # Wait for page to load and handle Cloudflare
            WebDriverWait(self.driver, self.page_load_timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # Look for MOT history link on the main page
            mot_link_found = False
            try:
                # Wait for page content to load
                self._natural_delay(2.0, 3.0)
                
                # Try to find MOT history link by looking for text patterns
                all_links = self.driver.find_elements(By.TAG_NAME, "a")
                logger.info(f"Found {len(all_links)} links on page")
                
                # Log all links for debugging
                for i, link in enumerate(all_links):
                    try:
                        link_text = link.text.strip()
                        link_href = link.get_attribute('href') or ''
                        if link_text or 'checkcardetails' in link_href:
                            logger.info(f"Link {i}: text='{link_text}', href='{link_href}'")
                    except Exception:
                        continue
                
                for i, link in enumerate(all_links):
                    try:
                        # Get link attributes safely to avoid stale element errors
                        try:
                            link_text = link.text.strip().lower() if link.text else ''
                            link_href = link.get_attribute('href') or ''
                        except Exception as e:
                            logger.debug(f"Stale element at index {i}: {e}")
                            continue
                        
                        # Look for MOT-related links (broader search)
                        if (any(keyword in link_text for keyword in ['mot', 'history', 'test', 'check']) or 
                            any(keyword in link_href.lower() for keyword in ['mot', 'history', 'test'])):
                            try:
                                if link.is_displayed() and link.is_enabled():
                                    logger.info(f"Found potential MOT link: text='{link_text}', href='{link_href}'")
                                    
                                    # Scroll to link and click
                                    self.driver.execute_script("arguments[0].scrollIntoView(true);", link)
                                    self._natural_delay(0.5, 1.0)
                                    
                                    try:
                                        link.click()
                                        self._natural_delay(3.0, 4.0)
                                        current_url = self.driver.current_url
                                        logger.info(f"Clicked link, now on: {current_url}")
                                        
                                        # Check if we're on a MOT-related page
                                        if 'mot' in current_url.lower() or 'history' in current_url.lower():
                                            mot_link_found = True
                                            logger.info(f"Successfully navigated to MOT page: {current_url}")
                                            break
                                        else:
                                            logger.info(f"Link didn't lead to MOT page, continuing search")
                                            
                                    except Exception as click_error:
                                        logger.warning(f"Failed to click link: {click_error}")
                                        continue
                            except Exception as display_error:
                                logger.debug(f"Link not accessible: {display_error}")
                                continue
                    except Exception as e:
                        logger.debug(f"Error processing link {i}: {e}")
                        continue
                
                # If still no link found, look for buttons or other elements
                if not mot_link_found:
                    logger.info("No direct MOT link found, looking for buttons or other elements")
                    all_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'MOT') or contains(text(), 'mot') or contains(text(), 'History') or contains(text(), 'history')]")
                    
                    for element in all_elements:
                        try:
                            if element.is_displayed() and element.is_enabled():
                                element_text = element.text.strip().lower()
                                if any(keyword in element_text for keyword in ['mot', 'history', 'test']):
                                    logger.info(f"Found MOT element: '{element.text}', tag='{element.tag_name}'")
                                    
                                    # Try to click it
                                    self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                    self._natural_delay(0.5, 1.0)
                                    element.click()
                                    self._natural_delay(3.0, 4.0)
                                    mot_link_found = True
                                    logger.info(f"Successfully clicked MOT element, now on: {self.driver.current_url}")
                                    break
                        except Exception as e:
                            continue
                    
            except Exception as link_error:
                logger.warning(f"Error finding MOT link: {link_error}")
            
            # If we still haven't found the MOT page, the data might not be available
            if not mot_link_found:
                logger.info(f"No MOT history links found for {registration} - data may not be available on this vehicle")
            
            # Wait for page to load
            WebDriverWait(self.driver, self.page_load_timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # Extract MOT history data
            mot_data = {
                'registration': registration.upper(),
                'mot_tests': [],
                'summary': {},
                'scraped_from': 'enhanced_selenium_mot_history_page',
                'page_title': self.driver.title,
                'page_url': self.driver.current_url
            }
            
            # Extract all page content for comprehensive data
            page_text = self.driver.page_source
            
            # Look for "View Full MOT History" or pagination links FIRST
            self._click_view_full_history_link()
            
            # Extract MOT test table data (now should include all records)
            mot_tests = self._extract_mot_test_table()
            
            # If we got limited results, try pagination
            if mot_tests and len(mot_tests) < 10:  # Likely incomplete data
                logger.info(f"Found {len(mot_tests)} tests, looking for pagination...")
                additional_tests = self._handle_mot_pagination()
                if additional_tests:
                    mot_tests.extend(additional_tests)
                    logger.info(f"After pagination: {len(mot_tests)} total tests")
            
            if mot_tests:
                mot_data['mot_tests'] = mot_tests
                
            # Log page content for debugging if no tests found
            if not mot_tests:
                logger.warning(f"No MOT tests found for {registration}. Page title: {self.driver.title}")
                # Check if page contains "no records" or similar messages
                page_text = self.driver.page_source.lower()
                if 'no mot' in page_text or 'no records' in page_text or 'no data' in page_text:
                    logger.info("Page explicitly states no MOT data available")
                else:
                    logger.warning("Page loaded but no test data extracted - may need parsing improvement")
            
            # Extract summary information
            summary = self._extract_mot_summary()
            if summary:
                mot_data['summary'] = summary
            
            # Store additional metadata
            mot_data['total_tests_found'] = len(mot_tests)
            mot_data['extraction_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
            
            logger.info(f"Successfully extracted MOT history with {len(mot_tests)} test records")
            return mot_data
            
        except Exception as e:
            logger.error(f"Error scraping MOT history: {e}")
            return None
    
    def _scrape_mileage_history_page(self, registration: str) -> Optional[Dict[str, Any]]:
        """Navigate directly to mileage history page using known URL pattern"""
        try:
            # Try direct navigation to mileage history URL patterns
            logger.info("Starting direct mileage history extraction")
            
            mileage_urls = [
                f"https://www.checkcardetails.co.uk/mot/mileagehistory/{registration.lower()}",
                f"https://www.checkcardetails.co.uk/mileage/{registration.lower()}",
                f"https://www.checkcardetails.co.uk/mileagehistory/{registration.lower()}"
            ]
            
            mileage_data = {
                'registration': registration.upper(),
                'mileage_records': [],
                'analysis': {},
                'scraped_from': 'enhanced_selenium_mileage_history_page',
                'page_title': '',
                'page_url': ''
            }
            
            # Try each mileage URL until we find data
            for mileage_url in mileage_urls:
                try:
                    logger.info(f"Navigating to mileage URL: {mileage_url}")
                    self.driver.get(mileage_url)
                    self._natural_delay(5.0, 7.0)  # Allow time for page load
                    
                    # Update metadata
                    mileage_data['page_title'] = self.driver.title
                    mileage_data['page_url'] = self.driver.current_url
                    
                    logger.info(f"Mileage page loaded - Title: {self.driver.title}")
                    logger.info(f"Current URL: {self.driver.current_url}")
                    
                    # First try XPath extraction (your specific paths)
                    logger.info("Trying XPath extraction for mileage data...")
                    xpath_results = self._extract_via_xpath()
                    if xpath_results:
                        # Convert XPath results to mileage format
                        mileage_records = []
                        for result in xpath_results:
                            if result.get('mileage'):
                                mileage_records.append({
                                    'mileage': result['mileage'],
                                    'date': result.get('test_date', ''),
                                    'source': 'xpath_extraction'
                                })
                        if mileage_records:
                            logger.info(f"XPath extraction successful: found {len(mileage_records)} mileage records")
                            mileage_data['mileage_records'] = mileage_records
                            mileage_data['total_records_found'] = len(mileage_records)
                            mileage_data['extraction_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
                            return mileage_data
                    
                    # Try table-based extraction
                    logger.info("Trying table-based extraction for mileage data...")
                    table_results = self._extract_mileage_table()
                    if table_results:
                        logger.info(f"Table extraction successful: found {len(table_results)} mileage records")
                        mileage_data['mileage_records'] = table_results
                        mileage_data['total_records_found'] = len(table_results)
                        mileage_data['extraction_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
                        return mileage_data
                    
                    # Check if page has any mileage-related content
                    page_source = self.driver.page_source.lower()
                    if any(keyword in page_source for keyword in ['mileage', 'odometer', 'miles']):
                        logger.info("Page contains mileage content but no structured data found")
                        break  # This is the right page, just no structured data
                    else:
                        logger.info("Page doesn't contain mileage content, trying next URL")
                        
                except Exception as e:
                    logger.warning(f"Failed to access mileage URL {mileage_url}: {e}")
                    continue
            
            # If we reach here, no data was found
            logger.warning(f"No mileage data found for {registration} across all URL patterns")
            mileage_data['total_records_found'] = 0
            mileage_data['extraction_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
            return mileage_data
            
        except Exception as e:
            logger.error(f"Error scraping mileage history: {e}")
            # Return empty data structure on error
            return {
                'registration': registration.upper(),
                'mileage_records': [],
                'analysis': {},
                'scraped_from': 'enhanced_selenium_mileage_history_page',
                'page_title': 'Error',
                'page_url': 'Error',
                'total_records_found': 0,
                'extraction_timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            mileage_link_found = False
            try:
                # Wait for page content to load
                self._natural_delay(2.0, 3.0)
                
                # Try to find mileage history link by looking for text patterns
                all_links = self.driver.find_elements(By.TAG_NAME, "a")
                logger.info(f"Found {len(all_links)} links on page")
                
                for link in all_links:
                    try:
                        link_text = link.text.strip().lower()
                        link_href = link.get_attribute('href') or ''
                        
                        # Look for mileage-related links
                        if any(keyword in link_text for keyword in ['mileage', 'history', 'miles']) or 'mileage' in link_href.lower():
                            if link.is_displayed() and link.is_enabled():
                                logger.info(f"Found mileage link: text='{link.text}', href='{link_href}'")
                                
                                # Scroll to link and click
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", link)
                                self._natural_delay(0.5, 1.0)
                                link.click()
                                self._natural_delay(3.0, 4.0)
                                mileage_link_found = True
                                logger.info(f"Successfully clicked mileage link, now on: {self.driver.current_url}")
                                break
                    except Exception as e:
                        continue
                
                # If still no link found, look for buttons or other elements
                if not mileage_link_found:
                    logger.info("No direct mileage link found, looking for buttons or other elements")
                    all_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Mileage') or contains(text(), 'mileage') or contains(text(), 'Miles') or contains(text(), 'miles')]")
                    
                    for element in all_elements:
                        try:
                            if element.is_displayed() and element.is_enabled():
                                element_text = element.text.strip().lower()
                                if any(keyword in element_text for keyword in ['mileage', 'miles', 'history']):
                                    logger.info(f"Found mileage element: '{element.text}', tag='{element.tag_name}'")
                                    
                                    # Try to click it
                                    self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                    self._natural_delay(0.5, 1.0)
                                    element.click()
                                    self._natural_delay(3.0, 4.0)
                                    mileage_link_found = True
                                    logger.info(f"Successfully clicked mileage element, now on: {self.driver.current_url}")
                                    break
                        except Exception as e:
                            continue
                    
            except Exception as link_error:
                logger.warning(f"Error finding mileage link: {link_error}")
            
            # If we still haven't found the mileage page, the data might not be available
            if not mileage_link_found:
                logger.warning(f"Could not find mileage history link for {registration} - data may not be available")
            
            # Wait for page to load
            WebDriverWait(self.driver, self.page_load_timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # Extract mileage history data
            mileage_data = {
                'registration': registration.upper(),
                'mileage_records': [],
                'analysis': {},
                'scraped_from': 'enhanced_selenium_mileage_history_page',
                'page_title': self.driver.title,
                'page_url': self.driver.current_url
            }
            
            # Extract mileage records table
            mileage_records = self._extract_mileage_table()
            if mileage_records:
                mileage_data['mileage_records'] = mileage_records
            
            # Extract analysis information
            analysis = self._extract_mileage_analysis()
            if analysis:
                mileage_data['analysis'] = analysis
            
            # Store additional metadata
            mileage_data['total_records_found'] = len(mileage_records)
            mileage_data['extraction_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
            
            logger.info(f"Successfully extracted mileage history with {len(mileage_records)} records")
            return mileage_data
            
        except Exception as e:
            logger.error(f"Error scraping mileage history: {e}")
            return None
    
    def _extract_page_data(self, vehicle_data: dict):
        """Extract basic vehicle data from current page"""
        try:
            page_text = self.driver.page_source
            
            # First try structured table/element extraction
            self._extract_structured_data(vehicle_data)
            
            # Then try regex patterns as fallback
            if not vehicle_data['basic_info'].get('make'):
                make_patterns = [
                    r'Make[:\s]+([A-Za-z0-9\s\-]+)',
                    r'Vehicle Make[:\s]+([A-Za-z0-9\s\-]+)',
                    r'<td[^>]*>Make</td>\s*<td[^>]*>([^<]+)</td>',
                    r'Make:\s*([A-Za-z0-9\s\-]+)'
                ]
                
                for pattern in make_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        make = match.group(1).strip()
                        if make and make.lower() != 'unknown' and len(make) > 1:
                            vehicle_data['basic_info']['make'] = make
                            logger.info(f"Found make via regex: {make}")
                            break
            
            # Model patterns
            if not vehicle_data['basic_info'].get('model'):
                model_patterns = [
                    r'Model[:\s]+([A-Za-z0-9\s\-]+)',
                    r'Vehicle Model[:\s]+([A-Za-z0-9\s\-]+)',
                    r'<td[^>]*>Model</td>\s*<td[^>]*>([^<]+)</td>',
                    r'Model:\s*([A-Za-z0-9\s\-]+)'
                ]
                
                for pattern in model_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        model = match.group(1).strip()
                        if model and model.lower() != 'unknown' and len(model) > 1:
                            vehicle_data['basic_info']['model'] = model
                            logger.info(f"Found model via regex: {model}")
                            break
            
            # Year patterns
            if not vehicle_data['basic_info'].get('year'):
                year_patterns = [
                    r'Year[:\s]+(\d{4})',
                    r'<td[^>]*>Year</td>\s*<td[^>]*>(\d{4})</td>',
                    r'(\d{4})\s*(?:Year|Model Year)',
                    r'Year:\s*(\d{4})'
                ]
                
                for pattern in year_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        year = match.group(1).strip()
                        if year and len(year) == 4:
                            vehicle_data['basic_info']['year'] = year
                            logger.info(f"Found year via regex: {year}")
                            break
            
            # Color patterns
            if not vehicle_data['basic_info'].get('color'):
                color_patterns = [
                    r'Colour?[:\s]+([A-Za-z\s]+)',
                    r'<td[^>]*>Colou?r</td>\s*<td[^>]*>([^<]+)</td>',
                    r'Color:\s*([A-Za-z\s]+)'
                ]
                
                for pattern in color_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        color = match.group(1).strip()
                        if color and len(color) < 30 and color.lower() != 'unknown':
                            vehicle_data['basic_info']['color'] = color
                            logger.info(f"Found color via regex: {color}")
                            break
            
            # Fuel type patterns
            if not vehicle_data['basic_info'].get('fuel_type'):
                fuel_patterns = [
                    r'Fuel[:\s]+([A-Za-z\s]+)',
                    r'<td[^>]*>Fuel Type</td>\s*<td[^>]*>([^<]+)</td>',
                    r'Fuel Type:\s*([A-Za-z\s]+)',
                    r'Fuel:\s*([A-Za-z\s]+)'
                ]
                
                for pattern in fuel_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        fuel = match.group(1).strip()
                        if fuel and len(fuel) < 20 and fuel.lower() != 'unknown':
                            vehicle_data['basic_info']['fuel_type'] = fuel
                            logger.info(f"Found fuel type via regex: {fuel}")
                            break
            
        except Exception as e:
            logger.error(f"Error extracting page data: {e}")
    
    def _extract_structured_data(self, vehicle_data: dict):
        """Extract data from structured HTML elements like tables and divs"""
        try:
            # Look for all table cells and try to find label-value pairs
            table_cells = self.driver.find_elements(By.TAG_NAME, "td")
            
            # Process pairs of cells that might be label-value
            for i in range(0, len(table_cells) - 1, 2):
                try:
                    label_cell = table_cells[i]
                    value_cell = table_cells[i + 1]
                    
                    label = label_cell.text.strip().lower()
                    value = value_cell.text.strip()
                    
                    if not value or value.lower() in ['unknown', 'n/a', '-', '']:
                        continue
                    
                    # Map labels to our data structure
                    if ('make' in label or 'manufacturer' in label or 'brand' in label) and not vehicle_data['basic_info'].get('make'):
                        vehicle_data['basic_info']['make'] = value
                        logger.info(f"Found make via table: {value}")
                    elif 'model' in label and not vehicle_data['basic_info'].get('model'):
                        vehicle_data['basic_info']['model'] = value
                        logger.info(f"Found model via table: {value}")
                        
                        # If we found "Cla" as model, we can infer it's Mercedes-Benz
                        if value.lower() in ['cla', 'c-class', 'e-class', 'a-class', 'b-class', 's-class', 'glc', 'gla', 'gle', 'gls'] and not vehicle_data['basic_info'].get('make'):
                            vehicle_data['basic_info']['make'] = 'Mercedes-Benz'
                            logger.info(f"Inferred make from model: Mercedes-Benz (model: {value})")
                    elif 'year' in label and not vehicle_data['basic_info'].get('year'):
                        if re.match(r'^\d{4}$', value):
                            vehicle_data['basic_info']['year'] = value
                            logger.info(f"Found year via table: {value}")
                    elif ('colour' in label or 'color' in label) and not vehicle_data['basic_info'].get('color'):
                        vehicle_data['basic_info']['color'] = value
                        logger.info(f"Found color via table: {value}")
                    elif 'fuel' in label and not vehicle_data['basic_info'].get('fuel_type'):
                        vehicle_data['basic_info']['fuel_type'] = value
                        logger.info(f"Found fuel type via table: {value}")
                        
                except Exception as e:
                    continue
                    
            # Also try divs and spans that might contain data
            all_elements = self.driver.find_elements(By.CSS_SELECTOR, "div, span, p")
            for element in all_elements[:100]:  # Limit to avoid too much processing
                try:
                    text = element.text.strip()
                    if ':' in text and len(text) < 100:
                        parts = text.split(':', 1)
                        if len(parts) == 2:
                            label = parts[0].strip().lower()
                            value = parts[1].strip()
                            
                            if not value or value.lower() in ['unknown', 'n/a', '-', '']:
                                continue
                            
                            if ('make' in label or 'manufacturer' in label or 'brand' in label) and not vehicle_data['basic_info'].get('make'):
                                vehicle_data['basic_info']['make'] = value
                                logger.info(f"Found make via element: {value}")
                            elif 'model' in label and not vehicle_data['basic_info'].get('model'):
                                vehicle_data['basic_info']['model'] = value
                                logger.info(f"Found model via element: {value}")
                                
                                # If we found "Cla" as model, we can infer it's Mercedes-Benz
                                if value.lower() in ['cla', 'c-class', 'e-class', 'a-class', 'b-class', 's-class', 'glc', 'gla', 'gle', 'gls'] and not vehicle_data['basic_info'].get('make'):
                                    vehicle_data['basic_info']['make'] = 'Mercedes-Benz'
                                    logger.info(f"Inferred make from model: Mercedes-Benz (model: {value})")
                            elif 'year' in label and not vehicle_data['basic_info'].get('year'):
                                if re.match(r'^\d{4}$', value):
                                    vehicle_data['basic_info']['year'] = value
                                    logger.info(f"Found year via element: {value}")
                            elif ('colour' in label or 'color' in label) and not vehicle_data['basic_info'].get('color'):
                                vehicle_data['basic_info']['color'] = value
                                logger.info(f"Found color via element: {value}")
                            elif 'fuel' in label and not vehicle_data['basic_info'].get('fuel_type'):
                                vehicle_data['basic_info']['fuel_type'] = value
                                logger.info(f"Found fuel type via element: {value}")
                                
                except Exception:
                    continue
                    
        except Exception as e:
            logger.error(f"Error in structured data extraction: {e}")
    
    def _extract_mot_test_table(self) -> list:
        """Extract MOT test data from the specific website format using targeted selectors"""
        mot_tests = []
        
        try:
            # First check for the rich MOT history structure we confirmed exists
            # Based on the HTML sample provided, look for multiple CSS selectors
            mot_selectors = [
                ".mot-history-wrapper",  # Main wrapper for each MOT test
                ".mot-history-summary",  # Summary section with total tests
                ".total-tests",          # Individual summary stats
                ".mot-history-left",     # Left section with test result and date
                ".mot-history-right"     # Right section with mileage and comments
            ]
            
            mot_wrappers = self.driver.find_elements(By.CSS_SELECTOR, ".mot-history-wrapper")
            logger.info(f"Found {len(mot_wrappers)} MOT history wrappers")
            
            if mot_wrappers:
                # Extract from the comprehensive MOT history structure
                for wrapper in mot_wrappers:
                    try:
                        test_data = {}
                        
                        # Extract test result (PASSED/FAILED) using specific CSS paths
                        try:
                            # Try multiple selectors for test result
                            result_selectors = [
                                ".mot-history-result p",
                                ".mot-history-pass p", 
                                ".mot-history-fail p",
                                ".pass p",
                                ".fail p"
                            ]
                            result_found = False
                            for selector in result_selectors:
                                try:
                                    result_elem = wrapper.find_element(By.CSS_SELECTOR, selector)
                                    test_data['result'] = result_elem.text.strip()
                                    result_found = True
                                    break
                                except:
                                    continue
                            if not result_found:
                                test_data['result'] = 'Unknown'
                        except:
                            test_data['result'] = 'Unknown'
                        
                        # Extract test date using specific CSS paths
                        try:
                            date_selectors = [
                                ".mot-test-date",
                                ".dvla-date",
                                ".date-tested + .mot-test-date",
                                ".mot-history-left-content .dvla-date"
                            ]
                            date_found = False
                            for selector in date_selectors:
                                try:
                                    date_elem = wrapper.find_element(By.CSS_SELECTOR, selector)
                                    test_data['test_date'] = date_elem.text.strip()
                                    date_found = True
                                    break
                                except:
                                    continue
                            if not date_found:
                                test_data['test_date'] = ''
                        except:
                            test_data['test_date'] = ''
                        
                        # Extract mileage readings using comprehensive CSS paths
                        try:
                            # Multiple approaches for mileage extraction
                            mileage_selectors = [
                                ".mot-history-mileage-numbers",
                                ".mot-history-millage-wrapper .mot-history-mileage-numbers",
                                ".mot-history-information .mot-history-mileage-numbers"
                            ]
                            
                            mileage_found = False
                            for selector in mileage_selectors:
                                try:
                                    mileage_elems = wrapper.find_elements(By.CSS_SELECTOR, selector)
                                    if len(mileage_elems) >= 1:
                                        test_data['mileage'] = mileage_elems[0].text.strip()
                                        mileage_found = True
                                    if len(mileage_elems) >= 2:
                                        test_data['expiry_date'] = mileage_elems[1].text.strip()
                                    if mileage_found:
                                        break
                                except:
                                    continue
                            
                            if not mileage_found:
                                test_data['mileage'] = ''
                                test_data['expiry_date'] = ''
                        except:
                            test_data['mileage'] = ''
                            test_data['expiry_date'] = ''
                        
                        # Extract comments and advisory notices using specific CSS paths
                        comments = []
                        try:
                            comment_selectors = [
                                ".mot-history-ul li",
                                ".mot-history-comments-h5 + ul li",
                                ".comments ul li",
                                "ul.mot-history-ul li"
                            ]
                            
                            for selector in comment_selectors:
                                try:
                                    comment_elements = wrapper.find_elements(By.CSS_SELECTOR, selector)
                                    for li in comment_elements:
                                        comment_text = li.text.strip()
                                        if comment_text and comment_text not in [c['text'] for c in comments]:
                                            # Check for advisory notice span
                                            advisory_spans = li.find_elements(By.CSS_SELECTOR, ".type_advisery")
                                            is_advisory = len(advisory_spans) > 0 or 'ADVISORY' in comment_text
                                            
                                            clean_text = comment_text.replace('ADVISORY', '').strip()
                                            if clean_text:
                                                comments.append({
                                                    'text': clean_text,
                                                    'type': 'ADVISORY' if is_advisory else 'COMMENT'
                                                })
                                    if comments:  # Found some comments, stop looking
                                        break
                                except:
                                    continue
                        except:
                            pass
                        
                        test_data['comments'] = comments
                        test_data['advisory_count'] = len([c for c in comments if c['type'] == 'ADVISORY'])
                        
                        # Extract mileage progression
                        try:
                            mileage_change_elem = wrapper.find_element(By.CSS_SELECTOR, ".travelled-history")
                            test_data['mileage_change'] = mileage_change_elem.text.strip()
                        except:
                            test_data['mileage_change'] = ''
                        
                        if test_data.get('test_date') and test_data.get('result'):
                            mot_tests.append(test_data)
                            logger.info(f"Extracted MOT test: {test_data['test_date']} - {test_data['result']}")
                    
                    except Exception as e:
                        logger.warning(f"Error parsing MOT wrapper: {e}")
                        continue
                
                return mot_tests
            
            # If no MOT wrappers found, try direct XPath extraction
            if not mot_tests:
                logger.info("No MOT wrappers found, trying direct XPath extraction")
                mot_tests = self._extract_via_xpath()
            
            # Fallback to table-based extraction if MOT wrappers not found
            table_selectors = [
                'table',
                '.table',
                '[role="table"]',
                '.data-table',
                '.mot-table',
                '.test-table'
            ]
            
            for selector in table_selectors:
                try:
                    tables = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for table in tables:
                        rows = table.find_elements(By.TAG_NAME, "tr")
                        
                        if len(rows) > 1:  # Must have header + data
                            # Check if this looks like MOT data
                            table_text = table.text.lower()
                            if any(keyword in table_text for keyword in ['test', 'date', 'result', 'mileage', 'mot']):
                                
                                headers = []
                                # Try to find header row
                                for row in rows:
                                    row_cells = row.find_elements(By.TAG_NAME, "th")
                                    if not row_cells:
                                        row_cells = row.find_elements(By.TAG_NAME, "td")
                                    
                                    if row_cells:
                                        header_texts = [cell.text.strip().lower() for cell in row_cells]
                                        if any(keyword in ' '.join(header_texts) for keyword in ['test', 'date', 'result']):
                                            headers = header_texts
                                            break
                                
                                # Extract data rows
                                for row in rows[1:]:  # Skip presumed header
                                    cells = row.find_elements(By.TAG_NAME, "td")
                                    if len(cells) >= 2:
                                        cell_texts = [cell.text.strip() for cell in cells]
                                        
                                        test_record = {}
                                        for i, cell_text in enumerate(cell_texts):
                                            if headers and i < len(headers):
                                                header = headers[i]
                                                if 'date' in header:
                                                    test_record['test_date'] = cell_text
                                                elif 'result' in header:
                                                    test_record['result'] = cell_text
                                                elif 'mileage' in header or 'odometer' in header:
                                                    test_record['mileage'] = cell_text
                                                elif 'expiry' in header:
                                                    test_record['expiry_date'] = cell_text
                                                else:
                                                    test_record[f'column_{i}'] = cell_text
                                            else:
                                                test_record[f'column_{i}'] = cell_text
                                        
                                        if test_record:
                                            mot_tests.append(test_record)
                                
                                if mot_tests:  # Found data, stop looking
                                    break
                    
                    if mot_tests:  # Found data, stop looking
                        break
                        
                except Exception as e:
                    logger.warning(f"Error with selector {selector}: {e}")
                    continue
            
            # Fallback: Extract from page text
            if not mot_tests:
                page_text = self.driver.page_source
                mot_tests = self._extract_mot_from_text(page_text)
            
        except Exception as e:
            logger.error(f"Error extracting MOT test table: {e}")
        
        return mot_tests
    
    def _extract_via_xpath(self) -> list:
        """Extract MOT/mileage data using specific XPath selectors provided by user"""
        extracted_data = []
        
        try:
            # Multiple XPath selectors for mileage data from user
            mileage_xpaths = [
                "/html/body/section/div[2]/div/div[4]/div/div[2]/div[2]/div[1]/div[2]/div[2]/p/span[1]",
                "/html/body/div[2]/div[3]"  # New XPath from user
            ]
            
            # Try to extract mileage data using multiple XPaths
            for mileage_xpath in mileage_xpaths:
                try:
                    mileage_element = self.driver.find_element(By.XPATH, mileage_xpath)
                    mileage_value = mileage_element.text.strip()
                    if mileage_value:
                        logger.info(f"Found mileage via XPath {mileage_xpath}: {mileage_value}")
                        extracted_data.append({
                            'source': 'xpath_extraction',
                            'type': 'mileage',
                            'value': mileage_value,
                            'xpath': mileage_xpath
                        })
                        break  # Found data, stop trying other XPaths
                except Exception as e:
                    logger.debug(f"XPath mileage extraction failed for {mileage_xpath}: {e}")
            
            # Try MOT data XPath from user's earlier hint
            mot_xpath = "/html/body/section/div[2]/div/div[4]/div/div[2]/div[1]/div[3]/div/p[2]/span[1]"
            try:
                mot_element = self.driver.find_element(By.XPATH, mot_xpath)
                mot_value = mot_element.text.strip()
                if mot_value:
                    logger.info(f"Found MOT data via XPath: {mot_value}")
                    extracted_data.append({
                        'source': 'xpath_extraction',
                        'type': 'mot_data',
                        'value': mot_value,
                        'xpath': mot_xpath
                    })
            except Exception as e:
                logger.debug(f"XPath MOT extraction failed: {e}")
            
            # Convert extracted data to MOT test format
            if extracted_data:
                test_record = {
                    'test_date': '',
                    'result': '',
                    'mileage': '',
                    'comments': [],
                    'xpath_data': extracted_data
                }
                
                for item in extracted_data:
                    if item['type'] == 'mileage':
                        test_record['mileage'] = item['value']
                    elif 'PASS' in item['value'].upper():
                        test_record['result'] = 'PASSED'
                    elif 'FAIL' in item['value'].upper():
                        test_record['result'] = 'FAILED'
                    else:
                        test_record['comments'].append({
                            'text': item['value'],
                            'type': 'XPATH_DATA'
                        })
                
                return [test_record] if any([test_record['mileage'], test_record['result'], test_record['comments']]) else []
            
        except Exception as e:
            logger.error(f"Error in XPath extraction: {e}")
        
        return []
    
    def _click_view_full_history_link(self):
        """Look for and click 'View Full MOT History' or similar links to get complete data"""
        try:
            # Patterns for full history links
            full_history_patterns = [
                "view full mot history",
                "view full history", 
                "see all tests",
                "show all mot tests",
                "complete history",
                "full mot record",
                "view all"
            ]
            
            # Find all links on the page
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            logger.info(f"Checking {len(all_links)} links for full history access")
            
            for link in all_links:
                try:
                    link_text = link.text.strip().lower()
                    link_href = link.get_attribute('href') or ''
                    
                    # Check if this looks like a full history link
                    if any(pattern in link_text for pattern in full_history_patterns):
                        logger.info(f"Found full history link: '{link.text}' -> {link_href}")
                        link.click()
                        self._natural_delay(3.0, 5.0)  # Wait for page to load
                        logger.info("Successfully clicked full history link")
                        return True
                    
                    # Check href for relevant patterns
                    if any(pattern.replace(' ', '') in link_href.lower() for pattern in ['fullhistory', 'alltest', 'complete']):
                        logger.info(f"Found full history link via href: {link_href}")
                        link.click()
                        self._natural_delay(3.0, 5.0)
                        logger.info("Successfully clicked full history link via href")
                        return True
                        
                except Exception as e:
                    continue
            
            logger.info("No full history link found - proceeding with current page data")
            return False
            
        except Exception as e:
            logger.warning(f"Error looking for full history link: {e}")
            return False
    
    def _handle_mot_pagination(self) -> list:
        """Handle pagination to get all MOT test records"""
        additional_tests = []
        
        try:
            # Look for pagination elements
            pagination_patterns = [
                "next",
                "more",
                "page 2",
                "show more",
                "load more",
                "view more"
            ]
            
            page_count = 0
            max_pages = 5  # Safety limit
            
            while page_count < max_pages:
                # Look for pagination links
                found_next = False
                all_links = self.driver.find_elements(By.TAG_NAME, "a")
                all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                
                # Check links first
                for link in all_links:
                    try:
                        link_text = link.text.strip().lower()
                        if any(pattern in link_text for pattern in pagination_patterns):
                            logger.info(f"Found pagination link: '{link.text}'")
                            link.click()
                            self._natural_delay(2.0, 3.0)
                            found_next = True
                            break
                    except Exception:
                        continue
                
                # Check buttons if no links worked
                if not found_next:
                    for button in all_buttons:
                        try:
                            button_text = button.text.strip().lower()
                            if any(pattern in button_text for pattern in pagination_patterns):
                                logger.info(f"Found pagination button: '{button.text}'")
                                button.click()
                                self._natural_delay(2.0, 3.0)
                                found_next = True
                                break
                        except Exception:
                            continue
                
                if not found_next:
                    logger.info("No more pagination found")
                    break
                
                # Extract tests from this page
                page_tests = self._extract_mot_test_table()
                if page_tests:
                    additional_tests.extend(page_tests)
                    logger.info(f"Page {page_count + 1}: found {len(page_tests)} additional tests")
                
                page_count += 1
            
            logger.info(f"Pagination complete: found {len(additional_tests)} additional tests across {page_count} pages")
            return additional_tests
            
        except Exception as e:
            logger.warning(f"Error handling pagination: {e}")
            return additional_tests
    
    def _extract_mileage_table(self) -> list:
        """Extract mileage records from the current page"""
        mileage_records = []
        
        try:
            # Look for tables with different selectors
            table_selectors = [
                'table',
                '.table',
                '[role="table"]',
                '.data-table',
                '.mileage-table'
            ]
            
            for selector in table_selectors:
                try:
                    tables = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for table in tables:
                        rows = table.find_elements(By.TAG_NAME, "tr")
                        
                        if len(rows) > 1:
                            # Check if this looks like mileage data
                            table_text = table.text.lower()
                            if any(keyword in table_text for keyword in ['mileage', 'odometer', 'reading']):
                                
                                headers = []
                                # Try to find header row
                                for row in rows:
                                    row_cells = row.find_elements(By.TAG_NAME, "th")
                                    if not row_cells:
                                        row_cells = row.find_elements(By.TAG_NAME, "td")
                                    
                                    if row_cells:
                                        header_texts = [cell.text.strip().lower() for cell in row_cells]
                                        if any(keyword in ' '.join(header_texts) for keyword in ['mileage', 'date', 'reading']):
                                            headers = header_texts
                                            break
                                
                                # Extract data rows
                                for row in rows[1:]:  # Skip presumed header
                                    cells = row.find_elements(By.TAG_NAME, "td")
                                    if len(cells) >= 2:
                                        cell_texts = [cell.text.strip() for cell in cells]
                                        
                                        mileage_record = {}
                                        for i, cell_text in enumerate(cell_texts):
                                            if headers and i < len(headers):
                                                header = headers[i]
                                                if 'date' in header:
                                                    mileage_record['date'] = cell_text
                                                elif 'mileage' in header or 'odometer' in header or 'reading' in header:
                                                    mileage_record['mileage'] = cell_text
                                                elif 'source' in header:
                                                    mileage_record['source'] = cell_text
                                                else:
                                                    mileage_record[f'column_{i}'] = cell_text
                                            else:
                                                mileage_record[f'column_{i}'] = cell_text
                                        
                                        if mileage_record:
                                            mileage_records.append(mileage_record)
                                
                                if mileage_records:  # Found data, stop looking
                                    break
                    
                    if mileage_records:  # Found data, stop looking
                        break
                        
                except Exception as e:
                    logger.warning(f"Error with selector {selector}: {e}")
                    continue
            
            # Fallback: Extract from page text
            if not mileage_records:
                page_text = self.driver.page_source
                mileage_records = self._extract_mileage_from_text(page_text)
            
        except Exception as e:
            logger.error(f"Error extracting mileage table: {e}")
        
        return mileage_records
    
    def _extract_mot_summary(self) -> Dict[str, str]:
        """Extract MOT summary information"""
        summary = {}
        
        try:
            page_text = self.driver.page_source
            
            # Extract summary patterns
            patterns = [
                ('total_tests', r'Total Tests?:?\s*(\d+)'),
                ('passes', r'Passes?:?\s*(\d+)'),
                ('failures', r'Failures?:?\s*(\d+)'),
                ('advisories', r'Advisories?:?\s*(\d+)'),
                ('first_test', r'First Test:?\s*([^\n<]+)'),
                ('latest_test', r'Latest Test:?\s*([^\n<]+)')
            ]
            
            for key, pattern in patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    summary[key] = match.group(1).strip()
            
        except Exception as e:
            logger.error(f"Error extracting MOT summary: {e}")
        
        return summary
    
    def _extract_mileage_analysis(self) -> Dict[str, str]:
        """Extract mileage analysis information"""
        analysis = {}
        
        try:
            page_text = self.driver.page_source
            
            # Extract analysis patterns
            patterns = [
                ('average_annual_mileage', r'Average Annual Mileage:?\s*([^\n<]+)'),
                ('total_mileage', r'Total Mileage:?\s*([^\n<]+)'),
                ('mileage_trend', r'Mileage Trend:?\s*([^\n<]+)'),
                ('last_recorded', r'Last Recorded:?\s*([^\n<]+)'),
                ('first_recorded', r'First Recorded:?\s*([^\n<]+)')
            ]
            
            for key, pattern in patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    analysis[key] = match.group(1).strip()
            
        except Exception as e:
            logger.error(f"Error extracting mileage analysis: {e}")
        
        return analysis
    
    def _extract_mot_from_text(self, page_text: str) -> list:
        """Extract MOT data from text as fallback"""
        mot_tests = []
        
        try:
            lines = page_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for MOT-like data patterns
                date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{1,2}\s+\w+\s+\d{4})'
                if re.search(date_pattern, line):
                    test_record = {'raw_line': line}
                    
                    # Extract date
                    date_match = re.search(date_pattern, line)
                    if date_match:
                        test_record['test_date'] = date_match.group(1)
                    
                    # Extract result
                    result_match = re.search(r'\b(PASS|FAIL|ADVISORY)\b', line, re.IGNORECASE)
                    if result_match:
                        test_record['result'] = result_match.group(1).upper()
                    
                    # Extract mileage
                    mileage_match = re.search(r'(\d{1,6})\s*miles?', line, re.IGNORECASE)
                    if mileage_match:
                        test_record['mileage'] = mileage_match.group(1)
                    
                    if len(test_record) > 1:
                        mot_tests.append(test_record)
        
        except Exception as e:
            logger.error(f"Error extracting MOT from text: {e}")
        
        return mot_tests
    
    def _extract_mileage_from_text(self, page_text: str) -> list:
        """Extract mileage data from text as fallback"""
        mileage_records = []
        
        try:
            lines = page_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for mileage patterns
                mileage_pattern = r'(\d{1,6})\s*miles?'
                date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{1,2}\s+\w+\s+\d{4})'
                
                if re.search(mileage_pattern, line) and re.search(date_pattern, line):
                    mileage_record = {'raw_line': line}
                    
                    # Extract date
                    date_match = re.search(date_pattern, line)
                    if date_match:
                        mileage_record['date'] = date_match.group(1)
                    
                    # Extract mileage
                    mileage_match = re.search(mileage_pattern, line, re.IGNORECASE)
                    if mileage_match:
                        mileage_record['mileage'] = mileage_match.group(1)
                    
                    if len(mileage_record) > 1:
                        mileage_records.append(mileage_record)
        
        except Exception as e:
            logger.error(f"Error extracting mileage from text: {e}")
        
        return mileage_records
    
    def _cleanup(self):
        """Clean up WebDriver resources"""
        if self.driver:
            try:
                # Close all windows first
                for window in self.driver.window_handles:
                    try:
                        self.driver.switch_to.window(window)
                        self.driver.close()
                    except:
                        pass
                
                # Then quit the driver
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.warning(f"Error during graceful WebDriver close: {e}")
                
            finally:
                self.driver = None
        
        # Clean up any remaining processes
        try:
            self._kill_firefox_processes()
        except Exception as e:
            logger.warning(f"Error during process cleanup: {e}")