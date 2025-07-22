#!/usr/bin/env python3
"""
Fast Vehicle Scraper - Optimized for quick web interface responses
Focuses on basic vehicle data extraction with minimal processing time
"""

import logging
import time
import random
from typing import Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.service import Service

logger = logging.getLogger(__name__)

class FastVehicleScraper:
    """Fast vehicle scraper optimized for web interface - basic data only"""
    
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
        self.timeout = 10  # Reduced timeout for speed
        
    def _init_driver(self):
        """Initialize Firefox WebDriver with optimized settings for speed"""
        try:
            options = Options()
            if self.headless:
                options.add_argument("--headless")
            
            # Performance optimizations
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-images")
            options.add_argument("--disable-javascript")  # Speed optimization
            
            # Set preferences for faster loading
            options.set_preference("network.http.pipelining", True)
            options.set_preference("network.http.proxy.pipelining", True)
            options.set_preference("network.http.pipelining.maxrequests", 8)
            options.set_preference("content.notify.interval", 500000)
            options.set_preference("content.notify.ontimer", True)
            options.set_preference("content.switch.threshold", 250000)
            options.set_preference("browser.cache.memory.capacity", 65536)
            options.set_preference("browser.startup.homepage", "about:blank")
            options.set_preference("browser.startup.page", 0)
            options.set_preference("browser.cache.disk.enable", False)
            options.set_preference("browser.cache.memory.enable", False)
            options.set_preference("browser.cache.offline.enable", False)
            options.set_preference("network.http.use-cache", False)
            
            service = Service(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=options)
            self.driver.set_page_load_timeout(self.timeout)
            
            logger.info("Fast Firefox WebDriver initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            return False
    
    def scrape_basic_vehicle_data(self, registration: str) -> Optional[Dict[str, Any]]:
        """Scrape basic vehicle data quickly - no history data"""
        if not self._init_driver():
            return None
            
        try:
            logger.info(f"Fast scraping basic data for: {registration}")
            
            # Navigate directly to the site
            self.driver.get("https://www.checkcardetails.co.uk/")
            
            # Quick wait for page load
            time.sleep(1)
            
            # Find and fill registration input
            try:
                # Try multiple selectors quickly
                search_input = None
                selectors = [
                    "input[placeholder*='reg']",
                    "input[name*='reg']", 
                    "input[id*='reg']",
                    "input[type='text']"
                ]
                
                for selector in selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            if elem.is_displayed() and elem.is_enabled():
                                search_input = elem
                                break
                        if search_input:
                            break
                    except:
                        continue
                
                if not search_input:
                    logger.error("Could not find registration input field")
                    return None
                
                # Enter registration
                search_input.clear()
                search_input.send_keys(registration.upper())
                time.sleep(0.5)
                
                # Find and click submit button
                submit_button = None
                button_selectors = [
                    "button[type='submit']",
                    "input[type='submit']", 
                    "button:contains('Search')",
                    ".btn-primary",
                    ".search-btn"
                ]
                
                for selector in button_selectors:
                    try:
                        buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for btn in buttons:
                            if btn.is_displayed() and btn.is_enabled():
                                submit_button = btn
                                break
                        if submit_button:
                            break
                    except:
                        continue
                
                if submit_button:
                    submit_button.click()
                    time.sleep(2)  # Wait for results
                else:
                    logger.error("Could not find submit button")
                    return None
                
                # Extract basic vehicle data quickly
                vehicle_data = {
                    'registration': registration,
                    'make': 'Unknown',
                    'model': 'Unknown', 
                    'year': None,
                    'color': 'Unknown',
                    'fuel_type': 'Unknown'
                }
                
                # Try to extract basic data from page
                try:
                    # Look for common data patterns
                    page_text = self.driver.page_source.lower()
                    
                    # Extract make/model if visible in page
                    text_elements = self.driver.find_elements(By.TAG_NAME, "td")
                    for elem in text_elements[:20]:  # Limit search for speed
                        try:
                            text = elem.text.strip()
                            if text and len(text) > 2:
                                # Basic pattern matching for vehicle data
                                if any(make in text.lower() for make in ['ford', 'bmw', 'audi', 'toyota', 'honda', 'nissan']):
                                    vehicle_data['make'] = text
                                elif any(color in text.lower() for color in ['red', 'blue', 'black', 'white', 'silver', 'grey']):
                                    vehicle_data['color'] = text
                                elif any(fuel in text.lower() for fuel in ['petrol', 'diesel', 'electric', 'hybrid']):
                                    vehicle_data['fuel_type'] = text
                        except:
                            continue
                    
                    logger.info(f"Fast extraction completed for {registration}")
                    return vehicle_data
                    
                except Exception as e:
                    logger.warning(f"Error extracting data: {e}")
                    return vehicle_data  # Return basic structure even if extraction fails
                
            except Exception as e:
                logger.error(f"Error during form interaction: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Fast scraping failed: {e}")
            return None
            
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Quick cleanup"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None