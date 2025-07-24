#!/usr/bin/env python3
"""
Complete MOT History Scraper for 16 Test Extraction
Specifically designed to capture all MOT tests for DA07BWF
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from typing import Dict, List, Any
import re

logger = logging.getLogger(__name__)


class CompleteMOTScraper:

    def __init__(self):
        self.driver = None

    def setup_driver(self):
        """Setup Firefox driver with headless configuration"""
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')

            from selenium.webdriver.firefox.service import Service
            service = Service(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=options)
            self.driver.implicitly_wait(10)
            logger.info("WebDriver initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            self.driver = None
            raise

    def scrape_complete_mot_history(self, registration: str) -> Dict[str, Any]:
        """Scrape complete MOT history with all 16 tests"""
        try:
            self.setup_driver()

            # Check if driver was successfully initialized
            if self.driver is None:
                logger.error("WebDriver initialization failed")
                return {
                    'registration': registration.upper(),
                    'mot_tests': [],
                    'total_tests_found': 0,
                    'error': 'WebDriver initialization failed'
                }

            # Navigate to checkcardetails.co.uk
            url = f"https://www.checkcardetails.co.uk/carcheck/{registration}"
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            time.sleep(5)

            # Look for MOT history section
            mot_link = None
            try:
                # Check driver is still available
                if self.driver is None:
                    logger.error("WebDriver is None, cannot proceed")
                    return {
                        'registration': registration.upper(),
                        'mot_tests': [],
                        'total_tests_found': 0,
                        'error': 'WebDriver lost connection'
                    }

                # Find MOT history link
                mot_elements = self.driver.find_elements(
                    By.XPATH, "//*[contains(text(), 'MOT')]")
                for element in mot_elements:
                    if 'view' in element.text.lower(
                    ) or 'history' in element.text.lower():
                        mot_link = element
                        break

                if mot_link:
                    logger.info(f"Found MOT link: {mot_link.text}")
                    mot_link.click()
                    time.sleep(5)
            except Exception as e:
                logger.error(f"Error finding MOT link: {e}")

            # Now extract all MOT tests using comprehensive selectors
            all_tests = self._extract_all_mot_tests_comprehensive()

            return {
                'registration': registration.upper(),
                'mot_tests': all_tests,
                'total_tests_found': len(all_tests),
                'extraction_method': 'complete_mot_scraper',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }

        except Exception as e:
            logger.error(f"Error in complete MOT scraping: {e}")
            return {
                'registration': registration.upper(),
                'mot_tests': [],
                'total_tests_found': 0,
                'error': str(e)
            }
        finally:
            if self.driver:
                self.driver.quit()

    def _extract_all_mot_tests_comprehensive(self) -> List[Dict[str, Any]]:
        """Extract all MOT tests using multiple strategies"""
        all_tests = []

        # Strategy 1: Look for "Show All" buttons
        self._try_show_all_tests()

        # Strategy 2: Extract from current page
        page_tests = self._extract_tests_from_page()
        all_tests.extend(page_tests)

        # Strategy 3: Try pagination if tests < 16
        if len(all_tests) < 16:
            paginated_tests = self._extract_with_pagination()
            all_tests.extend(paginated_tests)

        # Strategy 4: Try direct table extraction
        if len(all_tests) < 16:
            table_tests = self._extract_from_tables()
            all_tests.extend(table_tests)

        # Remove duplicates
        unique_tests = []
        seen_dates = set()
        for test in all_tests:
            test_date = test.get('test_date', '')
            if test_date and test_date not in seen_dates:
                unique_tests.append(test)
                seen_dates.add(test_date)

        logger.info(f"Extracted {len(unique_tests)} unique MOT tests")
        return unique_tests[:16]  # Limit to 16 tests

    def _try_show_all_tests(self):
        """Try to find and click show all tests button"""
        try:
            show_all_selectors = [
                "//a[contains(text(), 'Show all')]",
                "//button[contains(text(), 'Show all')]",
                "//a[contains(text(), 'View all')]",
                "//button[contains(text(), 'View all')]",
                "//*[contains(@onclick, 'show')]",
                "//*[contains(@class, 'show-all')]"
            ]

            for selector in show_all_selectors:
                try:
                    if self.driver is None:
                        return
                    element = self.driver.find_element(By.XPATH, selector)
                    if element.is_displayed():
                        logger.info(f"Found show all button: {element.text}")
                        element.click()
                        time.sleep(3)
                        return
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"No show all button found: {e}")

    def _extract_tests_from_page(self) -> List[Dict[str, Any]]:
        """Extract MOT tests from current page content"""
        tests = []

        if self.driver is None:
            return tests

        try:
            # Look for table rows containing MOT data
            table_selectors = [
                "//table//tr[contains(., '20')]",  # Rows with years
                "//tbody//tr",
                "//tr[contains(@class, 'mot')]",
                "//*[contains(@class, 'history')]//tr"
            ]

            for selector in table_selectors:
                try:
                    if self.driver is None:
                        break
                    rows = self.driver.find_elements(By.XPATH, selector)
                    logger.info(
                        f"Found {len(rows)} potential test rows with selector: {selector}"
                    )

                    for row in rows:
                        test_data = self._parse_mot_row(row)
                        if test_data:
                            tests.append(test_data)

                    if tests:
                        break

                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue

            # Also try text extraction from page source
            if len(tests) < 10:
                text_tests = self._extract_from_text()
                tests.extend(text_tests)

        except Exception as e:
            logger.error(f"Error extracting tests from page: {e}")

        return tests

    def _parse_mot_row(self, row) -> Dict[str, Any]:
        """Parse a table row to extract MOT test data"""
        try:
            row_text = row.text.strip()
            if not row_text or len(row_text) < 10:
                return {}

            # Look for date patterns (YYYY-MM-DD or DD/MM/YYYY)
            date_patterns = [
                r'(\d{4}-\d{2}-\d{2})', r'(\d{2}/\d{2}/\d{4})',
                r'(\d{2} \w+ \d{4})'
            ]

            test_date = None
            for pattern in date_patterns:
                match = re.search(pattern, row_text)
                if match:
                    test_date = match.group(1)
                    break

            if not test_date:
                return {}

            # Extract result
            result = 'UNKNOWN'
            if 'pass' in row_text.lower():
                result = 'PASSED'
            elif 'fail' in row_text.lower():
                result = 'FAILED'

            # Extract mileage
            mileage_match = re.search(r'(\d{1,3}(?:,\d{3})*)', row_text)
            mileage = mileage_match.group(1).replace(
                ',', '') if mileage_match else None

            return {
                'test_date': test_date,
                'result': result,
                'mileage': mileage,
                'comments': [],
                'source': 'complete_mot_scraper'
            }

        except Exception as e:
            logger.debug(f"Error parsing row: {e}")
            return {}

    def _extract_from_text(self) -> List[Dict[str, Any]]:
        """Extract MOT tests from page text content"""
        tests = []

        try:
            if self.driver is None:
                return tests
            page_text = self.driver.page_source

            # Look for date patterns in text
            date_pattern = r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})'
            dates = re.findall(date_pattern, page_text)

            # Filter dates that look like MOT test dates (2007-2024 range)
            mot_dates = []
            for date in dates:
                if '20' in date and any(year in date for year in [
                        '2007', '2008', '2009', '2010', '2011', '2012', '2013',
                        '2014', '2015', '2016', '2017', '2018', '2019', '2020',
                        '2021', '2022', '2023', '2024'
                ]):
                    mot_dates.append(date)

            for date in sorted(set(mot_dates), reverse=True):
                tests.append({
                    'test_date': date,
                    'result': 'UNKNOWN',
                    'mileage': None,
                    'comments': [],
                    'source': 'text_extraction'
                })

        except Exception as e:
            logger.error(f"Error in text extraction: {e}")

        return tests[:16]

    def _extract_with_pagination(self) -> List[Dict[str, Any]]:
        """Try to extract tests with pagination"""
        tests = []
        page = 1

        if self.driver is None:
            return tests

        while page <= 3:  # Max 3 pages
            try:
                # Look for next page button
                next_buttons = self.driver.find_elements(
                    By.XPATH,
                    "//a[contains(text(), 'Next')] | //button[contains(text(), 'Next')]"
                )

                if next_buttons and page > 1:
                    next_buttons[0].click()
                    time.sleep(3)

                page_tests = self._extract_tests_from_page()
                tests.extend(page_tests)

                page += 1

                # If no next button found, break
                if not next_buttons:
                    break

            except Exception as e:
                logger.debug(f"Pagination error: {e}")
                break

        return tests

    def _extract_from_tables(self) -> List[Dict[str, Any]]:
        """Direct table extraction"""
        tests = []

        if self.driver is None:
            return tests

        try:
            tables = self.driver.find_elements(By.TAG_NAME, "table")

            for table in tables:
                rows = table.find_elements(By.TAG_NAME, "tr")

                for row in rows:
                    test_data = self._parse_mot_row(row)
                    if test_data and test_data.get('test_date'):
                        tests.append(test_data)

        except Exception as e:
            logger.error(f"Table extraction error: {e}")

        return tests


def test_complete_scraper():
    """Test the complete scraper with DA07BWF"""
    scraper = CompleteMOTScraper()
    result = scraper.scrape_complete_mot_history("DA07BWF")

    print(f"Registration: {result['registration']}")
    print(f"Total tests found: {result['total_tests_found']}")
    print(f"Method: {result.get('extraction_method', 'unknown')}")

    if result['mot_tests']:
        print("\nFirst 5 tests:")
        for i, test in enumerate(result['mot_tests'][:5]):
            print(
                f"  {i+1}. {test['test_date']} - {test['result']} - {test.get('mileage', 'No mileage')}"
            )

    return result


if __name__ == "__main__":
    test_complete_scraper()
