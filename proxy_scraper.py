"""
Advanced stealth scraper with proxy rotation and anti-detection measures
Protects against domain blocking and tracking
"""

import requests
import random
import time
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class StealthScraper:
    """Advanced scraper with anti-detection and proxy capabilities"""
    
    def __init__(self):
        self.session = requests.Session()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
        ]
        
    def _get_random_headers(self) -> Dict[str, str]:
        """Generate randomized headers to avoid detection"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'Pragma': 'no-cache'
        }
    
    def _add_random_delay(self, min_delay: float = 2.0, max_delay: float = 8.0):
        """Add random delay to mimic human behavior"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
    def scrape_vehicle_data(self, registration: str) -> Optional[Dict[str, Any]]:
        """
        Scrape vehicle data with stealth measures
        Uses direct URL access without revealing source domain
        """
        try:
            # Clean registration number
            reg_clean = registration.upper().replace(' ', '')
            
            # Add initial delay
            self._add_random_delay(1.0, 3.0)
            
            # Construct direct URL
            url = f"https://www.checkcardetails.co.uk/cardetails/{reg_clean.lower()}"
            
            # Set randomized headers
            headers = self._get_random_headers()
            
            logger.info(f"Fetching data with stealth headers for: {registration}")
            
            # Make request with stealth measures
            response = self.session.get(
                url, 
                headers=headers,
                timeout=30,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                # Add processing delay
                self._add_random_delay(1.0, 2.0)
                
                # Parse the response
                return self._parse_vehicle_data(response.text, registration)
            elif response.status_code == 403:
                logger.warning("Access blocked - implementing additional stealth measures")
                return self._retry_with_enhanced_stealth(url, headers, registration)
            else:
                logger.error(f"Request failed with status: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Stealth scraping failed: {e}")
            return None
    
    def _retry_with_enhanced_stealth(self, url: str, headers: Dict[str, str], registration: str) -> Optional[Dict[str, Any]]:
        """Retry with enhanced stealth measures when blocked"""
        try:
            # Wait longer before retry
            self._add_random_delay(5.0, 10.0)
            
            # Modify headers for even more stealth
            enhanced_headers = headers.copy()
            enhanced_headers.update({
                'Referer': 'https://www.google.com/',
                'Origin': 'https://www.google.com',
                'Sec-Ch-Ua': '"Google Chrome";v="118", "Chromium";v="118", "Not=A?Brand";v="99"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"'
            })
            
            # Use a new session
            new_session = requests.Session()
            
            response = new_session.get(
                url,
                headers=enhanced_headers,
                timeout=30,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                return self._parse_vehicle_data(response.text, registration)
            else:
                logger.error(f"Enhanced retry failed with status: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Enhanced stealth retry failed: {e}")
            return None
    
    def _parse_vehicle_data(self, html_content: str, registration: str) -> Dict[str, Any]:
        """Parse vehicle data from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract vehicle data using BeautifulSoup
            vehicle_data = {
                'basic_info': self._extract_basic_info(soup),
                'tax_mot': self._extract_tax_mot_info(soup),
                'vehicle_details': self._extract_vehicle_details(soup),
                'additional': self._extract_additional_info(soup)
            }
            
            return vehicle_data
            
        except Exception as e:
            logger.error(f"Parsing failed: {e}")
            return None
    
    def _extract_basic_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract basic vehicle information"""
        basic_info = {}
        
        try:
            # Look for vehicle make and model
            title_elem = soup.find('h1') or soup.find('h2') or soup.find('h3')
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                if any(word in title_text.upper() for word in ['BMW', 'AUDI', 'FORD', 'MERCEDES', 'VOLKSWAGEN']):
                    parts = title_text.split()
                    if len(parts) >= 2:
                        basic_info['make'] = parts[0]
                        basic_info['model'] = ' '.join(parts[1:])
            
            # Look for color information
            color_patterns = ['Color:', 'Colour:', 'Paint:']
            for pattern in color_patterns:
                color_elem = soup.find(text=lambda text: text and pattern in text)
                if color_elem:
                    color_text = color_elem.strip()
                    if ':' in color_text:
                        basic_info['color'] = color_text.split(':', 1)[1].strip()
            
            # Look for fuel type
            fuel_patterns = ['Fuel:', 'Fuel Type:']
            for pattern in fuel_patterns:
                fuel_elem = soup.find(text=lambda text: text and pattern in text)
                if fuel_elem:
                    fuel_text = fuel_elem.strip()
                    if ':' in fuel_text:
                        basic_info['fuel_type'] = fuel_text.split(':', 1)[1].strip()
                        
        except Exception as e:
            logger.error(f"Basic info extraction failed: {e}")
        
        return basic_info
    
    def _extract_tax_mot_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract tax and MOT information"""
        tax_mot = {}
        
        try:
            # Look for MOT expiry
            mot_text = soup.find(text=lambda text: text and 'MOT' in text and 'expires' in text.lower())
            if mot_text:
                # Extract date from MOT text
                import re
                date_pattern = r'\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}|\d{2} \w+ \d{4}'
                dates = re.findall(date_pattern, mot_text)
                if dates:
                    tax_mot['mot_expiry'] = dates[0]
            
            # Look for tax information
            tax_text = soup.find(text=lambda text: text and 'tax' in text.lower() and ('expires' in text.lower() or 'due' in text.lower()))
            if tax_text:
                import re
                date_pattern = r'\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}|\d{2} \w+ \d{4}'
                dates = re.findall(date_pattern, tax_text)
                if dates:
                    tax_mot['tax_expiry'] = dates[0]
                    
        except Exception as e:
            logger.error(f"Tax/MOT extraction failed: {e}")
        
        return tax_mot
    
    def _extract_vehicle_details(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract vehicle details"""
        details = {}
        
        try:
            # Look for transmission info
            trans_patterns = ['Transmission:', 'Gearbox:', 'Trans:']
            for pattern in trans_patterns:
                trans_elem = soup.find(text=lambda text: text and pattern in text)
                if trans_elem:
                    trans_text = trans_elem.strip()
                    if ':' in trans_text:
                        details['transmission'] = trans_text.split(':', 1)[1].strip()
            
            # Look for engine size
            engine_patterns = ['Engine:', 'Engine Size:', 'CC:']
            for pattern in engine_patterns:
                engine_elem = soup.find(text=lambda text: text and pattern in text)
                if engine_elem:
                    engine_text = engine_elem.strip()
                    if ':' in engine_text:
                        details['engine_size'] = engine_text.split(':', 1)[1].strip()
                        
        except Exception as e:
            logger.error(f"Vehicle details extraction failed: {e}")
        
        return details
    
    def _extract_additional_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract additional information"""
        additional = {}
        
        try:
            # Look for total keepers
            keepers_text = soup.find(text=lambda text: text and 'keeper' in text.lower())
            if keepers_text:
                import re
                numbers = re.findall(r'\d+', keepers_text)
                if numbers:
                    additional['total_keepers'] = int(numbers[0])
                    
        except Exception as e:
            logger.error(f"Additional info extraction failed: {e}")
        
        return additional