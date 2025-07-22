#!/usr/bin/env python3
"""
Ctrl+A Scraper for Complete MOT History Extraction
Uses Ctrl+A + Ctrl+C to copy entire page content for DA07BWF 16 tests
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from typing import Dict, List, Any
import re
# No need for pyperclip - using Selenium text extraction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CtrlAScraper:
    def __init__(self):
        self.driver = None
        
    def setup_driver(self):
        """Setup Firefox driver for Ctrl+A extraction"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        service = Service(GeckoDriverManager().install())
        self.driver = webdriver.Firefox(service=service, options=options)
        self.driver.set_page_load_timeout(20)
        
    def extract_all_16_tests_ctrl_a(self, registration: str) -> Dict[str, Any]:
        """Extract all 16 MOT tests using Ctrl+A method"""
        try:
            self.setup_driver()
            
            # Navigate to vehicle page
            url = f"https://www.checkcardetails.co.uk/carcheck/{registration}"
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            time.sleep(5)
            
            # Look for MOT history link and click it
            self._navigate_to_mot_history()
            
            # Get all page text content directly
            logger.info("Extracting all visible text content from page")
            body = self.driver.find_element(By.TAG_NAME, "body")
            
            # Get all visible text (equivalent to Ctrl+A selection)
            page_content = body.text
            logger.info(f"Extracted {len(page_content)} characters of visible text")
            
            # Also get page source as backup
            page_source = self.driver.page_source
            logger.info(f"Page source: {len(page_source)} characters")
            
            # Extract all MOT tests from the full content (visible text + source)
            all_tests = self._extract_tests_from_full_content(page_content)
            
            # If we don't get enough tests from visible text, try page source
            if len(all_tests) < 10:
                logger.info("Trying page source extraction for additional tests")
                source_tests = self._extract_tests_from_full_content(page_source)
                all_tests = self._merge_unique_tests(all_tests, source_tests)
            
            return {
                'registration': registration.upper(),
                'mot_tests': all_tests[:16],  # Limit to 16 tests
                'total_tests_found': len(all_tests),
                'extraction_method': 'ctrl_a_full_page_copy',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'content_length': len(page_content)
            }
            
        except Exception as e:
            logger.error(f"Error in Ctrl+A extraction: {e}")
            return {
                'registration': registration.upper(),
                'mot_tests': [],
                'total_tests_found': 0,
                'error': str(e)
            }
        finally:
            if self.driver:
                self.driver.quit()
    
    def _navigate_to_mot_history(self):
        """Navigate to MOT history page"""
        try:
            # Look for MOT history links
            mot_selectors = [
                "//a[contains(text(), 'MOT')]",
                "//a[contains(text(), 'View Full')]",
                "//a[contains(text(), 'History')]",
                "//*[contains(text(), 'MOT') and contains(text(), 'History')]"
            ]
            
            for selector in mot_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed() and 'history' in element.text.lower():
                            logger.info(f"Clicking MOT history link: {element.text}")
                            element.click()
                            time.sleep(5)
                            return
                except Exception:
                    continue
                    
            logger.warning("No MOT history link found, using current page")
            
        except Exception as e:
            logger.debug(f"Error navigating to MOT history: {e}")
    
    def _extract_tests_from_full_content(self, content: str) -> List[Dict[str, Any]]:
        """Extract all MOT tests from full page content"""
        tests = []
        
        try:
            # Clean up content
            content = content.replace('\n', ' ').replace('\t', ' ')
            
            # Look for comprehensive date patterns
            date_patterns = [
                r'(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4})',
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{2}/\d{2}/\d{4})',
                r'(\d{2}-\d{2}-\d{4})'
            ]
            
            # Extract all potential test dates
            all_dates = set()
            for pattern in date_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Filter for realistic MOT test years
                    if any(year in match for year in ['2007', '2008', '2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024']):
                        all_dates.add(match)
            
            logger.info(f"Found {len(all_dates)} potential test dates in full content")
            
            # For each date, try to extract associated test information
            for date in sorted(all_dates, reverse=True):
                test_info = self._extract_test_details_around_date(content, date)
                if test_info:
                    tests.append(test_info)
            
            # Additional extraction: Look for test result patterns
            additional_tests = self._extract_by_result_patterns(content)
            
            # Merge unique tests
            unique_tests = self._merge_unique_tests(tests, additional_tests)
            
            logger.info(f"Extracted {len(unique_tests)} unique tests from full content")
            return unique_tests
            
        except Exception as e:
            logger.error(f"Error extracting from full content: {e}")
            return []
    
    def _extract_test_details_around_date(self, content: str, date: str) -> Dict[str, Any]:
        """Extract test details around a specific date"""
        try:
            # Find the date in content and extract surrounding context
            date_index = content.lower().find(date.lower())
            if date_index == -1:
                return None
            
            # Extract context around the date (500 characters before and after)
            start = max(0, date_index - 500)
            end = min(len(content), date_index + 500)
            context = content[start:end]
            
            # Extract result
            result = 'UNKNOWN'
            context_lower = context.lower()
            if 'passed' in context_lower or 'pass' in context_lower:
                result = 'PASSED'
            elif 'failed' in context_lower or 'fail' in context_lower:
                result = 'FAILED'
            
            # Extract mileage
            mileage = None
            mileage_patterns = [
                r'(\d{1,3}(?:,\d{3})*)\s*(?:miles|mi)',
                r'mileage[:\s]*(\d{1,3}(?:,\d{3})*)',
                r'(\d{4,7})\s*(?:miles|mi|$)'
            ]
            
            for pattern in mileage_patterns:
                match = re.search(pattern, context, re.IGNORECASE)
                if match:
                    mileage = match.group(1).replace(',', '')
                    break
            
            # Extract comments/advisories
            comments = []
            advisory_patterns = [
                r'advisory[:\s]*([^.]+)',
                r'defect[:\s]*([^.]+)',
                r'attention[:\s]*([^.]+)'
            ]
            
            for pattern in advisory_patterns:
                matches = re.findall(pattern, context, re.IGNORECASE)
                for match in matches[:2]:  # Limit to 2 comments
                    if len(match.strip()) > 5:
                        comments.append({
                            'text': match.strip(),
                            'type': 'ADVISORY'
                        })
            
            return {
                'test_date': date,
                'result': result,
                'mileage': mileage,
                'comments': comments,
                'source': 'ctrl_a_extraction'
            }
            
        except Exception as e:
            logger.debug(f"Error extracting details for date {date}: {e}")
            return None
    
    def _extract_by_result_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Extract additional tests by looking for result patterns"""
        additional_tests = []
        
        try:
            # Look for patterns like "Test Date: XX Result: PASS/FAIL"
            result_patterns = [
                r'(?:test\s+date|date)[:\s]*([^,\n]+)[,\s]*(?:result|status)[:\s]*(pass|fail)',
                r'(\d{2}/\d{2}/\d{4})[^\n]*(?:pass|fail)',
                r'(\d{4}-\d{2}-\d{2})[^\n]*(?:pass|fail)'
            ]
            
            for pattern in result_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple) and len(match) >= 2:
                        date_part = match[0].strip()
                        result_part = match[1].upper() if len(match) > 1 else 'UNKNOWN'
                        
                        # Validate date format
                        if any(year in date_part for year in ['2007', '2008', '2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024']):
                            additional_tests.append({
                                'test_date': date_part,
                                'result': 'PASSED' if 'pass' in result_part.lower() else 'FAILED' if 'fail' in result_part.lower() else 'UNKNOWN',
                                'mileage': None,
                                'comments': [],
                                'source': 'pattern_extraction'
                            })
            
        except Exception as e:
            logger.debug(f"Error in pattern extraction: {e}")
        
        return additional_tests
    
    def _merge_unique_tests(self, tests1: List[Dict[str, Any]], tests2: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge two lists of tests, removing duplicates"""
        all_tests = tests1.copy()
        seen_dates = {test.get('test_date', '') for test in tests1}
        
        for test in tests2:
            test_date = test.get('test_date', '')
            if test_date and test_date not in seen_dates:
                all_tests.append(test)
                seen_dates.add(test_date)
        
        # Sort by date (newest first)
        try:
            all_tests.sort(key=lambda x: x.get('test_date', ''), reverse=True)
        except Exception:
            pass
        
        return all_tests

def test_ctrl_a_scraper():
    """Test the Ctrl+A scraper with DA07BWF"""
    scraper = CtrlAScraper()
    result = scraper.extract_all_16_tests_ctrl_a("DA07BWF")
    
    print(f"Registration: {result['registration']}")
    print(f"Total tests found: {result['total_tests_found']}")
    print(f"Method: {result.get('extraction_method', 'unknown')}")
    print(f"Content length: {result.get('content_length', 0)} characters")
    
    tests = result.get('mot_tests', [])
    if tests:
        print(f"\nAll {len(tests)} tests extracted:")
        for i, test in enumerate(tests):
            print(f"  {i+1}. {test['test_date']} - {test['result']} - {test.get('mileage', 'No mileage')} - {len(test.get('comments', []))} comments")
    
    return result

if __name__ == "__main__":
    test_ctrl_a_scraper()