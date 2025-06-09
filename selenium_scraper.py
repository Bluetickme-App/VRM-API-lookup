"""
Selenium-based vehicle scraper with VNC support
Uses Firefox with proper display for interactive scraping
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
import logging
import os
import re
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SeleniumVehicleScraper:
    """Selenium-based scraper with VNC display support"""
    
    def __init__(self, headless=False):
        self.driver = None
        self.wait = None
        self.headless = headless
        
    def _setup_driver(self):
        """Initialize Firefox WebDriver with proper configuration"""
        try:
            from webdriver_manager.firefox import GeckoDriverManager
            
            firefox_options = Options()
            
            if self.headless:
                firefox_options.add_argument('--headless')
            
            # Enhanced privacy and stealth options
            firefox_options.add_argument('--no-sandbox')
            firefox_options.add_argument('--disable-dev-shm-usage')
            firefox_options.add_argument('--window-size=1920,1080')
            firefox_options.add_argument('--disable-blink-features=AutomationControlled')
            firefox_options.add_argument('--disable-extensions')
            firefox_options.add_argument('--disable-plugins')
            firefox_options.add_argument('--disable-images')
            firefox_options.add_argument('--disable-javascript')
            firefox_options.add_argument('--disable-web-security')
            firefox_options.add_argument('--allow-running-insecure-content')
            
            # Set custom user agent to mimic regular browser
            firefox_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # Privacy preferences
            firefox_options.set_preference('dom.webdriver.enabled', False)
            firefox_options.set_preference('useAutomationExtension', False)
            firefox_options.set_preference('network.http.referer.spoofSource', True)
            firefox_options.set_preference('privacy.donottrackheader.enabled', True)
            firefox_options.set_preference('privacy.trackingprotection.enabled', True)
            firefox_options.set_preference('privacy.trackingprotection.socialtracking.enabled', True)
            firefox_options.set_preference('privacy.partition.network_state', False)
            firefox_options.set_preference('network.cookie.cookieBehavior', 1)
            firefox_options.set_preference('network.http.sendRefererHeader', 0)
            
            # Use webdriver-manager to get compatible geckodriver
            try:
                service = Service(GeckoDriverManager().install())
                self.driver = webdriver.Firefox(service=service, options=firefox_options)
            except Exception as service_error:
                logger.warning(f"WebDriver manager failed: {service_error}, trying system geckodriver")
                # Fallback to system geckodriver
                self.driver = webdriver.Firefox(options=firefox_options)
            
            self.wait = WebDriverWait(self.driver, 20)
            
            # Execute stealth scripts to hide automation
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
            self.driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
            self.driver.execute_script("Object.defineProperty(screen, 'colorDepth', {get: () => 24})")
            
            logger.info("Firefox WebDriver initialized successfully")
            return True
            
        except WebDriverException as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            return False
    
    def scrape_vehicle_data(self, registration: str) -> Optional[Dict[str, Any]]:
        """Main method to scrape vehicle data"""
        try:
            if not self._setup_driver():
                return None
            
            # Navigate to the website
            self.driver.get("https://www.checkcardetails.co.uk/")
            logger.info("Navigated to checkcardetails.co.uk")
            
            # Wait for page to load and look for the input field
            time.sleep(5)
            
            # Debug: Print page source to understand structure
            logger.info("Page loaded, looking for input field...")
            
            # Find and fill the registration input - try multiple approaches
            search_input = None
            
            # First, try to find any input fields on the page
            try:
                all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
                logger.info(f"Found {len(all_inputs)} input elements on page")
                
                for i, inp in enumerate(all_inputs):
                    try:
                        input_type = inp.get_attribute('type')
                        input_id = inp.get_attribute('id')
                        input_name = inp.get_attribute('name')
                        input_placeholder = inp.get_attribute('placeholder')
                        input_class = inp.get_attribute('class')
                        
                        logger.info(f"Input {i}: type='{input_type}', id='{input_id}', name='{input_name}', placeholder='{input_placeholder}', class='{input_class}'")
                        
                        # Look for registration-related input
                        if (input_type == 'text' and 
                            (input_placeholder and ('reg' in input_placeholder.lower() or 'vrm' in input_placeholder.lower())) or
                            (input_id and ('reg' in input_id.lower() or 'vrm' in input_id.lower())) or
                            (input_name and ('reg' in input_name.lower() or 'vrm' in input_name.lower()))):
                            search_input = inp
                            logger.info(f"Selected input field: {input_id or input_name or 'unnamed'}")
                            break
                    except Exception as e:
                        logger.warning(f"Error examining input {i}: {e}")
                        continue
                
                # If no specific match, try the first visible text input
                if not search_input:
                    for inp in all_inputs:
                        try:
                            if (inp.get_attribute('type') == 'text' and 
                                inp.is_displayed() and inp.is_enabled()):
                                search_input = inp
                                logger.info("Using first visible text input")
                                break
                        except:
                            continue
                            
            except Exception as e:
                logger.error(f"Error finding input elements: {e}")
            
            if not search_input:
                logger.error("Could not find any suitable registration input field")
                # Save screenshot for debugging
                try:
                    self.driver.save_screenshot("/tmp/debug_screenshot.png")
                    logger.info("Debug screenshot saved to /tmp/debug_screenshot.png")
                except:
                    pass
                return None
            
            try:
                # Clear and enter registration
                search_input.clear()
                search_input.click()
                search_input.send_keys(registration.upper())
                logger.info(f"Entered registration: {registration}")
                
                # Try to submit the form - look for submit button or press Enter
                try:
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit'], .submit-btn")
                    submit_button.click()
                    logger.info("Clicked submit button")
                except NoSuchElementException:
                    search_input.send_keys(Keys.RETURN)
                    logger.info("Pressed Enter to submit")
                
                # Wait for results page to load completely
                time.sleep(10)
                
                # Wait for vehicle data to appear
                try:
                    self.wait.until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    logger.info("Results page loaded")
                except TimeoutException:
                    logger.warning("Timeout waiting for results page")
                
                # Extract vehicle data from the results page
                vehicle_data = self._extract_vehicle_data()
                
                if vehicle_data:
                    vehicle_data['registration'] = registration.upper()
                    logger.info(f"Successfully extracted data for {registration}")
                    return vehicle_data
                else:
                    logger.warning(f"No data found for {registration}")
                    return None
                    
            except TimeoutException:
                logger.error("Timeout waiting for search input")
                return None
                
        except Exception as e:
            logger.error(f"Error scraping vehicle data: {e}")
            return None
            
        finally:
            self._cleanup()
    
    def _extract_vehicle_data(self) -> Dict[str, Any]:
        """Extract all vehicle data from the current page"""
        vehicle_data = {
            'basic_info': {},
            'tax_mot': {},
            'vehicle_details': {},
            'mileage': {},
            'performance': {},
            'fuel_economy': {},
            'safety': {},
            'additional': {}
        }
        
        try:
            # Save current page source for debugging
            page_source = self.driver.page_source
            logger.info(f"Page title: {self.driver.title}")
            
            # Look for all text content on the page for debugging and processing
            all_visible_text = []
            try:
                elements_with_text = self.driver.find_elements(By.XPATH, "//*[normalize-space(text())]")
                for element in elements_with_text[:100]:  # Limit to first 100 for performance
                    try:
                        text = element.text.strip()
                        if text and len(text) > 1 and text not in all_visible_text:
                            all_visible_text.append(text)
                    except:
                        continue
                logger.info(f"Sample visible text: {all_visible_text[:20]}")
                self.all_visible_text = all_visible_text  # Store for later use
            except:
                pass
            
            # Extract TAX and MOT data directly from visible text
            self._extract_tax_mot_from_visible_text(vehicle_data, all_visible_text)
            
            # Extract vehicle data using comprehensive approach
            
            # Look for any structured content first
            self._extract_structured_data(vehicle_data)
            
            # Extract from page text patterns 
            self._extract_from_text_patterns(vehicle_data, page_source)
            
            # Extract from all visible elements
            self._extract_from_elements(vehicle_data)
            
            # Extract from table structures
            self._extract_from_tables(vehicle_data)
            
            # Extract tax/MOT information
            self._extract_tax_mot_data(vehicle_data)
            
            # Post-process: Apply make inference if still missing
            if not vehicle_data['basic_info'].get('make') and vehicle_data['basic_info'].get('model'):
                self._infer_make_from_model(vehicle_data)
            
            logger.info(f"Extracted data structure: {vehicle_data}")
            
        except Exception as e:
            logger.error(f"Error in _extract_vehicle_data: {e}")
            
        return vehicle_data
    
    def _extract_tax_mot_from_visible_text(self, vehicle_data: dict, visible_text_list: list):
        """Extract TAX and MOT data from the visible text array"""
        try:
            import re
            
            # Join all visible text for pattern matching
            full_text = ' '.join(visible_text_list)
            
            # Look for TAX information
            for i, text in enumerate(visible_text_list):
                if 'TAX' in text:
                    # Check next few items for expiry date and days left
                    for j in range(i+1, min(i+4, len(visible_text_list))):
                        next_text = visible_text_list[j]
                        
                        # Look for expiry date pattern
                        if 'Expires:' in next_text:
                            date_match = re.search(r'Expires:\s*(.+)', next_text)
                            if date_match:
                                vehicle_data['tax_mot']['tax_expiry'] = date_match.group(1).strip()
                                
                        # Look for days left
                        elif 'days left' in next_text:
                            days_match = re.search(r'(\d+)\s+days\s+left', next_text)
                            if days_match:
                                vehicle_data['tax_mot']['tax_days_left'] = int(days_match.group(1))
                                
                # Look for MOT information
                elif 'MOT' in text:
                    # Check next few items for expiry date and days left
                    for j in range(i+1, min(i+4, len(visible_text_list))):
                        next_text = visible_text_list[j]
                        
                        # Look for expiry date pattern
                        if 'Expires:' in next_text:
                            date_match = re.search(r'Expires:\s*(.+)', next_text)
                            if date_match:
                                vehicle_data['tax_mot']['mot_expiry'] = date_match.group(1).strip()
                                
                        # Look for days left
                        elif 'days left' in next_text:
                            days_match = re.search(r'(\d+)\s+days\s+left', next_text)
                            if days_match:
                                vehicle_data['tax_mot']['mot_days_left'] = int(days_match.group(1))
            
            # Log what we found
            if vehicle_data['tax_mot']:
                logger.info(f"Extracted TAX/MOT data: {vehicle_data['tax_mot']}")
                        
        except Exception as e:
            logger.error(f"Error extracting TAX/MOT from visible text: {e}")
    
    def _infer_make_from_model(self, vehicle_data: dict):
        """Infer vehicle make from model when make is not explicitly found"""
        try:
            model = vehicle_data['basic_info'].get('model', '').lower()
            
            # Common make-model mappings
            model_to_make = {
                'compass': 'Jeep',
                'wrangler': 'Jeep', 
                'cherokee': 'Jeep',
                'renegade': 'Jeep',
                'focus': 'Ford',
                'fiesta': 'Ford',
                'mondeo': 'Ford',
                'kuga': 'Ford',
                'golf': 'Volkswagen',
                'polo': 'Volkswagen',
                'passat': 'Volkswagen',
                'tiguan': 'Volkswagen',
                'corolla': 'Toyota',
                'yaris': 'Toyota',
                'camry': 'Toyota',
                'prius': 'Toyota',
                'civic': 'Honda',
                'accord': 'Honda',
                'crv': 'Honda',
                'hrv': 'Honda',
                'astra': 'Vauxhall',
                'corsa': 'Vauxhall',
                'insignia': 'Vauxhall',
                'mokka': 'Vauxhall',
                'clio': 'Renault',
                'megane': 'Renault',
                'captur': 'Renault',
                'scenic': 'Renault',
                '208': 'Peugeot',
                '308': 'Peugeot',
                '508': 'Peugeot',
                '2008': 'Peugeot',
                'c3': 'Citroen',
                'c4': 'Citroen',
                'c5': 'Citroen',
                'berlingo': 'Citroen'
            }
            
            for model_name, make_name in model_to_make.items():
                if model_name in model:
                    vehicle_data['basic_info']['make'] = make_name
                    logger.info(f"Inferred make '{make_name}' from model '{model}'")
                    break
                    
        except Exception as e:
            logger.error(f"Error inferring make from model: {e}")
    
    def _extract_structured_data(self, vehicle_data: dict):
        """Extract data from structured elements using specific XPaths"""
        try:
            # Extract Total Keepers using the new XPath
            try:
                total_keepers_element = self.driver.find_element(By.XPATH, "/html/body/section/div[2]/div/div[4]/div/div[2]/div[1]/div[5]/div[2]/div/div[1]/div[2]")
                total_keepers_text = total_keepers_element.text.strip()
                if total_keepers_text and total_keepers_text.isdigit():
                    vehicle_data['additional'] = vehicle_data.get('additional', {})
                    vehicle_data['additional']['total_keepers'] = int(total_keepers_text)
                    logger.info(f"Found total keepers using XPath: {total_keepers_text}")
            except Exception as e:
                logger.warning(f"Could not find total keepers using specific XPath: {e}")

            # Extract Model Variant/Derivative using the specific XPath
            try:
                model_variant_element = self.driver.find_element(By.XPATH, "//*[@id='modelv']")
                model_variant_text = model_variant_element.text.strip()
                if model_variant_text and model_variant_text.lower() not in ['unknown', 'n/a', '-']:
                    vehicle_data['basic_info']['model'] = model_variant_text
                    vehicle_data['basic_info']['description'] = model_variant_text
                    logger.info(f"Found model variant using XPath: {model_variant_text}")
            except Exception as e:
                logger.warning(f"Could not find model variant using specific XPath: {e}")
            
            # Extract make using the original XPath (keeping as fallback)
            try:
                make_element = self.driver.find_element(By.XPATH, "/html/body/section/div[2]/div/h5[1]")
                make_text = make_element.text.strip()
                if make_text and make_text.lower() not in ['unknown', 'n/a', '-']:
                    vehicle_data['basic_info']['make'] = make_text
                    logger.info(f"Found make using XPath: {make_text}")
            except Exception as e:
                logger.warning(f"Could not find make using specific XPath: {e}")
                
            # Extract full description from visible text patterns
            try:
                if hasattr(self, 'all_visible_text'):
                    visible_text_list = self.all_visible_text
                    
                    # Look for full description patterns in the visible text
                    for i, text in enumerate(visible_text_list):
                        if 'Description' in text and i + 1 < len(visible_text_list):
                            next_text = visible_text_list[i + 1]
                            # Check if next text contains detailed description
                            if any(keyword in next_text for keyword in ['SE', 'TDI', 'Quattro', 'Auto', 'Limited', 'Edition', 'Sport', 'Turbo']):
                                vehicle_data['basic_info']['description'] = next_text
                                logger.info(f"Found detailed description: {next_text}")
                                break
                        elif 'Model Description' in text and i + 1 < len(visible_text_list):
                            next_text = visible_text_list[i + 1]
                            if next_text != 'Not Available' and len(next_text) > 3:
                                vehicle_data['basic_info']['description'] = next_text
                                logger.info(f"Found model description: {next_text}")
                                break
            except Exception as e:
                logger.warning(f"Error extracting detailed description: {e}")
            
            # Try alternative XPaths for other vehicle data
            xpath_mappings = {
                'make': [
                    "/html/body/section/div[2]/div/h5[1]",
                    "//h5[contains(text(), 'Make') or position()=1]",
                    "//span[contains(@class, 'make')]",
                    "//div[contains(@class, 'make')]"
                ],
                'model': [
                    "//h5[contains(text(), 'Model') or position()=2]",
                    "//span[contains(@class, 'model')]",
                    "//div[contains(@class, 'model')]"
                ],
                'year': [
                    "//h5[contains(text(), 'Year') or contains(text(), '20')]",
                    "//span[contains(@class, 'year')]"
                ]
            }
            
            for field, xpaths in xpath_mappings.items():
                if vehicle_data['basic_info'].get(field):
                    continue  # Skip if already found
                    
                for xpath in xpaths:
                    try:
                        element = self.driver.find_element(By.XPATH, xpath)
                        text = element.text.strip()
                        if text and text.lower() not in ['unknown', 'n/a', '-', '']:
                            vehicle_data['basic_info'][field] = text
                            logger.info(f"Found {field} using XPath {xpath}: {text}")
                            break
                    except:
                        continue
            
            # Look for common vehicle data containers as fallback
            container_selectors = [
                ".vehicle-info", ".car-details", ".vehicle-details", 
                "#vehicle-info", "#car-details", ".info-container"
            ]
            
            for selector in container_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text
                        if text and len(text) > 10:
                            self._parse_data_from_text(vehicle_data, text)
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"Error in structured data extraction: {e}")
    
    def _extract_tax_mot_data(self, vehicle_data: dict):
        """Extract TAX and MOT specific information"""
        try:
            # Look for TAX/MOT related text
            tax_mot_keywords = ['tax', 'mot', 'expires', 'expiry', 'valid', 'due']
            
            all_text_elements = self.driver.find_elements(By.XPATH, "//*[text()]")
            
            for element in all_text_elements:
                try:
                    text = element.text.strip()
                    text_lower = text.lower()
                    
                    if any(keyword in text_lower for keyword in tax_mot_keywords):
                        # Extract dates and status
                        import re
                        
                        # Look for date patterns - improved patterns
                        date_patterns = [
                            r'(\d{1,2}[\/\-\s]\d{1,2}[\/\-\s]\d{4})',  # DD/MM/YYYY, DD-MM-YYYY
                            r'(\d{1,2}\s+\w+\s+\d{4})',  # DD Month YYYY
                            r'(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})',  # YYYY/MM/DD
                            r'(\w+\s+\d{1,2},?\s+\d{4})'  # Month DD, YYYY
                        ]
                        
                        dates = []
                        for pattern in date_patterns:
                            dates.extend(re.findall(pattern, text))
                        
                        if dates:
                            if 'tax' in text_lower:
                                vehicle_data['tax_mot']['tax_expiry'] = dates[0]
                                # Look for status
                                if 'valid' in text_lower:
                                    vehicle_data['tax_mot']['tax_status'] = 'Valid'
                                elif 'expired' in text_lower or 'due' in text_lower:
                                    vehicle_data['tax_mot']['tax_status'] = 'Expired'
                            elif 'mot' in text_lower:
                                vehicle_data['tax_mot']['mot_expiry'] = dates[0]
                                # Look for status
                                if 'valid' in text_lower:
                                    vehicle_data['tax_mot']['mot_status'] = 'Valid'
                                elif 'expired' in text_lower or 'due' in text_lower:
                                    vehicle_data['tax_mot']['mot_status'] = 'Expired'
                            
                        # Look for days remaining
                        days_pattern = r'(\d+)\s*days'
                        days_match = re.search(days_pattern, text_lower)
                        if days_match:
                            days = days_match.group(1)
                            if 'tax' in text_lower:
                                vehicle_data['tax_mot']['tax_days_left'] = days
                            elif 'mot' in text_lower:
                                vehicle_data['tax_mot']['mot_days_left'] = days
                                
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"Error in TAX/MOT extraction: {e}")
    
    def _parse_data_from_text(self, vehicle_data: dict, text: str):
        """Parse vehicle data from a block of text"""
        try:
            import re
            
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if ':' not in line:
                    continue
                    
                parts = line.split(':', 1)
                if len(parts) != 2:
                    continue
                    
                key = parts[0].strip().lower()
                value = parts[1].strip()
                
                if not value or value.lower() in ['unknown', 'n/a', '-', '']:
                    continue
                
                # Map common vehicle data fields
                if 'make' in key or 'manufacturer' in key or 'brand' in key:
                    vehicle_data['basic_info']['make'] = value
                elif 'model' in key:
                    vehicle_data['basic_info']['model'] = value
                    # If we have a model but no make, try to infer make from common patterns
                    if not vehicle_data['basic_info'].get('make'):
                        # Common make-model patterns
                        model_to_make = {
                            'compass': 'Jeep',
                            'wrangler': 'Jeep', 
                            'cherokee': 'Jeep',
                            'focus': 'Ford',
                            'fiesta': 'Ford',
                            'golf': 'Volkswagen',
                            'polo': 'Volkswagen',
                            'corolla': 'Toyota',
                            'civic': 'Honda',
                            'accord': 'Honda'
                        }
                        model_lower = value.lower()
                        for model_name, make_name in model_to_make.items():
                            if model_name in model_lower:
                                vehicle_data['basic_info']['make'] = make_name
                                break
                elif 'year' in key or 'registration year' in key:
                    year_match = re.search(r'(\d{4})', value)
                    if year_match:
                        vehicle_data['basic_info']['year'] = year_match.group(1)
                elif 'colour' in key or 'color' in key:
                    vehicle_data['basic_info']['color'] = value
                elif 'fuel' in key:
                    vehicle_data['basic_info']['fuel_type'] = value
                elif 'engine' in key:
                    vehicle_data['vehicle_details']['engine_size'] = value
                elif 'transmission' in key:
                    vehicle_data['vehicle_details']['transmission'] = value
                elif 'body' in key:
                    vehicle_data['vehicle_details']['body_style'] = value
                elif 'doors' in key:
                    vehicle_data['vehicle_details']['doors'] = value
                    
        except Exception as e:
            logger.error(f"Error parsing text data: {e}")
    
    def _extract_from_text_patterns(self, vehicle_data: dict, page_source: str):
        """Extract vehicle data using text pattern matching"""
        try:
            import re
            
            # Vehicle make and model patterns
            make_patterns = [
                r'Make[:\s]+([A-Z][A-Za-z\s]+)',
                r'Manufacturer[:\s]+([A-Z][A-Za-z\s]+)',
                r'Brand[:\s]+([A-Z][A-Za-z\s]+)'
            ]
            
            for pattern in make_patterns:
                match = re.search(pattern, page_source, re.IGNORECASE)
                if match:
                    vehicle_data['basic_info']['make'] = match.group(1).strip()
                    break
            
            # Model patterns
            model_patterns = [
                r'Model[:\s]+([A-Za-z0-9\s\-]+)',
                r'Vehicle Model[:\s]+([A-Za-z0-9\s\-]+)'
            ]
            
            for pattern in model_patterns:
                match = re.search(pattern, page_source, re.IGNORECASE)
                if match:
                    vehicle_data['basic_info']['model'] = match.group(1).strip()
                    break
            
            # Year patterns
            year_patterns = [
                r'Year[:\s]+(\d{4})',
                r'Registration Year[:\s]+(\d{4})',
                r'Model Year[:\s]+(\d{4})'
            ]
            
            for pattern in year_patterns:
                match = re.search(pattern, page_source, re.IGNORECASE)
                if match:
                    vehicle_data['basic_info']['year'] = match.group(1)
                    break
            
            # Color patterns
            color_patterns = [
                r'Colour[:\s]+([A-Za-z\s]+)',
                r'Color[:\s]+([A-Za-z\s]+)'
            ]
            
            for pattern in color_patterns:
                match = re.search(pattern, page_source, re.IGNORECASE)
                if match:
                    color = match.group(1).strip()
                    if len(color) < 30:  # Reasonable color name length
                        vehicle_data['basic_info']['color'] = color
                    break
            
            # Fuel type patterns
            fuel_patterns = [
                r'Fuel[:\s]+([A-Za-z\s]+)',
                r'Fuel Type[:\s]+([A-Za-z\s]+)'
            ]
            
            for pattern in fuel_patterns:
                match = re.search(pattern, page_source, re.IGNORECASE)
                if match:
                    fuel = match.group(1).strip()
                    if len(fuel) < 20:  # Reasonable fuel type length
                        vehicle_data['basic_info']['fuel_type'] = fuel
                    break
                        
        except Exception as e:
            logger.error(f"Error in text pattern extraction: {e}")
    
    def _extract_from_elements(self, vehicle_data: dict):
        """Extract vehicle data from page elements"""
        try:
            # Look for elements containing vehicle information
            all_elements = self.driver.find_elements(By.XPATH, "//*[text()]")
            
            for element in all_elements:
                try:
                    text = element.text.strip()
                    if not text:
                        continue
                    
                    # Check for make/model/year in element text
                    if 'make' in text.lower() and ':' in text:
                        parts = text.split(':')
                        if len(parts) >= 2:
                            vehicle_data['basic_info']['make'] = parts[1].strip()
                    
                    elif 'model' in text.lower() and ':' in text:
                        parts = text.split(':')
                        if len(parts) >= 2:
                            vehicle_data['basic_info']['model'] = parts[1].strip()
                    
                    elif 'year' in text.lower() and ':' in text:
                        parts = text.split(':')
                        if len(parts) >= 2:
                            year_text = parts[1].strip()
                            year_match = re.search(r'(\d{4})', year_text)
                            if year_match:
                                vehicle_data['basic_info']['year'] = year_match.group(1)
                    
                    elif 'colour' in text.lower() and ':' in text:
                        parts = text.split(':')
                        if len(parts) >= 2:
                            vehicle_data['basic_info']['color'] = parts[1].strip()
                    
                    elif 'fuel' in text.lower() and ':' in text:
                        parts = text.split(':')
                        if len(parts) >= 2:
                            vehicle_data['basic_info']['fuel_type'] = parts[1].strip()
                            
                except Exception as e:
                    continue
                    
        except Exception as e:
            logger.error(f"Error in element extraction: {e}")
    
    def _extract_from_tables(self, vehicle_data: dict):
        """Extract vehicle data from table structures"""
        try:
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            for table in tables:
                rows = table.find_elements(By.TAG_NAME, "tr")
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        key = cells[0].text.strip().lower()
                        value = cells[1].text.strip()
                        
                        if 'make' in key:
                            vehicle_data['basic_info']['make'] = value
                        elif 'model' in key:
                            vehicle_data['basic_info']['model'] = value
                        elif 'year' in key:
                            vehicle_data['basic_info']['year'] = value
                        elif 'colour' in key or 'color' in key:
                            vehicle_data['basic_info']['color'] = value
                        elif 'fuel' in key:
                            vehicle_data['basic_info']['fuel_type'] = value
                        elif 'engine' in key:
                            vehicle_data['vehicle_details']['engine_size'] = value
                        elif 'transmission' in key:
                            vehicle_data['vehicle_details']['transmission'] = value
                            
        except Exception as e:
            logger.error(f"Error in table extraction: {e}")
    
    def _extract_legacy_data(self, vehicle_data: dict):
        """Legacy extraction method - keeping original patterns"""
        try:
            # Extract TAX information
            try:
                tax_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'TAX')]")
                for element in tax_elements:
                    parent = element.find_element(By.XPATH, "..")
                    text = parent.text
                    if 'Expires:' in text:
                        # Extract expiry date
                        date_match = re.search(r'Expires:\s*(\d{1,2}\s+\w+\s+\d{4})', text)
                        if date_match:
                            vehicle_data['tax_mot']['tax_expiry'] = date_match.group(1)
                        
                        # Extract days left
                        days_match = re.search(r'(\d+)\s+days\s+left', text)
                        if days_match:
                            vehicle_data['tax_mot']['tax_days_left'] = days_match.group(1)
                        break
            except:
                pass
            
            # Extract MOT information
            try:
                mot_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'MOT')]")
                for element in mot_elements:
                    parent = element.find_element(By.XPATH, "..")
                    text = parent.text
                    if 'Expires:' in text:
                        # Extract expiry date
                        date_match = re.search(r'Expires:\s*(\d{1,2}\s+\w+\s+\d{4})', text)
                        if date_match:
                            vehicle_data['tax_mot']['mot_expiry'] = date_match.group(1)
                        
                        # Extract days left
                        days_match = re.search(r'(\d+)\s+days\s+left', text)
                        if days_match:
                            vehicle_data['tax_mot']['mot_days_left'] = days_match.group(1)
                        break
            except:
                pass
            
            # Extract vehicle details from tables
            try:
                tables = self.driver.find_elements(By.TAG_NAME, "table")
                for table in tables:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 2:
                            key = cells[0].text.strip()
                            value = cells[1].text.strip()
                            if key and value:
                                normalized_key = self._normalize_key(key)
                                vehicle_data['vehicle_details'][normalized_key] = value
            except:
                pass
            
            # Extract mileage information
            page_text = self.driver.page_source
            
            # Mileage patterns
            mileage_patterns = {
                'last_mot_mileage': r'Last MOT Mileage[:\s]+([^\n\r<]+)',
                'mileage_issues': r'Mileage Issues[:\s]+([^\n\r<]+)',
                'average': r'Average[:\s]+([^\n\r<]+)',
                'status': r'Status[:\s]+([^\n\r<]+)'
            }
            
            for key, pattern in mileage_patterns.items():
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    vehicle_data['mileage'][key] = match.group(1).strip()
            
            # Extract performance data
            performance_patterns = {
                'power': r'Power[:\s]+([^\n\r<]+)',
                'max_speed': r'Max Speed[:\s]+([^\n\r<]+)',
                'torque': r'Torque[:\s]+([^\n\r<]+)'
            }
            
            for key, pattern in performance_patterns.items():
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    vehicle_data['performance'][key] = match.group(1).strip()
            
            # Extract fuel economy
            fuel_patterns = {
                'urban': r'Urban[^:]*:[:\s]+([^\n\r<]+)',
                'extra_urban': r'Extra Urban[^:]*:[:\s]+([^\n\r<]+)',
                'combined': r'Combined[^:]*:[:\s]+([^\n\r<]+)'
            }
            
            for key, pattern in fuel_patterns.items():
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    vehicle_data['fuel_economy'][key] = match.group(1).strip()
            
            # Extract safety ratings
            safety_patterns = {
                'child': r'Child[:\s]+(\d+\s*%)',
                'adult': r'Adult[:\s]+(\d+\s*%)',
                'pedestrian': r'Pedestrian[:\s]+(\d+\s*%)'
            }
            
            for key, pattern in safety_patterns.items():
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    vehicle_data['safety'][key] = match.group(1).strip()
            
            # Extract additional information
            # CO2 emissions
            co2_match = re.search(r'(\d+)\s*g/km', page_text, re.IGNORECASE)
            if co2_match:
                vehicle_data['additional']['co2_emissions'] = f"{co2_match.group(1)} g/km"
            
            # Tax costs
            tax_12_match = re.search(r'Tax 12 Months Cost[:\s]+([^\n\r<]+)', page_text, re.IGNORECASE)
            if tax_12_match:
                vehicle_data['additional']['tax_12_months'] = tax_12_match.group(1).strip()
            
            tax_6_match = re.search(r'Tax 6 Months Cost[:\s]+([^\n\r<]+)', page_text, re.IGNORECASE)
            if tax_6_match:
                vehicle_data['additional']['tax_6_months'] = tax_6_match.group(1).strip()
            
            return vehicle_data
            
        except Exception as e:
            logger.error(f"Error extracting vehicle data: {e}")
            return vehicle_data
    
    def _normalize_key(self, key: str) -> str:
        """Normalize key names for consistent data structure"""
        return key.lower().replace(' ', '_').replace('/', '_').replace('-', '_').replace('(', '').replace(')', '')
    
    def _cleanup(self):
        """Clean up WebDriver resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")