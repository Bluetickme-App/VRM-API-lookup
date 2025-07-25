#!/usr/bin/env python3
"""
Simple OCR test to verify functionality
"""

import requests
import base64
import json

def test_ocr_endpoint():
    """Test the OCR endpoint with a simple text image"""
    
    # Create a simple base64 test image (1x1 white pixel as minimal test)
    # In real usage, this would be an actual number plate image
    test_image_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    
    try:
        # Test the OCR endpoint
        response = requests.post('http://localhost:5000/api/ocr-process', 
                               json={'imageData': test_image_data},
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            result = response.json()
            print("✅ OCR endpoint is working")
            print(f"Response: {result}")
            
            if 'error' in result:
                print(f"⚠️ OCR processing error: {result['error']}")
            else:
                print("✅ OCR processing successful")
                
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server on localhost:5000")
    except Exception as e:
        print(f"❌ Test error: {e}")

def test_plate_patterns():
    """Test UK number plate patterns"""
    from ocr_processor import NumberPlateOCR
    
    ocr = NumberPlateOCR()
    
    test_plates = [
        "AB12CDE",
        "AB12 CDE", 
        "X123ABC",
        "DA07BWF",
        "RE13CEO"
    ]
    
    print("\nTesting plate pattern validation:")
    for plate in test_plates:
        is_valid = ocr.validate_uk_plate(plate)
        print(f"{plate}: {'✅ Valid' if is_valid else '❌ Invalid'}")
    
    # Test pattern finding
    test_text = "SOME TEXT AB12CDE MORE TEXT"
    plates = ocr._find_number_plates(test_text)
    print(f"\nPattern extraction from '{test_text}':")
    print(f"Found plates: {plates}")

if __name__ == "__main__":
    print("Testing OCR functionality...")
    test_ocr_endpoint()
    test_plate_patterns()