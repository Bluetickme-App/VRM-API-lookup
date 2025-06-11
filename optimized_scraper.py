"""
Optimized vehicle scraper with retry logic and fast response times
"""
import time
import random
import logging
from typing import Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.firefox import GeckoDriverManager
import re

logger = logging.getLogger(__name__)

class OptimizedVehicleScraper:
    """Optimized scraper with automatic retry and fast extraction"""
    
    def __init__(self, headless=False):
        self.driver = None
        self.wait = None
        self.headless = headless
        self.page_load_timeout = 20
        self.element_wait_timeout = 15
    
    def _setup_driver(self):
        """Initialize Firefox WebDriver"""
        try:
            firefox_options = Options()
            if self.headless:
                firefox_options.add_argument("--headless")
            
            firefox_options.add_argument("--no-sandbox")
            firefox_options.add_argument("--disable-dev-shm-usage")
            firefox_options.add_argument("--disable-gpu")
            firefox_options.add_argument("--window-size=1920,1080")
            
            # Use webdriver manager
            from selenium.webdriver.firefox.service import Service
            self.driver = webdriver.Firefox(
                service=Service(GeckoDriverManager().install()),
                options=firefox_options
            )
            
            self.driver.implicitly_wait(5)
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.wait = WebDriverWait(self.driver, self.element_wait_timeout)
            
            logger.info("WebDriver initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"WebDriver initialization failed: {e}")
            return False
    
    def _natural_delay(self, min_time=0.5, max_time=2.0):
        """Add natural human-like delay"""
        delay = random.uniform(min_time, max_time)
        time.sleep(delay)
    
    def scrape_vehicle_data(self, registration: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """Main scraping method with retry logic"""
        logger.info(f"Starting scrape for {registration} with {max_retries} max retries")
        
        for attempt in range(max_retries):
            logger.info(f"Attempt {attempt + 1}/{max_retries}")
            
            try:
                # Setup driver for this attempt
                if not self._setup_driver():
                    logger.error(f"Driver setup failed on attempt {attempt + 1}")
                    if attempt == max_retries - 1:
                        return None
                    continue
                
                # Navigate to website
                self.driver.get("https://www.checkcardetails.co.uk/")
                logger.info("Navigated to website")
                
                # Wait for page load
                self._natural_delay(2, 4)
                
                # Find registration input
                search_input = self._find_registration_input()
                if not search_input:
                    logger.error(f"Registration input not found on attempt {attempt + 1}")
                    if attempt == max_retries - 1:
                        return None
                    self._cleanup()
                    continue
                
                # Enter registration
                if not self._enter_registration(search_input, registration):
                    logger.error(f"Failed to enter registration on attempt {attempt + 1}")
                    if attempt == max_retries - 1:
                        return None
                    self._cleanup()
                    continue
                
                # Submit form
                if not self._submit_form(search_input):
                    logger.error(f"Failed to submit form on attempt {attempt + 1}")
                    if attempt == max_retries - 1:
                        return None
                    self._cleanup()
                    continue
                
                # Wait for results and extract data
                vehicle_data = self._extract_results_fast()
                
                if vehicle_data and vehicle_data.get('basic_info'):
                    vehicle_data['registration'] = registration.upper()
                    logger.info(f"Successfully extracted data on attempt {attempt + 1}")
                    self._cleanup()
                    return vehicle_data
                else:
                    logger.warning(f"No data found on attempt {attempt + 1}")
                    if attempt == max_retries - 1:
                        return None
                    self._cleanup()
                    continue
                    
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    return None
                self._cleanup()
                continue
        
        logger.error(f"All {max_retries} attempts failed for {registration}")
        return None
    
    def _find_registration_input(self):
        """Find the registration input field"""
        try:
            # Try multiple selectors
            selectors = [
                "#reg_num",
                "input[name='reg_num']",
                "input[placeholder*='REG']",
                "input[type='text']"
            ]
            
            for selector in selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    logger.info(f"Found input using selector: {selector}")
                    return element
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding registration input: {e}")
            return None
    
    def _enter_registration(self, input_element, registration):
        """Enter registration number"""
        try:
            input_element.clear()
            self._natural_delay(0.3, 0.7)
            
            # Type registration with human-like delays
            for char in registration.upper():
                input_element.send_keys(char)
                self._natural_delay(0.1, 0.2)
            
            logger.info(f"Entered registration: {registration}")
            self._natural_delay(0.5, 1.0)
            return True
            
        except Exception as e:
            logger.error(f"Error entering registration: {e}")
            return False
    
    def _submit_form(self, input_element):
        """Submit the search form"""
        try:
            # Try submit button first
            submit_selectors = [
                "input[type='submit']",
                "button[type='submit']",
                ".submit-btn",
                "button"
            ]
            
            for selector in submit_selectors:
                try:
                    button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    button.click()
                    logger.info(f"Clicked submit using: {selector}")
                    self._natural_delay(3, 6)
                    return True
                except:
                    continue
            
            # Fallback to Enter key
            input_element.send_keys(Keys.RETURN)
            logger.info("Used Enter key to submit")
            self._natural_delay(3, 6)
            return True
            
        except Exception as e:
            logger.error(f"Error submitting form: {e}")
            return False
    
    def _extract_results_fast(self):
        """Fast extraction of vehicle data"""
        try:
            # Wait for results page with dynamic content loading
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Additional wait for dynamic content to load
            time.sleep(3)
            
            vehicle_data = {
                'basic_info': {},
                'tax_mot': {},
                'vehicle_details': {},
                'additional': {}
            }
            
            # Get page text for parsing
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            
            # Log page content for debugging failures
            logger.info(f"Page contains {len(lines)} text lines")
            if len(lines) > 0:
                logger.info(f"First 20 lines: {lines[:20]}")
            
            # Look for specific field indicators
            field_indicators = []
            for i, line in enumerate(lines):
                if any(field in line.lower() for field in ['colour', 'fuel', 'transmission', 'description', 'mot', 'tax']):
                    field_indicators.append(f"Line {i}: '{line}' -> Next: '{lines[i+1] if i+1 < len(lines) else 'N/A'}'")
            
            if field_indicators:
                logger.info(f"Found field indicators: {field_indicators[:10]}")
            
            # Check for error pages or blocking
            if any(phrase in page_text.lower() for phrase in ['blocked', 'captcha', 'forbidden', 'access denied', 'robot']):
                logger.warning("Potential blocking or captcha detected")
                return {}
            
            # Extract key information
            self._parse_vehicle_info_fast(vehicle_data, lines)
            
            # Try specific XPaths for precise data
            self._extract_xpath_data(vehicle_data)
            
            # Validate that we found essential data
            has_data = (vehicle_data['basic_info'].get('make') or 
                       vehicle_data['basic_info'].get('model') or
                       vehicle_data['tax_mot'].get('mot_expiry') or
                       vehicle_data['additional'].get('total_keepers'))
            
            if not has_data:
                logger.warning("No essential vehicle data found in page content")
                logger.info(f"Available text content sample: {page_text[:500]}")
            
            logger.info(f"Extracted data: {vehicle_data}")
            return vehicle_data
            
        except Exception as e:
            logger.error(f"Error extracting results: {e}")
            return {}
    
    def _parse_vehicle_info_fast(self, vehicle_data, lines):
        """Parse vehicle information from text lines"""
        try:
            for i, line in enumerate(lines):
                # MOT information - check current line and next lines
                if line.strip() == 'MOT':
                    # Check next few lines for MOT expiry
                    for j in range(1, min(4, len(lines) - i)):
                        next_line = lines[i + j]
                        if 'Expires:' in next_line or 'Expired:' in next_line:
                            mot_match = re.search(r'(?:Expires|Expired):\s*(\d+\s+\w+\s+\d{4})', next_line)
                            if mot_match:
                                vehicle_data['tax_mot']['mot_expiry'] = mot_match.group(1)
                                logger.info(f"Found MOT expiry: {mot_match.group(1)}")
                                break
                
                # TAX information - check current line and next lines  
                elif line.strip() == 'TAX':
                    # Check next few lines for TAX expiry
                    for j in range(1, min(4, len(lines) - i)):
                        next_line = lines[i + j]
                        if 'Expires:' in next_line or 'Expired:' in next_line:
                            tax_match = re.search(r'(?:Expires|Expired):\s*(\d+\s+\w+\s+\d{4})', next_line)
                            if tax_match:
                                vehicle_data['tax_mot']['tax_expiry'] = tax_match.group(1)
                                logger.info(f"Found TAX expiry: {tax_match.group(1)}")
                                break
                
                # Vehicle details
                elif 'Description' in line and i + 1 < len(lines):
                    vehicle_data['basic_info']['description'] = lines[i + 1]
                    logger.info(f"Found description: {lines[i + 1]}")
                
                elif 'Primary Colour' in line and i + 1 < len(lines):
                    vehicle_data['basic_info']['color'] = lines[i + 1]
                    logger.info(f"Found color: {lines[i + 1]}")
                
                elif 'Colour' in line and i + 1 < len(lines) and not vehicle_data['basic_info'].get('color'):
                    vehicle_data['basic_info']['color'] = lines[i + 1]
                    logger.info(f"Found color (alt): {lines[i + 1]}")
                
                elif 'Fuel Type' in line and i + 1 < len(lines):
                    vehicle_data['basic_info']['fuel_type'] = lines[i + 1]
                    logger.info(f"Found fuel type: {lines[i + 1]}")
                
                elif 'Fuel' in line and i + 1 < len(lines) and not vehicle_data['basic_info'].get('fuel_type'):
                    # Check if next line looks like a fuel type
                    next_line = lines[i + 1]
                    if any(fuel in next_line.upper() for fuel in ['PETROL', 'DIESEL', 'ELECTRIC', 'HYBRID', 'LPG', 'CNG']):
                        vehicle_data['basic_info']['fuel_type'] = next_line
                        logger.info(f"Found fuel type (alt): {next_line}")
                
                elif 'Transmission' in line and i + 1 < len(lines):
                    vehicle_data['vehicle_details']['transmission'] = lines[i + 1]
                    logger.info(f"Found transmission: {lines[i + 1]}")
                
                # Enhanced make/model extraction
                elif any(brand in line.upper() for brand in ['AUDI', 'BMW', 'FORD', 'SMART', 'MERCEDES', 'VOLKSWAGEN', 'TOYOTA', 'HONDA', 'NISSAN', 'PEUGEOT', 'CITROEN', 'RENAULT', 'VAUXHALL', 'VOLVO', 'SKODA', 'SEAT', 'MINI', 'JAGUAR', 'LAND ROVER', 'BENTLEY', 'ROLLS-ROYCE', 'ASTON MARTIN', 'MCLAREN', 'LOTUS', 'MORGAN', 'TVR', 'CATERHAM', 'ARIEL', 'BAC', 'NOBLE', 'GINETTA', 'WESTFIELD', 'KIA', 'HYUNDAI']):
                    if not vehicle_data['basic_info'].get('make'):
                        vehicle_data['basic_info']['make'] = line
                
                # Extract model from variant line
                elif line == 'Model Variant' and i + 1 < len(lines):
                    vehicle_data['basic_info']['model'] = lines[i + 1]
                
                # Extract year from registration date
                elif 'Registration Date' in line and i + 1 < len(lines):
                    date_line = lines[i + 1]
                    year_match = re.search(r'\b(19|20)\d{2}\b', date_line)
                    if year_match:
                        vehicle_data['basic_info']['year'] = year_match.group(0)
                
                # Extract engine size
                elif 'cc' in line and 'Engine Size' in lines[max(0, i-2):i+1]:
                    engine_match = re.search(r'(\d+)\s*cc', line)
                    if engine_match:
                        vehicle_data['vehicle_details']['engine_size'] = f"{engine_match.group(1)} cc"
                
        except Exception as e:
            logger.warning(f"Error parsing text: {e}")
    
    def _extract_xpath_data(self, vehicle_data):
        """Extract data using specific XPaths"""
        try:
            # Total keepers
            try:
                keepers_xpath = "/html/body/section/div[2]/div/div[4]/div/div[2]/div[1]/div[5]/div[2]/div/div[1]/div[2]"
                keepers_element = self.driver.find_element(By.XPATH, keepers_xpath)
                vehicle_data['additional']['total_keepers'] = int(keepers_element.text.strip())
            except:
                pass
            
            # Model variant
            try:
                model_element = self.driver.find_element(By.XPATH, "//*[@id='modelv']")
                vehicle_data['basic_info']['model'] = model_element.text.strip()
            except:
                pass
            
        except Exception as e:
            logger.warning(f"XPath extraction failed: {e}")
    
    def _cleanup(self):
        """Clean up WebDriver resources"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
            self.wait = None