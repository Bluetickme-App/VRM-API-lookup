#!/usr/bin/env python3
"""
Simple JavaScript Mileage Extractor
Uses existing enhanced scraper with JavaScript execution for precise mileage data
"""

import logging
from enhanced_mot_scraper import EnhancedMOTScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleMileageJSExtractor(EnhancedMOTScraper):
    """Extract mileage using JavaScript within existing scraper framework"""
    
    def extract_mileage_with_js_selectors(self, registration: str):
        """Extract mileage data using JavaScript DOM queries"""
        try:
            # Initialize the scraper  
            self.setup_driver()
            
            # Navigate to vehicle page
            url = f"https://www.checkcardetails.co.uk/cardetails/{registration}"
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            
            # Wait and click MOT history
            import time
            time.sleep(3)
            
            # Find MOT history link
            try:
                mot_link = self.driver.find_element("link text", "View Full MOT History")
                mot_link.click()
                time.sleep(3)
                logger.info("Navigated to MOT history page")
            except:
                logger.warning("MOT history link not found")
                return {'success': False, 'error': 'MOT history not accessible'}
            
            # Execute JavaScript to extract mileage from table rows
            js_result = self.driver.execute_script("""
                // Find all table rows using the CSS selectors provided
                var selectors = [
                    'body > div.container > div.mot-history-wrapper.mot-history-wrapper-pass > div > table > tbody > tr',
                    'body > div.container > div.mot-history-wrapper.mot-history-wrapper-fail > div > table > tbody > tr',
                    'body > div.container > div.mot-history-wrapper > div > table > tbody > tr',
                    'div.container table tbody tr',
                    'tbody tr'
                ];
                
                var allRecords = [];
                
                for (var s = 0; s < selectors.length; s++) {
                    var rows = document.querySelectorAll(selectors[s]);
                    if (rows.length > 0) {
                        console.log('Found', rows.length, 'rows with selector:', selectors[s]);
                        
                        for (var i = 0; i < rows.length; i++) {
                            var row = rows[i];
                            var cells = row.querySelectorAll('td');
                            
                            if (cells.length >= 3) {
                                var record = {
                                    selector_used: selectors[s],
                                    row_index: i,
                                    test_date: '',
                                    mileage: '',
                                    result: '',
                                    raw_text: row.textContent.trim()
                                };
                                
                                // Extract from each cell
                                for (var j = 0; j < cells.length; j++) {
                                    var cellText = cells[j].textContent.trim();
                                    
                                    // Date pattern
                                    var dateMatch = cellText.match(/\\b\\d{1,2}[\/\\-]\\d{1,2}[\/\\-]\\d{4}\\b/);
                                    if (dateMatch) {
                                        record.test_date = dateMatch[0];
                                    }
                                    
                                    // Mileage pattern (reasonable range)
                                    var mileageMatch = cellText.match(/\\b(\\d{4,6})\\b/);
                                    if (mileageMatch && parseInt(mileageMatch[1]) > 1000 && parseInt(mileageMatch[1]) < 500000) {
                                        record.mileage = mileageMatch[1];
                                    }
                                    
                                    // Result pattern
                                    if (cellText.toLowerCase().includes('pass') && !cellText.toLowerCase().includes('fail')) {
                                        record.result = 'PASSED';
                                    } else if (cellText.toLowerCase().includes('fail')) {
                                        record.result = 'FAILED';
                                    }
                                }
                                
                                // Only add if we have meaningful data
                                if (record.test_date || record.mileage || record.result) {
                                    allRecords.push(record);
                                }
                            }
                        }
                        
                        if (allRecords.length > 0) {
                            break; // Found data with this selector, no need to try others
                        }
                    }
                }
                
                return {
                    total_found: allRecords.length,
                    records: allRecords,
                    page_url: window.location.href,
                    extraction_timestamp: new Date().toISOString()
                };
            """)
            
            return {
                'success': True,
                'registration': registration,
                'mileage_records': js_result.get('records', []),
                'total_records': js_result.get('total_found', 0),
                'page_url': js_result.get('page_url', ''),
                'extraction_method': 'javascript_table_selectors',
                'extracted_at': js_result.get('extraction_timestamp', '')
            }
            
        except Exception as e:
            logger.error(f"JavaScript extraction failed: {e}")
            return {'success': False, 'error': str(e)}
        
        finally:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()

def test_js_mileage():
    """Test JavaScript mileage extraction"""
    extractor = SimpleMileageJSExtractor()
    
    result = extractor.extract_mileage_with_js_selectors("RE13CEO")
    
    print(f"Success: {result.get('success', False)}")
    print(f"Total Records: {result.get('total_records', 0)}")
    
    for record in result.get('mileage_records', [])[:3]:
        print(f"Date: {record.get('test_date', 'No Date')}")
        print(f"Mileage: {record.get('mileage', 'No Mileage')} miles")
        print(f"Result: {record.get('result', 'No Result')}")
        print(f"Selector: {record.get('selector_used', 'Unknown')}")
        print()

if __name__ == "__main__":
    test_js_mileage()