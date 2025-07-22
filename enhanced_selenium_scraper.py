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
            
            # Then scrape MOT history
            try:
                mot_history = self._scrape_mot_history_page(registration)
                if mot_history:
                    vehicle_data['mot_history'] = mot_history
                    logger.info("Successfully extracted MOT history")
                else:
                    logger.warning("No MOT history data found")
            except Exception as e:
                logger.warning(f"Error extracting MOT history: {e}")
            
            # Finally scrape mileage history
            try:
                mileage_history = self._scrape_mileage_history_page(registration)
                if mileage_history:
                    vehicle_data['mileage_history'] = mileage_history
                    logger.info("Successfully extracted mileage history")
                else:
                    logger.warning("No mileage history data found")
            except Exception as e:
                logger.warning(f"Error extracting mileage history: {e}")
            
            self._cleanup()
            return vehicle_data
            
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
            
            # Extract basic vehicle data
            vehicle_data = {
                'registration': registration.upper(),
                'basic_info': {},
                'tax_mot': {},
                'vehicle_details': {},
                'scraped_from': 'enhanced_selenium_basic_page'
            }
            
            # Extract data from the page
            self._extract_page_data(vehicle_data)
            
            return vehicle_data
            
        except Exception as e:
            logger.error(f"Error scraping basic vehicle data: {e}")
            return None
    
    def _scrape_mot_history_page(self, registration: str) -> Optional[Dict[str, Any]]:
        """Navigate to and scrape MOT history page"""
        try:
            # Navigate to MOT history page
            mot_url = f"https://www.checkcardetails.co.uk/mot/mothistory/{registration.lower()}"
            logger.info(f"Navigating to MOT history: {mot_url}")
            
            self.driver.get(mot_url)
            self._natural_delay(1.0, 2.0)
            
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
            
            # Extract MOT test table data
            mot_tests = self._extract_mot_test_table()
            if mot_tests:
                mot_data['mot_tests'] = mot_tests
            
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
        """Navigate to and scrape mileage history page"""
        try:
            # Navigate to mileage history page
            mileage_url = f"https://www.checkcardetails.co.uk/mot/mileagehistory/{registration.lower()}"
            logger.info(f"Navigating to mileage history: {mileage_url}")
            
            self.driver.get(mileage_url)
            self._natural_delay(1.0, 2.0)
            
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
        """Extract MOT test data from the current page"""
        mot_tests = []
        
        try:
            # Look for tables with different selectors
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