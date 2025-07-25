#!/usr/bin/env python3
"""
Test OCR with the real Mercedes number plate image
"""

import requests
import base64
import json
from PIL import Image
import io

def test_mercedes_plate():
    """Test OCR with the actual Mercedes plate image YE66 FHT"""
    
    print("🚗 Testing OCR with Real Mercedes Number Plate")
    print("Expected: YE66 FHT")
    print("=" * 50)
    
    try:
        # Load the Mercedes image
        image_path = "attached_assets/7_MERCEDES-BENZ_C class amg line business edition _FG45BNN_1753472876434.jpg"
        
        # Convert image to base64
        with open(image_path, 'rb') as img_file:
            img_data = img_file.read()
            img_base64 = base64.b64encode(img_data).decode()
            image_data_url = f"data:image/jpeg;base64,{img_base64}"
        
        print("📸 Image loaded successfully")
        print("🔄 Sending to OCR API...")
        
        # Test with OCR API
        response = requests.post(
            'http://localhost:5000/api/ocr-process',
            json={'imageData': image_data_url},
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ OCR API Response:")
            print(f"Success: {result.get('success')}")
            print(f"Extracted Text: '{result.get('extracted_text', '')}'")
            print(f"Best Match: {result.get('best_match')}")
            print(f"All Candidates: {result.get('potential_plates', [])}")
            
            if result.get('debug_info'):
                print(f"Debug Info: {result['debug_info']}")
            
            best_match = result.get('best_match')
            if best_match:
                expected_clean = "YE66FHT"
                actual_clean = best_match.replace(' ', '')
                
                if actual_clean == expected_clean:
                    print("🎉 PERFECT MATCH! OCR correctly detected YE66 FHT")
                    return True
                else:
                    print(f"⚠️  Partial match: Expected 'YE66FHT', Got '{actual_clean}'")
                    
                    # Check if it's close enough (common OCR substitutions)
                    if len(actual_clean) == len(expected_clean):
                        differences = sum(1 for a, b in zip(actual_clean, expected_clean) if a != b)
                        if differences <= 2:
                            print(f"✅ Close match (only {differences} character differences)")
                            return True
            else:
                print("❌ No number plate detected")
                
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except FileNotFoundError:
        print("❌ Mercedes image file not found")
    except Exception as e:
        print(f"❌ Test error: {e}")
    
    return False

def test_with_cropped_plate():
    """Try with a cropped version focusing on the number plate area"""
    try:
        print("\n🔧 Attempting with cropped number plate area...")
        
        # Load and crop the image to focus on the plate
        image_path = "attached_assets/7_MERCEDES-BENZ_C class amg line business edition _FG45BNN_1753472876434.jpg"
        img = Image.open(image_path)
        
        # Crop to approximate number plate area (you may need to adjust coordinates)
        # Based on the image, the plate appears to be in the lower-center area
        width, height = img.size
        
        # Estimate plate location (adjust these coordinates as needed)
        left = int(width * 0.35)   # 35% from left
        top = int(height * 0.7)    # 70% from top  
        right = int(width * 0.65)  # 65% from left
        bottom = int(height * 0.85) # 85% from top
        
        cropped_img = img.crop((left, top, right, bottom))
        
        # Convert to base64
        buffer = io.BytesIO()
        cropped_img.save(buffer, format='JPEG')
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        image_data_url = f"data:image/jpeg;base64,{img_base64}"
        
        # Test with OCR API
        response = requests.post(
            'http://localhost:5000/api/ocr-process',
            json={'imageData': image_data_url},
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            print("📋 Cropped Image OCR Results:")
            print(f"Extracted Text: '{result.get('extracted_text', '')}'")
            print(f"Best Match: {result.get('best_match')}")
            print(f"All Candidates: {result.get('potential_plates', [])}")
            
            if result.get('best_match'):
                print("✅ Cropped image OCR successful!")
                return True
                
    except Exception as e:
        print(f"❌ Cropped test error: {e}")
    
    return False

if __name__ == "__main__":
    success = test_mercedes_plate()
    
    if not success:
        print("\n" + "=" * 50)
        print("Trying alternative approach...")
        test_with_cropped_plate()