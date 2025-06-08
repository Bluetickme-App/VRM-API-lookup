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
            
            # Basic Firefox options
            firefox_options.add_argument('--no-sandbox')
            firefox_options.add_argument('--disable-dev-shm-usage')
            firefox_options.add_argument('--window-size=1920,1080')
            
            # Use webdriver-manager to get compatible geckodriver
            try:
                service = Service(GeckoDriverManager().install())
                self.driver = webdriver.Firefox(service=service, options=firefox_options)
            except Exception as service_error:
                logger.warning(f"WebDriver manager failed: {service_error}, trying system geckodriver")
                # Fallback to system geckodriver
                self.driver = webdriver.Firefox(options=firefox_options)
            
            self.wait = WebDriverWait(self.driver, 20)
            
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
                
                # Wait for results page
                time.sleep(8)
                
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
            # Extract basic vehicle title
            try:
                title_elements = self.driver.find_elements(By.TAG_NAME, "h1")
                for element in title_elements:
                    text = element.text.strip()
                    if text and len(text) > 3:
                        vehicle_data['basic_info']['title'] = text
                        break
            except:
                pass
            
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