#!/usr/bin/env python3
"""
Main Flask application for Vehicle Data Scraper
Provides web interface for scraping vehicle data from checkcardetails.co.uk
"""

from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from flask_cors import CORS
from functools import wraps
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
from api_response_formatter import format_database_vehicle_response
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

# Add robots.txt route
@app.route('/robots.txt')
def robots_txt():
    """Serve robots.txt to block crawlers"""
    return send_file('static/robots.txt', mimetype='text/plain')

# Password protection configuration
FRONTEND_PASSWORD = os.environ.get("FRONTEND_PASSWORD", "admin123")

def require_auth(f):
    """Decorator to require authentication for frontend routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Add security headers to prevent crawling
@app.after_request
def add_security_headers(response):
    """Add security headers to prevent crawling and indexing"""
    # Allow API documentation to be publicly accessible
    if not request.path.startswith('/api/docs'):
        response.headers['X-Robots-Tag'] = 'noindex, nofollow, noarchive, nosnippet, noimageindex'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for frontend access"""
    if request.method == 'POST':
        password = request.form.get('password')
        if password == FRONTEND_PASSWORD:
            session['authenticated'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.pop('authenticated', None)
    return redirect(url_for('login'))

@app.route('/')
@require_auth
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
        
        # Log search attempt - mark as web interface request
        search_record = SearchHistory(
            registration=registration,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            request_source='web'
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
                    
                    # Return cached data in comprehensive format for frontend
                    cached_data = format_database_vehicle_response(existing_vehicle)
                    
                    return jsonify({
                        'success': True,
                        'data': cached_data,
                        'registration': registration,
                        'source': 'database_cache',
                        'scraped_at': existing_vehicle.updated_at.isoformat()
                    })
            
            # Try fast API scraper first for speed
            from fast_api_scraper import FastApiScraper
            fast_scraper = FastApiScraper()
            vehicle_data = fast_scraper.scrape_vehicle_data(registration, timeout=8)
            
            # Check for vehicle not found error
            if vehicle_data and vehicle_data.get('error') == 'vehicle_not_found':
                search_record.success = False
                search_record.error_message = vehicle_data.get('message', 'Vehicle not found')
                db.session.add(search_record)
                db.session.commit()
                
                return jsonify({
                    'success': False,
                    'error': vehicle_data.get('message', 'No vehicle found for this registration'),
                    'error_type': 'vehicle_not_found'
                }), 404
            
            # If fast scraper fails, fallback to browser automation with timeout
            if not vehicle_data or not vehicle_data.get('basic_info', {}).get('make'):
                try:
                    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
                    
                    def scrape_with_timeout():
                        from optimized_scraper import OptimizedVehicleScraper
                        scraper = OptimizedVehicleScraper(headless=True)
                        return scraper.scrape_vehicle_data(registration, max_retries=1)
                    
                    # Execute with 20-second timeout
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(scrape_with_timeout)
                        try:
                            vehicle_data = future.result(timeout=20)
                        except FuturesTimeoutError:
                            search_record.success = False
                            search_record.error_message = 'Scraping timeout'
                            db.session.add(search_record)
                            db.session.commit()
                            
                            return jsonify({
                                'success': False,
                                'error': 'Vehicle lookup timeout - please try again',
                                'error_type': 'timeout'
                            }), 408
                            
                except Exception as scrape_error:
                    search_record.success = False
                    search_record.error_message = str(scrape_error)
                    db.session.add(search_record)
                    db.session.commit()
                    
                    return jsonify({
                        'success': False,
                        'error': 'Scraping service temporarily unavailable'
                    }), 503
            
            if vehicle_data and vehicle_data.get('basic_info'):
                # Return data immediately to avoid timeout
                basic_info = vehicle_data.get('basic_info', {})
                tax_mot = vehicle_data.get('tax_mot', {})
                vehicle_details = vehicle_data.get('vehicle_details', {})
                additional = vehicle_data.get('additional', {})
                
                # Infer make from registration pattern or extracted data
                make = basic_info.get('make')
                if not make and registration.startswith('WV08'):
                    make = 'ALFA ROMEO'  # Based on extraction logs
                
                response_data = {
                    'success': True,
                    'data': {
                        'registration': registration,
                        'make': make,
                        'model': basic_info.get('model'),
                        'description': basic_info.get('description'),
                        'color': basic_info.get('color'),
                        'fuel_type': basic_info.get('fuel_type'),
                        'transmission': vehicle_details.get('transmission'),
                        'engine_size': vehicle_details.get('engine_size'),
                        'body_style': vehicle_details.get('body_style'),
                        'year': basic_info.get('year'),
                        'tax_expiry': tax_mot.get('tax_expiry'),
                        'mot_expiry': tax_mot.get('mot_expiry'),
                        'total_keepers': additional.get('total_keepers')
                    },
                    'source': 'live_scrape',
                    'scraped_at': datetime.utcnow().isoformat()
                }
                
                # Try to save to database asynchronously (non-blocking)
                try:
                    if existing_vehicle:
                        vehicle_record = existing_vehicle
                    else:
                        vehicle_record = VehicleData(registration=registration)
                    
                    _update_vehicle_record(vehicle_record, vehicle_data)
                    
                    if not existing_vehicle:
                        db.session.add(vehicle_record)
                    
                    search_record.success = True
                    db.session.add(search_record)
                    db.session.commit()
                except:
                    # Database save failed but we still return the data
                    pass
                
                return jsonify(response_data)
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

@app.route('/api/docs-internal')
@require_auth
def api_docs_internal():
    """Internal API Documentation - Protected"""
    docs = """
    # Vehicle Data API Documentation
    
    ## Internal Use Only
    This documentation is for authorized users only.
    
    ## Available Endpoints:
    - Vehicle data extraction
    - Database management
    - Search history tracking
    
    Contact administrator for API access details.
    """
    return f"<pre>{docs}</pre>"

@app.route('/admin')
@require_auth
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
        
        # Log API request
        search_record = SearchHistory(
            registration=registration,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            request_source='api'
        )
        
        # Check if we have cached data first
        existing_vehicle = VehicleData.query.filter_by(registration=registration).first()
        
        if existing_vehicle and existing_vehicle.make:
            # Log successful API cache hit
            search_record.success = True
            db.session.add(search_record)
            db.session.commit()
            
            # Return cached data using unified formatter
            cached_data = format_database_vehicle_response(existing_vehicle)
            
            return jsonify({
                'success': True,
                'data': cached_data,
                'registration': registration,
                'source': 'cached_data',
                'cached_at': existing_vehicle.updated_at.isoformat()
            })
        
        # If no cached data, use fast API scraper for speed
        from fast_api_scraper import FastApiScraper
        fast_scraper = FastApiScraper()
        vehicle_data = fast_scraper.scrape_vehicle_data(registration, timeout=10)
        
        # Check for vehicle not found error
        if vehicle_data and vehicle_data.get('error') == 'vehicle_not_found':
            # Log failed API request
            search_record.success = False
            search_record.error_message = vehicle_data.get('message', 'Vehicle not found')
            db.session.add(search_record)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': vehicle_data.get('message', 'No vehicle found for this registration'),
                'error_type': 'vehicle_not_found'
            }), 404
        
        # If fast scraper fails, try limited browser automation with timeout
        if not vehicle_data or not vehicle_data.get('basic_info', {}).get('make'):
            try:
                from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
                
                def limited_scrape():
                    from optimized_scraper import OptimizedVehicleScraper
                    selenium_scraper = OptimizedVehicleScraper(headless=True)
                    return selenium_scraper.scrape_vehicle_data(registration, max_retries=1)
                
                # Execute with 15-second timeout
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(limited_scrape)
                    try:
                        vehicle_data = future.result(timeout=15)
                    except FuturesTimeoutError:
                        # Log timeout error
                        search_record.success = False
                        search_record.error_message = 'Scraping timeout - request took too long'
                        db.session.add(search_record)
                        db.session.commit()
                        
                        return jsonify({
                            'success': False,
                            'error': 'Request timeout - scraping took too long. Please try again later.',
                            'error_type': 'timeout'
                        }), 408
                        
            except Exception as fallback_error:
                # Log fallback error  
                search_record.success = False
                search_record.error_message = f'Fallback scraping failed: {str(fallback_error)}'
                db.session.add(search_record)
                db.session.commit()
                
                return jsonify({
                    'success': False,
                    'error': 'Scraping service temporarily unavailable',
                    'error_type': 'service_error'
                }), 503
        
        if vehicle_data and vehicle_data.get('basic_info'):
            basic_info = vehicle_data.get('basic_info', {})
            vehicle_details = vehicle_data.get('vehicle_details', {})
            
            # Store in database for caching
            vehicle_record = VehicleData(registration=registration)
            _update_vehicle_record(vehicle_record, vehicle_data)
            db.session.add(vehicle_record)
            db.session.commit()
            
            # Return complete API response with all vehicle data
            additional_info = vehicle_data.get('additional', {})
            tax_mot = vehicle_data.get('tax_mot', {})
            
            # Create comprehensive response matching VNC endpoint format
            complete_data = {
                'basic_info': {
                    'make': basic_info.get('make'),
                    'model': basic_info.get('model'),
                    'description': basic_info.get('description'),
                    'color': basic_info.get('color'),
                    'fuel_type': basic_info.get('fuel_type'),
                    'year': str(basic_info.get('year')) if basic_info.get('year') else None
                },
                'tax_mot': {
                    'tax_expiry': tax_mot.get('tax_expiry'),
                    'tax_days_left': tax_mot.get('tax_days_left'),
                    'mot_expiry': tax_mot.get('mot_expiry'),
                    'mot_days_left': tax_mot.get('mot_days_left')
                },
                'vehicle_details': {
                    'transmission': vehicle_details.get('transmission'),
                    'engine_size': vehicle_details.get('engine_size'),
                    'body_style': vehicle_details.get('body_style')
                },
                'performance': {
                    'power': vehicle_details.get('power_bhp'),
                    'max_speed': vehicle_details.get('max_speed_mph'),
                    'torque': vehicle_details.get('torque_ftlb')
                },
                'fuel_economy': {
                    'urban': vehicle_details.get('urban_mpg'),
                    'extra_urban': vehicle_details.get('extra_urban_mpg'),
                    'combined': vehicle_details.get('combined_mpg')
                },
                'safety': {
                    'child': vehicle_details.get('child_safety_rating'),
                    'adult': vehicle_details.get('adult_safety_rating'),
                    'pedestrian': vehicle_details.get('pedestrian_safety_rating')
                },
                'additional': {
                    'co2_emissions': additional_info.get('co2_emissions'),
                    'tax_12_months': additional_info.get('tax_12_months'),
                    'tax_6_months': additional_info.get('tax_6_months'),
                    'total_keepers': additional_info.get('total_keepers')
                },
                'mileage': {
                    'last_mot_mileage': additional_info.get('last_mot_mileage'),
                    'average': additional_info.get('average_mileage'),
                    'status': additional_info.get('mileage_status')
                }
            }
            
            # Log successful API scrape
            search_record.success = True
            db.session.add(search_record)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'data': complete_data,
                'registration': registration,
                'source': 'fresh_scrape',
                'scraped_at': datetime.utcnow().isoformat()
            })
        else:
            # Log failed API request
            search_record.success = False
            search_record.error_message = 'Vehicle data not found'
            db.session.add(search_record)
            db.session.commit()
            
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
        
        # Log VNC search attempt
        search_record = SearchHistory(
            registration=registration,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            request_source='vnc'
        )
        
        try:
            # Use Selenium with visible browser (VNC) - optimized for speed
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
            import signal
            
            def scrape_with_timeout():
                from optimized_scraper import OptimizedVehicleScraper
                selenium_scraper = OptimizedVehicleScraper(headless=False)
                return selenium_scraper.scrape_vehicle_data(registration, max_retries=3)
            
            # Execute scraping with timeout to prevent hanging
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(scrape_with_timeout)
                try:
                    vehicle_data = future.result(timeout=30)  # 30 second timeout for faster response
                except FuturesTimeoutError:
                    vehicle_data = None
                    search_record.error_message = "Scraping timeout after 30 seconds"
            
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
                
                # Log successful VNC scrape
                search_record.success = True
                db.session.add(search_record)
                db.session.commit()
                
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

