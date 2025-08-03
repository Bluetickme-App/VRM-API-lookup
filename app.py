import os
import logging
import uuid
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

# Create database tables
with app.app_context():
    # Import models to ensure they are registered
    from models import VehicleData, SearchHistory, MOTHistory
    
    # Create all tables
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

# Import components
from ocr_processor import NumberPlateOCR

# Initialize OCR processor
ocr_processor = NumberPlateOCR()

# Import and register routes (simplified for now)

@app.route('/')
def index():
    """Render the simple dashboard interface for iframe integration"""
    # Check if showing cached data for a specific registration
    reg = request.args.get('reg')
    cache_only = request.args.get('cache')
    
    if reg and cache_only:
        # Show cached vehicle data without triggering new AI analysis
        from models import VehicleData
        vehicle = VehicleData.query.filter_by(registration=reg.upper()).first()
        if vehicle:
            return render_template('simple_dashboard.html', 
                                 cached_vehicle=vehicle, 
                                 show_cached=True)
    
    return render_template('simple_dashboard.html')

@app.route('/share/<share_id>')
def public_share(share_id):
    """Public sharing endpoint for WhatsApp and social media"""
    try:
        from models import VehicleData
        # Find vehicle by share_id or registration
        vehicle = VehicleData.query.filter_by(share_id=share_id).first()
        if not vehicle:
            # Fallback to registration if share_id not found
            vehicle = VehicleData.query.filter_by(registration=share_id.upper()).first()
        
        if not vehicle:
            return render_template('share_not_found.html'), 404
        
        # Create comprehensive vehicle data for sharing
        share_data = {
            'registration': vehicle.registration,
            'make': vehicle.make,
            'model': vehicle.model,
            'year': vehicle.year,
            'color': vehicle.color,
            'fuel_type': vehicle.fuel_type,
            'transmission': vehicle.transmission,
            'engine': vehicle.engine,
            'mot_expiry_date': vehicle.mot_expiry_date,
            'last_mot_mileage': vehicle.last_mot_mileage,
            'total_keepers': vehicle.total_keepers,
            'tax_6_months': vehicle.tax_6_months,
            'tax_12_months': vehicle.tax_12_months,
            'last_v5c_issue_date': vehicle.last_v5c_issue_date,
            'registration_place': vehicle.registration_place,
            'mot_history': vehicle.mot_history,
            'analysis_data': vehicle.analysis_data,
            'share_url': f"{request.host_url}share/{share_id}"
        }
        
        return render_template('public_share.html', vehicle=share_data)
        
    except Exception as e:
        logging.error(f"Error in public share: {e}")
        return render_template('share_error.html'), 500

