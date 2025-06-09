#!/usr/bin/env python3
"""
Main Flask application for Vehicle Data Scraper
Provides web interface for scraping vehicle data from checkcardetails.co.uk
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import json
import csv
import io
import os
from datetime import datetime
from enhanced_scraper import EnhancedVehicleScraper
from selenium_scraper import SeleniumVehicleScraper
from test_data_service import get_sample_vehicle_data
from utils import validate_registration, sanitize_filename
from models import db, VehicleData, SearchHistory
from sqlalchemy.orm import DeclarativeBase
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"

# Enable CORS for API access
CORS(app)

# Database configuration
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    """Main page with vehicle lookup form"""
    return render_template('index.html')

@app.route('/api/scrape', methods=['POST'])
def scrape_vehicle():
    """API endpoint to scrape vehicle data"""
    try:
        data = request.get_json()
        registration = data.get('registration', '').strip().upper()
        
        # Validate registration number
        if not validate_registration(registration):
            return jsonify({
                'success': False,
                'error': 'Invalid registration number format'
            }), 400
        
        # Log search attempt
        search_record = SearchHistory(
            registration=registration,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        
        try:
            # Check if we already have this vehicle in database
            existing_vehicle = VehicleData.query.filter_by(registration=registration).first()
            
            if existing_vehicle and existing_vehicle.updated_at:
                # Return cached data if it's recent (less than 24 hours old)
                time_diff = datetime.utcnow() - existing_vehicle.updated_at
                if time_diff.total_seconds() < 86400:  # 24 hours
                    search_record.success = True
                    db.session.add(search_record)
                    db.session.commit()
                    
                    return jsonify({
                        'success': True,
                        'data': existing_vehicle.to_dict(),
                        'registration': registration,
                        'source': 'database_cache',
                        'scraped_at': existing_vehicle.updated_at.isoformat()
                    })
            
            # Try enhanced scraper first (direct HTTP)
            scraper = EnhancedVehicleScraper()
            vehicle_data = scraper.scrape_vehicle_data(registration)
            
            # If HTTP scraping fails due to 403 blocking, inform user about browser automation option
            if not vehicle_data:
                search_record.success = False
                search_record.error_message = 'Website blocking detected - requires browser automation'
                db.session.add(search_record)
                db.session.commit()
                
                return jsonify({
                    'success': False,
                    'error': 'The website is blocking automated requests. Please use the "VNC Browser Search" button below for interactive scraping, or contact the website administrator for API access.',
                    'suggestion': 'vnc_required'
                }), 403
            
            if vehicle_data:
                # Store or update vehicle data in database
                if existing_vehicle:
                    # Update existing record
                    vehicle_record = existing_vehicle
                else:
                    # Create new record
                    vehicle_record = VehicleData(registration=registration)
                
                # Map scraped data to database fields
                _update_vehicle_record(vehicle_record, vehicle_data)
                
                if not existing_vehicle:
                    db.session.add(vehicle_record)
                
                search_record.success = True
                db.session.add(search_record)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'data': vehicle_record.to_dict(),
                    'registration': registration,
                    'source': 'live_scrape',
                    'scraped_at': datetime.utcnow().isoformat()
                })
            else:
                search_record.success = False
                search_record.error_message = 'No vehicle data found'
                db.session.add(search_record)
                db.session.commit()
                
                return jsonify({
                    'success': False,
                    'error': 'No vehicle data found for this registration'
                }), 404
                
        except Exception as scrape_error:
            search_record.success = False
            search_record.error_message = str(scrape_error)
            db.session.add(search_record)
            db.session.commit()
            raise scrape_error
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Scraping failed: {str(e)}'
        }), 500

@app.route('/api/export/<format_type>/<registration>')
def export_data(format_type, registration):
    """Export vehicle data in JSON or CSV format"""
    try:
        # Re-scrape data for export (in production, you might want to cache this)
        scraper = EnhancedVehicleScraper()
        vehicle_data = scraper.scrape_vehicle_data(registration.upper())
        
        if not vehicle_data:
            return jsonify({'error': 'No data found for this registration'}), 404
        
        filename = sanitize_filename(f"{registration}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        if format_type.lower() == 'json':
            # Export as JSON
            json_data = json.dumps(vehicle_data, indent=2, ensure_ascii=False)
            buffer = io.BytesIO()
            buffer.write(json_data.encode('utf-8'))
            buffer.seek(0)
            
            return send_file(
                buffer,
                as_attachment=True,
                download_name=f"{filename}.json",
                mimetype='application/json'
            )
            
        elif format_type.lower() == 'csv':
            # Export as CSV (flatten nested data)
            flattened_data = flatten_dict(vehicle_data)
            
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            
            # Write headers and data
            writer.writerow(['Field', 'Value'])
            for key, value in flattened_data.items():
                writer.writerow([key, value])
            
            output = buffer.getvalue()
            buffer = io.BytesIO()
            buffer.write(output.encode('utf-8'))
            buffer.seek(0)
            
            return send_file(
                buffer,
                as_attachment=True,
                download_name=f"{filename}.csv",
                mimetype='text/csv'
            )
        else:
            return jsonify({'error': 'Invalid format. Use json or csv'}), 400
            
    except Exception as e:
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

def flatten_dict(d, parent_key='', sep='_'):
    """Flatten nested dictionary for CSV export"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    items.extend(flatten_dict(item, f"{new_key}_{i}", sep=sep).items())
                else:
                    items.append((f"{new_key}_{i}", item))
        else:
            items.append((new_key, v))
    return dict(items)

