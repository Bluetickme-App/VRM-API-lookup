#!/usr/bin/env python3
"""
Test script for the Enhanced Selenium Scraper with MOT and mileage history
"""

import logging
from enhanced_selenium_scraper import EnhancedSeleniumScraper
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_enhanced_scraper():
    """Test the enhanced scraper with a sample registration"""
    
    # Use a common test registration (this would be replaced with a real one in production)
    test_registration = "AB12CDE"
    
    logger.info(f"Testing enhanced scraper with registration: {test_registration}")
    
    try:
        # Initialize the enhanced scraper
        scraper = EnhancedSeleniumScraper(headless=True)
        
        # Scrape complete vehicle data including MOT and mileage history
        result = scraper.scrape_complete_vehicle_data(test_registration)
        
        if result:
            logger.info("✅ Enhanced scraping completed successfully!")
            
            # Print basic info
            basic_info = result.get('basic_info', {})
            logger.info(f"Make: {basic_info.get('make', 'Unknown')}")
            logger.info(f"Model: {basic_info.get('model', 'Unknown')}")
            logger.info(f"Year: {basic_info.get('year', 'Unknown')}")
            
            # Check for MOT history
            mot_history = result.get('mot_history', {})
            if mot_history:
                mot_tests = mot_history.get('mot_tests', [])
                logger.info(f"📋 MOT History: Found {len(mot_tests)} test records")
                
                if mot_tests:
                    logger.info("Recent MOT tests:")
                    for i, test in enumerate(mot_tests[:3]):  # Show first 3
                        test_date = test.get('test_date', 'Unknown date')
                        result_status = test.get('result', 'Unknown result')
                        mileage = test.get('mileage', 'Unknown mileage')
                        logger.info(f"  {i+1}. {test_date} - {result_status} ({mileage})")
                
                summary = mot_history.get('summary', {})
                if summary:
                    logger.info(f"MOT Summary: {summary}")
            else:
                logger.info("📋 No MOT history data found")
            
            # Check for mileage history
            mileage_history = result.get('mileage_history', {})
            if mileage_history:
                mileage_records = mileage_history.get('mileage_records', [])
                logger.info(f"🛣️ Mileage History: Found {len(mileage_records)} records")
                
                if mileage_records:
                    logger.info("Recent mileage records:")
                    for i, record in enumerate(mileage_records[:3]):  # Show first 3
                        date = record.get('date', 'Unknown date')
                        mileage = record.get('mileage', 'Unknown mileage')
                        source = record.get('source', 'Unknown source')
                        logger.info(f"  {i+1}. {date} - {mileage} ({source})")
                
                analysis = mileage_history.get('analysis', {})
                if analysis:
                    logger.info(f"Mileage Analysis: {analysis}")
            else:
                logger.info("🛣️ No mileage history data found")
            
            # Save full result to file for inspection
            with open('test_scraper_result.json', 'w') as f:
                json.dump(result, f, indent=2, default=str)
            logger.info("💾 Full result saved to test_scraper_result.json")
            
            return True
            
        else:
            logger.error("❌ Enhanced scraping failed - no data returned")
            return False
            
    except Exception as e:
        logger.error(f"❌ Enhanced scraping failed with error: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting Enhanced Selenium Scraper Test")
    success = test_enhanced_scraper()
    
    if success:
        logger.info("✅ Test completed successfully!")
    else:
        logger.info("❌ Test failed!")