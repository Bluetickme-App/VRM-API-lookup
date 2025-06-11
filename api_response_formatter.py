"""
Unified API response formatter for vehicle data
Ensures consistent comprehensive data structure across all endpoints
"""

from datetime import datetime

def format_complete_vehicle_response(vehicle_data, source='api', scraped_at=None):
    """
    Format vehicle data into comprehensive API response structure
    Used by all API endpoints to ensure consistency
    """
    if not vehicle_data:
        return None
    
    # Extract data sections
    basic_info = vehicle_data.get('basic_info', {})
    tax_mot = vehicle_data.get('tax_mot', {})
    vehicle_details = vehicle_data.get('vehicle_details', {})
    additional = vehicle_data.get('additional', {})
    
    # Create comprehensive response
    formatted_response = {
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
            'co2_emissions': additional.get('co2_emissions'),
            'tax_12_months': additional.get('tax_12_months'),
            'tax_6_months': additional.get('tax_6_months'),
            'total_keepers': additional.get('total_keepers')
        },
        'mileage': {
            'last_mot_mileage': additional.get('last_mot_mileage'),
            'average': additional.get('average_mileage'),
            'status': additional.get('mileage_status')
        }
    }
    
    return formatted_response

def format_database_vehicle_response(vehicle_record):
    """
    Format database vehicle record into comprehensive API response
    """
    formatted_response = {
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
            'tax_6_months': vehicle_record.tax_6_months,
            'total_keepers': vehicle_record.total_keepers
        },
        'mileage': {
            'last_mot_mileage': vehicle_record.last_mot_mileage,
            'average': vehicle_record.average_mileage,
            'status': vehicle_record.mileage_status
        }
    }
    
    return formatted_response