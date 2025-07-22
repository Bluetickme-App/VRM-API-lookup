"""
Test script for the Direct Vehicle Extractor
"""
import logging
from direct_vehicle_extractor import DirectVehicleExtractor

logging.basicConfig(level=logging.INFO)

def test_extraction(registration):
    print(f"=== TESTING DIRECT EXTRACTOR FOR {registration} ===")
    
    extractor = DirectVehicleExtractor()
    result = extractor.extract_authentic_vehicle_data(registration)
    extractor.cleanup()
    
    print(f"Registration: {result['registration']}")
    print(f"Data Source: {result['data_source']}")
    print(f"Success: {result['extraction_success']}")
    
    critical_fields = {
        'make': result['make'],
        'model': result['model'], 
        'year': result['year'],
        'color': result['color'],
        'fuel_type': result['fuel_type'],
        'transmission': result['transmission'],
        'engine_size': result['engine_size']
    }
    
    filled = sum(1 for val in critical_fields.values() if val and str(val) not in ['Unknown', '', 'None'])
    total = len(critical_fields)
    
    print(f"\nEXTRACTION RESULTS: {filled}/{total} fields ({(filled/total)*100:.1f}%)")
    
    for field, value in critical_fields.items():
        status = '✅' if value and str(value) not in ['Unknown', '', 'None'] else '❌'
        print(f'{status} {field}: {value or "Missing"}')
    
    return result

if __name__ == "__main__":
    test_extraction("RE13CEO")