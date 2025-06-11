"""
VNC-Primary API endpoint for maximum reliability
Uses browser automation as the primary method, bypassing unreliable direct scraping
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from models import db, VehicleData, SearchHistory
from utils import validate_registration
import logging

# Create blueprint for VNC-primary API
vnc_primary = Blueprint('vnc_primary', __name__)

logger = logging.getLogger(__name__)

@vnc_primary.route('/api/vnc-vehicle', methods=['GET', 'POST'])
def vnc_primary_lookup():
    """
    VNC-primary vehicle lookup - uses browser automation for maximum reliability
    Bypasses unreliable direct scraping methods
    """
    try:
        # Handle both GET and POST requests
        if request.method == 'GET':
            registration = request.args.get('registration', '').upper().replace(' ', '')
        else:
            data = request.get_json()
            registration = data.get('registration', '').upper().replace(' ', '') if data else ''
        
        if not registration:
            return jsonify({
                'success': False,
                'error': 'Registration number required',
                'usage': 'GET: /api/vnc-vehicle?registration=ABC123 or POST: {"registration": "ABC123"}'
            }), 400
        
        # Validate registration format
        if not validate_registration(registration):
            return jsonify({
                'success': False,
                'error': 'Invalid UK registration number format',
                'error_type': 'invalid_format'
            }), 400
        
        # Log VNC request
        search_record = SearchHistory(
            registration=registration,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            request_source='vnc_primary'
        )
        
        # Check cache first for performance
        existing_vehicle = VehicleData.query.filter_by(registration=registration).first()
        
        if existing_vehicle and existing_vehicle.make and existing_vehicle.updated_at:
            cache_age = datetime.utcnow() - existing_vehicle.updated_at
            
            # Return fresh cache (< 6 hours for VNC-primary)
            if cache_age < timedelta(hours=6):
                search_record.success = True
                search_record.error_message = 'VNC cache hit'
                db.session.add(search_record)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'data': {
                        'registration': existing_vehicle.registration,
                        'make': existing_vehicle.make,
                        'model': existing_vehicle.model,
                        'description': existing_vehicle.description,
                        'color': existing_vehicle.color,
                        'fuel_type': existing_vehicle.fuel_type,
                        'transmission': existing_vehicle.transmission,
                        'engine_size': existing_vehicle.engine_size,
                        'body_style': existing_vehicle.body_style,
                        'year': existing_vehicle.year,
                        'tax_expiry': existing_vehicle.tax_expiry.isoformat() if existing_vehicle.tax_expiry else None,
                        'mot_expiry': existing_vehicle.mot_expiry.isoformat() if existing_vehicle.mot_expiry else None,
                        'total_keepers': existing_vehicle.total_keepers
                    },
                    'source': 'vnc_cache',
                    'cache_age_hours': round(cache_age.total_seconds() / 3600, 1),
                    'method': 'cached_vnc_data'
                })
        
        # Execute VNC automation with maximum reliability
        try:
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
            
            def reliable_vnc_scrape():
                from optimized_scraper import OptimizedVehicleScraper
                scraper = OptimizedVehicleScraper(headless=True)
                return scraper.scrape_vehicle_data(registration, max_retries=3)
            
            # Execute with extended timeout for thorough extraction
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(reliable_vnc_scrape)
                try:
                    vehicle_data = future.result(timeout=60)
                except FuturesTimeoutError:
                    search_record.success = False
                    search_record.error_message = 'VNC timeout after 60 seconds'
                    db.session.add(search_record)
                    db.session.commit()
                    
                    return jsonify({
                        'success': False,
                        'error': 'VNC automation timeout - extraction taking longer than expected',
                        'error_type': 'vnc_timeout',
                        'retry_after': 180,
                        'method': 'vnc_automation'
                    }), 408
        
        except Exception as vnc_error:
            search_record.success = False
            search_record.error_message = f'VNC error: {str(vnc_error)}'
            db.session.add(search_record)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': 'VNC automation service error',
                'error_type': 'vnc_service_error',
                'method': 'vnc_automation'
            }), 503
        
        # Process VNC extraction results
        if vehicle_data and vehicle_data.get('basic_info'):
            basic_info = vehicle_data.get('basic_info', {})
            tax_mot = vehicle_data.get('tax_mot', {})
            vehicle_details = vehicle_data.get('vehicle_details', {})
            additional = vehicle_data.get('additional', {})
            
            # Store in database for caching
            try:
                if existing_vehicle:
                    vehicle_record = existing_vehicle
                else:
                    vehicle_record = VehicleData(registration=registration)
                
                # Update vehicle record with VNC data (with length validation)
                make_text = basic_info.get('make') or 'Unknown'
                if len(make_text) > 100:
                    make_text = make_text[:97] + '...'
                vehicle_record.make = make_text
                vehicle_record.model = basic_info.get('model')
                vehicle_record.description = basic_info.get('description')
                vehicle_record.color = basic_info.get('color')
                vehicle_record.fuel_type = basic_info.get('fuel_type')
                vehicle_record.transmission = vehicle_details.get('transmission')
                vehicle_record.engine_size = vehicle_details.get('engine_size')
                vehicle_record.body_style = vehicle_details.get('body_style')
                vehicle_record.year = basic_info.get('year')
                vehicle_record.total_keepers = additional.get('total_keepers')
                
                # Parse dates
                if tax_mot.get('tax_expiry'):
                    try:
                        from datetime import datetime
                        vehicle_record.tax_expiry = datetime.strptime(tax_mot.get('tax_expiry'), '%d %b %Y').date()
                    except:
                        pass
                
                if tax_mot.get('mot_expiry'):
                    try:
                        from datetime import datetime
                        vehicle_record.mot_expiry = datetime.strptime(tax_mot.get('mot_expiry'), '%d %b %Y').date()
                    except:
                        pass
                
                if not existing_vehicle:
                    db.session.add(vehicle_record)
                
                search_record.success = True
                search_record.error_message = 'VNC extraction successful'
                db.session.add(search_record)
                db.session.commit()
                
            except Exception as db_error:
                logger.error(f"Database save error: {str(db_error)}")
                # Continue with response even if database save fails
            
            return jsonify({
                'success': True,
                'data': {
                    'registration': registration,
                    'make': basic_info.get('make'),
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
                'source': 'vnc_automation',
                'method': 'browser_automation',
                'extraction_time': datetime.utcnow().isoformat(),
                'reliability': 'maximum'
            })
        
        else:
            # No vehicle data found
            search_record.success = False
            search_record.error_message = 'No vehicle found via VNC'
            db.session.add(search_record)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': f'No vehicle found for registration {registration}',
                'error_type': 'vehicle_not_found',
                'method': 'vnc_automation'
            }), 404
            
    except Exception as e:
        logger.error(f"VNC primary API error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'VNC primary service error',
            'error_type': 'service_error'
        }), 500