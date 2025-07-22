"""
Main routes for the Vehicle Data Scraper application
"""

from flask import render_template, request, jsonify, send_file, session, redirect, url_for
from functools import wraps
import json
import csv
import io
import os
from datetime import datetime, timedelta
from app import app, db
from models import VehicleData, SearchHistory
from utils import validate_registration, sanitize_filename
from api_response_formatter import format_database_vehicle_response
import logging

logger = logging.getLogger(__name__)

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

# Add robots.txt route
@app.route('/robots.txt')
def robots_txt():
    """Serve robots.txt to block crawlers"""
    return "User-agent: *\nDisallow: /", 200, {'Content-Type': 'text/plain'}

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
        search_record = SearchHistory()
        search_record.registration = registration
        search_record.ip_address = request.remote_addr
        search_record.user_agent = request.headers.get('User-Agent', '')
        search_record.request_source = 'web'
        
        try:
            # Check if we already have this vehicle in database
            existing_vehicle = VehicleData.query.filter_by(registration=registration).first()
            
            if existing_vehicle and existing_vehicle.updated_at:
                # Check if data is less than 24 hours old
                time_diff = datetime.utcnow() - existing_vehicle.updated_at
                if time_diff < timedelta(hours=24):
                    search_record.success = True
                    search_record.error_message = 'Data served from cache'
                    db.session.add(search_record)
                    db.session.commit()
                    
                    # Format response using consistent API formatter
                    response_data = format_database_vehicle_response(existing_vehicle)
                    # Ensure response_data is a dictionary before adding fields
                    if not isinstance(response_data, dict):
                        response_data = {}
                    
                    # Add cache information - create new dict to avoid type issues
                    cache_info = {
                        'cached': True,
                        'cache_age_hours': round(time_diff.total_seconds() / 3600, 2)
                    }
                    response_data = {**response_data, **cache_info}
                    
                    return jsonify(response_data)
            
            # Always use enhanced scraper for comprehensive data extraction
            try:
                from enhanced_selenium_scraper import EnhancedSeleniumScraper
                
                logger.info(f"Starting enhanced scrape for registration: {registration}")
                scraper = EnhancedSeleniumScraper(headless=True)
                basic_data = scraper.scrape_complete_vehicle_data(registration)
                
                if basic_data:
                    
                    # Create new vehicle record
                    vehicle_record = VehicleData()
                    vehicle_record.registration = registration
                    
                    # Extract data from enhanced scraper format
                    basic_info = basic_data.get('basic_info', {})
                    vehicle_details = basic_data.get('vehicle_details', {})
                    
                    # Update with scraped data
                    vehicle_record.make = (basic_info.get('make') or basic_data.get('make') or 'Unknown')[:50]
                    vehicle_record.model = (basic_info.get('model') or basic_data.get('model') or 'Unknown')[:50]
                    vehicle_record.description = (basic_info.get('description') or basic_data.get('description') or 'Unknown')[:200]
                    vehicle_record.color = (basic_info.get('color') or basic_data.get('color') or 'Unknown')[:50]
                    vehicle_record.fuel_type = (basic_info.get('fuel_type') or basic_data.get('fuel_type') or 'Unknown')[:50]
                    
                    # Handle year conversion
                    year_value = basic_info.get('year') or basic_data.get('year')
                    if year_value:
                        try:
                            vehicle_record.year = int(year_value)
                        except (ValueError, TypeError):
                            vehicle_record.year = None
                    
                    # Store raw data for future reference
                    vehicle_record.raw_data = basic_data
                    
                    # Store in database
                    db.session.add(vehicle_record)
                    search_record.success = True
                    db.session.add(search_record)
                    db.session.commit()
                    
                    logger.info(f"Successfully scraped and stored data for {registration}")
                    
                    return jsonify({
                        'success': True,
                        'data': {
                            'registration': registration,
                            'make': vehicle_record.make,
                            'model': vehicle_record.model,
                            'description': vehicle_record.description,
                            'color': vehicle_record.color,
                            'fuel_type': vehicle_record.fuel_type,
                            'year': vehicle_record.year,
                            'mot_history': basic_data.get('mot_history'),
                            'mileage_history': basic_data.get('mileage_history')
                        },
                        'source': 'fresh_scrape',
                        'method': 'enhanced_selenium_only'
                    })
                
                else:
                    search_record.success = False
                    search_record.error_message = 'No vehicle data found'
                    db.session.add(search_record)
                    db.session.commit()
                    
                    return jsonify({
                        'success': False,
                        'error': 'Vehicle not found or data could not be extracted',
                        'registration': registration
                    }), 404
                    
            except Exception as scrape_error:
                logger.error(f"Scraping failed for {registration}: {scrape_error}")
                search_record.success = False
                search_record.error_message = f'Scraping error: {str(scrape_error)}'
                db.session.add(search_record)
                db.session.commit()
                
                return jsonify({
                    'success': False,
                    'error': 'Scraping failed. Please try again later.',
                    'registration': registration
                }), 500
            
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            search_record.success = False
            search_record.error_message = f'Database error: {str(e)}'
            db.session.add(search_record)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': 'Database error occurred'
            }), 500
            
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/vehicles')
def get_vehicles():
    """Get all vehicles in database"""
    try:
        vehicles = VehicleData.query.all()
        return jsonify([{
            'registration': v.registration,
            'make': v.make,
            'model': v.model,
            'year': v.year,
            'updated_at': v.updated_at.isoformat() if v.updated_at else None
        } for v in vehicles])
    except Exception as e:
        logger.error(f"Error fetching vehicles: {str(e)}")
        return jsonify({'error': 'Failed to fetch vehicles'}), 500

@app.route('/api/vehicle/<registration>')
def get_vehicle(registration):
    """Get specific vehicle data from database"""
    try:
        vehicle = VehicleData.query.filter_by(registration=registration.upper()).first()
        if not vehicle:
            return jsonify({'error': 'Vehicle not found'}), 404
        
        response_data = format_database_vehicle_response(vehicle)
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error fetching vehicle {registration}: {str(e)}")
        return jsonify({'error': 'Failed to fetch vehicle data'}), 500

@app.route('/api/search-history')
def get_search_history():
    """Get recent search history"""
    try:
        history = SearchHistory.query.order_by(SearchHistory.search_timestamp.desc()).limit(100).all()
        return jsonify([{
            'registration': h.registration,
            'timestamp': h.search_timestamp.isoformat(),
            'success': h.success,
            'source': h.request_source
        } for h in history])
    except Exception as e:
        logger.error(f"Error fetching search history: {str(e)}")
        return jsonify({'error': 'Failed to fetch search history'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': 'connected' if db.engine.dialect.name else 'unknown'
    })

@app.route('/api/docs')
def api_documentation():
    """Public API Documentation for third-party developers"""
    return render_template('api_docs.html')