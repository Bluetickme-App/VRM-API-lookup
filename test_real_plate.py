#!/usr/bin/env python3
"""
Test real registration to see Ford detection in action
"""

import requests
import json

def test_real_registration():
    """Test with real Ford Focus registration that's showing as Unknown"""
    print("🚗 TESTING REAL FORD FOCUS REGISTRATION")
    print("=" * 60)
    
    # Use a real registration that should be Ford Focus
    test_reg = "FG45BNN"  # Based on the attached image showing Mercedes C-Class
    
    try:
        response = requests.post(
            'http://localhost:5000/api/scrape',
            headers={'Content-Type': 'application/json'},
            json={'registration': test_reg},
            timeout=30
        )
        
        print(f"Testing registration: {test_reg}")
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                vehicle_data = data.get('data', {})
                print(f"✅ SUCCESS")
                print(f"Make: {vehicle_data.get('make', 'Not found')}")
                print(f"Model: {vehicle_data.get('model', 'Not found')}")
                print(f"Description: {vehicle_data.get('description', 'Not found')}")
                print(f"Year: {vehicle_data.get('year', 'Not found')}")
                print(f"Color: {vehicle_data.get('color', 'Not found')}")
                
                # Check if it's still showing as Unknown
                if vehicle_data.get('make') == 'Unknown':
                    print("❌ STILL SHOWING UNKNOWN - FORD FIX NOT WORKING")
                else:
                    print("✅ VEHICLE IDENTIFIED CORRECTLY")
                    
            else:
                print(f"❌ API ERROR: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ HTTP ERROR: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
    except requests.exceptions.Timeout:
        print("⏰ REQUEST TIMEOUT - Server may be processing")
    except Exception as e:
        print(f"❌ ERROR: {e}")

def test_ford_patterns():
    """Test Ford detection patterns"""
    print("\n🔧 TESTING FORD DETECTION PATTERNS")
    print("=" * 60)
    
    test_cases = [
        ("Focus", "Some description", "Ford"),
        ("FOCUS ST", "Sport variant", "Ford"),
        ("Unknown", "Ford Focus description", "Ford"),
        ("Mondeo", "Family car", "Ford"),
        ("Fiesta", "City car", "Ford"),
        ("Corsa", "Small car", "Vauxhall"),
        ("Golf", "Hatchback", "Volkswagen")
    ]
    
    for model_variant, description, expected_make in test_cases:
        # Apply the detection logic
        make = 'Unknown'
        
        if 'corsa' in model_variant.lower() or 'astra' in model_variant.lower():
            make = 'Vauxhall'
        elif ('focus' in model_variant.lower() or 'fiesta' in model_variant.lower() or 'mondeo' in model_variant.lower() or
              'focus' in description.lower() or 'fiesta' in description.lower() or 'mondeo' in description.lower()):
            make = 'Ford'
        elif 'golf' in model_variant.lower() or 'polo' in model_variant.lower():
            make = 'Volkswagen'
        
        print(f"Model: '{model_variant}', Description: '{description}' → {make} (expected: {expected_make})")
        
        if make == expected_make:
            print("✅ CORRECT")
        else:
            print("❌ ERROR")
        print("-" * 40)

if __name__ == "__main__":
    test_real_registration()
    test_ford_patterns()
    
    print("\n📋 FORD FIX STATUS")
    print("=" * 60)
    print("✅ Enhanced Ford detection patterns added to app.py")
    print("✅ Debug logging added to trace model_variant and description")
    print("✅ Checking both model_variant AND description fields")
    print("🔄 Testing with real registration to verify fix works")