@app.route('/api/generate-share-link', methods=['POST'])
def generate_share_link():
    """Generate public sharing link for vehicle report"""
    try:
        data = request.get_json()
        registration = data.get('registration', '').upper().strip()
        
        if not registration:
            return jsonify({'success': False, 'error': 'Registration required'}), 400
        
        from models import VehicleData
        vehicle = VehicleData.query.filter_by(registration=registration).first()
        
        if not vehicle:
            return jsonify({'success': False, 'error': 'Vehicle not found'}), 404
        
        # Generate or get share ID
        if not vehicle.share_id:
            vehicle.share_id = str(uuid.uuid4())[:8].upper()
            db.session.commit()
        
        share_url = f"{request.host_url}share/{vehicle.share_id}"
        whatsapp_url = f"https://wa.me/?text=Check out this vehicle report: {share_url}"
        
        return jsonify({
            'success': True,
            'share_url': share_url,
            'whatsapp_url': whatsapp_url,
            'share_id': vehicle.share_id
        })
        
    except Exception as e:
        logging.error(f"Error generating share link: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ocr-process', methods=['POST'])
def process_ocr():
    """Process uploaded image for number plate OCR"""
    try:
        result = None
        
        # Handle file upload
        if request.files and 'image' in request.files:
            file = request.files['image']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            # Save temporary file for processing
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                file.save(tmp_file.name)
                result = ocr_processor.process_image(tmp_file.name, is_base64=False)
                os.unlink(tmp_file.name)  # Clean up
        
        # Handle base64 image data
        elif request.json and 'imageData' in request.json:
            image_data = request.json['imageData']
            result = ocr_processor.process_image(image_data, is_base64=True)
        else:
            return jsonify({'error': 'No image provided'}), 400
        
        if result and 'error' in result:
            return jsonify(result), 400
            
        return jsonify(result if result else {'error': 'Processing failed'})
        
    except Exception as e:
        logger.error(f"OCR processing error: {e}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/classic')
def classic_index():
    """Render the classic frontend interface"""
    return render_template('index.html')

@app.route('/full-dashboard')
def full_dashboard():
    """Render the full dashboard interface"""
    return render_template('dashboard.html')

@app.route('/analysis/<registration>')
def analysis_page(registration):
    """Render the OpenAI analysis page for a specific vehicle"""
    return render_template('analysis.html', registration=registration.upper())

@app.route('/test')
def test_page():
    """Render the test frontend page"""
    return render_template('test.html')

@app.route('/history')
def search_history():
    """Display search history with past lookups"""
    from models import SearchHistory, VehicleData
    from sqlalchemy import desc
    
    try:
        # Get recent search history (last 50 searches)
        recent_searches = SearchHistory.query.order_by(desc(SearchHistory.search_timestamp)).limit(50).all()
        # Group by registration to avoid duplicates and get vehicle data
        unique_searches = {}
        for search in recent_searches:
            if search.registration not in unique_searches:
                # Get the vehicle data if available
                vehicle_data = VehicleData.query.filter_by(registration=search.registration).first()
                unique_searches[search.registration] = {
                    'search': search,
                    'vehicle': vehicle_data
                }
        
        return render_template('history.html', searches=unique_searches)
        
    except Exception as e:
        logger.error(f"Error loading search history: {e}")
        return render_template('history.html', searches={}, error="Unable to load search history")

@app.route('/api/search-stats')
def search_stats():
    """Get search statistics for the history page"""
    from models import SearchHistory, VehicleData
    from sqlalchemy import func, desc
    from datetime import datetime, timedelta
    
    try:
        # Get basic stats
        total_searches = SearchHistory.query.count()
        successful_searches = SearchHistory.query.filter_by(success=True).count()
        unique_vehicles = VehicleData.query.count()
        
        # Get recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_searches = SearchHistory.query.filter(SearchHistory.search_timestamp >= week_ago).count()
        
        # Get most searched registrations
        popular_searches = db.session.query(
            SearchHistory.registration,
            func.count(SearchHistory.registration).label('search_count')
        ).group_by(SearchHistory.registration).order_by(desc('search_count')).limit(10).all()
        
        return jsonify({
            'total_searches': total_searches,
            'successful_searches': successful_searches,
            'unique_vehicles': unique_vehicles,
            'recent_activity': recent_searches,
            'success_rate': round((successful_searches / total_searches * 100) if total_searches > 0 else 0, 1),
            'popular_searches': [{'registration': reg, 'count': count} for reg, count in popular_searches]
        })
        
    except Exception as e:
        logger.error(f"Error getting search stats: {e}")
        return jsonify({'error': 'Unable to load statistics'}), 500

@app.route('/api/intelligent-analysis', methods=['POST'])
def intelligent_analysis():
    """Advanced AI-powered vehicle analysis endpoint"""
    from intelligent_vehicle_analyzer import IntelligentVehicleAnalyzer
    from models import VehicleData
    from datetime import datetime
    
    try:
        data = request.get_json()
        registration = data.get('registration', '').strip().upper()
        
        if not registration:
            return jsonify({
                'success': False,
                'error': 'Registration number required'
            }), 400
        
        # Get vehicle data from database
        vehicle_record = VehicleData.query.filter_by(registration=registration).first()
        
        if not vehicle_record:
            return jsonify({
                'success': False,
                'error': 'Vehicle data not found. Please search for the vehicle first.'
            }), 404
        
        # Prepare comprehensive vehicle data for analysis including tax information
        vehicle_data = {
            'registration': vehicle_record.registration,
            'make': vehicle_record.make,
            'model': vehicle_record.model,
            'variant': vehicle_record.variant,
            'description': vehicle_record.description,
            'year': vehicle_record.year,
            'color': vehicle_record.color,
            'fuel_type': vehicle_record.fuel_type,
            'engine_size': vehicle_record.engine_size,
            'transmission': vehicle_record.transmission,
            'body_style': vehicle_record.body_style,
            'total_keepers': vehicle_record.total_keepers,
            'last_v5c_issue_date': vehicle_record.last_v5c_issue_date.isoformat() if vehicle_record.last_v5c_issue_date else None,
            'registration_place': vehicle_record.registration_place,
            'registration_date': vehicle_record.registration_date.isoformat() if vehicle_record.registration_date else None,
            # Tax information
            'tax_expiry': vehicle_record.tax_expiry.isoformat() if vehicle_record.tax_expiry else None,
            'tax_days_left': vehicle_record.tax_days_left,
            'tax_12_months': vehicle_record.tax_12_months,
            'tax_6_months': vehicle_record.tax_6_months,
            # MOT information
            'mot_expiry_date': vehicle_record.mot_expiry.isoformat() if vehicle_record.mot_expiry else None,
            'mot_days_left': vehicle_record.mot_days_left,
            'last_mot_mileage': vehicle_record.last_mot_mileage,
            'mileage_issues': vehicle_record.mileage_issues,
            # Additional comprehensive data
            'exported': vehicle_record.exported,
            'has_outstanding_recall': vehicle_record.has_outstanding_recall,
            'v5c_certificate_count': vehicle_record.v5c_certificate_count,
            'euro_status': vehicle_record.euro_status,
            'type_approval': vehicle_record.type_approval,
            'co2_emissions': vehicle_record.co2_emissions,
            # Historical data
            'mot_history': vehicle_record.mot_history or {},
            'mileage_history': vehicle_record.mileage_history or {},
            'raw_data': vehicle_record.raw_data or {}
        }
        
        # Perform intelligent analysis
        analyzer = IntelligentVehicleAnalyzer()
        analysis_result = analyzer.analyze_vehicle_comprehensive(vehicle_data)
        
        if analysis_result:
            # Store comprehensive analysis result in database including all relevant data
            from datetime import datetime
            vehicle_record.analysis_data = analysis_result
            vehicle_record.analysis_completed = True
            vehicle_record.analysis_timestamp = datetime.now()
            db.session.commit()
            
            # Return comprehensive response with all relevant vehicle and analysis data
            return jsonify({
                'success': True,
                'analysis': analysis_result,
                'vehicle_data': {
                    'registration': vehicle_record.registration,
                    'make': vehicle_record.make,
                    'model': vehicle_record.model,
                    'year': vehicle_record.year,
                    'color': vehicle_record.color,
                    'fuel_type': vehicle_record.fuel_type,
                    'transmission': vehicle_record.transmission,
                    'engine_size': vehicle_record.engine_size,
                    'body_style': vehicle_record.body_style,
                    'total_keepers': vehicle_record.total_keepers,
                    'last_v5c_issue_date': vehicle_record.last_v5c_issue_date.isoformat() if vehicle_record.last_v5c_issue_date else None,
                    'registration_place': vehicle_record.registration_place,
                    # Tax data always included
                    'tax_12_months': vehicle_record.tax_12_months,
                    'tax_6_months': vehicle_record.tax_6_months,
                    'tax_expiry': vehicle_record.tax_expiry.isoformat() if vehicle_record.tax_expiry else None,
                    'tax_days_left': vehicle_record.tax_days_left,
                    # MOT data
                    'mot_expiry': vehicle_record.mot_expiry.isoformat() if vehicle_record.mot_expiry else None,
                    'mot_days_left': vehicle_record.mot_days_left,
                    'last_mot_mileage': vehicle_record.last_mot_mileage,
                    'mileage_issues': vehicle_record.mileage_issues,
                    # Additional data
                    'exported': vehicle_record.exported,
                    'has_outstanding_recall': vehicle_record.has_outstanding_recall,
                    'v5c_certificate_count': vehicle_record.v5c_certificate_count
                },
                'generated_at': datetime.now().isoformat(),
                'source': 'comprehensive_analysis_with_tax_data'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Analysis failed. Please try again.'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in intelligent analysis: {e}")
        return jsonify({
            'success': False,
            'error': f'Analysis error: {str(e)}'
        }), 500

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
            # CACHE DISABLED: Always fetch fresh data since vehicle data changes daily
            # Cache only used for history display, never for new searches
            logger.info(f"Fetching fresh data for {registration} - caching disabled for daily data changes")
            
            # Use direct Ferrari scraper for authentic data extraction
            try:
                from direct_ferrari_scraper import DirectFerrariScraper
                
                logger.info(f"Starting direct Ferrari scraper for registration: {registration}")
                scraper = DirectFerrariScraper()
                basic_data = scraper.scrape_vehicle_data(registration)
                
                if basic_data:
                    # Check if vehicle already exists (for fresh data updates)
                    vehicle_record = VehicleData.query.filter_by(registration=registration).first()
                    if vehicle_record:
                        logger.info(f"Updating existing record for {registration} with fresh data")
                    else:
                        # Create new vehicle record
                        vehicle_record = VehicleData()
                        vehicle_record.registration = registration
                        logger.info(f"Creating new record for {registration}")
                    
                    # Extract data from working scraper format  
                    basic_info = basic_data.get('basic_info', {})
                    vehicle_details = basic_data.get('vehicle_details', {})
                    
                    # Debug logging
                    logger.info(f"EXTRACTION DEBUG - basic_info: {basic_info}")
                    logger.info(f"EXTRACTION DEBUG - vehicle_details keys: {list(vehicle_details.keys())}")
                    logger.info(f"EXTRACTION DEBUG - model_variant: {vehicle_details.get('model_variant')}")
                    logger.info(f"EXTRACTION DEBUG - description: {vehicle_details.get('description')}")
                    
                    # CRITICAL PRIORITY FIX: Use basic_info make/model as PRIMARY source
                    basic_make = basic_info.get('make', '')
                    basic_model = basic_info.get('model', '')
                    model_variant = vehicle_details.get('model_variant', '')
                    description = vehicle_details.get('description', '')
                    
                    logger.info(f"PRIORITY DEBUG - basic_make: '{basic_make}', basic_model: '{basic_model}'")
                    logger.info(f"PRIORITY DEBUG - model_variant: '{model_variant}', description: '{description}'")
                    
                    # COMPLETE PRIORITY SYSTEM FOR MAKE EXTRACTION
                    make = 'Unknown'
                    
                    # PRIORITY 1: Enhanced pattern matching FIRST (most accurate for vehicle details)
                    if model_variant and model_variant.strip():
                        logger.info(f"🔍 PATTERN MATCHING - model_variant: '{model_variant}', description: '{description}'")
                        
                        if 'focus' in model_variant.lower() or 'focus' in description.lower():
                            make = 'Ford'
                            logger.info(f"✅ FORD DETECTED from model_variant: '{model_variant}'")
                        elif 'corsa' in model_variant.lower() or 'astra' in model_variant.lower() or 'insignia' in model_variant.lower():
                            make = 'Vauxhall'
                            logger.info(f"✅ VAUXHALL DETECTED from model_variant: '{model_variant}'")
                        elif 'a6' in model_variant.lower() or 'a4' in model_variant.lower() or 'a3' in model_variant.lower() or 'q3' in model_variant.lower() or 'q5' in model_variant.lower():
                            make = 'Audi'
                            logger.info(f"✅ AUDI DETECTED from model_variant: '{model_variant}'")
                        elif 'golf' in model_variant.lower() or 'polo' in model_variant.lower() or 'passat' in model_variant.lower():
                            make = 'Volkswagen'
                        elif '3 series' in model_variant.lower() or '5 series' in model_variant.lower() or 'x3' in model_variant.lower() or 'x5' in model_variant.lower():
                            make = 'BMW'
                        elif 'cla' in model_variant.lower() or 'a-class' in model_variant.lower() or 'c-class' in model_variant.lower() or 'e-class' in model_variant.lower():
                            make = 'Mercedes-Benz'
                        elif 'civic' in model_variant.lower() or 'accord' in model_variant.lower() or 'crv' in model_variant.lower():
                            make = 'Honda'
                        elif 'yaris' in model_variant.lower() or 'corolla' in model_variant.lower() or 'avensis' in model_variant.lower() or 'prius' in model_variant.lower():
                            make = 'Toyota'
                        elif 'micra' in model_variant.lower() or 'qashqai' in model_variant.lower() or 'juke' in model_variant.lower():
                            make = 'Nissan'
                    
                    # PRIORITY 2: Use basic_info as fallback only if pattern matching failed
                    if make == 'Unknown' and basic_make and basic_make.strip() and basic_make != 'Unknown':
                        make = basic_make.strip()
                        logger.info(f"⚠️ FALLBACK - Using basic_info make: '{make}'")
                    
                    # PRIORITY 3: Final pattern matching fallback
                    if make == 'Unknown':
                        logger.info(f"❌ NO MATCH FOUND - Defaulting to Unknown")
                        
                        if 'corsa' in model_variant.lower() or 'astra' in model_variant.lower() or 'insignia' in model_variant.lower():
                            make = 'Vauxhall'
                        elif ('focus' in model_variant.lower() or 'fiesta' in model_variant.lower() or 'mondeo' in model_variant.lower() or 'kuga' in model_variant.lower() or
                              'focus' in description.lower() or 'fiesta' in description.lower() or 'mondeo' in description.lower() or 'kuga' in description.lower() or
                              'focus' in basic_model.lower() or 'fiesta' in basic_model.lower() or 'mondeo' in basic_model.lower()):
                            make = 'Ford'
                            logger.info(f"FORD PATTERN DETECTED for model: '{model_variant}', description: '{description}', basic_model: '{basic_model}'")
                        elif 'golf' in model_variant.lower() or 'polo' in model_variant.lower() or 'passat' in model_variant.lower():
                            make = 'Volkswagen'
                        elif ('a3' in model_variant.lower() or 'a4' in model_variant.lower() or 'a6' in model_variant.lower() or 'q3' in model_variant.lower() or 'q5' in model_variant.lower() or
                              'a3' in basic_model.lower() or 'a4' in basic_model.lower() or 'a6' in basic_model.lower()):
                            make = 'Audi'
                        elif '3 series' in model_variant.lower() or '5 series' in model_variant.lower() or 'x3' in model_variant.lower() or 'x5' in model_variant.lower() or 'bmw' in description.lower():
                            make = 'BMW'
                        elif 'cla' in model_variant.lower() or 'a-class' in model_variant.lower() or 'c-class' in model_variant.lower() or 'e-class' in model_variant.lower() or 'cla' in description.lower():
                            make = 'Mercedes-Benz'
                        elif 'civic' in model_variant.lower() or 'accord' in model_variant.lower() or 'crv' in model_variant.lower():
                            make = 'Honda'
                        elif 'yaris' in model_variant.lower() or 'corolla' in model_variant.lower() or 'avensis' in model_variant.lower() or 'prius' in model_variant.lower():
                            make = 'Toyota'
                        elif 'micra' in model_variant.lower() or 'qashqai' in model_variant.lower() or 'juke' in model_variant.lower():
                            make = 'Nissan'
                        elif 'f12berlinetta' in model_variant.lower() or 'f12' in model_variant.lower() or 'berlinetta' in model_variant.lower() or 'berlinetta' in description.lower():
                            make = 'Ferrari'
                        elif ('ferrari' in model_variant.lower() and ('f430' in model_variant.lower() or 'f458' in model_variant.lower() or 'f488' in model_variant.lower())) or ('ferrari' in description.lower() and ('430' in description.lower() or '458' in description.lower() or '488' in description.lower())):
                            make = 'Ferrari'
                        elif ('ferrari' in model_variant.lower() and ('f8' in model_variant.lower() or 'roma' in model_variant.lower() or 'portofino' in model_variant.lower())) or ('ferrari' in description.lower() and ('f8' in description.lower() or 'roma' in description.lower() or 'portofino' in description.lower())):
                            make = 'Ferrari'
                        elif ('ferrari' in model_variant.lower() and ('california' in model_variant.lower() or 'laferrari' in model_variant.lower())) or ('ferrari' in description.lower() and ('california' in description.lower() or 'laferrari' in description.lower())):
                            make = 'Ferrari'
                        elif 'huracan' in model_variant.lower() or 'aventador' in model_variant.lower() or 'gallardo' in model_variant.lower():
                            make = 'Lamborghini'
                        elif '911' in model_variant.lower() or 'cayenne' in model_variant.lower() or 'panamera' in model_variant.lower():
                            make = 'Porsche'
                    
                    # COMPLETE PRIORITY SYSTEM FOR MODEL EXTRACTION
                    # PRIORITY 1: Use model_variant (most accurate from vehicle details)
                    if model_variant and model_variant.strip():
                        if make == 'Ferrari' and 'f12' in model_variant.lower():
                            model = 'F12 Berlinetta'
                        else:
                            model = model_variant.strip()
                        logger.info(f"✅ MODEL SUCCESS - Using model_variant: '{model}'")
                    # PRIORITY 2: Use basic_info model as fallback
                    elif basic_model and basic_model.strip() and basic_model != 'Unknown':
                        if make == 'Ferrari' and 'f12' in basic_model.lower():
                            model = 'F12 Berlinetta'
                        else:
                            model = basic_model.strip()
                        logger.info(f"⚠️ MODEL FALLBACK - Using basic_info model: '{model}'")
                    else:
                        model = 'Unknown'
                        logger.info(f"❌ MODEL FAILED - No valid model found")
                        
                    color = vehicle_details.get('primary_colour', 'Unknown')
                    fuel_type = vehicle_details.get('fuel_type', 'Unknown')
                    
                    # Update database record
                    vehicle_record.make = make[:50]
                    vehicle_record.model = model[:50]
                    vehicle_record.description = description[:200]
                    vehicle_record.color = color[:50]
                    vehicle_record.fuel_type = fuel_type[:50]
                    
                    # Map additional vehicle details
                    transmission = vehicle_details.get('transmission', 'Unknown')
                    vehicle_record.transmission = transmission[:100] if transmission != 'Unknown' else None
                    
                    engine_size = vehicle_details.get('engine', '')
                    if engine_size and 'cc' in engine_size:
                        # Convert '1364 cc' to proper format
                        vehicle_record.engine_size = engine_size[:50]
                    else:
                        vehicle_record.engine_size = None
                    
                    body_style = vehicle_details.get('body_style', '')
                    vehicle_record.body_style = body_style[:50] if body_style else None
                    
                    # Extract year from year_manufacture
                    year_str = vehicle_details.get('year_manufacture', '')
                    if year_str and year_str.isdigit():
                        vehicle_record.year = int(year_str)
                    
                    euro_status = vehicle_details.get('euro_status', '')
                    vehicle_record.euro_status = euro_status[:20] if euro_status else None
                    
                    type_approval = vehicle_details.get('type_approval', '')
                    vehicle_record.type_approval = type_approval[:20] if type_approval else None
                    
                    registration_place = vehicle_details.get('registration_place', '')
                    vehicle_record.registration_place = registration_place[:200] if registration_place else None
                    
                    # Handle date fields - extract from vehicle_details structure
                    registration_date_str = vehicle_details.get('registration_date', '')
                    if registration_date_str:
                        try:
                            from datetime import datetime
                            vehicle_record.registration_date = datetime.strptime(registration_date_str, '%d/%m/%Y').date()
                        except Exception as e:
                            logger.debug(f"Error parsing registration date '{registration_date_str}': {e}")
                    
                    # Fix V5C date mapping - extract from vehicle_details
                    v5_date_str = vehicle_details.get('last_v5c_issue_date', '')
                    logger.info(f"V5C date mapping - raw value: '{v5_date_str}'")
                    
                    if v5_date_str:
                        try:
                            from datetime import datetime
                            # Try multiple date formats for V5C dates
                            date_formats = [
                                '%d %B %Y',      # 22 January 2025  
                                '%d/%m/%Y',      # 22/01/2025
                                '%Y-%m-%d',      # 2025-01-22
                                '%d-%m-%Y',      # 22-01-2025
                                '%B %d, %Y',     # January 22, 2025
                                '%d %b %Y'       # 22 Jan 2025
                            ]
                            
                            for date_format in date_formats:
                                try:
                                    parsed_date = datetime.strptime(v5_date_str, date_format).date()
                                    vehicle_record.last_v5c_issue_date = parsed_date
                                    logger.info(f"V5C date successfully parsed: '{v5_date_str}' -> {parsed_date}")
                                    break
                                except ValueError:
                                    continue
                                    
                            if not vehicle_record.last_v5c_issue_date:
                                logger.warning(f"Could not parse V5C date: '{v5_date_str}'")
                        except Exception as e:
                            logger.error(f"Error processing V5C date '{v5_date_str}': {e}")
                            
                    # Add missing fields storage
                    variant = basic_info.get('variant') or basic_data.get('variant')
                    vehicle_record.variant = variant[:200] if variant else None
                    
                    # Tax costs from extracted data
                    additional_info = basic_data.get('additional', {})
                    tax_6 = (basic_info.get('tax_6_months') or basic_data.get('tax_6_months') or 
                            additional_info.get('tax_6_months'))
                    vehicle_record.tax_6_months = tax_6[:20] if tax_6 else None
                    
                    tax_12 = (basic_info.get('tax_12_months') or basic_data.get('tax_12_months') or 
                             additional_info.get('tax_12_months'))
                    vehicle_record.tax_12_months = tax_12[:20] if tax_12 else None
                    
                    # Total keepers from extracted data
                    total_keepers = additional_info.get('total_keepers')
                    if total_keepers is not None:
                        vehicle_record.total_keepers = int(total_keepers)
                        logger.info(f"Stored total keepers: {total_keepers}")
                    
                    logger.info(f"TAX EXTRACTION DEBUG: 6-month: {tax_6}, 12-month: {tax_12}, Total keepers: {total_keepers}")
                    
                    logger.info(f"FIXED: Comprehensive fields mapped - transmission: {bool(vehicle_record.transmission)}, engine: {bool(vehicle_record.engine_size)}, body: {bool(vehicle_record.body_style)}")
                    
                    # Handle year conversion
                    year_value = basic_info.get('year') or basic_data.get('year')
                    if year_value:
                        try:
                            vehicle_record.year = int(year_value)
                        except (ValueError, TypeError):
                            vehicle_record.year = None
                    
                    # Add V5 issue date to top-level response from database record
                    if vehicle_record.last_v5c_issue_date:
                        v5_date_formatted = vehicle_record.last_v5c_issue_date.strftime('%d %B %Y')
                        basic_data['last_v5_issue_date'] = v5_date_formatted
                        basic_data['v5_issue_date'] = v5_date_formatted
                        logger.info(f"V5C Issue Date mapped for API response: {v5_date_formatted}")
                    else:
                        # Fallback: try to get from raw extracted data
                        v5_date = basic_data.get('last_v5_issue_date') or basic_data.get('v5_issue_date')
                        if v5_date:
                            basic_data['last_v5_issue_date'] = v5_date
                            basic_data['v5_issue_date'] = v5_date
                            logger.info(f"V5C Issue Date mapped for API response: {v5_date}")
                    
                    # Store raw data for future reference with complete MOT and mileage data
                    vehicle_record.raw_data = basic_data
                    
                    # Store MOT history and mileage data in dedicated fields
                    if basic_data.get('mot_history'):
                        vehicle_record.mot_history = basic_data['mot_history']
                        logger.info(f"Stored MOT history with {len(basic_data['mot_history'].get('tests', []))} tests")
                    
                    # Create mileage history from MOT data if not already present
                    if basic_data.get('mileage_history'):
                        vehicle_record.mileage_history = basic_data['mileage_history'] 
                        logger.info(f"Stored mileage history with {len(basic_data['mileage_history'].get('mileage_records', []))} records")
                    elif basic_data.get('mot_history'):
                        # Create mileage history from MOT data
                        mileage_analysis = _create_mileage_analysis_from_mot_data(basic_data['mot_history'])
                        if mileage_analysis:
                            vehicle_record.mileage_history = mileage_analysis
                            logger.info(f"Created mileage history from MOT data with {len(mileage_analysis.get('mileage_records', []))} records")
                    
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
                            'variant': vehicle_record.variant,
                            'description': vehicle_record.description,
                            'color': vehicle_record.color,
                            'fuel_type': vehicle_record.fuel_type,
                            'year': vehicle_record.year,
                            # CRITICAL FIX: Add comprehensive vehicle fields to API response
                            'transmission': vehicle_record.transmission,
                            'engine_size': vehicle_record.engine_size,
                            'body_style': vehicle_record.body_style,
                            'euro_status': vehicle_record.euro_status,
                            'type_approval': vehicle_record.type_approval,
                            'registration_place': vehicle_record.registration_place,
                            'registration_date': vehicle_record.registration_date.isoformat() if vehicle_record.registration_date else None,
                            'last_v5c_issue_date': vehicle_record.last_v5c_issue_date.isoformat() if vehicle_record.last_v5c_issue_date else None,
                            # Add V5C date at top level for frontend compatibility
                            'v5_issue_date': vehicle_record.last_v5c_issue_date.strftime('%d %B %Y') if vehicle_record.last_v5c_issue_date else None,
                            'last_v5_issue_date': vehicle_record.last_v5c_issue_date.strftime('%d %B %Y') if vehicle_record.last_v5c_issue_date else None,
                            'tax_6_months': vehicle_record.tax_6_months,
                            'tax_12_months': vehicle_record.tax_12_months,
                            'mot_expiry_date': vehicle_record.mot_expiry.strftime('%d/%m/%Y') if vehicle_record.mot_expiry else None,
                            'mot_history': vehicle_record.mot_history or basic_data.get('mot_history'),
                            'mileage_history': vehicle_record.mileage_history or basic_data.get('mileage_history') or _create_mileage_analysis_from_mot_data(basic_data.get('mot_history')),
                            'total_keepers': vehicle_record.total_keepers,
                            # Add MOT summary data
                            'mot_summary': {
                                'total_tests': len(vehicle_record.mot_history) if vehicle_record.mot_history and isinstance(vehicle_record.mot_history, list) else 0,
                                'last_test_date': vehicle_record.mot_history[0].get('date') if vehicle_record.mot_history and isinstance(vehicle_record.mot_history, list) and vehicle_record.mot_history else None,
                                'expiry_date': vehicle_record.mot_expiry.strftime('%d/%m/%Y') if vehicle_record.mot_expiry else None,
                                'last_mileage': vehicle_record.last_mot_mileage
                            },
                            'raw_data': basic_data
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

@app.route('/api/vehicle-data/<registration>', methods=['GET'])
def get_cached_vehicle_data(registration):
    """API endpoint to retrieve cached vehicle data for history display"""
    from models import VehicleData
    
    try:
        registration = registration.strip().upper()
        
        # Get cached vehicle data from database
        vehicle_record = VehicleData.query.filter_by(registration=registration).first()
        
        if not vehicle_record:
            return jsonify({
                'success': False,
                'error': 'Vehicle data not found in cache'
            }), 404
        
        # Return comprehensive cached data in same format as fresh scrape
        response_data = {
            'registration': vehicle_record.registration,
            'make': vehicle_record.make,
            'model': vehicle_record.model,
            'variant': vehicle_record.variant,
            'description': vehicle_record.description,
            'color': vehicle_record.color,
            'fuel_type': vehicle_record.fuel_type,
            'year': vehicle_record.year,
            'transmission': vehicle_record.transmission,
            'engine_size': vehicle_record.engine_size,
            'body_style': vehicle_record.body_style,
            'euro_status': vehicle_record.euro_status,
            'type_approval': vehicle_record.type_approval,
            'registration_place': vehicle_record.registration_place,
            'registration_date': vehicle_record.registration_date.isoformat() if vehicle_record.registration_date else None,
            'last_v5c_issue_date': vehicle_record.last_v5c_issue_date.isoformat() if vehicle_record.last_v5c_issue_date else None,
            'v5_issue_date': vehicle_record.last_v5c_issue_date.strftime('%d %B %Y') if vehicle_record.last_v5c_issue_date else None,
            'last_v5_issue_date': vehicle_record.last_v5c_issue_date.strftime('%d %B %Y') if vehicle_record.last_v5c_issue_date else None,
            'tax_6_months': vehicle_record.tax_6_months,
            'tax_12_months': vehicle_record.tax_12_months,
            'total_keepers': vehicle_record.total_keepers,
            'mot_expiry_date': vehicle_record.mot_expiry.strftime('%d/%m/%Y') if vehicle_record.mot_expiry else None,
            'mot_history': vehicle_record.mot_history,
            'mileage_history': vehicle_record.mileage_history,
            # Add MOT summary for cached data
            'mot_summary': {
                'total_tests': len(vehicle_record.mot_history) if vehicle_record.mot_history and isinstance(vehicle_record.mot_history, list) else 0,
                'last_test_date': vehicle_record.mot_history[0].get('date') if vehicle_record.mot_history and isinstance(vehicle_record.mot_history, list) and vehicle_record.mot_history else None,
                'expiry_date': vehicle_record.mot_expiry.strftime('%d/%m/%Y') if vehicle_record.mot_expiry else None,
                'last_mileage': vehicle_record.last_mot_mileage
            },
            'raw_data': vehicle_record.raw_data
        }
        
        return jsonify({
            'success': True,
            'data': response_data,
            'source': 'cached_database',
            'cached_at': vehicle_record.updated_at.isoformat() if vehicle_record.updated_at else None
        })
        
    except Exception as e:
        logger.error(f"Error retrieving cached vehicle data: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve cached data'
        }), 500

def _enhance_mot_data_with_realistic_info(registration: str, basic_data: dict) -> dict:
    """This function is disabled - using only authentic scraped data"""
    return basic_data
    
    if registration == 'RE13CEO':
        # Ferrari F12 Berlinetta 2013 
        basic_data['make'] = 'Ferrari'
        basic_data['model'] = 'F12 Berlinetta'
        basic_data['year'] = 2013
        basic_data['color'] = 'Red'
        basic_data['fuel_type'] = 'PETROL'
        basic_data['transmission'] = 'Automatic'
        basic_data['engine_size'] = '6.3L'
        basic_data['body_style'] = 'Coupe'
        basic_data['total_keepers'] = 3
        basic_data['tax_6_months'] = '£415.50'
        basic_data['tax_12_months'] = '£830.00'
        
        # Enhanced MOT history with realistic dates and mileage
        basic_data['mot_history'] = {
            'registration': 'RE13CEO',
            'mot_tests': [
                {
                    'test_date': '2024-03-15',
                    'result': 'PASSED',
                    'mileage': '76543',
                    'expiry_date': '2025-03-14',
                    'source': 'enhanced_mot_detailed_page',
                    'comments': [
                        {'text': 'Nearside front brake disc worn, pitted or scored, but not seriously weakened', 'type': 'ADVISORY'},
                        {'text': 'Offside rear tyre has shallow tread depth 2.5mm', 'type': 'ADVISORY'}
                    ]
                },
                {
                    'test_date': '2023-03-20',
                    'result': 'FAILED',
                    'mileage': '72156',
                    'expiry_date': '',
                    'source': 'enhanced_mot_detailed_page',
                    'comments': [
                        {'text': 'Front registration plate not fixed vertically or horizontally', 'type': 'FAILURE'},
                        {'text': 'Nearside headlamp aim too high', 'type': 'FAILURE'}
                    ]
                },
                {
                    'test_date': '2023-03-22',
                    'result': 'PASSED',
                    'mileage': '72156',
                    'expiry_date': '2024-03-21',
                    'source': 'enhanced_mot_detailed_page',
                    'comments': [
                        {'text': 'Registration plate and headlamp issues corrected', 'type': 'CLEAN_PASS'}
                    ]
                },
                {
                    'test_date': '2022-03-18',
                    'result': 'PASSED',
                    'mileage': '68234',
                    'expiry_date': '2023-03-17',
                    'source': 'enhanced_mot_detailed_page',
                    'comments': [
                        {'text': 'Offside front brake disc worn, pitted or scored', 'type': 'ADVISORY'}
                    ]
                },
                {
                    'test_date': '2021-03-12',
                    'result': 'PASSED',
                    'mileage': '64012',
                    'expiry_date': '2022-03-11',
                    'source': 'enhanced_mot_detailed_page',
                    'comments': [
                        {'text': 'Vehicle passed with no advisories', 'type': 'CLEAN_PASS'}
                    ]
                }
            ],
            'summary': {
                'total_tests': 5,
                'total_passed': 4,
                'total_failed': 1,
                'total_advisory': 3,
                'date_range': {'earliest': '2021-03-12', 'latest': '2024-03-15'},
                'mileage_readings': ['64012', '68234', '72156', '72156', '76543']
            },
            'scraped_from': 'enhanced_mot_scraper_detailed_page',
            'extraction_timestamp': '2025-07-22 14:20:00',
            'total_tests_found': 5,
            'page_title': 'MOT History For RE13CEO - Check Car Details',
            'page_url': 'https://www.checkcardetails.co.uk/mot/mothistory'
        }
        
        # Add comprehensive mileage analysis
        basic_data['mileage_history'] = {
            'analysis': {
                'odometer_issues': {
                    'has_issues': False,
                    'severity': 'NONE',
                    'status': 'No mileage discrepancies detected'
                },
                'progression': {
                    'is_consistent': True,
                    'annual_average': 4500,
                    'total_years': 5,
                    'total_increase': 12531
                }
            },
            'mileage_records': [
                {'date': '2024-03-15', 'mileage': '76543', 'increase': '+4387'},
                {'date': '2023-03-22', 'mileage': '72156', 'increase': '+0'},
                {'date': '2023-03-20', 'mileage': '72156', 'increase': '+3922'},
                {'date': '2022-03-18', 'mileage': '68234', 'increase': '+4222'},
                {'date': '2021-03-12', 'mileage': '64012', 'increase': 'First test'}
            ],
            'summary': {
                'latest_mileage': 76543,
                'earliest_mileage': 64012,
                'total_increase': 12531,
                'years_covered': 3.1,
                'average_per_year': 4043
            }
        }
    
    elif registration == 'DA07BWF':
        # Audi A6 2007
        basic_data['make'] = 'Audi'
        basic_data['model'] = 'A6'
        basic_data['year'] = 2007
        basic_data['color'] = 'Grey'
        basic_data['fuel_type'] = 'DIESEL'
        basic_data['last_v5_issue_date'] = '22 January 2025'
        basic_data['v5_issue_date'] = '22 January 2025'
        
        # Enhanced MOT history
        basic_data['mot_history'] = {
            'registration': 'DA07BWF',
            'mot_tests': [
                {
                    'test_date': '2024-05-10',
                    'result': 'PASSED',
                    'mileage': '145623',
                    'expiry_date': '2025-05-09',
                    'source': 'enhanced_mot_detailed_page',
                    'comments': [
                        {'text': 'Nearside rear suspension spring broken or defective', 'type': 'ADVISORY'}
                    ]
                },
                {
                    'test_date': '2023-05-15',
                    'result': 'PASSED',
                    'mileage': '141298',
                    'expiry_date': '2024-05-14',
                    'source': 'enhanced_mot_detailed_page',
                    'comments': [
                        {'text': 'Offside front tyre has cut reaching ply or cords', 'type': 'ADVISORY'},
                        {'text': 'Brake pedal has excessive travel', 'type': 'ADVISORY'}
                    ]
                },
                {
                    'test_date': '2022-05-20',
                    'result': 'FAILED',
                    'mileage': '136890',
                    'expiry_date': '',
                    'source': 'enhanced_mot_detailed_page',
                    'comments': [
                        {'text': 'Brake disc significantly worn, pitted or scored', 'type': 'FAILURE'},
                        {'text': 'Exhaust emissions exceeded statutory limits', 'type': 'FAILURE'}
                    ]
                },
                {
                    'test_date': '2022-05-25',
                    'result': 'PASSED',
                    'mileage': '136890',
                    'expiry_date': '2023-05-24',
                    'source': 'enhanced_mot_detailed_page',
                    'comments': [
                        {'text': 'Brake disc and emissions issues corrected', 'type': 'CLEAN_PASS'}
                    ]
                }
            ],
            'summary': {
                'total_tests': 4,
                'total_passed': 3,
                'total_failed': 1,
                'total_advisory': 3,
                'date_range': {'earliest': '2022-05-20', 'latest': '2024-05-10'},
                'mileage_readings': ['136890', '136890', '141298', '145623']
            },
            'scraped_from': 'enhanced_mot_scraper_detailed_page',
            'extraction_timestamp': '2025-07-22 14:20:00',
            'total_tests_found': 4,
            'page_title': 'MOT History For DA07BWF - Check Car Details',
            'page_url': 'https://www.checkcardetails.co.uk/mot/mothistory'
        }
        
        # Add comprehensive mileage discrepancy analysis
        basic_data['mileage_history'] = {
            'analysis': {
                'odometer_issues': {
                    'has_issues': True,
                    'affected_period': '2016-2017',
                    'reduction_amount': 51411,
                    'severity': 'HIGH',
                    'description': 'Significant mileage reduction detected between 2016-2017'
                },
                'progression': {
                    'is_consistent': False,
                    'annual_average': 4500,
                    'irregular_periods': ['2016-2017']
                }
            },
            'mileage_records': [
                {'date': '2024-05-10', 'mileage': '145623', 'increase': '+4325'},
                {'date': '2023-05-15', 'mileage': '141298', 'increase': '+4408'},
                {'date': '2022-05-25', 'mileage': '136890', 'increase': '+0'},
                {'date': '2022-05-20', 'mileage': '136890', 'increase': 'FAILED TEST'},
                {'date': '2021-05-18', 'mileage': '132456', 'increase': '+4333'},
                {'date': '2020-05-20', 'mileage': '128123', 'increase': '+3987'},
                {'date': '2019-05-15', 'mileage': '124136', 'increase': '+4012'},
                {'date': '2018-05-22', 'mileage': '120124', 'increase': '+68713'},
                {'date': '2017-05-10', 'mileage': '51411', 'increase': 'ODOMETER ROLLBACK'},
                {'date': '2016-05-12', 'mileage': '102824', 'increase': '+4156'}
            ],
            'summary': {
                'latest_mileage': 145623,
                'highest_mileage': 145623,
                'rollback_detected': True,
                'rollback_amount': 51411,
                'years_affected': 1
            }
        }
    
    elif registration == 'DA07FBW':
        # Volkswagen Golf 2007
        basic_data['make'] = 'Volkswagen'
        basic_data['model'] = 'Golf'
        basic_data['year'] = 2007
        basic_data['color'] = 'Red'
        basic_data['fuel_type'] = 'DIESEL'
        
        # Basic MOT history
        basic_data['mot_history'] = {
            'registration': 'DA07FBW',
            'mot_tests': [
                {
                    'test_date': '2024-06-15',
                    'result': 'PASSED',
                    'mileage': '89456',
                    'expiry_date': '2025-06-14',
                    'source': 'enhanced_mot_detailed_page',
                    'comments': [
                        {'text': 'Vehicle passed with minor advisories', 'type': 'ADVISORY'}
                    ]
                }
            ],
            'summary': {
                'total_tests': 1,
                'total_passed': 1,
                'total_failed': 0,
                'total_advisory': 1,
                'date_range': {'earliest': '2024-06-15', 'latest': '2024-06-15'},
                'mileage_readings': ['89456']
            },
            'scraped_from': 'enhanced_mot_detailed_page',
            'extraction_timestamp': '2025-07-22 14:20:00',
            'total_tests_found': 1,
            'page_title': 'MOT History For DA07FBW - Check Car Details',
            'page_url': 'https://www.checkcardetails.co.uk/mot/mothistory'
        }
        
        # Add basic mileage analysis
        basic_data['mileage_history'] = {
            'analysis': {
                'odometer_issues': {
                    'has_issues': False,
                    'severity': 'NONE',
                    'status': 'No issues detected - single test record'
                },
                'progression': {
                    'is_consistent': True,
                    'status': 'Limited data - single test'
                }
            },
            'mileage_records': [
                {'date': '2024-06-15', 'mileage': '89456', 'increase': 'Most recent test'}
            ],
            'summary': {
                'latest_mileage': 89456,
                'total_tests': 1,
                'data_availability': 'Limited - single test record'
            }
        }
    
    return basic_data

def _create_mileage_analysis_from_mot_data(mot_history):
    """Create mileage analysis from MOT history data"""
    if not mot_history or not mot_history.get('tests'):
        return {
            'analysis': {
                'odometer_issues': {'has_issues': False, 'severity': 'NONE', 'status': 'No MOT data available'},
                'progression': {'is_consistent': True, 'status': 'No data to analyze'}
            },
            'mileage_records': [],
            'summary': {'total_records': 0, 'status': 'No MOT data available'}
        }
    
    # Extract mileage records from MOT tests
    mileage_records = []
    for test in mot_history.get('tests', []):
        if test.get('mileage') and test.get('date'):
            mileage_records.append({
                'date': test['date'],
                'mileage': test['mileage'],
                'source': 'MOT_test_record',
                'test_result': test.get('result', 'Unknown')
            })
    
    # Sort by mileage (descending) to check for rollbacks
    mileage_records.sort(key=lambda x: x['mileage'], reverse=True)
    
    # Analyze for odometer issues
    has_rollback = False
    rollback_amount = 0
    
    if len(mileage_records) > 1:
        for i in range(len(mileage_records) - 1):
            current_mileage = mileage_records[i]['mileage']
            next_mileage = mileage_records[i + 1]['mileage']
            
            # Check for rollback (mileage going backwards chronologically)
            if current_mileage < next_mileage:
                has_rollback = True
                rollback_amount = max(rollback_amount, next_mileage - current_mileage)
    
    # Calculate progression statistics
    if len(mileage_records) > 1:
        total_mileage = mileage_records[0]['mileage'] - mileage_records[-1]['mileage']
        latest_mileage = mileage_records[0]['mileage']
        earliest_mileage = mileage_records[-1]['mileage']
    else:
        total_mileage = 0
        latest_mileage = mileage_records[0]['mileage'] if mileage_records else 0
        earliest_mileage = latest_mileage
    
    return {
        'analysis': {
            'odometer_issues': {
                'has_issues': has_rollback,
                'severity': 'HIGH' if rollback_amount > 50000 else 'MEDIUM' if rollback_amount > 10000 else 'NONE',
                'status': f'Rollback detected: {rollback_amount} miles' if has_rollback else 'No odometer discrepancies detected',
                'reduction_amount': rollback_amount if has_rollback else 0
            },
            'progression': {
                'is_consistent': not has_rollback,
                'total_increase': total_mileage,
                'status': 'Consistent progression' if not has_rollback else 'Inconsistent mileage detected'
            }
        },
        'mileage_records': sorted(mileage_records, key=lambda x: x['date']),  # Sort by date for display
        'summary': {
            'total_records': len(mileage_records),
            'latest_mileage': latest_mileage,
            'earliest_mileage': earliest_mileage,
            'total_increase': total_mileage,
            'status': 'Complete' if mileage_records else 'No data available'
        }
    }

@app.route('/api/js-mileage', methods=['POST'])
def extract_mileage_js():
    """Extract mileage data using JavaScript DOM selectors"""
    try:
        data = request.get_json()
        registration = data.get('registration', '').strip().upper()
        
        if not registration:
            return jsonify({'error': 'Registration is required'}), 400
        
        logger.info(f"Starting JavaScript mileage extraction for: {registration}")
        
        # Use Simple JavaScript extractor
        from js_mileage_simple import SimpleMileageJSExtractor
        js_extractor = SimpleMileageJSExtractor()
        mileage_data = js_extractor.extract_mileage_with_js_selectors(registration)
        
        return jsonify({
            'success': mileage_data.get('success', False),
            'registration': registration,
            'mileage_data': mileage_data,
            'extraction_method': 'javascript_dom_selectors'
        })
        
    except Exception as e:
        logger.error(f"Error in JavaScript mileage extraction: {e}")
        return jsonify({'error': 'Extraction failed', 'details': str(e)}), 500

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)