#!/usr/bin/env python3
"""
Debug scraper to examine the actual structure of the results page
"""

from selenium_scraper import SeleniumVehicleScraper
import logging

# Enable detailed logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DebugScraper(SeleniumVehicleScraper):
    def debug_extract_data(self, registration: str):
        """Debug version that saves page content and examines structure"""
        try:
            if not self._setup_driver():
                return None
            
            # Navigate and search
            self.driver.get("https://www.checkcardetails.co.uk/")
            logger.info("Navigated to website")
            
            # Find input and submit
            all_inputs = self.driver.find_elements("tag name", "input")
            search_input = None
            
            for inp in all_inputs:
                if inp.get_attribute('id') == 'reg_num':
                    search_input = inp
                    break
            
            if search_input:
                search_input.clear()
                search_input.send_keys(registration.upper())
                logger.info(f"Entered registration: {registration}")
                
                # Submit
                search_input.send_keys("\n")
                
                # Wait for results
                import time
                time.sleep(10)
                
                # Debug: Save page source
                page_source = self.driver.page_source
                with open('/tmp/page_source.html', 'w', encoding='utf-8') as f:
                    f.write(page_source)
                logger.info("Page source saved to /tmp/page_source.html")
                
                # Find all text content
                all_elements = self.driver.find_elements("xpath", "//*[text()]")
                
                logger.info(f"Found {len(all_elements)} elements with text")
                
                # Print first 50 elements with text for debugging
                for i, element in enumerate(all_elements[:50]):
                    try:
                        text = element.text.strip()
                        if text and len(text) > 2:
                            tag = element.tag_name
                            logger.info(f"Element {i}: <{tag}> {text[:100]}")
                    except:
                        continue
                
                # Look for specific vehicle data patterns
                vehicle_keywords = ['make', 'model', 'year', 'colour', 'fuel', 'engine', 'transmission']
                
                for element in all_elements:
                    try:
                        text = element.text.strip().lower()
                        for keyword in vehicle_keywords:
                            if keyword in text and ':' in text:
                                logger.info(f"FOUND VEHICLE DATA: {element.text.strip()}")
                    except:
                        continue
                
                return True
                
        except Exception as e:
            logger.error(f"Debug error: {e}")
            return False
        finally:
            self._cleanup()

if __name__ == "__main__":
    debug_scraper = DebugScraper(headless=True)
    result = debug_scraper.debug_extract_data("LP68OHB")
    if result:
        print("Debug extraction completed - check logs for details")
    else:
        print("Debug extraction failed")