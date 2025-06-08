#!/usr/bin/env python3
"""
Main Flask application for Vehicle Data Scraper
Provides web interface for scraping vehicle data from checkcardetails.co.uk
"""

from flask import Flask, render_template, request, jsonify, send_file
import json
import csv
import io
import os
from datetime import datetime
from enhanced_scraper import EnhancedVehicleScraper
from test_data_service import get_sample_vehicle_data
from utils import validate_registration, sanitize_filename
from models import db, VehicleData, SearchHistory
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"

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
            
            # Initialize scraper and extract data
            scraper = EnhancedVehicleScraper()
            vehicle_data = scraper.scrape_vehicle_data(registration)
            
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
    
    # Extract basic info
    basic_info = vehicle_data.get('basic_info', {})
    if basic_info.get('title'):
        title_parts = basic_info['title'].split()
        if len(title_parts) >= 2:
            vehicle_record.make = title_parts[0]
            vehicle_record.model = ' '.join(title_parts[1:])
    
    # Extract vehicle details
    details = vehicle_data.get('vehicle_details', {})
    vehicle_record.variant = details.get('model_variant') or details.get('variant')
    vehicle_record.description = details.get('description')
    vehicle_record.color = details.get('primary_colour') or details.get('color')
    vehicle_record.fuel_type = details.get('fuel_type')
    vehicle_record.transmission = details.get('transmission')
    vehicle_record.engine_size = details.get('engine')
    vehicle_record.body_style = details.get('body_style')
    vehicle_record.euro_status = details.get('euro_status')
    vehicle_record.type_approval = details.get('type_approval')
    vehicle_record.wheel_plan = details.get('wheel_plan')
    vehicle_record.vehicle_age = details.get('vehicle_age')
    vehicle_record.registration_place = details.get('registration_place')
    
    # Parse year
    if details.get('year_manufacture'):
        try:
            vehicle_record.year = int(details['year_manufacture'])
        except (ValueError, TypeError):
            pass
    
    # Parse dates
    if details.get('registration_date'):
        try:
            date_str = details['registration_date']
            for fmt in ['%d/%m/%Y', '%d %B %Y', '%Y-%m-%d']:
                try:
                    vehicle_record.registration_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
        except:
            pass
    
    # Extract tax and MOT info
    tax_mot = vehicle_data.get('tax_mot', {})
    if tax_mot.get('tax_expiry'):
        try:
            date_str = tax_mot['tax_expiry']
            for fmt in ['%d %B %Y', '%d/%m/%Y', '%Y-%m-%d']:
                try:
                    vehicle_record.tax_expiry = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
        except:
            pass
    
    if tax_mot.get('mot_expiry'):
        try:
            date_str = tax_mot['mot_expiry']
            for fmt in ['%d %B %Y', '%d/%m/%Y', '%Y-%m-%d']:
                try:
                    vehicle_record.mot_expiry = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
        except:
            pass
    
    # Parse days left
    if tax_mot.get('tax_days_left'):
        try:
            vehicle_record.tax_days_left = int(tax_mot['tax_days_left'])
        except (ValueError, TypeError):
            pass
    
    if tax_mot.get('mot_days_left'):
        try:
            vehicle_record.mot_days_left = int(tax_mot['mot_days_left'])
        except (ValueError, TypeError):
            pass
    
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
