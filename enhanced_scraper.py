"""
Enhanced vehicle data scraper for checkcardetails.co.uk
Uses requests and BeautifulSoup for better reliability and performance
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedVehicleScraper:
    """Enhanced scraper using requests and BeautifulSoup"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def scrape_vehicle_data(self, registration: str) -> Optional[Dict[str, Any]]:
        """Main method to scrape vehicle data using direct URL access"""
        try:
            # Construct direct URL for the vehicle
            url = f"https://www.checkcardetails.co.uk/cardetails/{registration.lower()}"
            
            logger.info(f"Fetching data from: {url}")
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                return self._parse_vehicle_page(response.text, registration)
            else:
                logger.error(f"Failed to fetch page. Status code: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error scraping vehicle data: {e}")
            return None
    
    def _parse_vehicle_page(self, html_content: str, registration: str) -> Dict[str, Any]:
        """Parse the vehicle details page and extract all relevant data"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        vehicle_data = {
            'registration': registration.upper(),
            'basic_info': self._extract_basic_info(soup),
            'tax_mot': self._extract_tax_mot_info(soup),
            'vehicle_details': self._extract_vehicle_details(soup),
            'mileage': self._extract_mileage_info(soup),
            'performance': self._extract_performance_data(soup),
            'fuel_economy': self._extract_fuel_economy(soup),
            'safety': self._extract_safety_ratings(soup),
            'additional': self._extract_additional_info(soup)
        }
        
        return vehicle_data
    
    def _extract_basic_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract basic vehicle information"""
        basic_info = {}
        
        # Extract vehicle title/make/model
        title_selectors = ['h1', 'h2', '.vehicle-title']
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.get_text(strip=True):
                basic_info['title'] = title_elem.get_text(strip=True)
                break
        
        # Extract vehicle image
        img_elem = soup.select_one('img[src*="vehicleimages"], img[alt*="vehicle"], img[src*="brandlogos"]')
        if img_elem:
            basic_info['image_url'] = img_elem.get('src', '')
        
        return basic_info
    
    def _extract_tax_mot_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract TAX and MOT expiry information"""
        tax_mot = {}
        
        # Look for TAX section
        tax_section = soup.find(text=re.compile(r'TAX', re.IGNORECASE))
        if tax_section:
            parent = tax_section.parent
            if parent:
                # Look for expiry date in the same section
                expires_text = parent.find_next(text=re.compile(r'Expires:', re.IGNORECASE))
                if expires_text:
                    expires_parent = expires_text.parent
                    if expires_parent:
                        next_text = expires_parent.get_text(strip=True)
                        date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', next_text)
                        if date_match:
                            tax_mot['tax_expiry'] = date_match.group(1)
                
                # Look for days left
                days_text = parent.find_next(text=re.compile(r'\d+\s+days\s+left', re.IGNORECASE))
                if days_text:
                    days_match = re.search(r'(\d+)\s+days\s+left', days_text, re.IGNORECASE)
                    if days_match:
                        tax_mot['tax_days_left'] = days_match.group(1)
        
        # Look for MOT section
        mot_section = soup.find(text=re.compile(r'MOT', re.IGNORECASE))
        if mot_section:
            parent = mot_section.parent
            if parent:
                # Look for expiry date in the same section
                expires_text = parent.find_next(text=re.compile(r'Expires:', re.IGNORECASE))
                if expires_text:
                    expires_parent = expires_text.parent
                    if expires_parent:
                        next_text = expires_parent.get_text(strip=True)
                        date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', next_text)
                        if date_match:
                            tax_mot['mot_expiry'] = date_match.group(1)
                
                # Look for days left
                days_text = parent.find_next(text=re.compile(r'\d+\s+days\s+left', re.IGNORECASE))
                if days_text:
                    days_match = re.search(r'(\d+)\s+days\s+left', days_text, re.IGNORECASE)
                    if days_match:
                        tax_mot['mot_days_left'] = days_match.group(1)
        
        return tax_mot
    
    def _extract_vehicle_details(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract vehicle details from tables"""
        details = {}
        
        # Look for tables containing vehicle details
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if key and value:
                        normalized_key = self._normalize_key(key)
                        details[normalized_key] = value
        
        # Also look for specific patterns in text
        text_content = soup.get_text()
        
        # Extract specific fields using regex patterns
        patterns = {
            'model_variant': r'Model Variant[:\s]+([^\n\r]+)',
            'description': r'Description[:\s]+([^\n\r]+)',
            'primary_colour': r'Primary Colour[:\s]+([^\n\r]+)',
            'fuel_type': r'Fuel Type[:\s]+([^\n\r]+)',
            'transmission': r'Transmission[:\s]+([^\n\r]+)',
            'engine': r'Engine[:\s]+([^\n\r]+)',
            'body_style': r'Body Style[:\s]+([^\n\r]+)',
            'year_manufacture': r'Year Manufacture[:\s]+([^\n\r]+)',
            'euro_status': r'Euro Status[:\s]+([^\n\r]+)',
            'vehicle_age': r'Vehicle Age[:\s]+([^\n\r]+)',
            'registration_place': r'Registration Place[:\s]+([^\n\r]+)',
            'registration_date': r'Registration Date[:\s]+([^\n\r]+)',
            'last_v5c_issue_date': r'Last V5C Issue Date[:\s]+([^\n\r]+)',
            'type_approval': r'Type Approval[:\s]+([^\n\r]+)',
            'wheel_plan': r'Wheel Plan[:\s]+([^\n\r]+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text_content, re.IGNORECASE | re.MULTILINE)
            if match:
                details[key] = match.group(1).strip()
        
        return details
    
    def _extract_mileage_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract mileage information"""
        mileage = {}
        
        text_content = soup.get_text()
        
        # Mileage patterns
        patterns = {
            'last_mot_mileage': r'Last MOT Mileage[:\s]+([^\n\r]+)',
            'mileage_issues': r'Mileage Issues[:\s]+([^\n\r]+)',
            'average': r'Average[:\s]+([^\n\r]+)',
            'status': r'Status[:\s]+([^\n\r]+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text_content, re.IGNORECASE | re.MULTILINE)
            if match:
                mileage[key] = match.group(1).strip()
        
        return mileage
    
    def _extract_performance_data(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract performance data"""
        performance = {}
        
        text_content = soup.get_text()
        
        # Performance patterns
        patterns = {
            'power': r'Power[:\s]+([^\n\r]+)',
            'max_speed': r'Max Speed[:\s]+([^\n\r]+)',
            'torque': r'Torque[:\s]+([^\n\r]+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text_content, re.IGNORECASE | re.MULTILINE)
            if match:
                performance[key] = match.group(1).strip()
        
        return performance
    
    def _extract_fuel_economy(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract fuel economy information"""
        fuel_economy = {}
        
        text_content = soup.get_text()
        
        # Fuel economy patterns
        patterns = {
            'urban': r'Urban[^:]*:[:\s]+([^\n\r]+)',
            'extra_urban': r'Extra Urban[^:]*:[:\s]+([^\n\r]+)',
            'combined': r'Combined[^:]*:[:\s]+([^\n\r]+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text_content, re.IGNORECASE | re.MULTILINE)
            if match:
                fuel_economy[key] = match.group(1).strip()
        
        return fuel_economy
    
    def _extract_safety_ratings(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract safety ratings"""
        safety = {}
        
        text_content = soup.get_text()
        
        # Safety patterns
        patterns = {
            'child': r'Child[:\s]+(\d+\s*%)',
            'adult': r'Adult[:\s]+(\d+\s*%)',
            'pedestrian': r'Pedestrian[:\s]+(\d+\s*%)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text_content, re.IGNORECASE | re.MULTILINE)
            if match:
                safety[key] = match.group(1).strip()
        
        return safety
    
    def _extract_additional_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract additional information"""
        additional = {}
        
        text_content = soup.get_text()
        
        # CO2 emissions
        co2_match = re.search(r'(\d+)\s*g/km', text_content, re.IGNORECASE)
        if co2_match:
            additional['co2_emissions'] = f"{co2_match.group(1)} g/km"
        
        # Tax costs
        tax_12_match = re.search(r'Tax 12 Months Cost[:\s]+([^\n\r]+)', text_content, re.IGNORECASE)
        if tax_12_match:
            additional['tax_12_months'] = tax_12_match.group(1).strip()
        
        tax_6_match = re.search(r'Tax 6 Months Cost[:\s]+([^\n\r]+)', text_content, re.IGNORECASE)
        if tax_6_match:
            additional['tax_6_months'] = tax_6_match.group(1).strip()
        
        # Total keepers
        keepers_match = re.search(r'Total Keepers[:\s]+([^\n\r]+)', text_content, re.IGNORECASE)
        if keepers_match:
            additional['total_keepers'] = keepers_match.group(1).strip()
        
        # V5C Certificate Count
        v5c_match = re.search(r'V5C Certificate Count[:\s]+([^\n\r]+)', text_content, re.IGNORECASE)
        if v5c_match:
            additional['v5c_certificate_count'] = v5c_match.group(1).strip()
        
        return additional
    
    def _normalize_key(self, key: str) -> str:
        """Normalize key names for consistent data structure"""
        return key.lower().replace(' ', '_').replace('/', '_').replace('-', '_').replace('(', '').replace(')', '')