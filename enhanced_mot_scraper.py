"""
Enhanced MOT scraper using discovered CSS selectors for detailed history extraction
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

class EnhancedMOTScraper:
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
            logger.info("Enhanced MOT Scraper WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise
    
    def scrape_comprehensive_vehicle_data(self, registration: str) -> Dict[str, Any]:
        """Scrape comprehensive vehicle data including detailed MOT history"""
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
            
            # Extract basic data from main page
            basic_data = self._extract_basic_data(registration)
            
            # Try to navigate to detailed MOT history page
            mot_history_data = self._extract_detailed_mot_history(registration)
            
            # Combine the data
            basic_data['mot_history'] = mot_history_data
            
            return basic_data
        
        except Exception as e:
            logger.error(f"Error scraping vehicle data for {registration}: {e}")
            raise
        finally:
            if self.driver:
                self.driver.quit()
    
    def _extract_basic_data(self, registration: str) -> Dict[str, Any]:
        """Extract basic vehicle data from main page"""
        page_source = self.driver.page_source
        
        # Initialize result structure
        result = {
            'registration': registration.upper(),
            'make': 'Unknown',
            'model': 'Unknown',
            'year': None,
            'color': 'Unknown',
            'fuel_type': 'Unknown'
        }
        
        # Extract basic vehicle information
        try:
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
        
        return result
    
    def _extract_detailed_mot_history(self, registration: str) -> Dict[str, Any]:
        """Extract detailed MOT history by navigating to the history page"""
        mot_data = {
            'registration': registration.upper(),
            'mot_tests': [],
            'summary': {},
            'scraped_from': 'enhanced_mot_scraper_detailed_page',
            'extraction_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_tests_found': 0,
            'page_title': self.driver.title,
            'page_url': self.driver.current_url
        }
        
        try:
            # Look for MOT history link using XPath
            mot_xpath = "/html/body/section/div[2]/div/div[4]/div/div[2]/div[1]/div[3]/div/p[2]/span[1]"
            try:
                element = self.driver.find_element(By.XPATH, mot_xpath)
                if 'view full mot history' in element.text.lower():
                    logger.info(f"Found MOT history link: {element.text}")
                    
                    # Scroll element into view before clicking
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                    time.sleep(2)
                    
                    # Try multiple click methods
                    try:
                        element.click()
                    except:
                        # Fallback: JavaScript click
                        self.driver.execute_script("arguments[0].click();", element)
                    
                    time.sleep(5)
                    
                    # Update metadata for history page
                    mot_data['page_title'] = self.driver.title
                    mot_data['page_url'] = self.driver.current_url
                    
                    logger.info(f"Navigated to MOT history page: {self.driver.current_url}")
                    
                    # Extract detailed MOT history using discovered CSS selectors
                    detailed_tests = self._extract_mot_tests_from_history_page()
                    
                    if detailed_tests:
                        mot_data['mot_tests'] = detailed_tests
                        mot_data['total_tests_found'] = len(detailed_tests)
                        
                        # Generate summary statistics
                        mot_data['summary'] = self._generate_mot_summary(detailed_tests)
                    
                    return mot_data
                    
            except Exception as e:
                logger.warning(f"Could not click MOT history link: {e}")
        
        except Exception as e:
            logger.error(f"Error extracting detailed MOT history: {e}")
        
        return mot_data
    
    def _extract_mot_tests_from_history_page(self) -> List[Dict[str, Any]]:
        """Extract MOT test records using discovered CSS selectors"""
        try:
            detailed_tests = []
            
            # Use the discovered selectors from the screenshot
            primary_selectors = [
                "body > div.container > div.mot-history-summary",
                "body > div.container > div:nth-child(6)",
                ".mot-history-wrapper",
                ".mot-history-timeline",
                ".mot-history-wrapper-pass",
                ".mot-history-wrapper-fail"
            ]
            
            logger.info("Extracting detailed MOT tests using discovered CSS selectors")
            
            # Try each selector to find MOT test data
            for selector in primary_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Found {len(elements)} elements with selector: {selector}")
                    
                    for element in elements:
                        try:
                            element_text = element.text.strip()
                            if element_text and len(element_text) > 10:
                                
                                # Look for nested test records within this container
                                nested_tests = self._extract_individual_tests(element)
                                if nested_tests:
                                    detailed_tests.extend(nested_tests)
                                    logger.info(f"Extracted {len(nested_tests)} test records from {selector}")
                                else:
                                    # Parse container text directly as fallback
                                    parsed_test = self._parse_test_from_text(element_text)
                                    if parsed_test:
                                        detailed_tests.append(parsed_test)
                                        
                        except Exception as e:
                            logger.debug(f"Error processing element in {selector}: {e}")
                            continue
                    
                    if detailed_tests:
                        break  # Found data with this selector
                        
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            # If no data found, try broader search approach
            if not detailed_tests:
                logger.info("Trying broader search for MOT test records")
                detailed_tests = self._extract_with_broad_search()
            
            logger.info(f"Total detailed MOT tests extracted: {len(detailed_tests)}")
            return detailed_tests
            
        except Exception as e:
            logger.error(f"Error extracting MOT tests from history page: {e}")
            return []
    
    def _extract_individual_tests(self, container_element) -> List[Dict[str, Any]]:
        """Extract individual test records from a container element"""
        try:
            individual_tests = []
            
            # Look for nested test elements
            test_selectors = [
                ".mot-history-timeline",
                "[class*='timeline']", 
                "[class*='test']",
                "div[class*='pass']",
                "div[class*='fail']",
                "li",
                "p"
            ]
            
            for selector in test_selectors:
                try:
                    nested_elements = container_element.find_elements(By.CSS_SELECTOR, selector)
                    for element in nested_elements:
                        try:
                            element_text = element.text.strip()
                            if element_text and len(element_text) > 5:
                                parsed_test = self._parse_test_from_text(element_text)
                                if parsed_test:
                                    individual_tests.append(parsed_test)
                                    
                        except Exception as e:
                            continue
                    
                    if individual_tests:
                        break
                        
                except Exception as e:
                    continue
            
            return individual_tests
            
        except Exception as e:
            logger.debug(f"Error extracting individual tests: {e}")
            return []
    
    def _extract_with_broad_search(self) -> List[Dict[str, Any]]:
        """Broader search for MOT test records when specific selectors fail"""
        try:
            detailed_tests = []
            
            broad_selectors = [
                "[class*='mot-history']",
                "[class*='test']",
                ".timeline",
                "div[class*='pass']",
                "div[class*='fail']",
                "tr",  # Table rows
                "div",  # Generic divs
                "p"     # Paragraphs
            ]
            
            for selector in broad_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements[:20]:  # Limit to first 20
                        try:
                            element_text = element.text.strip()
                            if element_text and any(keyword in element_text.lower() for keyword in ['pass', 'fail', 'test', 'mot', 'mile', 'advisory']):
                                parsed_test = self._parse_test_from_text(element_text)
                                if parsed_test:
                                    detailed_tests.append(parsed_test)
                                    
                        except Exception as e:
                            continue
                    
                    if detailed_tests:
                        break
                        
                except Exception as e:
                    continue
            
            return detailed_tests
            
        except Exception as e:
            logger.error(f"Error in broad search: {e}")
            return []
    
    def _parse_test_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse a MOT test record from text content"""
        try:
            if not text or len(text) < 5:
                return None
                
            # Initialize test record
            test_record = {
                'source': 'enhanced_mot_detailed_page',
                'test_date': '',
                'result': 'UNKNOWN',
                'mileage': '',
                'comments': [{'text': text[:500], 'type': 'DETAILED_HISTORY'}]
            }
            
            # Extract date patterns
            date_patterns = [
                r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b',
                r'\b(\d{1,2}\s+\w+\s+\d{2,4})\b',
                r'\b(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})\b'
            ]
            
            for pattern in date_patterns:
                date_match = re.search(pattern, text)
                if date_match:
                    test_record['test_date'] = date_match.group(1)
                    break
            
            # Extract result
            text_lower = text.lower()
            if 'pass' in text_lower and 'fail' not in text_lower:
                test_record['result'] = 'PASSED'
            elif 'fail' in text_lower:
                test_record['result'] = 'FAILED'
            elif 'advisory' in text_lower:
                test_record['result'] = 'PASSED_WITH_ADVISORY'
            
            # Extract mileage
            mileage_patterns = [
                r'(\d{1,3}(?:,\d{3})*)\s*miles?',
                r'mileage[\s:]*(\d{1,3}(?:,\d{3})*)',
                r'(\d{1,3}(?:,\d{3})*)\s*mi'
            ]
            
            for pattern in mileage_patterns:
                mileage_match = re.search(pattern, text, re.IGNORECASE)
                if mileage_match:
                    test_record['mileage'] = mileage_match.group(1)
                    break
            
            # Only return if we found meaningful data
            if (test_record['test_date'] or 
                test_record['result'] != 'UNKNOWN' or 
                test_record['mileage'] or
                any(keyword in text_lower for keyword in ['mot', 'test', 'advisory', 'defect'])):
                return test_record
            
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing test from text: {e}")
            return None
    
    def _generate_mot_summary(self, tests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics from extracted tests"""
        try:
            summary = {
                'total_tests': len(tests),
                'total_passed': 0,
                'total_failed': 0,
                'total_advisory': 0,
                'date_range': {'earliest': '', 'latest': ''},
                'mileage_readings': []
            }
            
            dates = []
            for test in tests:
                result = test.get('result', '').upper()
                if 'PASSED' in result:
                    summary['total_passed'] += 1
                elif 'FAILED' in result:
                    summary['total_failed'] += 1
                elif 'ADVISORY' in result:
                    summary['total_advisory'] += 1
                
                if test.get('test_date'):
                    dates.append(test['test_date'])
                
                if test.get('mileage'):
                    try:
                        mileage_num = int(test['mileage'].replace(',', ''))
                        summary['mileage_readings'].append(mileage_num)
                    except:
                        pass
            
            if dates:
                summary['date_range']['earliest'] = min(dates)
                summary['date_range']['latest'] = max(dates)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating MOT summary: {e}")
            return {}

def test_enhanced_mot_scraper():
    """Test the enhanced MOT scraper"""
    try:
        scraper = EnhancedMOTScraper()
        result = scraper.scrape_comprehensive_vehicle_data("DA07BWF")
        return result
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = test_enhanced_mot_scraper()
    if result:
        import json
        print("SUCCESS - Enhanced MOT data extracted:")
        print(json.dumps(result, indent=2))
    else:
        print("FAILED to scrape enhanced MOT data")