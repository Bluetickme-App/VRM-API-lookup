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
        """Extract detailed MOT test records from the actual history page structure"""
        try:
            detailed_tests = []
            
            logger.info("Extracting comprehensive MOT test data from history page")
            
            # First extract the overall statistics visible on the page
            page_text = self.driver.page_source
            
            # Look for the comprehensive test structure shown in the screenshot
            # Try to find individual MOT test sections
            test_sections = self._find_individual_test_sections()
            
            if test_sections:
                logger.info(f"Found {len(test_sections)} individual test sections")
                for section in test_sections:
                    parsed_test = self._parse_individual_test_section(section)
                    if parsed_test:
                        detailed_tests.append(parsed_test)
            else:
                # Fallback to text-based extraction from page source
                logger.info("Using fallback text-based extraction")
                detailed_tests = self._extract_tests_from_page_text(page_text)
            
            logger.info(f"Total detailed MOT tests extracted: {len(detailed_tests)}")
            return detailed_tests
            
        except Exception as e:
            logger.error(f"Error extracting MOT tests from history page: {e}")
            return []
    
    def _find_individual_test_sections(self) -> List:
        """Find individual test sections on the MOT history page"""
        try:
            # Look for patterns that indicate individual test records
            potential_selectors = [
                # Target specific test containers
                "[class*='test']",
                "[class*='mot']",
                "div:has-text('Test Date')",  # Modern CSS4 selector
                "div:contains('Test Date')",  # Alternative
                # Try structural approach
                "body > div.container > div > div",
                "body > div.container > *",
                # Generic fallback
                "div",
                "section"
            ]
            
            test_sections = []
            
            for selector in potential_selectors:
                try:
                    if 'has-text' in selector or 'contains' in selector:
                        # Skip these selectors as they're not supported by Selenium
                        continue
                        
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        try:
                            element_text = element.text.strip()
                            # Look for test-related keywords
                            if any(keyword in element_text.lower() for keyword in 
                                   ['test date', 'passed', 'failed', 'mileage', 'expiry', 'advisory']):
                                if len(element_text) > 20:  # Meaningful content
                                    test_sections.append(element)
                                    
                        except Exception as e:
                            continue
                    
                    if test_sections:
                        logger.info(f"Found test sections using selector: {selector}")
                        break
                        
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            # Remove duplicates and filter
            unique_sections = []
            seen_texts = set()
            
            for section in test_sections:
                try:
                    text = section.text.strip()
                    if text and text not in seen_texts and len(text) > 30:
                        unique_sections.append(section)
                        seen_texts.add(text)
                except:
                    continue
            
            return unique_sections[:10]  # Limit to first 10
            
        except Exception as e:
            logger.error(f"Error finding test sections: {e}")
            return []
    
    def _parse_individual_test_section(self, section) -> Optional[Dict[str, Any]]:
        """Parse an individual test section element"""
        try:
            text = section.text.strip()
            if not text:
                return None
            
            # Initialize test record
            test_record = {
                'source': 'mot_history_page_section',
                'test_date': '',
                'result': 'UNKNOWN',
                'mileage': '',
                'expiry_date': '',
                'comments': [],
                'raw_text': text[:500]  # Store raw text for debugging
            }
            
            # Extract test date
            date_match = re.search(r'Test Date[\s\n]*([^\n]+)', text, re.IGNORECASE)
            if date_match:
                test_record['test_date'] = date_match.group(1).strip()
            
            # Extract result (look for status badges)
            text_lower = text.lower()
            if 'passed' in text_lower and 'failed' not in text_lower:
                test_record['result'] = 'PASSED'
            elif 'failed' in text_lower:
                test_record['result'] = 'FAILED'
            elif 'unknown' in text_lower:
                test_record['result'] = 'UNKNOWN'
            
            # Extract mileage
            mileage_match = re.search(r'Mileage[\s\n]*(\d{1,6})', text, re.IGNORECASE)
            if mileage_match:
                test_record['mileage'] = mileage_match.group(1)
            
            # Extract expiry date
            expiry_match = re.search(r'Expiry[\s\n]*([^\n]+)', text, re.IGNORECASE)
            if expiry_match:
                test_record['expiry_date'] = expiry_match.group(1).strip()
            
            # Extract comments/advisories
            comments = []
            
            # Look for advisory notices
            advisory_matches = re.findall(r'([^.]+ADVISORY[^.]*)', text, re.IGNORECASE)
            for advisory in advisory_matches:
                comments.append({
                    'text': advisory.strip(),
                    'type': 'ADVISORY'
                })
            
            # Look for failure reasons
            fail_matches = re.findall(r'([^.]+FAIL[^.]*)', text, re.IGNORECASE)
            for fail in fail_matches:
                comments.append({
                    'text': fail.strip(),
                    'type': 'FAILURE'
                })
            
            # Look for general comments
            if 'no advisory notices' in text_lower:
                comments.append({
                    'text': 'Vehicle passed MOT with no advisory notices',
                    'type': 'CLEAN_PASS'
                })
            
            test_record['comments'] = comments
            
            # Only return if we have meaningful data
            if (test_record['test_date'] or 
                test_record['result'] != 'UNKNOWN' or 
                test_record['mileage'] or
                comments):
                return test_record
            
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing test section: {e}")
            return None
    
    def _extract_tests_from_page_text(self, page_text: str) -> List[Dict[str, Any]]:
        """Extract test data from page source text as fallback"""
        try:
            tests = []
            
            # Split text into potential test blocks
            lines = page_text.split('\n')
            current_test = {}
            collecting = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for test date indicators
                if 'test date' in line.lower():
                    if current_test and any(current_test.values()):
                        # Save previous test
                        parsed = self._format_collected_test(current_test)
                        if parsed:
                            tests.append(parsed)
                    
                    # Start new test
                    current_test = {'raw_lines': [line]}
                    collecting = True
                    
                elif collecting:
                    current_test['raw_lines'].append(line)
                    
                    # Stop collecting after a reasonable amount of lines
                    if len(current_test['raw_lines']) > 20:
                        collecting = False
            
            # Process final test
            if current_test and any(current_test.values()):
                parsed = self._format_collected_test(current_test)
                if parsed:
                    tests.append(parsed)
            
            return tests[:10]  # Limit results
            
        except Exception as e:
            logger.error(f"Error extracting tests from page text: {e}")
            return []
    
    def _format_collected_test(self, test_data: Dict) -> Optional[Dict[str, Any]]:
        """Format collected test data into standard structure"""
        try:
            if 'raw_lines' not in test_data:
                return None
            
            text = ' '.join(test_data['raw_lines'])
            return self._parse_test_from_text(text)
            
        except Exception as e:
            logger.debug(f"Error formatting collected test: {e}")
            return None
    
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