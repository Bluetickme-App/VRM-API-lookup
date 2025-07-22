#!/usr/bin/env python3
"""
Test OpenAI GPT-4o Analysis with sample vehicle data
Demonstrates the intelligent analysis capabilities
"""

from vehicle_analyzer import analyze_vehicle_data, format_analysis_for_display
import json

def test_openai_analysis():
    """Test the OpenAI analysis with sample vehicle data"""
    
    # Sample vehicle data based on K5WBR structure
    sample_vehicle_data = {
        'registration': 'K5WBR',
        'make': 'Unknown',
        'model': 'Unknown', 
        'year': 2024,
        'color': 'White',
        'fuel_type': 'DIESEL',
        'engine_size': 'Unknown',
        'co2_emissions': 'Unknown',
        'date_first_registered': '2024-01-01',
        'tax_status': 'Taxed',
        'mot_status': 'Valid',
        'mot_expiry': '2024-06-07',
        'mot_history': {
            'mot_tests': [
                {
                    'test_date': '08/06/2023',
                    'result': 'PASSED_WITH_ADVISORY',
                    'mileage': '116639',
                    'expiry_date': '07/06/2024',
                    'comments': 'Offside Front Tyre tread depth low'
                },
                {
                    'test_date': '25/03/2022',
                    'result': 'FAILED',
                    'mileage': '103225',
                    'expiry_date': '24/03/2023',
                    'comments': 'Offside Front Tyre tread depth below minimum'
                },
                {
                    'test_date': '24/03/2021',
                    'result': 'PASSED_WITH_ADVISORY',
                    'mileage': '95122',
                    'expiry_date': '23/03/2022',
                    'comments': 'Brake disc worn, suspension component worn'
                },
                {
                    'test_date': '22/03/2021',
                    'result': 'FAILED',
                    'mileage': '95122',
                    'expiry_date': '',
                    'comments': 'Nearside Front Tyre has a cut or defect'
                },
                {
                    'test_date': '09/03/2020',
                    'result': 'PASSED_WITH_ADVISORY',
                    'mileage': '88002',
                    'expiry_date': '20/03/2021',
                    'comments': 'Oil leak, brake disc worn'
                },
                {
                    'test_date': '21/03/2019',
                    'result': 'PASSED_WITH_ADVISORY',
                    'mileage': '76799',
                    'expiry_date': '20/03/2020',
                    'comments': 'Tyre worn close to legal limit'
                },
                {
                    'test_date': '17/04/2018',
                    'result': 'PASSED_WITH_ADVISORY',
                    'mileage': '58950',
                    'expiry_date': '22/04/2019',
                    'comments': 'Windscreen washer reservoir low'
                }
            ]
        },
        'mileage_history': {
            'mileage_records': [
                {'date': '08/06/2023', 'mileage': '116639'},
                {'date': '25/03/2022', 'mileage': '103225'},
                {'date': '24/03/2021', 'mileage': '95122'},
                {'date': '22/03/2021', 'mileage': '95122'},
                {'date': '09/03/2020', 'mileage': '88002'},
                {'date': '21/03/2019', 'mileage': '76799'},
                {'date': '17/04/2018', 'mileage': '58950'}
            ]
        }
    }
    
    print("🧠 Testing OpenAI GPT-4o Vehicle Analysis...")
    print(f"Vehicle: {sample_vehicle_data['registration']} ({sample_vehicle_data['year']} {sample_vehicle_data['color']} {sample_vehicle_data['fuel_type']})")
    print(f"MOT Tests: {len(sample_vehicle_data['mot_history']['mot_tests'])}")
    print()
    
    # Perform OpenAI analysis
    print("Sending data to OpenAI GPT-4o for analysis...")
    analysis_result = analyze_vehicle_data(sample_vehicle_data)
    
    if "error" in analysis_result:
        print(f"❌ Analysis failed: {analysis_result['error']}")
        return
    
    print("✅ Analysis completed successfully!")
    print()
    
    # Format for display
    formatted_result = format_analysis_for_display(analysis_result)
    
    if not formatted_result['success']:
        print(f"❌ Formatting failed: {formatted_result['error']}")
        return
    
    # Display key results
    display_data = formatted_result['display_data']
    overall = display_data.get('overall_assessment', {})
    mot_pred = display_data.get('mot_predictions', {})
    costs = display_data.get('cost_breakdown', {})
    
    print("🔍 INTELLIGENT ANALYSIS RESULTS:")
    print("=" * 50)
    print(f"Overall Risk Level: {overall.get('risk_level', 'Unknown')}")
    print(f"Mechanical Grade: {overall.get('mechanical_grade', 'Unknown')}")
    print(f"Trade Recommendation: {overall.get('trade_advice', 'Unknown')}")
    print(f"CAP Pricing Tier: {overall.get('cap_tier', 'Unknown')}")
    print()
    
    print("🚨 MOT FAILURE PREDICTIONS:")
    print(f"Failure Probability: {mot_pred.get('failure_probability', 0)}%")
    likely_failures = mot_pred.get('likely_failures', [])
    if likely_failures:
        print("Likely Failure Areas:")
        for failure in likely_failures:
            print(f"  - {failure}")
    print()
    
    print("💰 COST ESTIMATES:")
    print(f"Immediate Repairs: £{costs.get('immediate_repairs', 0)}")
    print(f"Pre-MOT Work: £{costs.get('pre_mot_work', 0)}")
    print(f"Annual Maintenance: £{costs.get('annual_maintenance', 0)}")
    print(f"Total First Year: £{costs.get('total_first_year', 0)}")
    print()
    
    print("⚠️ RISK FACTORS:")
    risk_factors = display_data.get('risk_factors', [])
    if risk_factors:
        for factor in risk_factors:
            print(f"  - {factor}")
    else:
        print("  No significant risk factors identified")
    print()
    
    print("✅ POSITIVE INDICATORS:")
    positives = display_data.get('positive_indicators', [])
    if positives:
        for positive in positives:
            print(f"  - {positive}")
    else:
        print("  No positive indicators identified")
    print()
    
    print("📊 MILEAGE ANALYSIS:")
    mileage = display_data.get('mileage_analysis', {})
    if mileage:
        if mileage.get('current_mileage'):
            print(f"Current Mileage: {mileage['current_mileage']:,} miles")
        if mileage.get('annual_average'):
            print(f"Annual Average: {mileage['annual_average']:,} miles/year")
        if mileage.get('mileage_risk'):
            print(f"Mileage Risk: {mileage['mileage_risk']}")
    print()
    
    print("🔧 OWNERSHIP ANALYSIS:")
    ownership = display_data.get('ownership_analysis', {})
    if ownership.get('v5_changes_detected') is not None:
        print(f"V5 Changes Detected: {'Yes' if ownership['v5_changes_detected'] else 'No'}")
    
    trading_indicators = ownership.get('trading_indicators', [])
    if trading_indicators:
        print("Trading Indicators:")
        for indicator in trading_indicators:
            print(f"  - {indicator}")
    
    print("\n" + "=" * 50)
    print("🎯 OpenAI GPT-4o Analysis Complete!")
    
    # Save full result for inspection
    with open('sample_analysis_result.json', 'w') as f:
        json.dump(analysis_result, f, indent=2)
    
    print("📄 Full analysis saved to: sample_analysis_result.json")


if __name__ == '__main__':
    test_openai_analysis()