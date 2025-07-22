#!/usr/bin/env python3
"""
Direct test to verify 16 MOT tests extraction for DA07BWF
"""

import requests
import json
import time

def test_16_tests_extraction():
    """Test the enhanced system to capture all 16 MOT tests"""
    print("🔍 Testing Enhanced 16-Test Extraction System for DA07BWF")
    
    # Clear any cached data first
    try:
        response = requests.delete("http://localhost:5000/api/clear-cache/DA07BWF")
        print("✅ Cache cleared")
    except:
        print("⚠️ Cache clear failed - continuing anyway")
    
    # Test the enhanced extraction
    start_time = time.time()
    
    try:
        response = requests.post(
            "http://localhost:5000/api/vehicle-data",
            json={"registration": "DA07BWF"},
            timeout=120
        )
        
        elapsed_time = time.time() - start_time
        print(f"⏱️ Request completed in {elapsed_time:.1f} seconds")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                vehicle_data = data.get('vehicle_data', {})
                mot_history = vehicle_data.get('mot_history', {})
                mot_tests = mot_history.get('mot_tests', [])
                
                print(f"\n📊 RESULTS:")
                print(f"MOT Tests Captured: {len(mot_tests)} / 16 target")
                print(f"Source: {mot_history.get('scraped_from', 'unknown')}")
                
                if len(mot_tests) >= 16:
                    print("🎯 SUCCESS: All 16+ tests captured!")
                    success_rate = "COMPLETE"
                elif len(mot_tests) >= 10:
                    print(f"📈 EXCELLENT: {len(mot_tests)} tests - major improvement!")
                    success_rate = "EXCELLENT"
                elif len(mot_tests) > 4:
                    print(f"📊 PROGRESS: {len(mot_tests)} tests (improvement from 4)")
                    success_rate = "PROGRESS"
                else:
                    print(f"⚠️ LIMITED: {len(mot_tests)} tests - same as before")
                    success_rate = "LIMITED"
                
                # Show year coverage
                years = set()
                for test in mot_tests:
                    date = test.get('test_date', '')
                    if date and len(date) >= 4:
                        years.add(date[:4])
                
                print(f"Years covered: {sorted(years)} ({len(years)} year span)")
                
                if len(years) >= 10:
                    print("✅ Comprehensive historical coverage achieved")
                
                # Show sample tests
                if mot_tests:
                    print(f"\n📋 Sample Tests (first 5):")
                    for i, test in enumerate(mot_tests[:5]):
                        result = test.get('result', 'UNKNOWN')
                        date = test.get('test_date', 'Unknown date')
                        mileage = test.get('mileage', 'No mileage')
                        comments_count = len(test.get('comments', []))
                        print(f"  {i+1}. {date} - {result} - {mileage} miles - {comments_count} comments")
                
                return {
                    'success': True,
                    'tests_captured': len(mot_tests),
                    'success_rate': success_rate,
                    'years_covered': len(years),
                    'response_time': elapsed_time
                }
            else:
                print(f"❌ API Error: {data.get('error', 'Unknown error')}")
                return {'success': False, 'error': data.get('error')}
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
    except requests.exceptions.Timeout:
        print("⏱️ Request timed out - enhanced extraction may still be running")
        return {'success': False, 'error': 'Timeout'}
    except Exception as e:
        print(f"❌ Exception: {e}")
        return {'success': False, 'error': str(e)}

def main():
    """Main test function"""
    print("=" * 60)
    print("DA07BWF - 16 MOT Tests Extraction Verification")
    print("=" * 60)
    
    result = test_16_tests_extraction()
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    
    if result.get('success'):
        tests = result.get('tests_captured', 0)
        rate = result.get('success_rate', 'Unknown')
        years = result.get('years_covered', 0)
        time_taken = result.get('response_time', 0)
        
        print(f"✅ Tests Captured: {tests}/16")
        print(f"📈 Success Rate: {rate}")
        print(f"📅 Historical Coverage: {years} years")
        print(f"⏱️ Response Time: {time_taken:.1f}s")
        
        if tests >= 16:
            print("🏆 MISSION ACCOMPLISHED: Complete 16-test extraction achieved!")
        elif tests >= 10:
            print("🥇 EXCELLENT PROGRESS: Major improvement in test extraction!")
        elif tests > 4:
            print("🥈 GOOD PROGRESS: Improvement from previous 4-test limitation!")
        else:
            print("🔧 NEEDS WORK: Still limited to original test count")
    else:
        print(f"❌ Test Failed: {result.get('error', 'Unknown error')}")
    
    print("=" * 60)

if __name__ == "__main__":
    main()