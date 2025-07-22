#!/usr/bin/env python3
"""
JavaScript-based Mileage Extractor
Uses Selenium to execute JavaScript selectors for precise mileage data extraction
"""

import logging
import re
import time
from typing import Dict, List, Optional, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MileageJSExtractor:
    """Extract mileage data using JavaScript selectors and DOM manipulation"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """Initialize WebDriver with JavaScript execution capabilities"""
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            
            from webdriver_manager.firefox import GeckoDriverManager
            self.driver = webdriver.Firefox(options=options)
            self.wait = WebDriverWait(self.driver, 15)
            logger.info("JavaScript extractor WebDriver initialized")
            
        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {e}")
            raise
    
    def extract_mileage_with_js(self, registration: str) -> Dict[str, Any]:
        """Extract mileage data using JavaScript DOM queries"""
        try:
            if not self.driver:
                self.setup_driver()
                
            # Navigate to vehicle page
            url = f"https://www.checkcardetails.co.uk/cardetails/{registration}"
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            
            # Wait for page load
            time.sleep(3)
            
            # Find and click MOT history link
            try:
                mot_link = self.wait.until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "View Full MOT History"))
                )
                mot_link.click()
                logger.info("Clicked MOT history link")
                time.sleep(3)
            except TimeoutException:
                logger.warning("MOT history link not found")
                return self._create_empty_result()
            
            # Execute JavaScript to extract mileage data
            mileage_data = self._execute_mileage_js()
            
            return {
                'success': True,
                'registration': registration,
                'mileage_records': mileage_data.get('records', []),
                'extraction_method': 'javascript_selectors',
                'total_records': len(mileage_data.get('records', [])),
                'page_url': self.driver.current_url,
                'extracted_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"Error in JavaScript extraction: {e}")
            return self._create_empty_result()
        finally:
            if self.driver:
                self.driver.quit()
    
    def _execute_mileage_js(self) -> Dict[str, Any]:
        """Execute JavaScript to extract mileage from table rows"""
        
        # JavaScript code to extract mileage data
        js_code = """
        function extractMileageData() {
            const results = {
                records: [],
                selectors_tried: [],
                debug_info: []
            };
            
            // Multiple selector strategies for table rows
            const tableSelectors = [
                'body > div.container > div.mot-history-wrapper.mot-history-wrapper-pass > div > table > tbody > tr',
                'body > div.container > div.mot-history-wrapper.mot-history-wrapper-fail > div > table > tbody > tr',
                'body > div.container > div.mot-history-wrapper > div > table > tbody > tr',
                'div.container table tbody tr',
                'table.mot-history tbody tr',
                '[class*="mot-history"] table tr',
                'tbody tr',
                'table tr'
            ];
            
            let foundRows = [];
            
            // Try each selector
            for (let selector of tableSelectors) {
                try {
                    const rows = document.querySelectorAll(selector);
                    results.selectors_tried.push({
                        selector: selector,
                        found: rows.length
                    });
                    
                    if (rows.length > 0) {
                        foundRows = Array.from(rows);
                        results.debug_info.push(`Found ${rows.length} rows with: ${selector}`);
                        break;
                    }
                } catch (e) {
                    results.debug_info.push(`Error with selector ${selector}: ${e.message}`);
                }
            }
            
            // Extract data from found rows
            foundRows.forEach((row, index) => {
                try {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 3) {
                        let record = {
                            row_index: index,
                            test_date: '',
                            mileage: '',
                            result: '',
                            raw_text: row.textContent.trim()
                        };
                        
                        // Extract data from each cell
                        cells.forEach((cell, cellIndex) => {
                            const cellText = cell.textContent.trim();
                            
                            // Date patterns
                            const dateMatch = cellText.match(/\\b(\\d{1,2}[\/\\-]\\d{1,2}[\/\\-]\\d{4})|\\b(\\d{1,2}\\s+\\w+\\s+\\d{4})\\b/);
                            if (dateMatch) {
                                record.test_date = dateMatch[0];
                            }
                            
                            // Mileage patterns
                            const mileageMatch = cellText.match(/(\\d{1,6}(?:,\\d{3})*)\\s*(?:miles?|mi)?/i);
                            if (mileageMatch && cellText.length < 50) { // Avoid long text fields
                                const mileageNum = parseInt(mileageMatch[1].replace(/,/g, ''));
                                if (mileageNum > 1000 && mileageNum < 999999) { // Reasonable mileage range
                                    record.mileage = mileageMatch[1];
                                }
                            }
                            
                            // Result patterns
                            if (/\\bpass\\b/i.test(cellText) && !/\\bfail\\b/i.test(cellText)) {
                                record.result = 'PASSED';
                            } else if (/\\bfail\\b/i.test(cellText)) {
                                record.result = 'FAILED';
                            }
                        });
                        
                        // Only add if we have meaningful data
                        if (record.test_date || record.mileage || record.result) {
                            results.records.push(record);
                        }
                    }
                } catch (e) {
                    results.debug_info.push(`Error processing row ${index}: ${e.message}`);
                }
            });
            
            // Fallback: search for any mileage data in page text
            if (results.records.length === 0) {
                const pageText = document.body.textContent;
                const mileageMatches = pageText.match(/(\\d{4,6})\\s*(?:miles?|mi)/gi);
                if (mileageMatches) {
                    mileageMatches.slice(0, 5).forEach((match, index) => {
                        const mileageNum = match.match(/\\d{4,6}/)[0];
                        results.records.push({
                            row_index: index,
                            test_date: 'Date not found',
                            mileage: mileageNum,
                            result: 'Unknown',
                            source: 'text_fallback',
                            raw_text: match
                        });
                    });
                }
            }
            
            return results;
        }
        
        return extractMileageData();
        """
        
        try:
            # Execute the JavaScript code
            result = self.driver.execute_script(js_code)
            logger.info(f"JavaScript execution completed. Found {len(result.get('records', []))} records")
            
            # Log debug information
            for debug in result.get('debug_info', []):
                logger.info(f"JS Debug: {debug}")
                
            for selector_info in result.get('selectors_tried', []):
                logger.info(f"Selector '{selector_info['selector']}' found {selector_info['found']} elements")
            
            return result
            
        except Exception as e:
            logger.error(f"JavaScript execution failed: {e}")
            return {'records': [], 'error': str(e)}
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """Create empty result structure"""
        return {
            'success': False,
            'registration': '',
            'mileage_records': [],
            'extraction_method': 'javascript_selectors',
            'total_records': 0,
            'error': 'Extraction failed'
        }

# Usage example
def test_js_extraction():
    """Test the JavaScript mileage extraction"""
    extractor = MileageJSExtractor()
    
    test_registrations = ['RE13CEO', 'DA07FBW', 'DA07BWF']
    
    for reg in test_registrations:
        print(f"\n=== Testing {reg} ===")
        result = extractor.extract_mileage_with_js(reg)
        
        print(f"Success: {result['success']}")
        print(f"Total Records: {result['total_records']}")
        
        for record in result.get('mileage_records', [])[:3]:
            print(f"  {record.get('test_date', 'No Date')}: {record.get('mileage', 'No Mileage')} miles ({record.get('result', 'No Result')})")

if __name__ == "__main__":
    test_js_extraction()