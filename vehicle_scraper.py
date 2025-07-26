"""
Vehicle data scraper for checkcardetails.co.uk
Uses Selenium WebDriver to extract comprehensive vehicle information
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.firefox import GeckoDriverManager
from bs4 import BeautifulSoup
from data_extractor import DataExtractor
from config import SCRAPER_CONFIG
import time
import logging
import re
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VehicleScraper:
    """Main scraper class for vehicle data extraction"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.data_extractor = DataExtractor()
        self.start_time = time.time()
        
    def _setup_driver(self):
        """Initialize Firefox WebDriver with optimized options for speed"""
        try:
            firefox_options = Options()
            firefox_options.add_argument('--headless')  # Run in background
            firefox_options.add_argument('--no-sandbox')
            firefox_options.add_argument('--disable-dev-shm-usage')
            firefox_options.add_argument('--disable-gpu')
            firefox_options.add_argument('--disable-images')  # Speed optimization
            firefox_options.add_argument('--window-size=1280,720')  # Smaller window
            firefox_options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0")
            firefox_options.set_preference("media.volume_scale", "0.0")
            firefox_options.set_preference("dom.ipc.plugins.enabled.libflashplayer.so", "false")
            
            # Use webdriver-manager to automatically manage GeckoDriver
            service = Service(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=firefox_options)
            self.wait = WebDriverWait(self.driver, SCRAPER_CONFIG['timeout'])
            logger.info("WebDriver initialized successfully")
            
        except WebDriverException as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise
    
    def _navigate_to_search(self, registration):
        """Navigate directly to vehicle-specific URL"""
        try:
            # Navigate directly to vehicle details page - this works reliably
            direct_url = f"https://www.checkcardetails.co.uk/cardetails/{registration.lower()}"
            self.driver.get(direct_url)
            logger.info(f"Navigated directly to: {direct_url}")
            
            # Wait for vehicle details page to load
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
            
            logger.info("Vehicle page loaded successfully")
            return True
            
        except TimeoutException:
            logger.error("Timeout waiting for vehicle page to load")
            return False
        except Exception as e:
            logger.error(f"Error navigating to vehicle page: {e}")
            return False
    
    def _check_timeout(self):
        """Check if execution time limit exceeded"""
        if time.time() - self.start_time > SCRAPER_CONFIG.get('max_execution_time', 20):
            raise TimeoutException("Maximum execution time exceeded")
    
    def scrape_vehicle_data(self, registration):
        """Main method to scrape vehicle data with MOT and mileage history"""
        try:
            self.start_time = time.time()
            self._setup_driver()
            
            # Navigate and search for basic data
            if not self._navigate_to_search(registration):
                return None
            
            self._check_timeout()
            # Reduced wait for faster response
            time.sleep(1)
            
            # Debug: Save page source to see what we're working with
            page_source = self.driver.page_source
            logger.info(f"Page title: {self.driver.title}")
            
            # Page source loaded successfully - proceed with extraction
            
            # Extract basic vehicle data using the working extractor
            vehicle_data = self.data_extractor.extract_all_data(self.driver)
            
            # Debug: Log what we extracted
            if vehicle_data:
                basic_info = vehicle_data.get('basic_info', {})
                vehicle_details = vehicle_data.get('vehicle_details', {})
                logger.info(f"Basic info extracted: {basic_info}")
                logger.info(f"Vehicle details extracted: {vehicle_details}")
            
            if vehicle_data:
                logger.info(f"Successfully extracted basic data for {registration}")
                
                # Check timeout before MOT extraction
                self._check_timeout()
                
                # Now add MOT history - navigate directly to MOT page
                self._add_mot_history(registration, vehicle_data)
                
                # Add mileage history - temporarily disabled to prevent timeout
                # self._add_mileage_history(registration, vehicle_data)
                
                return vehicle_data
            else:
                logger.warning(f"No basic data extracted for {registration}")
                return None
                
        except Exception as e:
            logger.error(f"Error scraping vehicle data: {e}")
            return None
            
        finally:
            self._cleanup()
    
    def _add_mot_history(self, registration, vehicle_data):
        """Add MOT history to existing vehicle data"""
        try:
            # Navigate from main page to MOT history (don't construct URL directly)
            main_url = f"https://www.checkcardetails.co.uk/cardetails/{registration.lower()}"
            logger.info(f"Starting from main page: {main_url}")
            
            self.driver.get(main_url)
            self._check_timeout()
            time.sleep(2)  # Reduced for speed
            
            # Try to find and click MOT History link on the main page
            try:
                # First try the specific "View Full MOT History" element using user's JS selector
                mot_clicked = False
                try:
                    # Try the more specific CSS selector from user's JavaScript path
                    viewfull_element = self.driver.find_element(By.CSS_SELECTOR, "#viewfullmothistory > span:nth-child(1)")
                    if viewfull_element:
                        logger.info("Found MOT link using user's JS selector: #viewfullmothistory > span:nth-child(1)")
                        viewfull_element.click()
                        time.sleep(4)
                        mot_clicked = True
                except:
                    # Fallback to ID selector
                    try:
                        viewfull_element = self.driver.find_element(By.ID, "viewfullmothistory")
                        if viewfull_element:
                            logger.info("Found 'View Full MOT History' button by ID (fallback)")
                            viewfull_element.click()
                            time.sleep(4)
                            mot_clicked = True
                    except:
                        logger.debug("Both JS selector and ID selector failed, trying other methods")
                
                # Method 3: Look for specific MOT links (avoid /cars/listing URLs)
                if not mot_clicked:
                    mot_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'MOT') or contains(text(), 'mot')]")
                    
                    for link in mot_links:
                        try:
                            link_text = link.text.strip()
                            link_href = link.get_attribute('href') or ''
                            logger.info(f"Found MOT link: '{link_text}' -> {link_href}")
                            
                            # Only click valid MOT links, avoid /cars/listing
                            if link_text and 'view' in link_text.lower() and 'mot' in link_text.lower():
                                if '/cars/listing' not in link_href and link_href:
                                    if link.is_displayed() and link.is_enabled():
                                        logger.info(f"Clicking valid MOT link: {link_text}")
                                        self.driver.execute_script("arguments[0].click();", link)
                                        time.sleep(4)
                                        mot_clicked = True
                                        break
                        except Exception as e:
                            continue
                
                # If clicking didn't work, the page may not have MOT data
                if not mot_clicked:
                    logger.info("No clickable MOT link found - staying on current page to extract available data")
                    
            except Exception as e:
                logger.debug(f"Error in MOT navigation: {e}")
            
            # Extract MOT tests
            mot_tests = []
            
            # Look for MOT test rows in the page
            try:
                # First, debug what's actually on the page
                page_text = self.driver.page_source
                logger.info(f"MOT page contains: {len(page_text)} characters")
                
                # Check if page shows "No MOT History Available"
                if "No MOT History Available" in page_text or "No MOT test records" in page_text:
                    logger.info("Page explicitly shows no MOT history available")
                else:
                    logger.info("Page may contain MOT data, attempting extraction")
                    
                # Debug: Look for any MOT-related class names in the page
                soup = BeautifulSoup(page_text, 'html.parser')
                mot_elements = soup.find_all(class_=lambda x: x and 'mot' in x.lower())
                logger.info(f"Found {len(mot_elements)} elements with 'mot' in class name")
                for elem in mot_elements[:3]:  # Show first 3
                    logger.info(f"MOT element class: {elem.get('class')} - tag: {elem.name}")
                
                # Check for various MOT wrapper types (including new user-provided)
                wrapper_variants = [
                    'mot-history-wrapper-pass',
                    'mot-history-wrapper-fail', 
                    'mot-history-wrapper',
                    'mot-history-summary',  # User-provided summary
                    'mot-wrapper',
                    'mot-summary',
                    'history-wrapper',
                    'history-summary'
                ]
                
                for variant in wrapper_variants:
                    found = soup.find_all(class_=lambda x: x and variant in str(x).lower())
                    if found:
                        logger.info(f"Found {len(found)} elements with class containing '{variant}'")
                
                # Also check nth-child(6) specifically
                container_divs = soup.select("body > div.container > div")
                if len(container_divs) >= 6:
                    logger.info(f"Found container with {len(container_divs)} child divs, checking 6th child")
                    sixth_child = container_divs[5]  # 0-indexed
                    all_children = sixth_child.find_all()
                    logger.info(f"6th child div has {len(all_children)} total descendant elements")
                
                # Enhanced MOT extraction based on actual HTML structure
                # First, check for "View Full MOT History" button and click it
                try:
                    view_full_button = self.driver.find_element(By.CSS_SELECTOR, "#viewfullmothistory")
                    if view_full_button.is_displayed():
                        logger.info("Found 'View Full MOT History' button, clicking to expand data")
                        self.driver.execute_script("arguments[0].click();", view_full_button)
                        time.sleep(2)  # Wait for expansion
                except Exception as e:
                    logger.debug(f"No expandable MOT history button found: {e}")
                
                # Look for the actual table structure with MOT data
                mot_table_elements = self.driver.find_elements(By.CSS_SELECTOR, "table.main-mileage-table")
                mot_timeline_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.mot-history-timeline")
                
                # Extract from table structure first (more reliable)
                if mot_table_elements:
                    logger.info(f"Found {len(mot_table_elements)} MOT table elements")
                    
                    for table_elem in mot_table_elements:
                        # Extract table rows with MOT data
                        rows = table_elem.find_elements(By.CSS_SELECTOR, "tr")
                        logger.info(f"Found {len(rows)} table rows in MOT data")
                        
                        for row in rows:
                            try:
                                # Look for date cells with dvla-date class
                                date_cell = row.find_elements(By.CSS_SELECTOR, "td.dvla-date")
                                mileage_cell = row.find_elements(By.CSS_SELECTOR, "td.odometervalue")
                                
                                if date_cell and len(date_cell) > 0:
                                    date_text = date_cell[0].text.strip()
                                    logger.info(f"Found MOT date: {date_text}")
                                    
                                    # Extract mileage if available
                                    mileage = None
                                    if mileage_cell and len(mileage_cell) > 0:
                                        mileage_text = mileage_cell[0].text.strip()
                                        # Extract numeric mileage (15493, 2294, etc.)
                                        mileage_match = re.search(r'(\d+)', mileage_text)
                                        if mileage_match:
                                            mileage = int(mileage_match.group(1))
                                            logger.info(f"Extracted mileage: {mileage}")
                                    
                                    # Determine result - look for failure indicators in row text
                                    row_text = row.text.lower()
                                    result = 'FAIL' if any(fail_word in row_text for fail_word in ['fail', 'failed', 'advisory']) else 'PASS'
                                    
                                    mot_tests.append({
                                        'date': date_text,
                                        'result': result,
                                        'mileage': mileage,
                                        'raw_text': row.text[:150]
                                    })
                                    logger.info(f"Extracted MOT from table: {date_text} - {result} - {mileage} miles")
                                    
                            except Exception as e:
                                logger.debug(f"Error processing table row: {e}")
                                continue
                
                # First try user's main container selector: body > div.container
                container_found = False
                try:
                    main_container = self.driver.find_element(By.CSS_SELECTOR, "body > div.container")
                    if main_container:
                        logger.info("Found main container using user's selector: body > div.container")
                        container_found = True
                        
                        # Extract MOT summary from within the container
                        try:
                            total_tests_elem = main_container.find_element(By.CSS_SELECTOR, ".total-tests .mot-history-summary-two")
                            if total_tests_elem:
                                total_tests = int(total_tests_elem.text.strip())
                                logger.info(f"Found MOT summary in container: {total_tests} total tests")
                        except:
                            total_tests = 0
                except:
                    # Fallback to global search
                    try:
                        total_tests_elem = self.driver.find_element(By.CSS_SELECTOR, ".total-tests .mot-history-summary-two")
                        if total_tests_elem:
                            total_tests = int(total_tests_elem.text.strip())
                            logger.info(f"Found MOT summary (global): {total_tests} total tests")
                    except:
                        total_tests = 0
                
                # Extract from MOT wrapper elements using user's container selector first
                if container_found:
                    mot_wrapper_elements = main_container.find_elements(By.CSS_SELECTOR, ".mot-history-wrapper")
                    logger.info(f"Searching for MOT wrappers within user's container selector")
                else:
                    mot_wrapper_elements = self.driver.find_elements(By.CSS_SELECTOR, ".mot-history-wrapper")
                if mot_wrapper_elements:
                    logger.info(f"Found {len(mot_wrapper_elements)} mot-history-wrapper elements from authentic DVLA data")
                    
                    for wrapper in mot_wrapper_elements:
                        try:
                            # Extract test result (PASSED/FAILED) from user's HTML structure
                            result_elem = wrapper.find_element(By.CSS_SELECTOR, ".mot-history-result p")
                            result = result_elem.text.strip() if result_elem else "Unknown"
                            
                            # Extract test date using dvla-date class from user's structure
                            date_elem = wrapper.find_element(By.CSS_SELECTOR, ".mot-test-date.dvla-date")
                            test_date = date_elem.text.strip() if date_elem else "Unknown"
                            
                            # Extract mileage using mot-history-mileage-numbers class
                            mileage_elem = wrapper.find_element(By.CSS_SELECTOR, ".mot-history-mileage-numbers")
                            mileage_text = mileage_elem.text.strip() if mileage_elem else ""
                            mileage = None
                            if mileage_text and mileage_text.isdigit():
                                mileage = int(mileage_text)
                            
                            # Extract expiry date from dvla-date in expiry section
                            expiry_date = None
                            try:
                                expiry_elems = wrapper.find_elements(By.CSS_SELECTOR, ".mot-history-expiry-date .mot-history-mileage-numbers.dvla-date")
                                if expiry_elems:
                                    expiry_date = expiry_elems[0].text.strip()
                            except:
                                pass
                            
                            # Extract advisory/failure comments from MOT history
                            comments = []
                            try:
                                comment_items = wrapper.find_elements(By.CSS_SELECTOR, ".mot-history-ul li")
                                for item in comment_items:
                                    comment_text = item.text.strip()
                                    if comment_text:
                                        comments.append(comment_text)
                            except:
                                pass
                            
                            if test_date != "Unknown" and result != "Unknown":
                                mot_tests.append({
                                    'date': test_date,
                                    'result': result,
                                    'mileage': mileage,
                                    'expiry_date': expiry_date,
                                    'comments': comments,
                                    'source': 'DVLA_wrapper_authentic'
                                })
                                logger.info(f"Extracted authentic DVLA MOT: {test_date} - {result} - {mileage} miles")
                            
                        except Exception as e:
                            logger.debug(f"Error extracting MOT wrapper data: {e}")
                            continue

                elif mot_timeline_elements:
                    logger.info(f"Found {len(mot_timeline_elements)} mot-history-timeline elements")
                    
                    for timeline_elem in mot_timeline_elements:
                        timeline_text = timeline_elem.text.strip()
                        logger.info(f"Timeline content preview: {timeline_text[:100]}")
                        
                        # Extract MOT test data from timeline
                        if timeline_text and len(timeline_text) > 20:
                            # Look for date patterns and results in timeline
                            if any(word in timeline_text.lower() for word in ['pass', 'fail', 'advisory', '20']):
                                logger.info(f"Found potential MOT data in timeline: {timeline_text[:150]}")
                                
                                # Extract dates and results
                                date_patterns = [
                                    r'\b(\d{2}/\d{2}/\d{4})\b',  # DD/MM/YYYY
                                    r'\b(\d{1,2}/\d{1,2}/\d{4})\b',  # D/M/YYYY
                                    r'\b(\d{1,2}\s+\w+\s+\d{4})\b'  # D Month YYYY
                                ]
                                
                                for pattern in date_patterns:
                                    date_matches = re.findall(pattern, timeline_text)
                                    if date_matches:
                                        for date_str in date_matches:
                                            # Find result for this date
                                            result = 'FAIL' if 'fail' in timeline_text.lower() else 'PASS'
                                            
                                            # Extract mileage if present
                                            mileage_patterns = [
                                                r'(\d{1,3}(?:,\d{3})*)\s*mile',
                                                r'(\d{1,6})\s*mile',
                                            ]
                                            
                                            mileage = None
                                            for mileage_pattern in mileage_patterns:
                                                mileage_match = re.search(mileage_pattern, timeline_text, re.IGNORECASE)
                                                if mileage_match:
                                                    mileage = int(mileage_match.group(1).replace(',', ''))
                                                    break
                                            
                                            mot_tests.append({
                                                'date': date_str,
                                                'result': result,
                                                'mileage': mileage,
                                                'raw_text': timeline_text[:200]
                                            })
                                            logger.info(f"Extracted MOT from timeline: {date_str} - {result} - {mileage} miles")
                                        break
                
                # Also try the specific selectors for backup including table-based extraction
                backup_selectors = [
                    "table.main-mileage-table tr",  # Table rows with MOT data
                    "td.dvla-date",  # Date cells specifically
                    "td.odometervalue",  # Mileage cells specifically
                    "div.mot-history-wrapper-pass div.mot-history-timeline",
                    "div.mot-history-wrapper-fail div.mot-history-timeline", 
                    ".total-tests",
                    "div.mot-history-summary",
                    "body > div.container > div:nth-child(6) *"
                ]
                
                # Try user-provided XPath for exact MOT data location
                xpath_elements = []
                
                # Try XPath on current page (MOT history page)
                try:
                    xpath_element = self.driver.find_element(By.XPATH, '/html/body/section/div[2]/div/div[4]/div/div[2]/div[1]/div[3]/div/p[2]/span[1]')
                    if xpath_element:
                        xpath_elements.append(xpath_element)
                        logger.info(f"Found user XPath element on MOT page: {xpath_element.text[:100]}")
                except Exception as e:
                    logger.debug(f"User XPath not found on MOT page: {e}")
                
                # Also try XPath on main vehicle page if not found on MOT page
                if not xpath_elements:
                    try:
                        # Navigate back to main page to try XPath there
                        main_url = f"https://www.checkcardetails.co.uk/cardetails/{registration.lower()}"
                        self.driver.get(main_url)
                        time.sleep(2)
                        
                        xpath_element = self.driver.find_element(By.XPATH, '/html/body/section/div[2]/div/div[4]/div/div[2]/div[1]/div[3]/div/p[2]/span[1]')
                        if xpath_element:
                            xpath_elements.append(xpath_element)
                            logger.info(f"Found user XPath element on main page: {xpath_element.text[:100]}")
                            
                        # Navigate back to MOT page after checking main page
                        mot_url = f"https://www.checkcardetails.co.uk/cardetails/{registration.lower()}/mot-history"
                        self.driver.get(mot_url)
                        time.sleep(2)
                        
                    except Exception as e:
                        logger.debug(f"User XPath not found on main page either: {e}")
                
                # Debug: Log current page structure to understand layout
                try:
                    page_source_preview = self.driver.page_source[:1000]
                    if 'section' in page_source_preview:
                        logger.info("Page contains section elements - XPath structure might be present")
                    if 'div[2]' in page_source_preview or 'div[3]' in page_source_preview:
                        logger.info("Page contains nested div structure")
                except Exception as e:
                    logger.debug(f"Error checking page structure: {e}")
                
                # Process XPath elements first (highest priority)
                for element in xpath_elements:
                    try:
                        text = element.text.strip()
                        if text and len(text) > 5:
                            logger.info(f"XPath MOT element content: {text}")
                            
                            # Extract MOT data from the XPath element
                            date_patterns = [
                                r'\b(\d{2}/\d{2}/\d{4})\b',  # DD/MM/YYYY
                                r'\b(\d{1,2}/\d{1,2}/\d{4})\b',  # D/M/YYYY
                                r'\b(\d{4}-\d{2}-\d{2})\b',  # YYYY-MM-DD
                                r'\b(\d{1,2}\s+\w+\s+\d{4})\b'  # D Month YYYY
                            ]
                            
                            for pattern in date_patterns:
                                date_match = re.search(pattern, text)
                                if date_match:
                                    test_date = date_match.group(1)
                                    result = 'FAIL' if 'fail' in text.lower() else 'PASS'
                                    
                                    # Extract mileage if present
                                    mileage_patterns = [
                                        r'(\d{1,3}(?:,\d{3})*)\s*mile',
                                        r'(\d{1,6})\s*mile',
                                        r'mileage[:\s]*(\d{1,3}(?:,\d{3})*)'
                                    ]
                                    
                                    mileage = None
                                    for mileage_pattern in mileage_patterns:
                                        mileage_match = re.search(mileage_pattern, text, re.IGNORECASE)
                                        if mileage_match:
                                            mileage = int(mileage_match.group(1).replace(',', ''))
                                            break
                                    
                                    mot_tests.append({
                                        'date': test_date,
                                        'result': result,
                                        'mileage': mileage,
                                        'raw_text': text[:200]
                                    })
                                    logger.info(f"Extracted MOT from XPath: {test_date} - {result} - {mileage} miles")
                                    break
                    except Exception as e:
                        logger.debug(f"Error processing XPath element: {e}")
                
                # Continue with backup selectors if timeline didn't work
                for selector in backup_selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Backup selector '{selector}' found {len(elements)} elements")
                    
                    for element in elements:
                        try:
                            text = element.text.strip()
                            if text and len(text) > 10:  # Only check substantial text
                                # Look for date patterns and MOT-related keywords
                                if any(word in text.lower() for word in ['pass', 'fail', 'advisory', 'mot', '202', '201']):
                                    logger.info(f"Found potential MOT text: {text[:100]}")
                                    
                                    # Extract date pattern (DD/MM/YYYY or similar)
                                    date_patterns = [
                                        r'\b(\d{2}/\d{2}/\d{4})\b',  # DD/MM/YYYY
                                        r'\b(\d{1,2}/\d{1,2}/\d{4})\b',  # D/M/YYYY
                                        r'\b(\d{4}-\d{2}-\d{2})\b',  # YYYY-MM-DD
                                        r'\b(\d{1,2}\s+\w+\s+\d{4})\b'  # D Month YYYY
                                    ]
                                    
                                    for pattern in date_patterns:
                                        date_match = re.search(pattern, text)
                                        if date_match:
                                            test_date = date_match.group(1)
                                            
                                            # Determine result
                                            result = 'FAIL' if 'fail' in text.lower() else 'PASS'
                                            
                                            # Extract mileage if present  
                                            mileage_patterns = [
                                                r'(\d{1,3}(?:,\d{3})*)\s*mile',
                                                r'(\d{1,6})\s*mile',
                                                r'mileage[:\s]*(\d{1,3}(?:,\d{3})*)',
                                            ]
                                            
                                            mileage = None
                                            for mileage_pattern in mileage_patterns:
                                                mileage_match = re.search(mileage_pattern, text, re.IGNORECASE)
                                                if mileage_match:
                                                    mileage = int(mileage_match.group(1).replace(',', ''))
                                                    break
                                            
                                            mot_tests.append({
                                                'date': test_date,
                                                'result': result,
                                                'mileage': mileage,
                                                'raw_text': text[:100]  # Keep first 100 chars for reference
                                            })
                                            logger.info(f"Extracted MOT test: {test_date} - {result}")
                                            break  # Found date, move to next element
                        except Exception as e:
                            logger.debug(f"Error processing element: {e}")
                            continue
                
                if mot_tests:
                    vehicle_data['mot_history'] = {
                        'tests': mot_tests,
                        'total_tests': len(mot_tests)
                    }
                    logger.info(f"Extracted {len(mot_tests)} MOT tests")
                else:
                    logger.info("No MOT tests found")
                    
            except Exception as e:
                logger.error(f"Error extracting MOT tests: {e}")
                
        except Exception as e:
            logger.error(f"Error getting MOT history: {e}")
    
    def _add_mileage_history(self, registration, vehicle_data):
        """Add mileage history to existing vehicle data"""
        try:
            # Navigate from main page to mileage history (don't construct URL directly)
            main_url = f"https://www.checkcardetails.co.uk/cardetails/{registration.lower()}"
            logger.info(f"Starting from main page for mileage: {main_url}")
            
            self.driver.get(main_url)
            time.sleep(3)
            
            # Try to find and click Mileage History link on the main page
            try:
                # Look for any element containing "Mileage" text that might be clickable
                elements_with_mileage = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Mileage') or contains(text(), 'mileage')]")
                
                mileage_clicked = False
                for element in elements_with_mileage:
                    try:
                        # Check if element is clickable (link or button)
                        if element.tag_name in ['a', 'button'] or 'click' in element.get_attribute('onclick') or '':
                            logger.info(f"Found clickable Mileage element: {element.text[:50]}")
                            element.click()
                            time.sleep(4)
                            mileage_clicked = True
                            break
                    except Exception as e:
                        continue
                
                # If clicking didn't work, try the URL approach but navigate properly
                if not mileage_clicked:
                    logger.info("No clickable Mileage link found - using direct URL navigation")
                    # Use the proper URL format that maintains session/registration context
                    current_url = self.driver.current_url
                    if '/cardetails/' in current_url:
                        # Extract the base URL and append mileage-history
                        base_url = current_url.split('?')[0]  # Remove any query parameters
                        mileage_url = f"{base_url}/mileage-history"
                        logger.info(f"Navigating to mileage history: {mileage_url}")
                        self.driver.get(mileage_url)
                        time.sleep(4)
                    
            except Exception as e:
                logger.debug(f"Error in mileage navigation: {e}")
            
            # Extract mileage readings
            mileage_readings = []
            
            try:
                # First, debug what's actually on the page
                page_text = self.driver.page_source
                logger.info(f"Mileage page contains: {len(page_text)} characters")
                
                # Check if page shows "No Mileage Analysis Available"
                if "No Mileage Analysis Available" in page_text or "No mileage data" in page_text:
                    logger.info("Page explicitly shows no mileage data available")
                else:
                    logger.info("Page may contain mileage data, attempting extraction")
                
                # Try comprehensive selectors for mileage data
                mileage_selectors = [
                    "table tr",
                    ".mileage-reading", 
                    ".reading",
                    ".mileage-history-item",
                    ".history-item",
                    "div[class*='mileage']",
                    "div[class*='reading']", 
                    "*[class*='history']",
                    "tbody tr",
                    ".row"
                ]
                
                all_elements = []
                for selector in mileage_selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    all_elements.extend(elements)
                    logger.info(f"Mileage selector '{selector}' found {len(elements)} elements")
                
                logger.info(f"Total mileage elements to scan: {len(all_elements)}")
                
                for element in all_elements:
                    try:
                        text = element.text.strip()
                        if text and len(text) > 5:  # Only check substantial text
                            # Look for mileage patterns: numbers followed by miles/km
                            mileage_patterns = [
                                r'(\d{1,3}(?:,\d{3})*)\s*mile',
                                r'(\d{1,6})\s*mile',
                                r'mileage[:\s]*(\d{1,3}(?:,\d{3})*)',
                            ]
                            
                            # Look for date patterns
                            date_patterns = [
                                r'\b(\d{2}/\d{2}/\d{4})\b',  # DD/MM/YYYY
                                r'\b(\d{1,2}/\d{1,2}/\d{4})\b',  # D/M/YYYY
                                r'\b(\d{1,2}\s+\w+\s+\d{4})\b'  # D Month YYYY
                            ]
                            
                            mileage_match = None
                            for pattern in mileage_patterns:
                                mileage_match = re.search(pattern, text, re.IGNORECASE)
                                if mileage_match:
                                    break
                            
                            date_match = None
                            for pattern in date_patterns:
                                date_match = re.search(pattern, text)
                                if date_match:
                                    break
                            
                            if mileage_match and date_match:
                                mileage = int(mileage_match.group(1).replace(',', ''))
                                date = date_match.group(1)
                                
                                mileage_readings.append({
                                    'date': date,
                                    'mileage': mileage,
                                    'source': 'MOT_test_record'
                                })
                                logger.info(f"Extracted mileage reading: {date} - {mileage} miles")
                            elif mileage_match:
                                logger.info(f"Found mileage without date: {text[:50]}")
                            elif any(word in text.lower() for word in ['mile', 'mileage']):
                                logger.info(f"Found mileage-related text: {text[:50]}")
                    except Exception as e:
                        logger.debug(f"Error processing mileage element: {e}")
                        continue
                
                if mileage_readings:
                    # Sort by date (convert to proper date format for sorting)
                    mileage_readings.sort(key=lambda x: datetime.strptime(x['date'], '%d/%m/%Y'))
                    
                    vehicle_data['mileage_history'] = {
                        'readings': mileage_readings,
                        'total_readings': len(mileage_readings),
                        'latest_mileage': mileage_readings[-1]['mileage'] if mileage_readings else None
                    }
                    logger.info(f"Extracted {len(mileage_readings)} mileage readings")
                else:
                    logger.info("No mileage readings found")
                    
            except Exception as e:
                logger.error(f"Error extracting mileage readings: {e}")
                
        except Exception as e:
            logger.error(f"Error getting mileage history: {e}")
    
    def _create_mileage_analysis_from_mot_tests(self, mot_tests):
        """Create comprehensive mileage analysis from MOT test data"""
        if not mot_tests:
            return {
                'analysis': {
                    'odometer_issues': {'has_issues': False, 'severity': 'NONE', 'status': 'No MOT data available'},
                    'progression': {'is_consistent': True, 'status': 'No data to analyze'}
                },
                'mileage_records': [],
                'summary': {'total_records': 0, 'status': 'No MOT data available'}
            }
        
        # Extract mileage records from MOT tests
        mileage_records = []
        for test in mot_tests:
            if test.get('mileage') and test.get('date'):
                mileage_records.append({
                    'date': test['date'],
                    'mileage': test['mileage'],
                    'source': 'MOT_test_record',
                    'test_result': test.get('result', 'Unknown')
                })
        
        # Sort by mileage (descending) to check for rollbacks
        mileage_records.sort(key=lambda x: x['mileage'], reverse=True)
        
        # Analyze for odometer issues
        has_rollback = False
        rollback_amount = 0
        
        if len(mileage_records) > 1:
            for i in range(len(mileage_records) - 1):
                current_mileage = mileage_records[i]['mileage']
                next_mileage = mileage_records[i + 1]['mileage']
                
                # Check for rollback (mileage going backwards chronologically)
                if current_mileage < next_mileage:
                    has_rollback = True
                    rollback_amount = max(rollback_amount, next_mileage - current_mileage)
        
        # Calculate progression statistics
        if len(mileage_records) > 1:
            total_mileage = mileage_records[0]['mileage'] - mileage_records[-1]['mileage']
            latest_mileage = mileage_records[0]['mileage']
            earliest_mileage = mileage_records[-1]['mileage']
        else:
            total_mileage = 0
            latest_mileage = mileage_records[0]['mileage'] if mileage_records else 0
            earliest_mileage = latest_mileage
        
        return {
            'analysis': {
                'odometer_issues': {
                    'has_issues': has_rollback,
                    'severity': 'HIGH' if rollback_amount > 50000 else 'MEDIUM' if rollback_amount > 10000 else 'NONE',
                    'status': f'Rollback detected: {rollback_amount} miles' if has_rollback else 'No odometer discrepancies detected',
                    'reduction_amount': rollback_amount if has_rollback else 0
                },
                'progression': {
                    'is_consistent': not has_rollback,
                    'total_increase': total_mileage,
                    'status': 'Consistent progression' if not has_rollback else 'Inconsistent mileage detected'
                }
            },
            'mileage_records': sorted(mileage_records, key=lambda x: x['date']),  # Sort by date for display
            'summary': {
                'total_records': len(mileage_records),
                'latest_mileage': latest_mileage,
                'earliest_mileage': earliest_mileage,
                'total_increase': total_mileage,
                'status': 'Complete' if mileage_records else 'No data available'
            }
        }
    
    def _cleanup(self):
        """Clean up WebDriver resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")
