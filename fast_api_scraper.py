"""
Fast API scraper optimized for quick response times
Uses lightweight approach for API endpoints
"""

import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class FastApiScraper:
    """Lightweight scraper optimized for API speed"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
    def scrape_vehicle_data(self, registration: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """
        Fast scraping method with timeout for API calls
        """
        try:
            start_time = time.time()
            logger.info(f"Fast API scrape starting for {registration} with {timeout}s timeout")
            
            # Direct URL approach for speed
            url = f"https://www.checkcardetails.co.uk/cardetails/{registration}"
            
            response = self.session.get(url, timeout=timeout)
            
            if response.status_code == 200:
                elapsed = time.time() - start_time
                logger.info(f"Page loaded in {elapsed:.2f}s")
                
                # Check for "No Vehicle Found" error
                if "No Vehicle Found" in response.text or "Please Try Again" in response.text:
                    logger.warning(f"Vehicle {registration} not found in DVLA database")
                    return {
                        'error': 'vehicle_not_found',
                        'message': f'No vehicle found for registration {registration}'
                    }
                
                soup = BeautifulSoup(response.content, 'html.parser')
                vehicle_data = self._extract_essential_data(soup, registration)
                
                total_elapsed = time.time() - start_time
                logger.info(f"Fast extraction completed in {total_elapsed:.2f}s")
                
                return vehicle_data
            else:
                logger.warning(f"HTTP {response.status_code} - falling back to browser automation")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"Fast scraping failed: {e}")
            return None
    
    def _extract_essential_data(self, soup: BeautifulSoup, registration: str) -> Dict[str, Any]:
        """Extract essential vehicle data quickly"""
        vehicle_data = {
            'basic_info': {},
            'tax_mot': {},
            'vehicle_details': {},
            'additional': {}
        }
        
        try:
            # Get page text for quick parsing
            page_text = soup.get_text()
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            
            # Quick pattern matching for essential fields
            for i, line in enumerate(lines):
                if i < len(lines) - 1:
                    next_line = lines[i + 1] if i + 1 < len(lines) else ""
                    
                    # Make/Model detection
                    if not vehicle_data['basic_info'].get('make') and len(line.split()) >= 2:
                        words = line.split()
                        if any(word.isupper() and len(word) > 2 for word in words):
                            if 'VEHICLE' not in line and 'DETAILS' not in line:
                                vehicle_data['basic_info']['make'] = line
                                if len(words) >= 2:
                                    vehicle_data['basic_info']['model'] = words[-1]
                    
                    # TAX/MOT
                    if line.upper() == 'TAX' and 'xpir' in next_line:
                        vehicle_data['tax_mot']['tax_expiry'] = next_line.replace('Expires: ', '').replace('Expired: ', '')
                    elif line.upper() == 'MOT' and 'xpir' in next_line:
                        vehicle_data['tax_mot']['mot_expiry'] = next_line.replace('Expires: ', '').replace('Expired: ', '')
                    
                    # Color
                    elif 'Primary Colour' in line or 'Colour' in line:
                        color = next_line
                        if color and len(color) < 20:
                            vehicle_data['basic_info']['color'] = color
                    
                    # Fuel Type
                    elif 'Fuel Type' in line:
                        fuel = next_line
                        if fuel and len(fuel) < 20:
                            vehicle_data['basic_info']['fuel_type'] = fuel
                    
                    # Transmission
                    elif 'Transmission' in line:
                        trans = next_line
                        if trans and len(trans) < 30:
                            vehicle_data['vehicle_details']['transmission'] = trans
                    
                    # Engine
                    elif 'Engine' in line and 'cc' in next_line:
                        engine = next_line
                        if engine and 'cc' in engine:
                            vehicle_data['vehicle_details']['engine_size'] = engine
                    
                    # Description
                    elif 'Description' in line:
                        desc = next_line
                        if desc and len(desc) < 50:
                            vehicle_data['basic_info']['description'] = desc
            
            logger.info(f"Fast extraction found: make={vehicle_data['basic_info'].get('make')}, "
                       f"color={vehicle_data['basic_info'].get('color')}, "
                       f"fuel={vehicle_data['basic_info'].get('fuel_type')}")
            
            return vehicle_data
            
        except Exception as e:
            logger.error(f"Essential data extraction failed: {e}")
            return vehicle_data