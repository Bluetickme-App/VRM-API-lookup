import os
import logging
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "vehicle-scraper-secret")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Enable CORS for API access
CORS(app)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Import and register routes (simplified for now)

@app.route('/')
def index():
    """Render the main frontend interface"""
    return render_template('index.html')

@app.route('/api/scrape', methods=['POST'])
def scrape_vehicle():
    """API endpoint to scrape vehicle data"""
    from models import VehicleData, SearchHistory
    from datetime import datetime, timedelta
    from utils import validate_registration
    
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
                    
                    # Return cached data
                    cached_raw_data = existing_vehicle.raw_data or {}
                    
                    return jsonify({
                        'success': True,
                        'data': {
                            'registration': existing_vehicle.registration,
                            'make': existing_vehicle.make,
                            'model': existing_vehicle.model,
                            'description': existing_vehicle.description,
                            'color': existing_vehicle.color,
                            'fuel_type': existing_vehicle.fuel_type,
                            'year': existing_vehicle.year,
                            'mot_history': cached_raw_data.get('mot_history'),
                            'mileage_history': cached_raw_data.get('mileage_history')
                        },
                        'source': 'cache',
                        'method': 'final_scraper_with_xpath_navigation',
                        'cached': True,
                        'cache_age_hours': round(time_diff.total_seconds() / 3600, 2)
                    })
            
            # Use enhanced scraper for comprehensive data extraction
            try:
                from enhanced_mot_scraper import EnhancedMOTScraper
                
                logger.info(f"Starting enhanced MOT scraper for registration: {registration}")
                scraper = EnhancedMOTScraper()
                basic_data = scraper.scrape_comprehensive_vehicle_data(registration)
                
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
                        'method': 'final_scraper_with_xpath_navigation'
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
            
        except Exception as db_error:
            logger.error(f"Database error for {registration}: {db_error}")
            try:
                db.session.rollback()
            except:
                pass
            
            return jsonify({
                'success': False,
                'error': 'Database error occurred'
            }), 500
    
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)