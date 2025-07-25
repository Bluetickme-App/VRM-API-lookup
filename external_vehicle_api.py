"""
External Vehicle API Endpoint
Complete vehicle data retrieval API for external integration
Returns comprehensive DVLA data including MOT history, ownership, tax costs, and AI analysis
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
from models import VehicleData, db
from data_extractor import DataExtractor
from vehicle_analyzer import analyze_vehicle_data, format_analysis_for_display

# Create blueprint for external API
external_api = Blueprint('external_vehicle_api', __name__)


@external_api.route('/api/external/vehicle/<registration>', methods=['GET'])
def get_complete_vehicle_data(registration):
    """
    External API endpoint to get complete vehicle data by registration
    Returns comprehensive vehicle information including MOT history and AI analysis
    
    Usage: GET /api/external/vehicle/K5WBR
    Returns: Complete vehicle data in JSON format
    """
    try:
        registration = registration.upper().strip()
        
        if not registration:
            return jsonify({
                'success': False,
                'error': 'Registration number is required',
                'data': None
            }), 400
        
        logging.info(f"External API request for registration: {registration}")
        
        # Check if vehicle data exists in database (24-hour cache)
        vehicle_record = VehicleData.query.filter_by(registration=registration).first()
        
        # If no data exists or data is older than 24 hours, scrape fresh data
        if not vehicle_record or is_data_expired(vehicle_record.last_updated):
            logging.info(f"Scraping fresh data for {registration}")
            
            # Use DataExtractor to get comprehensive vehicle data
            extractor = DataExtractor()
            scrape_result = extractor.extract_complete_vehicle_data(registration)
            
            if not scrape_result['success']:
                return jsonify({
                    'success': False,
                    'error': f'Failed to retrieve vehicle data: {scrape_result.get("error", "Unknown error")}',
                    'data': None
                }), 404
            
            # Save to database
            vehicle_data = scrape_result['data']
            save_vehicle_data_to_db(registration, vehicle_data)
            
            # Get updated record
            vehicle_record = VehicleData.query.filter_by(registration=registration).first()
        
        # Format comprehensive response
        response_data = format_complete_vehicle_response(vehicle_record)
        
        # Include AI analysis if available
        if vehicle_record.analysis_completed and vehicle_record.analysis_data:
            response_data['ai_analysis'] = vehicle_record.analysis_data
            response_data['analysis_available'] = True
        else:
            response_data['analysis_available'] = False
        
        return jsonify({
            'success': True,
            'data': response_data,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'cached' if vehicle_record.last_updated else 'fresh'
        })
        
    except Exception as e:
        logging.error(f"External API error for {registration}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}',
            'data': None
        }), 500


@external_api.route('/api/external/vehicle/<registration>/analyze', methods=['POST'])
def get_vehicle_with_analysis(registration):
    """
    External API endpoint to get complete vehicle data with AI analysis
    Performs fresh AI analysis if not already available
    
    Usage: POST /api/external/vehicle/K5WBR/analyze
    Returns: Complete vehicle data with AI analysis
    """
    try:
        registration = registration.upper().strip()
        
        if not registration:
            return jsonify({
                'success': False,
                'error': 'Registration number is required',
                'data': None
            }), 400
        
        logging.info(f"External API analysis request for registration: {registration}")
        
        # Get vehicle data (scrape if needed)
        vehicle_record = VehicleData.query.filter_by(registration=registration).first()
        
        if not vehicle_record:
            return jsonify({
                'success': False,
                'error': f'No vehicle data found for {registration}. Please scrape vehicle data first.',
                'data': None
            }), 404
        
        # Perform AI analysis if not already done
        if not vehicle_record.analysis_completed or not vehicle_record.analysis_data:
            logging.info(f"Performing AI analysis for {registration}")
            
            # Prepare vehicle data for analysis
            vehicle_data = prepare_data_for_analysis(vehicle_record)
            
            # Perform OpenAI analysis
            analysis_result = analyze_vehicle_data(vehicle_data)
            formatted_result = format_analysis_for_display(analysis_result)
            
            if formatted_result['success']:
                # Cache analysis result
                vehicle_record.analysis_data = formatted_result['display_data']
                vehicle_record.analysis_completed = True
                vehicle_record.analysis_timestamp = datetime.utcnow()
                db.session.commit()
                logging.info(f"AI analysis cached for {registration}")
        
        # Format complete response with analysis
        response_data = format_complete_vehicle_response(vehicle_record)
        response_data['ai_analysis'] = vehicle_record.analysis_data
        response_data['analysis_available'] = True
        
        return jsonify({
            'success': True,
            'data': response_data,
            'timestamp': datetime.utcnow().isoformat(),
            'analysis_timestamp': vehicle_record.analysis_timestamp.isoformat() if vehicle_record.analysis_timestamp else None
        })
        
    except Exception as e:
        logging.error(f"External API analysis error for {registration}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}',
            'data': None
        }), 500


def is_data_expired(last_updated, hours=24):
    """Check if data is older than specified hours"""
    if not last_updated:
        return True
    
    time_diff = datetime.utcnow() - last_updated
    return time_diff.total_seconds() > (hours * 3600)


def save_vehicle_data_to_db(registration, vehicle_data):
    """Save scraped vehicle data to database"""
    try:
        # Check if record exists
        existing_record = VehicleData.query.filter_by(registration=registration).first()
        
        if existing_record:
            # Update existing record
            update_vehicle_record(existing_record, vehicle_data)
        else:
            # Create new record
            create_vehicle_record(registration, vehicle_data)
        
        db.session.commit()
        logging.info(f"Vehicle data saved to database for {registration}")
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Failed to save vehicle data for {registration}: {str(e)}")
        raise


def calculate_mot_fields(data):
    """Calculate MOT expiry date, days left, last mileage, and mileage issues from MOT history"""
    from datetime import datetime, date
    
    mot_expiry_date = None
    mot_days_left = None
    last_mot_mileage = None
    mileage_issues = "No"
    
    # Get MOT history
    mot_history = data.get('mot_history', {})
    mot_tests = mot_history.get('tests', []) or mot_history.get('mot_tests', [])
    
    if mot_tests:
        # Sort tests by date (newest first)
        sorted_tests = sorted(mot_tests, key=lambda x: x.get('test_date') or x.get('date', ''), reverse=True)
        
        # Find the most recent PASSED test for expiry date
        for test in sorted_tests:
            if 'pass' in (test.get('result', '').lower()):
                expiry = test.get('expiry_date') or test.get('expiry')
                if expiry and expiry.strip():
                    try:
                        # Parse expiry date and calculate days left
                        if '/' in expiry:
                            mot_expiry_date = datetime.strptime(expiry, '%d/%m/%Y').date()
                        elif '-' in expiry:
                            mot_expiry_date = datetime.strptime(expiry, '%Y-%m-%d').date()
                        
                        if mot_expiry_date:
                            today = date.today()
                            mot_days_left = (mot_expiry_date - today).days
                        break
                    except Exception as e:
                        continue
        
        # Get last MOT mileage from most recent test
        if sorted_tests:
            latest_test = sorted_tests[0]
            mileage = latest_test.get('mileage')
            if mileage:
                try:
                    # Extract numeric mileage
                    import re
                    mileage_match = re.search(r'(\d+)', str(mileage))
                    if mileage_match:
                        last_mot_mileage = int(mileage_match.group(1))
                except:
                    pass
        
        # Check for mileage issues (rollback detection)
        mileage_history = data.get('mileage_history', {})
        if mileage_history:
            analysis = mileage_history.get('analysis', {})
            odometer_issues = analysis.get('odometer_issues', {})
            if odometer_issues.get('has_issues', False):
                mileage_issues = "Yes"
    
    return mot_expiry_date, mot_days_left, last_mot_mileage, mileage_issues


def update_vehicle_record(record, data):
    """Update existing vehicle record with new data"""
    record.make = data.get('make', 'Unknown')
    record.model = data.get('model', 'Unknown')
    record.year = data.get('year')
    record.color = data.get('color')
    record.fuel_type = data.get('fuel_type')
    record.transmission = data.get('transmission')
    record.engine_size = data.get('engine_size')
    record.body_style = data.get('body_style')
    record.co2_emissions = data.get('co2_emissions')
    record.date_first_registered = data.get('date_first_registered')
    record.tax_status = data.get('tax_status')
    record.mot_status = data.get('mot_status')
    record.mot_expiry = data.get('mot_expiry')
    record.tax_6_months = data.get('tax_6_months')
    record.tax_12_months = data.get('tax_12_months')
    record.last_v5c_issue_date = data.get('last_v5c_issue_date')
    record.registration_place = data.get('registration_place')
    record.total_keepers = data.get('total_keepers')
    record.mot_history = data.get('mot_history', {})
    record.mileage_history = data.get('mileage_history', {})
    record.raw_data = data
    record.last_updated = datetime.utcnow()
    
    # Calculate and populate MOT fields
    mot_expiry_date, mot_days_left, last_mot_mileage, mileage_issues = calculate_mot_fields(data)
    record.mot_expiry_date = str(mot_expiry_date) if mot_expiry_date else None
    record.mot_days_left = mot_days_left
    record.last_mot_mileage = last_mot_mileage
    record.mileage_issues = mileage_issues


def create_vehicle_record(registration, data):
    """Create new vehicle record"""
    # Calculate MOT fields
    mot_expiry_date, mot_days_left, last_mot_mileage, mileage_issues = calculate_mot_fields(data)
    
    new_record = VehicleData()
    new_record.registration = registration
    new_record.make = data.get('make', 'Unknown')
    new_record.model = data.get('model', 'Unknown')
    new_record.year = data.get('year')
    new_record.color = data.get('color')
    new_record.fuel_type = data.get('fuel_type')
    new_record.transmission = data.get('transmission')
    new_record.engine_size = data.get('engine_size')
    new_record.body_style = data.get('body_style')
    new_record.co2_emissions = data.get('co2_emissions')
    new_record.date_first_registered = data.get('date_first_registered')
    new_record.tax_status = data.get('tax_status')
    new_record.mot_status = data.get('mot_status')
    new_record.mot_expiry = data.get('mot_expiry')
    new_record.tax_6_months = data.get('tax_6_months')
    new_record.tax_12_months = data.get('tax_12_months')
    new_record.last_v5c_issue_date = data.get('last_v5c_issue_date')
    new_record.registration_place = data.get('registration_place')
    new_record.total_keepers = data.get('total_keepers')
    new_record.mot_history = data.get('mot_history', {})
    new_record.mileage_history = data.get('mileage_history', {})
    new_record.raw_data = data
    new_record.last_updated = datetime.utcnow()
    # Populate the missing MOT fields
    new_record.mot_expiry_date = str(mot_expiry_date) if mot_expiry_date else None
    new_record.mot_days_left = mot_days_left
    new_record.last_mot_mileage = last_mot_mileage
    new_record.mileage_issues = mileage_issues
    db.session.add(new_record)


def prepare_data_for_analysis(vehicle_record):
    """Prepare vehicle record data for AI analysis"""
    raw_data = vehicle_record.raw_data or {}
    
    return {
        'registration': vehicle_record.registration,
        'make': vehicle_record.make,
        'model': vehicle_record.model,
        'year': vehicle_record.year,
        'color': vehicle_record.color,
        'fuel_type': vehicle_record.fuel_type,
        'engine_size': vehicle_record.engine_size,
        'co2_emissions': vehicle_record.co2_emissions,
        'date_first_registered': vehicle_record.date_first_registered,
        'tax_status': vehicle_record.tax_status,
        'mot_status': vehicle_record.mot_status,
        'mot_expiry': vehicle_record.mot_expiry,
        'tax_6_months': vehicle_record.tax_6_months,
        'tax_12_months': vehicle_record.tax_12_months,
        'last_v5_issue_date': vehicle_record.last_v5c_issue_date,
        'registration_place': vehicle_record.registration_place,
        'total_keepers': vehicle_record.total_keepers,
        'mot_history': vehicle_record.mot_history or {},
        'mileage_history': vehicle_record.mileage_history or {},
        'basic_info': raw_data.get('basic_info', {}),
        'vehicle_details': raw_data.get('vehicle_details', {}),
        'summary': raw_data.get('summary', {})
    }


def format_complete_vehicle_response(vehicle_record):
    """Format complete vehicle data response for external API"""
    
    # Count MOT tests
    mot_history = vehicle_record.mot_history or {}
    mot_tests = mot_history.get('tests', []) or mot_history.get('mot_tests', [])
    total_tests = len(mot_tests)
    
    # Count pass/fail rates
    passed_tests = sum(1 for test in mot_tests if 'pass' in test.get('result', '').lower())
    failed_tests = total_tests - passed_tests
    pass_rate = round((passed_tests / total_tests * 100)) if total_tests > 0 else 0
    
    # Count advisories
    total_advisories = 0
    for test in mot_tests:
        comments = test.get('comments', [])
        if isinstance(comments, list):
            total_advisories += sum(1 for comment in comments if 'advisory' in str(comment).lower())
    
    # Get latest mileage
    current_mileage = None
    if mot_tests:
        latest_test = mot_tests[0]
        current_mileage = latest_test.get('mileage')
    
    # Determine failure risk based on recent MOT performance
    failure_risk = "Low"
    if failed_tests > 0 and total_tests > 0:
        fail_rate = failed_tests / total_tests
        if fail_rate > 0.3:
            failure_risk = "High"
        elif fail_rate > 0.1:
            failure_risk = "Medium"
    
    return {
        'registration': vehicle_record.registration,
        'vehicle_info': {
            'make': vehicle_record.make,
            'model': vehicle_record.model,
            'year': vehicle_record.year,
            'color': vehicle_record.color,
            'fuel_type': vehicle_record.fuel_type,
            'transmission': vehicle_record.transmission,
            'engine_size': vehicle_record.engine_size,
            'body_style': vehicle_record.body_style,
            'co2_emissions': vehicle_record.co2_emissions
        },
        'ownership_info': {
            'total_keepers': vehicle_record.total_keepers,
            'last_v5c_issue_date': vehicle_record.last_v5c_issue_date,
            'registration_place': vehicle_record.registration_place,
            'date_first_registered': vehicle_record.date_first_registered
        },
        'tax_info': {
            'tax_status': vehicle_record.tax_status,
            'tax_6_months': vehicle_record.tax_6_months,
            'tax_12_months': vehicle_record.tax_12_months
        },
        'mot_summary': {
            'mot_status': vehicle_record.mot_status,
            'mot_expiry': vehicle_record.mot_expiry,
            'mot_expiry_date': vehicle_record.mot_expiry_date,
            'mot_days_left': vehicle_record.mot_days_left,
            'last_mot_mileage': vehicle_record.last_mot_mileage,
            'mileage_issues': vehicle_record.mileage_issues,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'pass_rate': pass_rate,
            'total_advisories': total_advisories,
            'failure_risk': failure_risk,
            'current_mileage': current_mileage
        },
        'complete_mot_history': mot_history,
        'mileage_history': vehicle_record.mileage_history or {},
        'raw_data': vehicle_record.raw_data or {},
        'last_updated': vehicle_record.last_updated.isoformat() if vehicle_record.last_updated else None
    }


@external_api.route('/api/external/health', methods=['GET'])
def health_check():
    """Health check endpoint for external API"""
    return jsonify({
        'status': 'healthy',
        'service': 'UK Vehicle Intelligence API',
        'version': '1.0',
        'timestamp': datetime.utcnow().isoformat()
    })


@external_api.route('/api/external/docs', methods=['GET'])
def api_documentation():
    """API documentation endpoint"""
    return jsonify({
        'api_name': 'UK Vehicle Intelligence API',
        'version': '1.0',
        'endpoints': {
            'GET /api/external/vehicle/<registration>': {
                'description': 'Get complete vehicle data by registration',
                'example': '/api/external/vehicle/K5WBR',
                'response': 'Complete vehicle information including MOT history'
            },
            'POST /api/external/vehicle/<registration>/analyze': {
                'description': 'Get vehicle data with AI analysis',
                'example': '/api/external/vehicle/K5WBR/analyze',
                'response': 'Vehicle data with comprehensive AI analysis'
            },
            'GET /api/external/health': {
                'description': 'Health check endpoint',
                'response': 'Service status and timestamp'
            }
        },
        'data_sources': [
            'DVLA official records',
            'MOT test history',
            'Vehicle registration data',
            'Tax and compliance information'
        ],
        'features': [
            'Complete vehicle information',
            'MOT test history with details',
            'Ownership tracking',
            'Tax cost calculations',
            'AI-powered risk analysis',
            'Mileage progression tracking',
            '24-hour intelligent caching'
        ]
    })