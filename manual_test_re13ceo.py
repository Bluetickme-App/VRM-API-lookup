#!/usr/bin/env python3
"""
Manual test script to verify RE13CEO should return Ferrari F12 Berlinetta
This will help us understand what the correct data should be
"""

import requests
from bs4 import BeautifulSoup
import time

def test_direct_request():
    """Test direct HTTP request to see what data is available"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    try:
        # First, try the main page
        print("Testing main page access...")
        main_response = session.get("https://www.checkcardetails.co.uk/", timeout=15)
        print(f"Main page status: {main_response.status_code}")
        
        time.sleep(2)
        
        # Then try the vehicle page
        print("Testing RE13CEO vehicle page...")
        url = "https://www.checkcardetails.co.uk/cardetails/re13ceo"
        response = session.get(url, timeout=15)
        
        print(f"Vehicle page status: {response.status_code}")
        print(f"Content length: {len(response.text)}")
        print(f"Page title: {BeautifulSoup(response.text, 'html.parser').title.text if BeautifulSoup(response.text, 'html.parser').title else 'No title'}")
        
        # Check for Cloudflare protection
        if "just a moment" in response.text.lower():
            print("❌ Cloudflare protection detected")
        elif "ferrari" in response.text.lower():
            print("✅ Ferrari found in page content!")
        elif "f12" in response.text.lower():
            print("✅ F12 found in page content!")
        else:
            print("⚠️ No Ferrari/F12 detected - content may be blocked")
            
        # Look for any vehicle make/model info
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text().lower()
        
        for make in ['ferrari', 'audi', 'mercedes', 'bmw', 'ford', 'vauxhall']:
            if make in text:
                print(f"Found vehicle make: {make.upper()}")
                
        return response.text
        
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    test_direct_request()