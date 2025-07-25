#!/usr/bin/env python3
"""
Complete OCR system test demonstrating all functionality
"""

import requests
import json
from PIL import Image, ImageDraw, ImageFont
import base64
import io

def create_realistic_numberplate(registration="AB12 CDE"):
    """Create a realistic UK number plate image"""
    # UK number plate dimensions (roughly 520x111mm scaled down)
    width, height = 400, 80
    
    # Create white background with black border
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw black border
    draw.rectangle([2, 2, width-2, height-2], outline='black', width=2)
    
    # Try to load a font
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 32)
    except:
        font = ImageFont.load_default()
    
    # Calculate text position (centered)
    bbox = draw.textbbox((0, 0), registration, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    # Draw the registration text
    draw.text((x, y), registration, fill='black', font=font)
    
    return img

def image_to_base64(image):
    """Convert PIL image to base64 data URL"""
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_base64}"

def test_complete_ocr_workflow():
    """Test the complete OCR workflow with realistic number plates"""
    
    print("🔍 Testing Complete OCR System")
    print("=" * 50)
    
    # Test different UK registration formats
    test_registrations = [
        "AB12 CDE",  # Current format
        "X123 ABC",  # Current format  
        "DA07 BWF",  # Current format
        "RE13 CEO",  # Current format
        "SJ57 PGV"   # Current format
    ]
    
    success_count = 0
    total_tests = len(test_registrations)
    
    for i, registration in enumerate(test_registrations, 1):
        print(f"\n📋 Test {i}/{total_tests}: {registration}")
        print("-" * 30)
        
        try:
            # Create realistic number plate image
            print("📸 Creating number plate image...")
            plate_image = create_realistic_numberplate(registration)
            
            # Convert to base64
            image_data = image_to_base64(plate_image)
            print("🔄 Converting to base64...")
            
            # Send to OCR endpoint
            print("🚀 Sending to OCR API...")
            response = requests.post(
                'http://localhost:5000/api/ocr-process',
                json={'imageData': image_data},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    extracted_text = result.get('extracted_text', '')
                    best_match = result.get('best_match')
                    potential_plates = result.get('potential_plates', [])
                    
                    print(f"✅ OCR Response: Success")
                    print(f"📝 Extracted Text: '{extracted_text}'")
                    print(f"🎯 Best Match: {best_match}")
                    print(f"🔍 All Candidates: {potential_plates}")
                    
                    # Check if we got the correct registration
                    expected_clean = registration.replace(' ', '')
                    if best_match and best_match.replace(' ', '') == expected_clean:
                        print(f"🎉 PERFECT MATCH! Expected: {registration}")
                        success_count += 1
                    elif best_match:
                        print(f"⚠️  Close match (Expected: {registration}, Got: {best_match})")
                        success_count += 0.5  # Partial credit
                    else:
                        print(f"❌ No match found")
                        if result.get('debug_info'):
                            print(f"🐛 Debug: {result['debug_info']}")
                else:
                    print(f"❌ OCR Failed: {result.get('error', 'Unknown error')}")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to server")
            break
        except Exception as e:
            print(f"❌ Test error: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Total Tests: {total_tests}")
    print(f"Successful: {success_count}")
    print(f"Success Rate: {(success_count/total_tests)*100:.1f}%")
    
    if success_count >= total_tests * 0.8:
        print("🎉 OCR SYSTEM: EXCELLENT PERFORMANCE!")
    elif success_count >= total_tests * 0.6:
        print("✅ OCR SYSTEM: GOOD PERFORMANCE")
    else:
        print("⚠️  OCR SYSTEM: NEEDS IMPROVEMENT")

def test_vehicle_integration():
    """Test OCR integration with vehicle lookup"""
    print("\n🚗 Testing OCR → Vehicle Lookup Integration")
    print("=" * 50)
    
    # Use a known working registration
    test_reg = "DA07 BWF"
    
    try:
        # Create number plate image
        plate_image = create_realistic_numberplate(test_reg)
        image_data = image_to_base64(plate_image)
        
        # OCR Step
        print("1. 📸 OCR Processing...")
        ocr_response = requests.post(
            'http://localhost:5000/api/ocr-process',
            json={'imageData': image_data},
            headers={'Content-Type': 'application/json'}
        )
        
        if ocr_response.status_code == 200:
            ocr_result = ocr_response.json()
            detected_reg = ocr_result.get('best_match')
            
            if detected_reg:
                print(f"✅ OCR Detected: {detected_reg}")
                
                # Vehicle Lookup Step
                print("2. 🔍 Vehicle Data Lookup...")
                vehicle_response = requests.get(
                    f'http://localhost:5000/api/vehicle-data?registration={detected_reg}',
                    timeout=30
                )
                
                if vehicle_response.status_code == 200:
                    vehicle_data = vehicle_response.json()
                    
                    if vehicle_data.get('success'):
                        print("✅ Vehicle Data Retrieved Successfully!")
                        print(f"🚗 Make: {vehicle_data.get('make', 'N/A')}")
                        print(f"📝 Model: {vehicle_data.get('model', 'N/A')}")
                        print(f"📅 Year: {vehicle_data.get('year', 'N/A')}")
                        print("🎉 COMPLETE WORKFLOW SUCCESS!")
                    else:
                        print(f"⚠️  Vehicle lookup failed: {vehicle_data.get('error', 'Unknown')}")
                else:
                    print(f"❌ Vehicle API error: {vehicle_response.status_code}")
            else:
                print("❌ No registration detected by OCR")
        else:
            print(f"❌ OCR API error: {ocr_response.status_code}")
            
    except Exception as e:
        print(f"❌ Integration test error: {e}")

if __name__ == "__main__":
    test_complete_ocr_workflow()
    test_vehicle_integration()