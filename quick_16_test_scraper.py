#!/usr/bin/env python3
"""
Quick 16-Test MOT Scraper for DA07BWF
Optimized for speed and complete extraction
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from typing import Dict, List, Any
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Quick16TestScraper:
    def __init__(self):
        self.driver = None
        
    def setup_driver(self):
        """Setup optimized Firefox driver"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-images')
        options.add_argument('--disable-javascript')  # Speed optimization
        options.add_argument('--window-size=1920,1080')
        
        service = Service(GeckoDriverManager().install())
        self.driver = webdriver.Firefox(service=service, options=options)
        self.driver.set_page_load_timeout(15)  # Reduced timeout
        
    def extract_all_16_tests(self, registration: str) -> Dict[str, Any]:
        """Extract all 16 MOT tests with optimized approach"""
        try:
            self.setup_driver()
            
            # Navigate directly to MOT history page
            url = f"https://www.checkcardetails.co.uk/mot/mothistory/{registration}"
            logger.info(f"Direct navigation to: {url}")
            self.driver.get(url)
            time.sleep(3)
            
            # Try alternative URL patterns if first fails
            if "error" in self.driver.page_source.lower() or "not found" in self.driver.page_source.lower():
                alt_url = f"https://www.checkcardetails.co.uk/carcheck/{registration}"
                logger.info(f"Trying alternative URL: {alt_url}")
                self.driver.get(alt_url)
                time.sleep(3)
                
                # Look for MOT history link
                mot_links = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "MOT")
                for link in mot_links:
                    if "history" in link.text.lower() or "view" in link.text.lower():
                        link.click()
                        time.sleep(3)
                        break
            
            # Extract all tests using multiple methods
            all_tests = []
            
            # Method 1: Direct table extraction
            tests = self._extract_from_tables()
            all_tests.extend(tests)
            
            # Method 2: Page source regex extraction
            if len(all_tests) < 16:
                page_tests = self._extract_from_page_source()
                all_tests.extend(page_tests)
            
            # Method 3: Show all tests if available
            if len(all_tests) < 16:
                self._click_show_all()
                additional_tests = self._extract_from_tables()
                all_tests.extend(additional_tests)
            
            # Remove duplicates based on test date
            unique_tests = self._remove_duplicates(all_tests)
            
            logger.info(f"Extracted {len(unique_tests)} unique MOT tests")
            
            return {
                'registration': registration.upper(),
                'mot_tests': unique_tests[:16],  # Limit to 16 tests
                'total_tests_found': len(unique_tests),
                'extraction_method': 'quick_16_test_scraper',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'optimized_extraction'
            }
            
        except Exception as e:
            logger.error(f"Error in quick extraction: {e}")
            return {
                'registration': registration.upper(),
                'mot_tests': [],
                'total_tests_found': 0,
                'error': str(e)
            }
        finally:
            if self.driver:
                self.driver.quit()
    
    def _extract_from_tables(self) -> List[Dict[str, Any]]:
        """Extract tests from HTML tables"""
        tests = []
        
        try:
            # Find all table rows
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            
            for table in tables:
                rows = table.find_elements(By.TAG_NAME, "tr")
                
                for row in rows:
                    test_data = self._parse_table_row(row)
                    if test_data:
                        tests.append(test_data)
            
            logger.info(f"Table extraction found {len(tests)} tests")
            
        except Exception as e:
            logger.debug(f"Table extraction error: {e}")
        
        return tests
    
    def _parse_table_row(self, row) -> Dict[str, Any]:
        """Parse a table row for MOT test data"""
        try:
            row_text = row.text.strip()
            if not row_text or len(row_text) < 8:
                return None
            
            # Look for date patterns
            date_match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{1,2}\s+\w+\s+\d{4})', row_text)
            if not date_match:
                return None
            
            test_date = date_match.group(1)
            
            # Extract result
            result = 'UNKNOWN'
            if 'pass' in row_text.lower():
                result = 'PASSED'
            elif 'fail' in row_text.lower():
                result = 'FAILED'
            
            # Extract mileage
            mileage_match = re.search(r'(\d{1,3}(?:,\d{3})*)', row_text)
            mileage = mileage_match.group(1).replace(',', '') if mileage_match else None
            
            return {
                'test_date': test_date,
                'result': result,
                'mileage': mileage,
                'comments': [],
                'source': 'quick_table_extraction'
            }
            
        except Exception as e:
            logger.debug(f"Row parsing error: {e}")
            return None
    
    def _extract_from_page_source(self) -> List[Dict[str, Any]]:
        """Extract tests from page source using regex"""
        tests = []
        
        try:
            page_source = self.driver.page_source
            
            # Look for date patterns in the entire page
            date_patterns = [
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{2}/\d{2}/\d{4})',
                r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4})'
            ]
            
            found_dates = set()
            
            for pattern in date_patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                for match in matches:
                    # Filter for realistic MOT test dates (2007-2024)
                    if any(year in match for year in ['2007', '2008', '2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024']):
                        found_dates.add(match)
            
            # Create test records for each date found
            for date in sorted(found_dates, reverse=True):
                tests.append({
                    'test_date': date,
                    'result': 'UNKNOWN',
                    'mileage': None,
                    'comments': [],
                    'source': 'page_source_extraction'
                })
            
            logger.info(f"Page source extraction found {len(tests)} potential tests")
            
        except Exception as e:
            logger.debug(f"Page source extraction error: {e}")
        
        return tests[:16]  # Limit results
    
    def _click_show_all(self):
        """Try to click show all or expand buttons"""
        try:
            show_all_selectors = [
                "//a[contains(text(), 'Show all')]",
                "//button[contains(text(), 'Show all')]",
                "//a[contains(text(), 'View all')]",
                "//button[contains(text(), 'View all')]",
                "//a[contains(text(), 'More')]",
                "//button[contains(text(), 'More')]"
            ]
            
            for selector in show_all_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element.is_displayed() and element.is_enabled():
                        logger.info(f"Clicking show all: {element.text}")
                        element.click()
                        time.sleep(2)
                        return
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Show all click error: {e}")
    
    def _remove_duplicates(self, tests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate tests based on test date"""
        unique_tests = []
        seen_dates = set()
        
        for test in tests:
            test_date = test.get('test_date', '')
            if test_date and test_date not in seen_dates:
                unique_tests.append(test)
                seen_dates.add(test_date)
        
        # Sort by date (newest first)
        unique_tests.sort(key=lambda x: x.get('test_date', ''), reverse=True)
        
        return unique_tests

def test_quick_scraper():
    """Test the quick scraper with DA07BWF"""
    scraper = Quick16TestScraper()
    result = scraper.extract_all_16_tests("DA07BWF")
    
    print(f"Registration: {result['registration']}")
    print(f"Total tests found: {result['total_tests_found']}")
    print(f"Method: {result.get('extraction_method', 'unknown')}")
    
    tests = result.get('mot_tests', [])
    if tests:
        print(f"\nAll {len(tests)} tests extracted:")
        for i, test in enumerate(tests):
            print(f"  {i+1}. {test['test_date']} - {test['result']} - {test.get('mileage', 'No mileage')} - {test['source']}")
    
    return result

if __name__ == "__main__":
    test_quick_scraper()