def _update_vehicle_record(vehicle_record, vehicle_data):
    """Update vehicle record with scraped data"""
    from datetime import datetime
    import re
    
    # Extract basic info from the correct structure
    basic_info = vehicle_data.get('basic_info', {})
    vehicle_details = vehicle_data.get('vehicle_details', {})
    tax_mot = vehicle_data.get('tax_mot', {})
    
    # Map basic vehicle information
    vehicle_record.make = basic_info.get('make')
    vehicle_record.model = basic_info.get('model')
    vehicle_record.description = basic_info.get('description')
    vehicle_record.color = basic_info.get('color')
    vehicle_record.fuel_type = basic_info.get('fuel_type')
    if basic_info.get('year'):
        try:
            vehicle_record.year = int(basic_info['year'])
        except (ValueError, TypeError):
            pass
    
    # Map vehicle details
    vehicle_record.transmission = vehicle_details.get('transmission')
    vehicle_record.engine_size = vehicle_details.get('engine_size')
    
    # Map TAX/MOT information
    if tax_mot.get('tax_expiry'):
        try:
            from datetime import datetime
            tax_date = datetime.strptime(tax_mot['tax_expiry'], '%d %b %Y').date()
            vehicle_record.tax_expiry = tax_date
        except:
            pass
    
    if tax_mot.get('tax_days_left'):
        vehicle_record.tax_days_left = tax_mot['tax_days_left']
        
    if tax_mot.get('mot_expiry'):
        try:
            from datetime import datetime
            mot_date = datetime.strptime(tax_mot['mot_expiry'], '%d %b %Y').date()
            vehicle_record.mot_expiry = mot_date
        except:
            pass
    
    if tax_mot.get('mot_days_left'):
        vehicle_record.mot_days_left = tax_mot['mot_days_left']
    
    # Store raw data for debugging
    vehicle_record.raw_data = vehicle_data
    
    # Extract mileage info
    mileage = vehicle_data.get('mileage', {})
    if mileage.get('last_mot_mileage'):
        try:
            mileage_str = str(mileage['last_mot_mileage']).replace(',', '')
            vehicle_record.last_mot_mileage = int(re.sub(r'[^\d]', '', mileage_str))
        except (ValueError, TypeError):
            pass
    
    if mileage.get('average'):
        try:
            avg_str = str(mileage['average']).replace(',', '')
            vehicle_record.average_mileage = int(re.sub(r'[^\d]', '', avg_str))
        except (ValueError, TypeError):
            pass
    
    vehicle_record.mileage_issues = mileage.get('mileage_issues')
    vehicle_record.mileage_status = mileage.get('status')
    
    # Extract performance data
    performance = vehicle_data.get('performance', {})
    vehicle_record.power_bhp = performance.get('power')
    vehicle_record.max_speed_mph = performance.get('max_speed')
    vehicle_record.torque_ftlb = performance.get('torque')
    
    # Extract fuel economy
    fuel_economy = vehicle_data.get('fuel_economy', {})
    vehicle_record.urban_mpg = fuel_economy.get('urban')
    vehicle_record.extra_urban_mpg = fuel_economy.get('extra_urban')
    vehicle_record.combined_mpg = fuel_economy.get('combined')
    
    # Extract safety ratings
    safety = vehicle_data.get('safety', {})
    vehicle_record.child_safety_rating = safety.get('child')
    vehicle_record.adult_safety_rating = safety.get('adult')
    vehicle_record.pedestrian_safety_rating = safety.get('pedestrian')
    
    # Extract additional info
    additional = vehicle_data.get('additional', {})
    vehicle_record.co2_emissions = additional.get('co2_emissions')
    vehicle_record.tax_12_months = additional.get('tax_12_months')
    vehicle_record.tax_6_months = additional.get('tax_6_months')
    
    if additional.get('total_keepers'):
        try:
            vehicle_record.total_keepers = int(additional['total_keepers'])
        except (ValueError, TypeError):
            pass
    
    if additional.get('v5c_certificate_count'):
        try:
            vehicle_record.v5c_certificate_count = int(additional['v5c_certificate_count'])
        except (ValueError, TypeError):
            pass
    
    # Store raw data for reference
    vehicle_record.raw_data = vehicle_data
    vehicle_record.updated_at = datetime.utcnow()

