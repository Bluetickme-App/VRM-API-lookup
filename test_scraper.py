#!/usr/bin/env python3
"""
Quick test script to validate the scraping functionality
"""

import requests
from enhanced_scraper import EnhancedVehicleScraper
from test_data_service import get_sample_vehicle_data
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_website_access():
    """Test if we can access the website directly"""
    try:
        response = requests.get("https://www.checkcardetails.co.uk/", 
                              headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        logger.info(f"Website response: {response.status_code}")
        if response.status_code == 200:
            logger.info("Website is accessible")
            return True
        else:
            logger.warning(f"Website returned status code: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Cannot access website: {e}")
        return False

def test_enhanced_scraper():
    """Test the enhanced scraper"""
    logger.info("Testing Enhanced Scraper...")
    scraper = EnhancedVehicleScraper()
    result = scraper.scrape_vehicle_data("LP68OHB")
    
    if result:
        logger.info("Enhanced scraper SUCCESS")
        return result
    else:
        logger.info("Enhanced scraper FAILED")
        return None

def test_sample_data():
    """Test sample data generation"""
    logger.info("Testing sample data generation...")
    sample = get_sample_vehicle_data("LP68OHB")
    if sample:
        logger.info("Sample data generation SUCCESS")
        return sample
    else:
        logger.info("Sample data generation FAILED")
        return None

if __name__ == "__main__":
    print("=== Vehicle Scraper Test Suite ===")
    
    # Test 1: Website accessibility
    print("\n1. Testing website access...")
    website_ok = test_website_access()
    
    # Test 2: Enhanced scraper
    print("\n2. Testing enhanced scraper...")
    enhanced_result = test_enhanced_scraper()
    
    # Test 3: Sample data fallback
    print("\n3. Testing sample data fallback...")
    sample_result = test_sample_data()
    
    print("\n=== Test Results ===")
    print(f"Website accessible: {website_ok}")
    print(f"Enhanced scraper working: {enhanced_result is not None}")
    print(f"Sample data available: {sample_result is not None}")
    
    if enhanced_result:
        print(f"Extracted data keys: {list(enhanced_result.keys())}")
    elif sample_result:
        print(f"Sample data keys: {list(sample_result.keys())}")