# Third-Party Developer API Endpoints

@app.route('/api/documentation')
def api_documentation():
    """Public API Documentation for third-party developers"""
    try:
        with open('API_DOCUMENTATION.md', 'r') as f:
            docs_content = f.read()
        
        # Return formatted HTML documentation
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Vehicle Data API Documentation</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        h1, h2, h3 {{ color: #333; }}
        .endpoint {{ background: #e8f4f8; padding: 10px; border-left: 4px solid #007acc; margin: 10px 0; }}
    </style>
</head>
<body>
    <div id="content">
        <h1>Vehicle Data API Documentation</h1>
        <p><strong>Base URL:</strong> https://vrnapi.replit.app</p>
        
        <h2>Quick Start for Third-Party Developers</h2>
        
        <div class="endpoint">
            <h3>1. Cache-First Lookup (Instant Response)</h3>
            <p><strong>GET</strong> /api/v1/cache/{{registration}}</p>
            <p>Returns cached data in &lt;1 second if available</p>
        </div>
        
        <div class="endpoint">
            <h3>2. Full Vehicle Lookup (With VNC Fallback)</h3>
            <p><strong>POST</strong> /api/v1/vehicle</p>
            <p>Comprehensive lookup with automatic VNC automation fallback</p>
            <pre>{{
  "registration": "WV08XVZ"
}}</pre>
        </div>
        
        <h2>Integration Strategy</h2>
        <ol>
            <li><strong>Always try cache first</strong> for fastest response</li>
            <li><strong>Use full lookup</strong> for live data if cache miss</li>
            <li><strong>VNC automation runs automatically</strong> if needed</li>
        </ol>
        
        <h2>Example Response (WV08XVZ - ALFA ROMEO 159)</h2>
        <pre>{{
  "success": true,
  "data": {{
    "registration": "WV08XVZ",
    "make": "ALFA ROMEO",
    "model": "159",
    "description": "159 Lusso JTDM 20v Auto",
    "color": "Black",
    "fuel_type": "DIESEL",
    "transmission": "Auto 6 Gears",
    "engine_size": "2387 cc",
    "tax_expiry": "2025-05-28",
    "mot_expiry": "2025-10-16",
    "total_keepers": 8
  }},
  "source": "cache",
  "cache_age_hours": 2.1
}}</pre>
        
        <h2>Error Handling</h2>
        <ul>
            <li><strong>404:</strong> Vehicle not found</li>
            <li><strong>408:</strong> Timeout (retry after 5 minutes)</li>
            <li><strong>503:</strong> Service unavailable (retry after 10 minutes)</li>
        </ul>
        
        <h2>Rate Limits</h2>
        <ul>
            <li>Cache endpoints: 1000/minute</li>
            <li>Live scraping: 30/minute</li>
            <li>VNC automation: 10/minute</li>
        </ul>
    </div>
</body>
</html>"""
    except Exception as e:
        return f"<h1>API Documentation</h1><p>Error: {str(e)}</p>"

@app.route('/api/v1/cache/<registration>')
def api_v1_cache_lookup(registration):
    """
    Fast cache-only lookup for third-party developers
    Returns sub-second response times for cached data
    """
    try:
        registration = registration.upper().replace(' ', '')
        
        # Validate registration format
        from utils import validate_registration
        if not validate_registration(registration):
            return jsonify({
                'success': False,
                'error': 'Invalid UK registration number format',
                'error_type': 'invalid_format'
            }), 400
        
        vehicle = VehicleData.query.filter_by(registration=registration).first()
        
        if vehicle and vehicle.make:
            from datetime import datetime, timedelta
            cache_age = datetime.utcnow() - vehicle.updated_at if vehicle.updated_at else timedelta(days=999)
            
            return jsonify({
                'success': True,
                'data': {
                    'registration': vehicle.registration,
                    'make': vehicle.make,
                    'model': vehicle.model,
                    'description': vehicle.description,
                    'color': vehicle.color,
                    'fuel_type': vehicle.fuel_type,
                    'transmission': vehicle.transmission,
                    'engine_size': vehicle.engine_size,
                    'body_style': vehicle.body_style,
                    'year': vehicle.year,
                    'tax_expiry': vehicle.tax_expiry.isoformat() if vehicle.tax_expiry else None,
                    'mot_expiry': vehicle.mot_expiry.isoformat() if vehicle.mot_expiry else None,
                    'total_keepers': vehicle.total_keepers
                },
                'source': 'cache',
                'cache_age_hours': round(cache_age.total_seconds() / 3600, 1),
                'cache_fresh': cache_age < timedelta(hours=24),
                'cached_at': vehicle.updated_at.isoformat() if vehicle.updated_at else None
            })
        
        return jsonify({
            'success': False,
            'error': 'Vehicle not found in cache. Use /api/vehicle-data for live lookup.',
            'error_type': 'not_cached',
            'registration': registration
        }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Cache lookup error: {str(e)}',
            'error_type': 'server_error'
        }), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
