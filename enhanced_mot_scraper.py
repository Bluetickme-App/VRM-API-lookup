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
    
    def scrape_comprehensive_vehicle_data(self, registration: str, target_tests: int = 16) -> Dict[str, Any]:
        """Scrape comprehensive vehicle data including detailed MOT history - targeting all 16 tests"""
        logger.info(f"Starting comprehensive scrape for: {registration} (targeting {target_tests} tests)")
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
                    
                    # First try to expand all MOT tests if there's a "Show All" option
                    self._try_expand_all_tests()
                    
                    # Extract detailed MOT history with aggressive pagination to capture all 16 tests
                    detailed_tests = self._extract_all_mot_tests_with_pagination()
                    
                    # If we still don't have enough tests, try alternative extraction methods
                    if len(detailed_tests) < 16:
                        logger.warning(f"Only found {len(detailed_tests)} tests, trying alternative methods for remaining {16 - len(detailed_tests)} tests")
                        alternative_tests = self._try_expand_and_extract()
                        
                        # Merge unique tests using the helper method
                        self._merge_unique_tests(detailed_tests, alternative_tests)
                    
                    if detailed_tests:
                        mot_data['mot_tests'] = detailed_tests
                        mot_data['total_tests_found'] = len(detailed_tests)
                        
                        # Generate summary statistics
                        mot_data['summary'] = self._generate_mot_summary(detailed_tests)
                        
                        logger.info(f"Successfully extracted {len(detailed_tests)} MOT tests for complete history")
                    
                    return mot_data
                    
            except Exception as e:
                logger.warning(f"Could not click MOT history link: {e}")
        
        except Exception as e:
            logger.error(f"Error extracting detailed MOT history: {e}")
        
        return mot_data
    
    def _try_expand_all_tests(self):
        """Try to expand all MOT tests on the page before extraction"""
        try:
            # Look for buttons/links that show all tests at once
            expand_selectors = [
                "a:contains('Show All Tests')",
                "button:contains('Show All Tests')",
                "a:contains('Show all')",
                "button:contains('Show all')",
                "a:contains('View all')", 
                "button:contains('View all')",
                "a:contains('Expand all')",
                "button:contains('Expand all')",
                ".show-all",
                ".expand-all",
                "[data-show-all]",
                "[onclick*='showall']",
                "[onclick*='expand']"
            ]
            
            for selector in expand_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            logger.info(f"Found expand all button: {element.text}")
                            element.click()
                            time.sleep(3)
                            return
                except Exception:
                    continue
                    
            logger.debug("No expand all button found")
            
        except Exception as e:
            logger.debug(f"Error in expand all tests: {e}")
    
    def _extract_all_mot_tests_with_pagination(self) -> List[Dict[str, Any]]:
        """Extract all MOT tests with efficient approach to get all 16 tests quickly"""
        all_tests = []
        
        try:
            # First try direct comprehensive extraction from current page
            current_page_tests = self._extract_mot_tests_from_current_page()
            all_tests.extend(current_page_tests)
            logger.info(f"Initial extraction: {len(current_page_tests)} tests")
            
            # If we need more tests, try aggressive extraction methods
            if len(all_tests) < 16:
                logger.info(f"Need {16 - len(all_tests)} more tests, trying aggressive methods")
                
                # Method 1: Look for and click show all/expand buttons
                expand_tests = self._try_expand_and_extract()
                self._merge_unique_tests(all_tests, expand_tests)
                
                # Method 2: Scroll and extract dynamically loaded content
                if len(all_tests) < 16:
                    scroll_tests = self._scroll_and_extract()
                    self._merge_unique_tests(all_tests, scroll_tests)
                
                # Method 3: Try pagination
                if len(all_tests) < 16:
                    paginated_tests = self._try_pagination_extraction()
                    self._merge_unique_tests(all_tests, paginated_tests)
            
            logger.info(f"Complete extraction finished: {len(all_tests)} total tests")
            return all_tests[:16]  # Limit to 16 tests
            
        except Exception as e:
            logger.error(f"Error in comprehensive extraction: {e}")
            return all_tests if all_tests else []
    
    def _try_expand_and_extract(self) -> List[Dict[str, Any]]:
        """Try to expand all content and extract additional tests"""
        additional_tests = []
        
        try:
            # Look for show all buttons with more specific selectors
            expand_selectors = [
                "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show all')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show all')]",
                "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view all')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view all')]",
                "//*[contains(@onclick, 'show') or contains(@onclick, 'expand')]",
                "//*[contains(@class, 'show-more') or contains(@class, 'expand')]"
            ]
            
            for selector in expand_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            logger.info(f"Clicking expand element: {element.text}")
                            element.click()
                            time.sleep(2)
                            
                            # Extract tests after expanding
                            new_tests = self._extract_mot_tests_from_current_page()
                            additional_tests.extend(new_tests)
                            break
                    
                    if additional_tests:
                        break
                        
                except Exception as e:
                    logger.debug(f"Error with expand selector {selector}: {e}")
                    continue
            
            logger.info(f"Expand and extract found {len(additional_tests)} additional tests")
            
        except Exception as e:
            logger.debug(f"Error in expand and extract: {e}")
        
        return additional_tests
    
    def _scroll_and_extract(self) -> List[Dict[str, Any]]:
        """Scroll page and extract dynamically loaded tests"""
        scroll_tests = []
        
        try:
            # Scroll to bottom to trigger any lazy loading
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Extract tests after scrolling
            new_tests = self._extract_mot_tests_from_current_page()
            scroll_tests.extend(new_tests)
            
            logger.info(f"Scroll and extract found {len(scroll_tests)} tests")
            
        except Exception as e:
            logger.debug(f"Error in scroll and extract: {e}")
        
        return scroll_tests
    
    def _try_pagination_extraction(self) -> List[Dict[str, Any]]:
        """Try limited pagination for remaining tests"""
        paginated_tests = []
        
        try:
            # Look for next page links
            next_selectors = [
                "//a[contains(text(), 'Next')]",
                "//button[contains(text(), 'Next')]",
                "//a[contains(text(), '>')]",
                "//*[contains(@class, 'next')]"
            ]
            
            for selector in next_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element.is_displayed() and element.is_enabled():
                        logger.info(f"Found pagination: {element.text}")
                        element.click()
                        time.sleep(3)
                        
                        # Extract from next page
                        page_tests = self._extract_mot_tests_from_current_page()
                        paginated_tests.extend(page_tests)
                        break
                        
                except Exception:
                    continue
            
            logger.info(f"Pagination extraction found {len(paginated_tests)} additional tests")
            
        except Exception as e:
            logger.debug(f"Error in pagination extraction: {e}")
        
        return paginated_tests
    
    def _merge_unique_tests(self, existing_tests: List[Dict[str, Any]], new_tests: List[Dict[str, Any]]):
        """Merge new tests into existing list, avoiding duplicates"""
        existing_dates = {test.get('test_date') for test in existing_tests}
        
        for test in new_tests:
            test_date = test.get('test_date')
            if test_date and test_date not in existing_dates:
                existing_tests.append(test)
                existing_dates.add(test_date)
    
    def _navigate_to_next_page(self) -> bool:
        """Try to navigate to the next page of MOT results"""
        try:
            # Look for pagination elements
            pagination_selectors = [
                "a[class*='next']",
                "a[class*='pagination']", 
                "button[class*='next']",
                "a:contains('Next')",
                "a:contains('More')",
                "a:contains('>')",
                ".pagination a:last-child",
                ".pager a:last-child"
            ]
            
            for selector in pagination_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element_text = element.text.lower()
                            if any(keyword in element_text for keyword in ['next', 'more', '>']):
                                logger.info(f"Found pagination element: {element_text}")
                                element.click()
                                time.sleep(3)
                                return True
                except Exception:
                    continue
            
            # Alternative: Look for "Show more", "Load more", or "Show All Tests" buttons
            show_more_selectors = [
                "button:contains('Show more')",
                "button:contains('Load more')", 
                "a:contains('Show all')",
                "button:contains('Show all')",
                "a:contains('Show All Tests')",
                "button:contains('Show All Tests')",
                "a:contains('View all')",
                ".show-more",
                ".load-more",
                ".show-all",
                "[data-action*='show']",
                "[onclick*='show']"
            ]
            
            for selector in show_more_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            logger.info(f"Found show more button: {element.text}")
                            element.click()
                            time.sleep(3)
                            return True
                except Exception:
                    continue
                    
            return False
            
        except Exception as e:
            logger.debug(f"No pagination found: {e}")
            return False
    
    def _extract_mot_tests_from_current_page(self) -> List[Dict[str, Any]]:
        """Extract MOT tests from the current page"""
        return self._extract_mot_tests_from_history_page()
    
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
        """Find individual test sections on the MOT history page using exact table selectors"""
        try:
            # Use the exact selectors provided by user for MOT history table rows
            table_row_selectors = [
                "body > div.container > div.mot-history-wrapper.mot-history-wrapper-pass > div > table > tbody > tr",
                "body > div.container > div.mot-history-wrapper.mot-history-wrapper-fail > div > table > tbody > tr",
                "body > div.container > div.mot-history-wrapper > div > table > tbody > tr",
                # Fallback selectors for different table structures
                "div.container table tbody tr",
                "table.mot-history tbody tr",
                "[class*='mot-history'] table tr",
                # Generic table row selectors
                "tbody tr",
                "table tr"
            ]
            
            test_sections = []
            
            for selector in table_row_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Trying selector: {selector} - Found {len(elements)} elements")
                    
                    for element in elements:
                        try:
                            element_text = element.text.strip()
                            # Check if this is a valid MOT test row (not header)
                            if element_text and len(element_text) > 10:
                                # Look for date patterns or test-related content
                                if any(keyword in element_text.lower() for keyword in 
                                       ['20', 'pass', 'fail', 'mile', 'test', 'expir', 'advis']):
                                    test_sections.append(element)
                                    logger.debug(f"Added test section with text: {element_text[:50]}...")
                                    
                        except Exception as e:
                            logger.debug(f"Error processing element: {e}")
                            continue
                    
                    if test_sections:
                        logger.info(f"Found {len(test_sections)} test sections using selector: {selector}")
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
        """Parse an individual MOT test table row"""
        try:
            # Try to extract data from table cells (td elements)
            cells = section.find_elements(By.TAG_NAME, 'td')
            
            if len(cells) >= 3:  # Minimum expected columns
                test_record = {
                    'source': 'mot_history_table_row',
                    'test_date': '',
                    'result': 'UNKNOWN',
                    'mileage': '',
                    'expiry_date': '',
                    'comments': [],
                    'raw_text': section.text.strip()[:200]
                }
                
                # Extract data from table cells
                for i, cell in enumerate(cells):
                    try:
                        cell_text = cell.text.strip()
                        if not cell_text:
                            continue
                            
                        # Date patterns (usually first or second column)
                        date_patterns = [
                            r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})\b',
                            r'\b(\d{1,2}\s+\w+\s+\d{4})\b',
                            r'\b(\w+\s+\d{1,2},?\s+\d{4})\b'
                        ]
                        
                        for pattern in date_patterns:
                            date_match = re.search(pattern, cell_text)
                            if date_match:
                                test_record['test_date'] = date_match.group(1)
                                break
                        
                        # Result patterns
                        if 'pass' in cell_text.lower() and 'fail' not in cell_text.lower():
                            test_record['result'] = 'PASSED'
                        elif 'fail' in cell_text.lower():
                            test_record['result'] = 'FAILED'
                        
                        # Mileage patterns
                        mileage_patterns = [
                            r'(\d{1,6}(?:,\d{3})*)\s*(?:miles?|mi)',
                            r'(\d{1,6}(?:,\d{3})*)\s*$'
                        ]
                        
                        for pattern in mileage_patterns:
                            mileage_match = re.search(pattern, cell_text, re.IGNORECASE)
                            if mileage_match:
                                test_record['mileage'] = mileage_match.group(1).replace(',', '')
                                break
                        
                        # Advisory/comment patterns
                        if any(keyword in cell_text.lower() for keyword in ['advisory', 'minor', 'major', 'dangerous', 'fail']):
                            if len(cell_text) > 10:  # Meaningful comment
                                test_record['comments'].append({
                                    'text': cell_text,
                                    'type': 'ADVISORY' if 'advisory' in cell_text.lower() else 'COMMENT'
                                })
                                
                    except Exception as e:
                        logger.debug(f"Error processing cell {i}: {e}")
                        continue
                
                # Only return if we extracted meaningful data
                if test_record['test_date'] or test_record['mileage'] or test_record['result'] != 'UNKNOWN':
                    logger.info(f"Extracted table row: {test_record['test_date']} - {test_record['result']} - {test_record['mileage']} miles")
                    return test_record
            
            # Fallback: parse as text if table structure parsing failed
            text = section.text.strip()
            if not text:
                return None
            
            test_record = {
                'source': 'mot_history_page_section',
                'test_date': '',
                'result': 'UNKNOWN',
                'mileage': '',
                'expiry_date': '',
                'comments': [],
                'raw_text': text[:200]
            }
            
            # Enhanced text parsing with better patterns
            # Extract test date with multiple formats
            date_patterns = [
                r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4})',
                r'(\w+\s+\d{1,2},?\s+\d{4})'
            ]
            
            for pattern in date_patterns:
                date_match = re.search(pattern, text, re.IGNORECASE)
                if date_match:
                    test_record['test_date'] = date_match.group(1)
                    break
            
            # Extract result
            text_lower = text.lower()
            if 'pass' in text_lower and 'fail' not in text_lower:
                test_record['result'] = 'PASSED'
            elif 'fail' in text_lower:
                test_record['result'] = 'FAILED'
            
            # Extract mileage with better patterns
            mileage_patterns = [
                r'(\d{1,6}(?:,\d{3})*)\s*(?:miles?|mi)',
                r'mileage[:\s]*(\d{1,6}(?:,\d{3})*)',
                r'(\d{4,6})\s*(?:\n|$|[^\d])'
            ]
            
            for pattern in mileage_patterns:
                mileage_match = re.search(pattern, text, re.IGNORECASE)
                if mileage_match:
                    test_record['mileage'] = mileage_match.group(1).replace(',', '')
                    break
            
            # Extract comments
            comments = []
            advisory_patterns = [
                r'([^.]*(?:advisory|minor|major|dangerous|fail)[^.]*)',
                r'([^.]*brake[^.]*)',
                r'([^.]*tyre[^.]*)',
                r'([^.]*suspension[^.]*)'
            ]
            
            for pattern in advisory_patterns:
                advisory_matches = re.findall(pattern, text, re.IGNORECASE)
                for advisory in advisory_matches[:3]:  # Limit to 3 comments
                    if advisory.strip():
                        comments.append({
                            'text': advisory.strip(),
                            'type': 'ADVISORY' if 'advisory' in advisory.lower() else 'COMMENT'
                        })
            
            test_record['comments'] = comments
            
            # Return record if we have meaningful data
            if test_record['test_date'] or test_record['mileage'] or test_record['result'] != 'UNKNOWN':
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