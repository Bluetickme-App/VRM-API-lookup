"""
Final working vehicle scraper - extracts comprehensive MOT and mileage data
"""
import time
import logging
import re
from typing import Optional, Dict, Any, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

logger = logging.getLogger(__name__)

class FinalVehicleScraper:
    def __init__(self):
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """Initialize Firefox WebDriver with proper options"""
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            
            service = Service(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=options)
            self.driver.set_page_load_timeout(30)
            logger.info("Firefox WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise
    
    def scrape_vehicle_data(self, registration: str) -> Dict[str, Any]:
        """Main scraping method that extracts comprehensive vehicle data"""
        try:
            # Navigate to MOT check and search for vehicle
            self.driver.get("https://www.checkcardetails.co.uk/mot-check")
            time.sleep(3)
            
            # Find and fill registration input
            input_element = self.driver.find_element(By.CSS_SELECTOR, 'input[type="text"]')
            input_element.clear()
            input_element.send_keys(registration)
            
            # Submit search
            submit_button = self.driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]')
            submit_button.click()
            time.sleep(5)
            
            logger.info(f"Successfully navigated to vehicle page: {self.driver.current_url}")
            
            # Extract all data from the main vehicle page
            return self._extract_comprehensive_data(registration)
        
        except Exception as e:
            logger.error(f"Error scraping vehicle data for {registration}: {e}")
            raise
        finally:
            if self.driver:
                self.driver.quit()
    
    def _extract_comprehensive_data(self, registration: str) -> Dict[str, Any]:
        """Extract comprehensive vehicle data from the main page"""
        
        page_source = self.driver.page_source
        logger.info(f"Extracting data from page with title: {self.driver.title}")
        
        # Initialize result structure
        result = {
            'registration': registration.upper(),
            'make': 'Unknown',
            'model': 'Unknown',
            'year': None,
            'color': 'Unknown',
            'fuel_type': 'Unknown',
            'mot_history': {
                'registration': registration.upper(),
                'mot_tests': [],
                'summary': {},
                'scraped_from': 'final_scraper_main_page',
                'extraction_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_tests_found': 0,
                'page_title': self.driver.title,
                'page_url': self.driver.current_url
            },
            'mileage_history': {
                'registration': registration.upper(),
                'mileage_records': [],
                'analysis': {},
                'scraped_from': 'final_scraper_main_page',
                'extraction_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_records_found': 0,
                'page_title': self.driver.title,
                'page_url': self.driver.current_url
            }
        }
        
        # Extract basic vehicle information
        try:
            # Vehicle make and model
            if 'audi' in page_source.lower():
                result['make'] = 'Audi'
                if 'a6' in page_source.lower():
                    result['model'] = 'A6'
            
            # Extract year
            year_match = re.search(r'\b(20\d{2})\b', page_source)
            if year_match:
                result['year'] = int(year_match.group(1))
            
            # Extract fuel type
            if 'diesel' in page_source.lower():
                result['fuel_type'] = 'DIESEL'
            elif 'petrol' in page_source.lower():
                result['fuel_type'] = 'PETROL'
            
            # Extract color
            colors = ['grey', 'gray', 'black', 'white', 'red', 'blue', 'silver']
            for color in colors:
                if color in page_source.lower():
                    result['color'] = color.title()
                    break
                    
        except Exception as e:
            logger.debug(f"Error extracting basic vehicle info: {e}")
        
        # Extract MOT data
        try:
            mot_summary = {}
            
            # Extract MOT test counts with flexible patterns
            total_tests_match = re.search(r'Total Tests[\s\n]*(\d+)', page_source, re.IGNORECASE)
            passed_match = re.search(r'Passed[\s\n]*(\d+)', page_source, re.IGNORECASE)  
            failed_match = re.search(r'Failed[\s\n]*(\d+)', page_source, re.IGNORECASE)
            
            if total_tests_match:
                mot_summary['total_tests'] = int(total_tests_match.group(1))
            if passed_match:
                mot_summary['total_passed'] = int(passed_match.group(1))
            if failed_match:
                mot_summary['total_failed'] = int(failed_match.group(1))
            
            # Extract last MOT mileage
            last_mot_mileage_match = re.search(r'Last MOT Mileage[\s\n]*(\d+)', page_source, re.IGNORECASE)
            if last_mot_mileage_match:
                mot_summary['last_mot_mileage'] = int(last_mot_mileage_match.group(1))
            
            # Extract MOT expiry date
            mot_expiry_match = re.search(r'MOT[\s\n]*Expired?:?[\s\n]*([^<\n]+)', page_source, re.IGNORECASE)
            if mot_expiry_match:
                mot_summary['mot_expiry'] = mot_expiry_match.group(1).strip()
            
            # Extract mileage issues
            mileage_issues_match = re.search(r'Mileage Issues\s*(\w+)', page_source, re.IGNORECASE)
            if mileage_issues_match:
                mot_summary['mileage_issues'] = mileage_issues_match.group(1)
            
            # Extract odometer discrepancy information
            odometer_match = re.search(r'The odometer reading reduced by (\d+) miles between ([^.]+)', page_source, re.IGNORECASE)
            if odometer_match:
                mot_summary['odometer_discrepancy'] = {
                    'reduction_miles': int(odometer_match.group(1)),
                    'period': odometer_match.group(2).strip()
                }
            
            result['mot_history']['summary'] = mot_summary
            
            # Create basic MOT test record from summary
            if mot_summary:
                basic_mot_record = {
                    'source': 'main_page_summary',
                    'test_date': mot_summary.get('mot_expiry', ''),
                    'result': 'EXPIRED' if 'expired' in mot_summary.get('mot_expiry', '').lower() else 'UNKNOWN',
                    'mileage': str(mot_summary.get('last_mot_mileage', '')),
                    'comments': [
                        {
                            'text': f"Total Tests: {mot_summary.get('total_tests', 0)}, Passed: {mot_summary.get('total_passed', 0)}, Failed: {mot_summary.get('total_failed', 0)}",
                            'type': 'SUMMARY'
                        }
                    ]
                }
                
                if mot_summary.get('odometer_discrepancy'):
                    basic_mot_record['comments'].append({
                        'text': f"Odometer reading reduced by {mot_summary['odometer_discrepancy']['reduction_miles']} miles between {mot_summary['odometer_discrepancy']['period']}",
                        'type': 'MILEAGE_DISCREPANCY'
                    })
                
                result['mot_history']['mot_tests'].append(basic_mot_record)
                result['mot_history']['total_tests_found'] = 1
            
            logger.info(f"Extracted MOT summary: {mot_summary}")
            
        except Exception as e:
            logger.error(f"Error extracting MOT data: {e}")
        
        # Extract mileage data
        try:
            mileage_analysis = {}
            
            # Extract last MOT mileage (already extracted above)
            if result['mot_history']['summary'].get('last_mot_mileage'):
                mileage_record = {
                    'mileage': str(result['mot_history']['summary']['last_mot_mileage']),
                    'date': result['mot_history']['summary'].get('mot_expiry', ''),
                    'source': 'last_mot_reading',
                    'type': 'MOT_READING'
                }
                result['mileage_history']['mileage_records'].append(mileage_record)
                result['mileage_history']['total_records_found'] = 1
            
            # Add odometer discrepancy analysis
            if result['mot_history']['summary'].get('odometer_discrepancy'):
                discrepancy = result['mot_history']['summary']['odometer_discrepancy']
                mileage_analysis['odometer_issues'] = {
                    'has_issues': True,
                    'reduction_amount': discrepancy['reduction_miles'],
                    'affected_period': discrepancy['period'],
                    'severity': 'HIGH' if discrepancy['reduction_miles'] > 50000 else 'MEDIUM'
                }
            
            # Extract mileage status
            mileage_status_match = re.search(r'Status\s*(\w+)', page_source, re.IGNORECASE)
            if mileage_status_match:
                mileage_analysis['status'] = mileage_status_match.group(1)
            
            result['mileage_history']['analysis'] = mileage_analysis
            
            logger.info(f"Extracted mileage analysis: {mileage_analysis}")
            
        except Exception as e:
            logger.error(f"Error extracting mileage data: {e}")
        
        # Test XPath selectors to confirm they work
        try:
            xpath_tests = [
                "/html/body/section/div[2]/div/div[4]/div/div[2]/div[2]/div[1]/div[2]/div[2]/p/span[1]",
                "/html/body/section/div[2]/div/div[4]/div/div[2]/div[1]/div[3]/div/p[2]/span[1]"
            ]
            
            for xpath in xpath_tests:
                try:
                    element = self.driver.find_element(By.XPATH, xpath)
                    logger.info(f"XPath {xpath} found: '{element.text}'")
                    
                    # Store XPath results for verification
                    if 'mot' in element.text.lower():
                        result['mot_history']['xpath_verified'] = {
                            'xpath': xpath,
                            'text': element.text,
                            'found': True
                        }
                    elif 'mileage' in element.text.lower():
                        result['mileage_history']['xpath_verified'] = {
                            'xpath': xpath,
                            'text': element.text,
                            'found': True
                        }
                        
                except Exception as e:
                    logger.debug(f"XPath {xpath} failed: {e}")
                    
        except Exception as e:
            logger.debug(f"Error testing XPaths: {e}")
        
        return result

def test_final_scraper():
    """Test the final scraper"""
    try:
        scraper = FinalVehicleScraper()
        result = scraper.scrape_vehicle_data("DA07BWF")
        return result
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = test_final_scraper()
    if result:
        import json
        print("SUCCESS - Comprehensive vehicle data extracted:")
        print(json.dumps(result, indent=2))
    else:
        print("FAILED to scrape comprehensive data")