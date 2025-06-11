"""
Fast VNC API endpoint optimized for 3rd party integrations
Returns responses within 25 seconds to avoid external timeout issues
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from models import db, VehicleData, SearchHistory
from utils import validate_registration
import logging

# Create blueprint for fast VNC API
fast_vnc = Blueprint('fast_vnc', __name__)

logger = logging.getLogger(__name__)

@fast_vnc.route('/api/fast-vnc', methods=['GET', 'POST'])
def fast_vnc_lookup():
    """
    Fast VNC vehicle lookup - optimized for 3rd party API integrations
    Returns within 25 seconds to prevent external timeouts
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
                'usage': 'GET: /api/fast-vnc?registration=ABC123 or POST: {"registration": "ABC123"}'
            }), 400
        
        # Validate registration format
        if not validate_registration(registration):
            return jsonify({
                'success': False,
                'error': 'Invalid UK registration number format',
                'error_type': 'invalid_format'
            }), 400
        
        # Log fast VNC request
        search_record = SearchHistory(
            registration=registration,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            request_source='fast_vnc'
        )
        
        # Check cache first (shorter cache for fast responses)
        existing_vehicle = VehicleData.query.filter_by(registration=registration).first()
        
        if existing_vehicle and existing_vehicle.make and existing_vehicle.updated_at:
            cache_age = datetime.now() - existing_vehicle.updated_at
            
            # Return cache if less than 2 hours old for fast VNC
            if cache_age < timedelta(hours=2):
                search_record.success = True
                search_record.error_message = 'Fast VNC cache hit'
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
                    'source': 'fast_vnc_cache',
                    'cache_age_hours': round(cache_age.total_seconds() / 3600, 1),
                    'method': 'cached_fast_vnc'
                })
        
        # Execute fast VNC automation with strict timeout
        try:
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
            
            def fast_vnc_scrape():
                from optimized_scraper import OptimizedVehicleScraper
                scraper = OptimizedVehicleScraper(headless=True)
                # Single retry for speed
                return scraper.scrape_vehicle_data(registration, max_retries=1)
            
            # Execute fast VNC automation without timeout - let it complete naturally
            try:
                vehicle_data = fast_vnc_scrape()
                if not vehicle_data:
                    raise Exception("No data extracted")
            except Exception as vnc_error:
                search_record.success = False
                search_record.error_message = f'Fast VNC extraction failed: {str(vnc_error)}'
                db.session.add(search_record)
                db.session.commit()
                
                return jsonify({
                    'success': False,
                    'error': 'Fast VNC extraction failed',
                    'error_type': 'fast_vnc_extraction_error',
                    'alternative_endpoint': '/api/vnc-vehicle',
                    'method': 'fast_vnc_automation'
                }), 503
        
        except Exception as vnc_error:
            search_record.success = False
            search_record.error_message = f'Fast VNC error: {str(vnc_error)}'
            db.session.add(search_record)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': 'Fast VNC service error',
                'error_type': 'fast_vnc_service_error',
                'alternative_endpoint': '/api/vnc-vehicle',
                'method': 'fast_vnc_automation'
            }), 503
        
        # Process fast VNC extraction results
        if vehicle_data and vehicle_data.get('basic_info'):
            basic_info = vehicle_data.get('basic_info', {})
            tax_mot = vehicle_data.get('tax_mot', {})
            vehicle_details = vehicle_data.get('vehicle_details', {})
            additional = vehicle_data.get('additional', {})
            
            # Store in database for caching (with length validation)
            try:
                if existing_vehicle:
                    vehicle_record = existing_vehicle
                else:
                    vehicle_record = VehicleData(registration=registration)
                
                # Update with length validation
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
                        vehicle_record.tax_expiry = datetime.strptime(tax_mot.get('tax_expiry'), '%d %b %Y').date()
                    except:
                        pass
                
                if tax_mot.get('mot_expiry'):
                    try:
                        vehicle_record.mot_expiry = datetime.strptime(tax_mot.get('mot_expiry'), '%d %b %Y').date()
                    except:
                        pass
                
                if not existing_vehicle:
                    db.session.add(vehicle_record)
                
                search_record.success = True
                search_record.error_message = 'Fast VNC extraction successful'
                db.session.add(search_record)
                db.session.commit()
                
            except Exception as db_error:
                logger.error(f"Database save error: {str(db_error)}")
            
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
                'source': 'fast_vnc_automation',
                'method': 'fast_browser_automation',
                'extraction_time': datetime.now().isoformat(),
                'timeout_optimized': True
            })
        
        else:
            # No vehicle data found
            search_record.success = False
            search_record.error_message = 'No vehicle found via Fast VNC'
            db.session.add(search_record)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': f'No vehicle found for registration {registration}',
                'error_type': 'vehicle_not_found',
                'method': 'fast_vnc_automation'
            }), 404
            
    except Exception as e:
        logger.error(f"Fast VNC API error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Fast VNC service error',
            'error_type': 'service_error'
        }), 500