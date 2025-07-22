"""
Intelligent Vehicle Analysis API
Provides OpenAI GPT-4o powered vehicle analysis endpoints
"""

from flask import Blueprint, request, jsonify, render_template
from datetime import datetime
import logging
from vehicle_analyzer import analyze_vehicle_data, format_analysis_for_display
from models import VehicleData, db

# Create blueprint for intelligent analysis
intelligent_api = Blueprint('intelligent_analysis', __name__)

@intelligent_api.route('/api/intelligent-analysis', methods=['POST'])
def intelligent_vehicle_analysis():
    """
    Perform intelligent analysis on vehicle data using OpenAI GPT-4o
    """
    try:
        data = request.get_json()
        registration = data.get('registration', '').upper().strip()
        
        if not registration:
            return jsonify({
                'success': False,
                'error': 'Registration number is required'
            }), 400
        
        logging.info(f"Starting intelligent analysis for registration: {registration}")
        
        # Get vehicle data from database
        vehicle_record = VehicleData.query.filter_by(registration=registration).first()
        
        if not vehicle_record:
            return jsonify({
                'success': False,
                'error': f'No vehicle data found for {registration}. Please scrape the vehicle data first.'
            }), 404
        
        # Extract complete data from raw_data field (contains all scraped MOT/mileage data)
        raw_data = vehicle_record.raw_data or {}
        
        # Convert database record to analysis format with complete scraped data
        vehicle_data = {
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
            # Use complete scraped data from raw_data field
            'mot_history': raw_data.get('mot_history', {}),
            'mileage_history': raw_data.get('mileage_history', {}),
            # Include all additional scraped information
            'basic_info': raw_data.get('basic_info', {}),
            'vehicle_details': raw_data.get('vehicle_details', {}),
            'summary': raw_data.get('summary', {})
        }
        
        logging.info(f"Performing OpenAI analysis for {registration}")
        
        # Perform OpenAI analysis
        analysis_result = analyze_vehicle_data(vehicle_data)
        
        # Format for display
        formatted_result = format_analysis_for_display(analysis_result)
        
        if not formatted_result['success']:
            return jsonify({
                'success': False,
                'error': formatted_result['error']
            }), 500
        
        # Store analysis timestamp in database
        vehicle_record.last_analyzed = datetime.utcnow()
        db.session.commit()
        
        logging.info(f"Successfully completed intelligent analysis for {registration}")
        
        return jsonify({
            'success': True,
            'registration': registration,
            'vehicle_data': vehicle_data,
            'analysis': formatted_result['display_data'],
            'raw_analysis': formatted_result['raw_analysis'],
            'analyzed_at': analysis_result.get('analysis_metadata', {}).get('analyzed_at')
        })
        
    except Exception as e:
        logging.error(f"Error in intelligent analysis: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        }), 500


@intelligent_api.route('/api/analyze/<registration>')
def analyze_vehicle_by_registration(registration):
    """
    GET endpoint for vehicle analysis by registration
    """
    try:
        registration = registration.upper().strip()
        
        # Get vehicle data from database
        vehicle_record = VehicleData.query.filter_by(registration=registration).first()
        
        if not vehicle_record:
            return jsonify({
                'success': False,
                'error': f'No vehicle data found for {registration}. Please scrape the vehicle data first.',
                'suggestion': f'Use /api/scrape with registration {registration} first'
            }), 404
        
        # Extract complete data from raw_data field (contains all scraped MOT/mileage data)
        raw_data = vehicle_record.raw_data or {}
        
        # Debug logging to verify data extraction
        logging.info(f"Raw data keys for {registration}: {list(raw_data.keys())}")
        if 'mot_history' in raw_data:
            mot_tests_count = len(raw_data['mot_history'].get('mot_tests', []))
            logging.info(f"Found {mot_tests_count} MOT tests in raw_data for {registration}")
        
        # Convert to analysis format with complete scraped data
        vehicle_data = {
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
            # Use complete scraped data from raw_data field
            'mot_history': raw_data.get('mot_history', {}),
            'mileage_history': raw_data.get('mileage_history', {}),
            # Include all additional scraped information
            'basic_info': raw_data.get('basic_info', {}),
            'vehicle_details': raw_data.get('vehicle_details', {}),
            'summary': raw_data.get('summary', {})
        }
        
        # Perform analysis
        analysis_result = analyze_vehicle_data(vehicle_data)
        formatted_result = format_analysis_for_display(analysis_result)
        
        if not formatted_result['success']:
            return jsonify({
                'success': False,
                'error': formatted_result['error']
            }), 500
        
        # Update analysis timestamp
        vehicle_record.last_analyzed = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'registration': registration,
            'analysis': formatted_result['display_data'],
            'raw_analysis': formatted_result['raw_analysis']
        })
        
    except Exception as e:
        logging.error(f"Error in vehicle analysis: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        }), 500


@intelligent_api.route('/analysis/<registration>')
def vehicle_analysis_page(registration):
    """
    Web page for vehicle analysis display
    """
    try:
        registration = registration.upper().strip()
        
        # Get vehicle data from database
        vehicle_record = VehicleData.query.filter_by(registration=registration).first()
        
        if not vehicle_record:
            return render_template('error.html', 
                                 error=f'No vehicle data found for {registration}',
                                 suggestion=f'Please search for {registration} first to gather vehicle data.')
        
        return render_template('analysis.html', 
                             registration=registration,
                             vehicle_data=vehicle_record)
        
    except Exception as e:
        logging.error(f"Error loading analysis page: {str(e)}")
        return render_template('error.html', 
                             error='Failed to load analysis page',
                             suggestion='Please try again or contact support.')


@intelligent_api.route('/api/scrape-and-analyze', methods=['POST'])
def scrape_and_analyze():
    """
    Combined endpoint: scrape vehicle data then perform intelligent analysis
    """
    try:
        data = request.get_json()
        registration = data.get('registration', '').upper().strip()
        
        if not registration:
            return jsonify({
                'success': False,
                'error': 'Registration number is required'
            }), 400
        
        logging.info(f"Starting scrape and analyze for registration: {registration}")
        
        # First, import and use the scraper
        from enhanced_mot_scraper import EnhancedMOTScraper
        
        # Scrape the vehicle data
        logging.info(f"Scraping data for {registration}")
        scraper = EnhancedMOTScraper()
        scrape_result = scraper.scrape_comprehensive_vehicle_data(registration)
        
        if not scrape_result.get('success', False):
            return jsonify({
                'success': False,
                'error': f'Failed to scrape data for {registration}: {scrape_result.get("error", "Unknown error")}',
                'scrape_result': scrape_result
            }), 500
        
        # Get the scraped data from database
        vehicle_record = VehicleData.query.filter_by(registration=registration).first()
        
        if not vehicle_record:
            return jsonify({
                'success': False,
                'error': f'Vehicle data was scraped but not found in database for {registration}'
            }), 500
        
        # Convert to analysis format
        vehicle_data = {
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
            'mot_history': vehicle_record.mot_history or {},
            'mileage_history': vehicle_record.mileage_history or {}
        }
        
        # Perform intelligent analysis
        logging.info(f"Analyzing scraped data for {registration}")
        analysis_result = analyze_vehicle_data(vehicle_data)
        formatted_result = format_analysis_for_display(analysis_result)
        
        if not formatted_result['success']:
            return jsonify({
                'success': False,
                'error': formatted_result['error'],
                'scrape_success': True,
                'scraped_data': vehicle_data
            }), 500
        
        # Update analysis timestamp
        vehicle_record.last_analyzed = datetime.utcnow()
        db.session.commit()
        
        logging.info(f"Successfully completed scrape and analyze for {registration}")
        
        return jsonify({
            'success': True,
            'registration': registration,
            'scrape_result': scrape_result,
            'vehicle_data': vehicle_data,
            'analysis': formatted_result['display_data'],
            'raw_analysis': formatted_result['raw_analysis'],
            'analyzed_at': analysis_result.get('analysis_metadata', {}).get('analyzed_at')
        })
        
    except Exception as e:
        logging.error(f"Error in scrape and analyze: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Scrape and analyze failed: {str(e)}'
        }), 500