# Add database routes
@app.route('/api/history')
def get_search_history():
    """Get recent search history"""
    try:
        searches = SearchHistory.query.order_by(SearchHistory.search_timestamp.desc()).limit(50).all()
        return jsonify({
            'success': True,
            'searches': [{
                'registration': search.registration,
                'timestamp': search.search_timestamp.isoformat(),
                'success': search.success,
                'error': search.error_message
            } for search in searches]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/vehicles')
def get_vehicles():
    """Get all vehicles in database"""
    try:
        vehicles = VehicleData.query.order_by(VehicleData.updated_at.desc()).limit(100).all()
        return jsonify({
            'success': True,
            'vehicles': [vehicle.to_dict() for vehicle in vehicles]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/vehicle/<registration>')
def get_vehicle(registration):
    """Get specific vehicle data from database"""
    try:
        vehicle = VehicleData.query.filter_by(registration=registration.upper()).first()
        if vehicle:
            return jsonify({
                'success': True,
                'vehicle': vehicle.to_dict()
            })
        else:
            return jsonify({'success': False, 'error': 'Vehicle not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/docs')
def api_docs():
    """API Documentation"""
    docs = """
    # Vehicle Data API Documentation
    
    ## Endpoint: /api/vehicle-data
    **Methods:** GET, POST
    
    ### Request Examples:
    
    **GET Request:**
    ```
    GET /api/vehicle-data?registration=RE13CEO
    ```
    
    **POST Request:**
    ```json
    {
        "registration": "RE13CEO"
    }
    ```
    
    ### Response Format:
    ```json
    {
        "success": true,
        "registration": "RE13CEO",
        "make": "FERRARI F12BERLINETTA AB S-A",
        "model": "F12berlinetta Ab S-a",
        "description": "F12 Berlinetta AB Semi-Auto",
        "year": 2013,
        "color": "Black",
        "fuel_type": "PETROL",
        "transmission": "Auto 7 Gears",
        "engine_size": "6262 cc",
        "source": "fresh_scrape"
    }
    ```
    
    ### Error Response:
    ```json
    {
        "success": false,
        "error": "Invalid registration number format"
    }
    ```
    """
    return f"<pre>{docs}</pre>"

@app.route('/admin')
def admin():
    """Database administration page"""
    return render_template('admin.html')

@app.route('/api/add-test-data', methods=['POST'])
def add_test_data():
    """Add test data to demonstrate database functionality"""
    try:
        data = request.get_json()
        registration = data.get('registration', '').strip().upper()
        
        if not registration:
            return jsonify({'success': False, 'error': 'Registration required'}), 400
        
        # Get sample data
        vehicle_data = get_sample_vehicle_data(registration)
        
        # Check if vehicle already exists
        existing_vehicle = VehicleData.query.filter_by(registration=registration).first()
        
        if existing_vehicle:
            # Update existing record
            vehicle_record = existing_vehicle
        else:
            # Create new record
            vehicle_record = VehicleData()
            vehicle_record.registration = registration
        
        # Map data to database fields
        _update_vehicle_record(vehicle_record, vehicle_data)
        
        if not existing_vehicle:
            db.session.add(vehicle_record)
        
        # Add search history record
        search_record = SearchHistory()
        search_record.registration = registration
        search_record.ip_address = request.remote_addr
        search_record.user_agent = request.headers.get('User-Agent', '')
        search_record.success = True
        
        db.session.add(search_record)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Test data added for {registration}',
            'vehicle': vehicle_record.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/demo-data/<registration>')
def get_demo_data(registration):
    """Get demonstration data for a registration number"""
    try:
        registration = registration.strip().upper()
        
        if not validate_registration(registration):
            return jsonify({
                'success': False,
                'error': 'Invalid registration number format'
            }), 400
        
        # Generate demonstration data
        demo_data = get_sample_vehicle_data(registration)
        
        return jsonify({
            'success': True,
            'data': demo_data,
            'registration': registration,
            'source': 'demonstration_data',
            'note': 'This is demonstration data showing the expected structure. Real scraping requires browser automation due to website restrictions.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/vehicle-data', methods=['POST', 'GET'])
def get_vehicle_data_api():
    """Simple API endpoint for external calls - returns basic vehicle data"""
    try:
        # Handle both GET and POST requests
        if request.method == 'GET':
            registration = request.args.get('registration', '').strip().upper()
        else:
            data = request.get_json()
            registration = data.get('registration', '').strip().upper() if data else ''
        
        if not validate_registration(registration):
            return jsonify({
                'success': False,
                'error': 'Invalid registration number format'
            }), 400
        
        # Check if we have cached data first
        existing_vehicle = VehicleData.query.filter_by(registration=registration).first()
        
        if existing_vehicle and existing_vehicle.make:
            # Return cached data in simple format
            return jsonify({
                'success': True,
                'registration': registration,
                'make': existing_vehicle.make,
                'model': existing_vehicle.model,
                'description': existing_vehicle.description,
                'year': existing_vehicle.year,
                'color': existing_vehicle.color,
                'fuel_type': existing_vehicle.fuel_type,
                'transmission': existing_vehicle.transmission,
                'engine_size': existing_vehicle.engine_size,
                'total_keepers': existing_vehicle.total_keepers,
                'source': 'cached_data'
            })
        
        # If no cached data, scrape fresh
        selenium_scraper = SeleniumVehicleScraper(headless=True)  # Headless for API
        vehicle_data = selenium_scraper.scrape_vehicle_data(registration)
        
        if vehicle_data and vehicle_data.get('basic_info'):
            basic_info = vehicle_data.get('basic_info', {})
            vehicle_details = vehicle_data.get('vehicle_details', {})
            
            # Store in database for caching
            vehicle_record = VehicleData()
            vehicle_record.registration = registration
            _update_vehicle_record(vehicle_record, vehicle_data)
            db.session.add(vehicle_record)
            db.session.commit()
            
            # Return simple API response
            additional_info = vehicle_data.get('additional', {})
            return jsonify({
                'success': True,
                'registration': registration,
                'make': basic_info.get('make'),
                'model': basic_info.get('model'),
                'description': basic_info.get('description'),
                'year': basic_info.get('year'),
                'color': basic_info.get('color'),
                'fuel_type': basic_info.get('fuel_type'),
                'transmission': vehicle_details.get('transmission'),
                'engine_size': vehicle_details.get('engine_size'),
                'total_keepers': additional_info.get('total_keepers'),
                'source': 'fresh_scrape'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Vehicle data not found or scraping failed'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'API error: {str(e)}'
        }), 500

@app.route('/api/scrape-vnc', methods=['POST'])
def scrape_vehicle_vnc():
    """VNC-based scraping endpoint for interactive browser automation"""
    try:
        data = request.get_json()
        registration = data.get('registration', '').strip().upper()
        
        if not validate_registration(registration):
            return jsonify({
                'success': False,
                'error': 'Invalid registration number format'
            }), 400
        
        # Log search attempt
        search_record = SearchHistory()
        search_record.registration = registration
        search_record.ip_address = request.remote_addr
        search_record.user_agent = request.headers.get('User-Agent', '')
        
        try:
            # Use Selenium with visible browser (VNC)
            selenium_scraper = SeleniumVehicleScraper(headless=False)
            vehicle_data = selenium_scraper.scrape_vehicle_data(registration)
            
            if vehicle_data:
                # Check if vehicle already exists
                existing_vehicle = VehicleData.query.filter_by(registration=registration).first()
                
                if existing_vehicle:
                    vehicle_record = existing_vehicle
                else:
                    vehicle_record = VehicleData()
                    vehicle_record.registration = registration
                
                # Map data to database fields
                _update_vehicle_record(vehicle_record, vehicle_data)
                
                if not existing_vehicle:
                    db.session.add(vehicle_record)
                
                search_record.success = True
                db.session.add(search_record)
                db.session.commit()
                
                # Convert database model back to frontend-expected format
                frontend_data = {
                    'basic_info': {
                        'make': vehicle_record.make,
                        'model': vehicle_record.model,
                        'description': vehicle_record.description,
                        'color': vehicle_record.color,
                        'fuel_type': vehicle_record.fuel_type,
                        'year': str(vehicle_record.year) if vehicle_record.year else None
                    },
                    'tax_mot': {
                        'tax_expiry': vehicle_record.tax_expiry.strftime('%d %b %Y') if vehicle_record.tax_expiry else None,
                        'tax_days_left': vehicle_record.tax_days_left,
                        'mot_expiry': vehicle_record.mot_expiry.strftime('%d %b %Y') if vehicle_record.mot_expiry else None,
                        'mot_days_left': vehicle_record.mot_days_left
                    },
                    'vehicle_details': {
                        'transmission': vehicle_record.transmission,
                        'engine_size': vehicle_record.engine_size,
                        'body_style': vehicle_record.body_style
                    },
                    'performance': {
                        'power': vehicle_record.power_bhp,
                        'max_speed': vehicle_record.max_speed_mph,
                        'torque': vehicle_record.torque_ftlb
                    },
                    'fuel_economy': {
                        'urban': vehicle_record.urban_mpg,
                        'extra_urban': vehicle_record.extra_urban_mpg,
                        'combined': vehicle_record.combined_mpg
                    },
                    'safety': {
                        'child': vehicle_record.child_safety_rating,
                        'adult': vehicle_record.adult_safety_rating,
                        'pedestrian': vehicle_record.pedestrian_safety_rating
                    },
                    'additional': {
                        'co2_emissions': vehicle_record.co2_emissions,
                        'tax_12_months': vehicle_record.tax_12_months,
                        'tax_6_months': vehicle_record.tax_6_months
                    },
                    'mileage': {
                        'last_mot_mileage': vehicle_record.last_mot_mileage,
                        'average': vehicle_record.average_mileage,
                        'status': vehicle_record.mileage_status
                    }
                }
                
                return jsonify({
                    'success': True,
                    'data': frontend_data,
                    'registration': registration,
                    'source': 'vnc_scrape',
                    'scraped_at': datetime.utcnow().isoformat()
                })
            else:
                search_record.success = False
                search_record.error_message = 'VNC scraping failed - no data extracted'
                db.session.add(search_record)
                db.session.commit()
                
                return jsonify({
                    'success': False,
                    'error': 'VNC scraping failed to extract vehicle data'
                }), 404
                
        except Exception as scrape_error:
            search_record.success = False
            search_record.error_message = str(scrape_error)
            db.session.add(search_record)
            db.session.commit()
            raise scrape_error
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'VNC scraping failed: {str(e)}'
        }), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
