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
        self.page_load_timeout = 30  # Increased from 20 to handle slow loads
        self.element_wait_timeout = 20  # Increased from 15 for better reliability
    
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
    
    def _check_extraction_ready(self, driver):
        """Check if the page is ready for data extraction"""
        try:
            page_text = driver.find_element(By.TAG_NAME, "body").text
            
            # Check for key indicators that the page has loaded completely
            indicators = [
                "Vehicle Details" in page_text,
                "TAX" in page_text,
                "MOT" in page_text,
                len(page_text) > 500  # Minimum content threshold
            ]
            
            # Page is ready if we have at least 3 indicators
            is_ready = sum(indicators) >= 3
            
            if is_ready:
                logger.info("Page extraction ready - all key indicators found")
            
            return is_ready
            
        except Exception as e:
            logger.debug(f"Extraction readiness check failed: {e}")
            return False
    
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
        """Fast extraction of vehicle data with completion detection"""
        try:
            # Wait for results page with specific content indicators
            WebDriverWait(self.driver, 20).until(
                lambda driver: self._check_extraction_ready(driver)
            )
            
            # Signal extraction is ready
            logger.info("Extraction ready - content fully loaded")
            
            vehicle_data = {
                'basic_info': {},
                'tax_mot': {},
                'vehicle_details': {},
                'additional': {}
            }
            
            # Perform complete data extraction
            self._parse_vehicle_info_fast(vehicle_data, [])
            
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
            
            # Scroll down to load any additional content
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self._natural_delay(1, 2)
                
                # Scroll back up to capture any missed content
                self.driver.execute_script("window.scrollTo(0, 0);")
                self._natural_delay(1, 2)
                
                # Get updated page content after scrolling
                updated_text = self.driver.find_element(By.TAG_NAME, "body").text
                updated_lines = [line.strip() for line in updated_text.split('\n') if line.strip()]
                
                # Parse any additional fields found after scrolling
                if len(updated_lines) > len(lines):
                    logger.info(f"Found additional content after scrolling: {len(updated_lines) - len(lines)} more lines")
                    self._parse_vehicle_info_fast(vehicle_data, updated_lines)
                    
            except Exception as e:
                logger.warning(f"Error during scrolling: {e}")
            
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
            
            # Signal completion by adding a marker to the page
            try:
                self.driver.execute_script("""
                    var completionMarker = document.createElement('div');
                    completionMarker.id = 'vnc-extraction-complete';
                    completionMarker.style.display = 'none';
                    completionMarker.textContent = 'VNC_EXTRACTION_COMPLETE';
                    document.body.appendChild(completionMarker);
                """)
                logger.info("VNC extraction completion signal added to page")
            except Exception as e:
                logger.debug(f"Could not add completion signal: {e}")
            
            return vehicle_data
            
        except Exception as e:
            logger.error(f"Error extracting results: {e}")
            return {}
    
    def _parse_vehicle_info_fast(self, vehicle_data, lines):
        """Parse vehicle information from text lines with proper field alignment"""
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
                
                # Vehicle details - parse line content directly (single line format)
                elif line.startswith('Description '):
                    vehicle_data['basic_info']['description'] = line.replace('Description ', '').strip()
                    logger.info(f"Found description: {vehicle_data['basic_info']['description']}")
                
                elif line.startswith('Primary Colour '):
                    vehicle_data['basic_info']['color'] = line.replace('Primary Colour ', '').strip()
                    logger.info(f"Found color: {vehicle_data['basic_info']['color']}")
                
                elif line.startswith('Fuel Type '):
                    vehicle_data['basic_info']['fuel_type'] = line.replace('Fuel Type ', '').strip()
                    logger.info(f"Found fuel type: {vehicle_data['basic_info']['fuel_type']}")
                
                elif line.startswith('Transmission '):
                    vehicle_data['vehicle_details']['transmission'] = line.replace('Transmission ', '').strip()
                    logger.info(f"Found transmission: {vehicle_data['vehicle_details']['transmission']}")
                
                elif line.startswith('Engine ') and 'cc' in line:
                    vehicle_data['vehicle_details']['engine_size'] = line.replace('Engine ', '').strip()
                    logger.info(f"Found engine size: {vehicle_data['vehicle_details']['engine_size']}")
                
                elif line.startswith('Body Style '):
                    vehicle_data['vehicle_details']['body_style'] = line.replace('Body Style ', '').strip()
                    logger.info(f"Found body style: {vehicle_data['vehicle_details']['body_style']}")
                
                elif line.startswith('Year Manufacture '):
                    year_text = line.replace('Year Manufacture ', '').strip()
                    year_match = re.search(r'\d{4}', year_text)
                    if year_match:
                        vehicle_data['basic_info']['year'] = year_match.group(0)
                        logger.info(f"Found manufacture year: {vehicle_data['basic_info']['year']}")
                
                # Enhanced make/model extraction
                elif any(brand in line.upper() for brand in ['ALFA ROMEO', 'AUDI', 'BMW', 'FORD', 'SMART', 'MERCEDES', 'VOLKSWAGEN', 'TOYOTA', 'HONDA', 'NISSAN', 'PEUGEOT', 'CITROEN', 'RENAULT', 'VAUXHALL', 'VOLVO', 'SKODA', 'SEAT', 'MINI', 'JAGUAR', 'LAND ROVER', 'BENTLEY', 'ROLLS-ROYCE', 'ASTON MARTIN', 'MCLAREN', 'LOTUS', 'MORGAN', 'TVR', 'CATERHAM', 'ARIEL', 'BAC', 'NOBLE', 'GINETTA', 'WESTFIELD', 'KIA', 'HYUNDAI', 'FIAT', 'FERRARI', 'LAMBORGHINI', 'MASERATI', 'PORSCHE', 'SUBARU', 'MITSUBISHI', 'SUZUKI', 'MAZDA', 'LEXUS', 'INFINITI', 'ACURA', 'CADILLAC', 'CHEVROLET', 'BUICK', 'GMC', 'LINCOLN', 'CHRYSLER', 'DODGE', 'JEEP', 'RAM']):
                    if not vehicle_data['basic_info'].get('make'):
                        # Extract just the make from the line (e.g., "ALFA ROMEO" from "ALFA ROMEO 159")
                        for brand in ['ALFA ROMEO', 'AUDI', 'BMW', 'FORD', 'SMART', 'MERCEDES', 'VOLKSWAGEN', 'TOYOTA', 'HONDA', 'NISSAN', 'PEUGEOT', 'CITROEN', 'RENAULT', 'VAUXHALL', 'VOLVO', 'SKODA', 'SEAT', 'MINI', 'JAGUAR', 'LAND ROVER', 'BENTLEY', 'ROLLS-ROYCE', 'ASTON MARTIN', 'MCLAREN', 'LOTUS', 'MORGAN', 'TVR', 'CATERHAM', 'ARIEL', 'BAC', 'NOBLE', 'GINETTA', 'WESTFIELD', 'KIA', 'HYUNDAI', 'FIAT', 'FERRARI', 'LAMBORGHINI', 'MASERATI', 'PORSCHE', 'SUBARU', 'MITSUBISHI', 'SUZUKI', 'MAZDA', 'LEXUS', 'INFINITI', 'ACURA', 'CADILLAC', 'CHEVROLET', 'BUICK', 'GMC', 'LINCOLN', 'CHRYSLER', 'DODGE', 'JEEP', 'RAM']:
                            if brand in line.upper():
                                vehicle_data['basic_info']['make'] = brand
                                # Extract model from the same line (everything after the make)
                                model_part = line.replace(brand, '').strip()
                                if model_part and not vehicle_data['basic_info'].get('model'):
                                    vehicle_data['basic_info']['model'] = model_part
                                logger.info(f"Found make: {brand}, model: {model_part}")
                                break
                
                # Extract model from variant line
                elif line == 'Model Variant' and i + 1 < len(lines):
                    vehicle_data['basic_info']['model'] = lines[i + 1]
                
                # Extract year from registration date
                elif 'Registration Date' in line and i + 1 < len(lines):
                    date_line = lines[i + 1]
                    year_match = re.search(r'\b(19|20)\d{2}\b', date_line)
                    if year_match:
                        vehicle_data['basic_info']['year'] = year_match.group(0)
                
                # Extract total keepers
                elif 'Total Keepers' in line and i + 1 < len(lines):
                    keepers_text = lines[i + 1]
                    keepers_match = re.search(r'(\d+)', keepers_text)
                    if keepers_match:
                        vehicle_data['additional']['total_keepers'] = int(keepers_match.group(1))
                        logger.info(f"Found total keepers: {keepers_match.group(1)}")
                
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