"""
Test data service to demonstrate the vehicle scraper functionality
This provides sample data structure that matches what would be scraped from checkcardetails.co.uk
"""

def get_sample_vehicle_data(registration):
    """Return sample vehicle data for testing purposes"""
    
    # Sample data based on the LP68OHB example you provided
    if registration.upper() == "LP68OHB":
        return {
            'registration': registration.upper(),
            'basic_info': {
                'title': 'JEEP COMPASS',
                'image_url': 'https://vehicleimages.ukvehicledata.co.uk/...'
            },
            'tax_mot': {
                'tax_expiry': '01 Jul 2025',
                'tax_days_left': '23',
                'mot_expiry': '13 May 2026',
                'mot_days_left': '340'
            },
            'vehicle_details': {
                'model_variant': 'Compass',
                'description': 'Compass Limited Edition MultiAir II 4x2',
                'primary_colour': 'Silver',
                'fuel_type': 'PETROL',
                'transmission': 'Manual 6 Gears',
                'engine': '1368 cc',
                'body_style': 'Suv',
                'year_manufacture': '2018',
                'euro_status': '6c',
                'vehicle_age': '6 years 6 months',
                'registration_place': 'Stanmore / London',
                'registration_date': '12/12/2018',
                'last_v5c_issue_date': '30 July 2024',
                'type_approval': 'M1',
                'wheel_plan': '2 Axle Rigid Body'
            },
            'mileage': {
                'last_mot_mileage': '33608',
                'mileage_issues': 'No',
                'average': '4801',
                'status': 'LOW'
            },
            'performance': {
                'power': '138 BHP',
                'max_speed': '119 MPH',
                'torque': '170 FtLb'
            },
            'fuel_economy': {
                'urban': '36.2 MPG',
                'extra_urban': '54.3 MPG',
                'combined': '36.7 MPG'
            },
            'safety': {
                'child': '83%',
                'adult': '90%',
                'pedestrian': '64%'
            },
            'additional': {
                'co2_emissions': '155 g/km',
                'tax_12_months': '£195',
                'tax_6_months': '£107.25',
                'total_keepers': '2',
                'v5c_certificate_count': '2'
            }
        }
    
    # Generic sample data for other registrations
    return {
        'registration': registration.upper(),
        'basic_info': {
            'title': f'Sample Vehicle {registration.upper()}',
            'image_url': ''
        },
        'tax_mot': {
            'tax_expiry': '01 Jan 2025',
            'tax_days_left': '100',
            'mot_expiry': '01 Jan 2025',
            'mot_days_left': '100'
        },
        'vehicle_details': {
            'model_variant': 'Sample Model',
            'description': 'Sample Description',
            'primary_colour': 'White',
            'fuel_type': 'PETROL',
            'transmission': 'Manual',
            'engine': '1600 cc',
            'body_style': 'Hatchback',
            'year_manufacture': '2020',
            'euro_status': '6',
            'vehicle_age': '4 years',
            'registration_place': 'London',
            'registration_date': '01/01/2020',
            'type_approval': 'M1'
        },
        'mileage': {
            'last_mot_mileage': '25000',
            'mileage_issues': 'No',
            'average': '12500',
            'status': 'NORMAL'
        },
        'performance': {
            'power': '120 BHP',
            'max_speed': '110 MPH',
            'torque': '150 FtLb'
        },
        'fuel_economy': {
            'urban': '35 MPG',
            'extra_urban': '50 MPG',
            'combined': '40 MPG'
        },
        'safety': {
            'child': '85%',
            'adult': '90%',
            'pedestrian': '70%'
        },
        'additional': {
            'co2_emissions': '140 g/km',
            'tax_12_months': '£165',
            'tax_6_months': '£90.75',
            'total_keepers': '1',
            'v5c_certificate_count': '1'
        }
    }