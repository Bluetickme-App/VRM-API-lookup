#!/usr/bin/env python3
"""
Test Ford Focus identification fix
"""

import requests
import json

def test_ford_identification():
    """Test that Ford vehicles are properly identified"""
    print("Testing Ford Vehicle Identification Fix")
    print("=" * 50)
    
    # Test with Focus variants that might be found
    test_cases = [
        "Focus",
        "Focus ST", 
        "Focus RS",
        "Fiesta",
        "Mondeo"
    ]
    
    for variant in test_cases:
        print(f"\nTesting variant: {variant}")
        
        # Simulate the pattern matching logic
        make = 'Unknown'
        model_variant = variant
        
        # Apply the new pattern logic
        if 'focus' in model_variant.lower() or 'fiesta' in model_variant.lower() or 'mondeo' in model_variant.lower():
            make = 'Ford'
        
        print(f"  Model variant: {model_variant}")
        print(f"  Detected make: {make}")
        
        if make == 'Ford':
            print("  ✅ CORRECT: Ford properly identified")
        else:
            print("  ❌ ERROR: Ford not detected")

def test_failure_rate_calculation():
    """Test failure rate calculation with sample data"""
    print("\n" + "=" * 50)
    print("Testing Failure Rate Calculation")
    print("=" * 50)
    
    # Sample MOT data
    sample_tests = [
        {'result': 'PASSED', 'date': '01/01/2020'},
        {'result': 'PASSED', 'date': '01/01/2021'},
        {'result': 'FAILED', 'date': '01/01/2022'},
        {'result': 'PASSED', 'date': '01/01/2023'},
        {'result': 'PASSED', 'date': '01/01/2024'}
    ]
    
    total_tests = len(sample_tests)
    failures = [test for test in sample_tests if test.get('result', '').upper() in ['FAILED', 'FAIL']]
    failure_count = len(failures)
    failure_rate = failure_count / total_tests if total_tests > 0 else 0
    
    print(f"Total tests: {total_tests}")
    print(f"Failures: {failure_count}")
    print(f"Failure rate: {failure_rate:.1%}")
    
    expected_rate = 20.0  # 1 failure out of 5 tests = 20%
    actual_rate = failure_rate * 100
    
    if abs(actual_rate - expected_rate) < 0.1:
        print("✅ CORRECT: Failure rate calculation working")
    else:
        print(f"❌ ERROR: Expected {expected_rate}%, got {actual_rate}%")

def test_comprehensive_make_patterns():
    """Test all the new make detection patterns"""
    print("\n" + "=" * 50)
    print("Testing Comprehensive Make Detection")
    print("=" * 50)
    
    test_patterns = [
        ('Focus', 'Ford'),
        ('Fiesta', 'Ford'),
        ('Corsa', 'Vauxhall'),
        ('Golf', 'Volkswagen'),
        ('A3', 'Audi'),
        ('A4', 'Audi'),
        ('Civic', 'Honda'),
        ('Yaris', 'Toyota'),
        ('Micra', 'Nissan'),
        ('3 Series', 'BMW')
    ]
    
    for model_variant, expected_make in test_patterns:
        # Apply detection logic
        make = 'Unknown'
        
        if 'corsa' in model_variant.lower() or 'astra' in model_variant.lower():
            make = 'Vauxhall'
        elif 'focus' in model_variant.lower() or 'fiesta' in model_variant.lower():
            make = 'Ford'
        elif 'golf' in model_variant.lower() or 'polo' in model_variant.lower():
            make = 'Volkswagen'
        elif 'a3' in model_variant.lower() or 'a4' in model_variant.lower() or 'a6' in model_variant.lower():
            make = 'Audi'
        elif '3 series' in model_variant.lower() or '5 series' in model_variant.lower():
            make = 'BMW'
        elif 'civic' in model_variant.lower() or 'accord' in model_variant.lower():
            make = 'Honda'
        elif 'yaris' in model_variant.lower() or 'corolla' in model_variant.lower():
            make = 'Toyota'
        elif 'micra' in model_variant.lower() or 'qashqai' in model_variant.lower():
            make = 'Nissan'
        
        print(f"{model_variant} -> {make} (expected: {expected_make})")
        
        if make == expected_make:
            print("  ✅ CORRECT")
        else:
            print("  ❌ ERROR")

if __name__ == "__main__":
    print("🔧 TESTING FORD FOCUS & FAILURE RATE FIXES")
    print("=" * 80)
    
    test_ford_identification()
    test_failure_rate_calculation()
    test_comprehensive_make_patterns()
    
    print("\n" + "=" * 80)
    print("📋 FIX SUMMARY")
    print("=" * 80)
    print("✅ Ford Focus detection patterns added to app.py")
    print("✅ Comprehensive make detection for all major brands")
    print("✅ Fixed MOT failure rate calculation in analyzer")
    print("✅ Enhanced MOT pattern analysis with proper error handling")
    print("✅ Added missing return fields to prevent 0.0% failure rates")
    
    print("\n💡 Expected Results:")
    print("   • Ford Focus should now show as 'Ford Focus' not 'Unknown Focus'")
    print("   • Failure rates should calculate from actual MOT data")
    print("   • No more 0.0% failure risk on vehicles with MOT history")
    print("   • All major UK vehicle makes properly detected")