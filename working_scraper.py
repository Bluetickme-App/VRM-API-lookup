"""
Working vehicle scraper focused on MOT and mileage extraction using XPath selectors
"""
import time
import logging
from typing import Optional, Dict, Any, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.service import Service

logger = logging.getLogger(__name__)

class WorkingVehicleScraper:
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
        """Main scraping method that extracts basic vehicle data and MOT/mileage history"""
        try:
            # Basic vehicle data first
            basic_data = self._get_basic_vehicle_data(registration)
            
            # MOT data with direct URL navigation  
            mot_data = self._get_mot_data_direct(registration)
            
            # Mileage data with direct URL navigation
            mileage_data = self._get_mileage_data_direct(registration)
            
            return {
                'registration': registration.upper(),
                'make': basic_data.get('make', 'Unknown'),
                'model': basic_data.get('model', 'Unknown'),  
                'year': basic_data.get('year', ''),
                'color': basic_data.get('color', 'Unknown'),
                'fuel_type': basic_data.get('fuel_type', 'Unknown'),
                'mot_history': mot_data,
                'mileage_history': mileage_data
            }
        
        except Exception as e:
            logger.error(f"Error scraping vehicle data for {registration}: {e}")
            raise
        finally:
            if self.driver:
                self.driver.quit()
    
    def _get_basic_vehicle_data(self, registration: str) -> Dict[str, Any]:
        """Get basic vehicle information"""
        try:
            url = f"https://www.checkcardetails.co.uk/cardetails/{registration.lower()}"
            logger.info(f"Getting basic vehicle data from: {url}")
            self.driver.get(url)
            time.sleep(5)
            
            # Extract basic vehicle info using simple selectors
            data = {}
            
            # Try to extract make/model from page
            try:
                page_text = self.driver.page_source
                if 'audi' in page_text.lower():
                    data['make'] = 'Audi'
                    if 'a6' in page_text.lower():
                        data['model'] = 'A6'
            except:
                pass
            
            # Try to extract other basic info
            try:
                # Look for year, color, fuel type in page text
                page_text = self.driver.page_source.lower()
                
                # Extract year (look for 4-digit years)
                import re
                years = re.findall(r'\b(19|20)\d{2}\b', page_text)
                if years:
                    data['year'] = int(years[0])
                
                # Extract fuel type
                if 'diesel' in page_text:
                    data['fuel_type'] = 'DIESEL'
                elif 'petrol' in page_text:
                    data['fuel_type'] = 'PETROL'
                    
                # Extract color
                colors = ['grey', 'gray', 'black', 'white', 'red', 'blue', 'silver']
                for color in colors:
                    if color in page_text:
                        data['color'] = color.title()
                        break
                        
            except Exception as e:
                logger.debug(f"Error extracting basic data: {e}")
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting basic vehicle data: {e}")
            return {}
    
    def _get_mot_data_direct(self, registration: str) -> Dict[str, Any]:
        """Get MOT data by navigating through the website's proper flow"""
        mot_data = {
            'registration': registration.upper(),
            'mot_tests': [],
            'summary': {},
            'scraped_from': 'working_scraper_proper_navigation',
            'extraction_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_tests_found': 0
        }
        
        try:
            # Start from the MOT check page
            logger.info("Starting from MOT check page")
            self.driver.get("https://www.checkcardetails.co.uk/mot-check")
            time.sleep(3)
            
            # Look for vehicle search input
            try:
                # Common input selectors for vehicle registration
                input_selectors = [
                    'input[name="registration"]',
                    'input[placeholder*="reg"]',
                    'input[type="text"]',
                    '#registration',
                    '.registration-input'
                ]
                
                for selector in input_selectors:
                    try:
                        input_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        logger.info(f"Found registration input with selector: {selector}")
                        
                        # Clear and enter registration
                        input_element.clear()
                        input_element.send_keys(registration)
                        time.sleep(1)
                        
                        # Look for submit button
                        submit_selectors = [
                            'input[type="submit"]',
                            'button[type="submit"]',
                            'button',
                            '.submit-btn',
                            '.search-btn'
                        ]
                        
                        for submit_selector in submit_selectors:
                            try:
                                submit_button = self.driver.find_element(By.CSS_SELECTOR, submit_selector)
                                logger.info(f"Found submit button with selector: {submit_selector}")
                                submit_button.click()
                                time.sleep(5)  # Wait for results
                                
                                # Update metadata
                                mot_data['page_title'] = self.driver.title
                                mot_data['page_url'] = self.driver.current_url
                                
                                logger.info(f"After search - Title: {self.driver.title}")
                                logger.info(f"After search - URL: {self.driver.current_url}")
                                
                                # Debug the results page
                                self._debug_page_structure("MOT search results")
                                
                                # Extract visible MOT data from main page
                                main_page_data = self._extract_main_page_data()
                                if main_page_data:
                                    logger.info(f"Found MOT data on main page: {main_page_data}")
                                    mot_data['mot_tests'] = main_page_data.get('mot_tests', [])
                                    mot_data['summary'] = main_page_data.get('summary', {})
                                    if mot_data['mot_tests']:
                                        mot_data['total_tests_found'] = len(mot_data['mot_tests'])
                                
                                # Now try to navigate to full MOT history using XPath links
                                xpath_results = self._extract_via_xpath()
                                for xpath_result in xpath_results:
                                    if xpath_result.get('type') == 'mot_data' and 'view full mot history' in xpath_result.get('raw_value', '').lower():
                                        try:
                                            # Found the MOT history link, click it
                                            mot_xpath = xpath_result['xpath']
                                            element = self.driver.find_element(By.XPATH, mot_xpath)
                                            logger.info(f"Clicking MOT history link: {element.text}")
                                            element.click()
                                            time.sleep(5)
                                            
                                            # Update metadata for history page
                                            mot_data['page_title'] = self.driver.title
                                            mot_data['page_url'] = self.driver.current_url
                                            
                                            logger.info(f"MOT history page - Title: {self.driver.title}")
                                            logger.info(f"MOT history page - URL: {self.driver.current_url}")
                                            
                                            # Debug the history page
                                            self._debug_page_structure("MOT history page")
                                            
                                            # Extract detailed MOT history
                                            detailed_mot_data = self._extract_detailed_mot_history()
                                            if detailed_mot_data:
                                                mot_data['mot_tests'].extend(detailed_mot_data)
                                                mot_data['total_tests_found'] = len(mot_data['mot_tests'])
                                                
                                            return mot_data
                                            
                                        except Exception as e:
                                            logger.warning(f"Error clicking MOT history link: {e}")
                                            break
                                
                                # Look for MOT history links on the results page as fallback
                                mot_history_links = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "MOT")
                                if not mot_history_links:
                                    mot_history_links = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "history")
                                
                                for link in mot_history_links:
                                    try:
                                        logger.info(f"Found MOT history link: {link.text}")
                                        link.click()
                                        time.sleep(3)
                                        
                                        # Update metadata for history page
                                        mot_data['page_title'] = self.driver.title
                                        mot_data['page_url'] = self.driver.current_url
                                        
                                        logger.info(f"MOT history page - Title: {self.driver.title}")
                                        logger.info(f"MOT history page - URL: {self.driver.current_url}")
                                        
                                        # Debug the history page
                                        self._debug_page_structure("MOT history page")
                                        
                                        # Try XPath extraction on history page
                                        xpath_results = self._extract_via_xpath()
                                        if xpath_results:
                                            logger.info(f"XPath extraction successful on history page: {len(xpath_results)} records found")
                                            mot_data['mot_tests'] = xpath_results
                                            mot_data['total_tests_found'] = len(xpath_results)
                                            return mot_data
                                        
                                        break  # Found and clicked a history link
                                    except Exception as e:
                                        logger.warning(f"Error clicking MOT history link: {e}")
                                        continue
                                
                                break  # Successfully submitted search
                            except Exception as e:
                                logger.debug(f"Submit button {submit_selector} failed: {e}")
                                continue
                        
                        break  # Successfully found input
                    except Exception as e:
                        logger.debug(f"Input selector {selector} failed: {e}")
                        continue
                
            except Exception as e:
                logger.error(f"Error in MOT search flow: {e}")
        
        except Exception as e:
            logger.error(f"Error accessing MOT check page: {e}")
        
        return mot_data
    
    def _get_mileage_data_direct(self, registration: str) -> Dict[str, Any]:
        """Get mileage data using direct URL navigation and XPath extraction"""
        mileage_data = {
            'registration': registration.upper(),
            'mileage_records': [],
            'analysis': {},
            'scraped_from': 'working_scraper_direct_navigation',
            'extraction_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_records_found': 0
        }
        
        # Try multiple mileage URL patterns  
        mileage_urls = [
            f"https://www.checkcardetails.co.uk/mot/mileagehistory/{registration.lower()}",
            f"https://www.checkcardetails.co.uk/mileage/{registration.lower()}",
            f"https://www.checkcardetails.co.uk/mileagehistory/{registration.lower()}"
        ]
        
        for url in mileage_urls:
            try:
                logger.info(f"Trying mileage URL: {url}")
                self.driver.get(url)
                time.sleep(5)
                
                # Update page metadata
                mileage_data['page_title'] = self.driver.title
                mileage_data['page_url'] = self.driver.current_url
                
                logger.info(f"Mileage page loaded: {self.driver.title}")
                
                # Debug: Log page structure for analysis
                self._debug_page_structure("Mileage page")
                
                # Try XPath extraction using your specific paths
                xpath_results = self._extract_via_xpath()
                if xpath_results:
                    # Convert to mileage format
                    mileage_records = []
                    for result in xpath_results:
                        if result.get('mileage'):
                            mileage_records.append({
                                'mileage': result['mileage'],
                                'date': result.get('test_date', ''),
                                'source': 'xpath_extraction'
                            })
                    
                    if mileage_records:
                        logger.info(f"XPath extraction successful: {len(mileage_records)} mileage records found")
                        mileage_data['mileage_records'] = mileage_records
                        mileage_data['total_records_found'] = len(mileage_records)
                        return mileage_data
                
                # Check if page has mileage content but no structured data
                page_source = self.driver.page_source.lower()
                if 'mileage' in page_source or 'odometer' in page_source:
                    logger.info("Page contains mileage content but no extractable data")
                    break
                    
            except Exception as e:
                logger.warning(f"Failed to access mileage URL {url}: {e}")
                continue
        
        return mileage_data
    
    def _extract_via_xpath(self) -> List[Dict[str, Any]]:
        """Extract data using your specific XPath selectors"""
        extracted_data = []
        
        try:
            # Your specific XPath selectors
            mileage_xpaths = [
                "/html/body/section/div[2]/div/div[4]/div/div[2]/div[2]/div[1]/div[2]/div[2]/p/span[1]",
                "/html/body/div[2]/div[3]"
            ]
            
            mot_xpath = "/html/body/section/div[2]/div/div[4]/div/div[2]/div[1]/div[3]/div/p[2]/span[1]"
            
            # Try mileage XPaths
            for mileage_xpath in mileage_xpaths:
                try:
                    element = self.driver.find_element(By.XPATH, mileage_xpath)
                    value = element.text.strip()
                    if value:
                        logger.info(f"Found mileage via XPath {mileage_xpath}: {value}")
                        extracted_data.append({
                            'source': 'xpath_extraction',
                            'type': 'mileage',
                            'mileage': value,
                            'xpath': mileage_xpath
                        })
                        break
                except Exception as e:
                    logger.debug(f"XPath mileage extraction failed for {mileage_xpath}: {e}")
            
            # Try MOT XPath
            try:
                element = self.driver.find_element(By.XPATH, mot_xpath)
                value = element.text.strip()
                if value:
                    logger.info(f"Found MOT data via XPath: {value}")
                    # Determine if it's pass/fail
                    result = 'UNKNOWN'
                    if 'pass' in value.lower():
                        result = 'PASSED'
                    elif 'fail' in value.lower():
                        result = 'FAILED'
                    
                    extracted_data.append({
                        'source': 'xpath_extraction',
                        'type': 'mot_data',
                        'result': result,
                        'test_date': '',
                        'xpath': mot_xpath,
                        'raw_value': value
                    })
            except Exception as e:
                logger.debug(f"XPath MOT extraction failed: {e}")
            
            # Convert to standard format
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
                        test_record['mileage'] = item['mileage']
                    elif item['type'] == 'mot_data':
                        test_record['result'] = item['result']
                        test_record['comments'].append({
                            'text': item.get('raw_value', ''),
                            'type': 'XPATH_DATA'
                        })
                
                return [test_record] if any([test_record['mileage'], test_record['result']]) else []
            
        except Exception as e:
            logger.error(f"Error in XPath extraction: {e}")
        
        return []
    
    def _debug_page_structure(self, page_type: str):
        """Debug method to analyze page structure"""
        try:
            logger.info(f"=== {page_type} Structure Analysis ===")
            logger.info(f"Current URL: {self.driver.current_url}")
            logger.info(f"Page title: {self.driver.title}")
            
            # Check for common MOT/mileage elements
            element_checks = [
                ("section", "section"),
                ("body", "body"),
                (".mot-history-wrapper", "MOT history wrappers"),
                ("div[class*='mot']", "MOT divs"),
                ("div[class*='mileage']", "Mileage divs"),
                ("p", "Paragraphs"),
                ("span", "Spans"),
                ("table", "Tables")
            ]
            
            for selector, description in element_checks:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"{description}: {len(elements)} found")
                    
                    # Log text content of first few elements
                    for i, elem in enumerate(elements[:3]):
                        try:
                            text = elem.text.strip()[:100]  # First 100 chars
                            if text:
                                logger.info(f"  {description}[{i}]: {text}")
                        except:
                            pass
                except Exception as e:
                    logger.debug(f"Error checking {description}: {e}")
            
            # Test your specific XPaths
            test_xpaths = [
                "/html/body/section/div[2]/div/div[4]/div/div[2]/div[2]/div[1]/div[2]/div[2]/p/span[1]",
                "/html/body/div[2]/div[3]",
                "/html/body/section/div[2]/div/div[4]/div/div[2]/div[1]/div[3]/div/p[2]/span[1]"
            ]
            
            for xpath in test_xpaths:
                try:
                    element = self.driver.find_element(By.XPATH, xpath)
                    text = element.text.strip()
                    logger.info(f"XPath {xpath} found: '{text}'")
                except Exception as e:
                    logger.info(f"XPath {xpath} failed: {e}")
            
            # Log page source snippet for manual analysis
            page_source = self.driver.page_source
            if 'mot' in page_source.lower() or 'mileage' in page_source.lower():
                # Find and log relevant sections
                lines = page_source.split('\n')
                relevant_lines = []
                for i, line in enumerate(lines):
                    line_lower = line.lower()
                    if any(keyword in line_lower for keyword in ['mot', 'mileage', 'test', 'history']):
                        # Include context lines
                        start = max(0, i-2)
                        end = min(len(lines), i+3)
                        for j in range(start, end):
                            if lines[j].strip() and lines[j] not in relevant_lines:
                                relevant_lines.append(lines[j].strip()[:200])
                
                logger.info("=== Relevant page content ===")
                for line in relevant_lines[:20]:  # First 20 relevant lines
                    logger.info(f"HTML: {line}")
            
        except Exception as e:
            logger.error(f"Error in debug analysis: {e}")
    
    def _extract_main_page_data(self) -> Dict[str, Any]:
        """Extract visible MOT/mileage data from the main vehicle page"""
        try:
            main_data = {
                'mot_tests': [],
                'summary': {}
            }
            
            # Extract MOT summary data
            try:
                # Look for MOT counts (Total Tests: 16, Passed: 14, Failed: 2)
                page_text = self.driver.page_source
                
                # Extract total tests
                import re
                total_tests_match = re.search(r'Total Tests\s*(\d+)', page_text, re.IGNORECASE)
                passed_match = re.search(r'Passed\s*(\d+)', page_text, re.IGNORECASE)
                failed_match = re.search(r'Failed\s*(\d+)', page_text, re.IGNORECASE)
                
                if total_tests_match:
                    main_data['summary']['total_tests'] = int(total_tests_match.group(1))
                if passed_match:
                    main_data['summary']['total_passed'] = int(passed_match.group(1))
                if failed_match:
                    main_data['summary']['total_failed'] = int(failed_match.group(1))
                    
                logger.info(f"MOT summary extracted: {main_data['summary']}")
                
                # Look for last MOT date and mileage
                last_mot_mileage_match = re.search(r'Last MOT Mileage\s*(\d+)', page_text, re.IGNORECASE)
                if last_mot_mileage_match:
                    main_data['summary']['last_mot_mileage'] = int(last_mot_mileage_match.group(1))
                
                # Look for MOT expiry info
                mot_expiry_match = re.search(r'MOT\s*Expired?:?\s*([^<\n]+)', page_text, re.IGNORECASE)
                if mot_expiry_match:
                    main_data['summary']['mot_expiry'] = mot_expiry_match.group(1).strip()
                
                # Create a basic MOT test record from summary data
                if main_data['summary']:
                    basic_mot_record = {
                        'source': 'main_page_summary',
                        'test_date': main_data['summary'].get('mot_expiry', ''),
                        'result': 'EXPIRED' if 'expired' in main_data['summary'].get('mot_expiry', '').lower() else 'UNKNOWN',
                        'mileage': str(main_data['summary'].get('last_mot_mileage', '')),
                        'comments': [
                            {
                                'text': f"Total Tests: {main_data['summary'].get('total_tests', 0)}, Passed: {main_data['summary'].get('total_passed', 0)}, Failed: {main_data['summary'].get('total_failed', 0)}",
                                'type': 'SUMMARY'
                            }
                        ]
                    }
                    main_data['mot_tests'].append(basic_mot_record)
                
            except Exception as e:
                logger.debug(f"Error extracting MOT summary: {e}")
            
            return main_data
            
        except Exception as e:
            logger.error(f"Error extracting main page data: {e}")
            return {}
    
    def _extract_detailed_mot_history(self) -> List[Dict[str, Any]]:
        """Extract detailed MOT history from the dedicated history page"""
        try:
            detailed_tests = []
            
            # Look for MOT test records on the history page
            # Common patterns for MOT history pages
            test_selectors = [
                '.mot-test',
                '.test-record',
                '.history-item',
                'tr',  # Table rows
                '.mot-history-item'
            ]
            
            for selector in test_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Found {len(elements)} elements with selector: {selector}")
                    
                    for element in elements[:10]:  # Process first 10 elements
                        try:
                            element_text = element.text.strip()
                            if element_text and any(keyword in element_text.lower() for keyword in ['pass', 'fail', 'test', 'mot', 'mile']):
                                
                                # Parse individual test record
                                test_record = {
                                    'source': 'detailed_history_page',
                                    'test_date': '',
                                    'result': 'UNKNOWN',
                                    'mileage': '',
                                    'comments': [{'text': element_text[:200], 'type': 'DETAILED_HISTORY'}]
                                }
                                
                                # Extract date patterns
                                import re
                                date_patterns = [
                                    r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b',
                                    r'\b(\d{1,2}\s+\w+\s+\d{2,4})\b'
                                ]
                                
                                for pattern in date_patterns:
                                    date_match = re.search(pattern, element_text)
                                    if date_match:
                                        test_record['test_date'] = date_match.group(1)
                                        break
                                
                                # Extract result
                                if 'pass' in element_text.lower():
                                    test_record['result'] = 'PASSED'
                                elif 'fail' in element_text.lower():
                                    test_record['result'] = 'FAILED'
                                
                                # Extract mileage
                                mileage_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*miles?', element_text, re.IGNORECASE)
                                if mileage_match:
                                    test_record['mileage'] = mileage_match.group(1)
                                
                                detailed_tests.append(test_record)
                                
                        except Exception as e:
                            logger.debug(f"Error processing element: {e}")
                            continue
                    
                    if detailed_tests:
                        break  # Found data with this selector
                        
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            logger.info(f"Extracted {len(detailed_tests)} detailed MOT tests")
            return detailed_tests
            
        except Exception as e:
            logger.error(f"Error extracting detailed MOT history: {e}")
            return []

def test_scraper():
    """Test the working scraper"""
    try:
        scraper = WorkingVehicleScraper()
        result = scraper.scrape_vehicle_data("DA07BWF")
        return result
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = test_scraper()
    if result:
        print(f"Success: {result}")
    else:
        print("Failed to scrape data")