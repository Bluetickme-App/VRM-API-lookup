"""
Configuration settings for the vehicle scraper
"""

SCRAPER_CONFIG = {
    'base_url': 'https://www.checkcardetails.co.uk/',
    'timeout': 10,  # Selenium wait timeout in seconds
    'retry_attempts': 3,
    'delay_between_requests': 1,  # Delay in seconds
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# CSS selectors for different elements
SELECTORS = {
    'search_input': '#vrm',
    'search_button': 'button[type="submit"], input[type="submit"]',
    'vehicle_title': 'h1, h2, .vehicle-title, .car-title',
    'vehicle_details_table': 'table, .vehicle-details table',
    'tax_section': '*[contains(text(), "TAX")]',
    'mot_section': '*[contains(text(), "MOT")]',
    'mileage_section': '*[contains(text(), "Mileage")]',
}

# Data field mappings for normalization
FIELD_MAPPINGS = {
    'model_variant': 'model',
    'primary_colour': 'color',
    'fuel_type': 'fuel',
    'year_manufacture': 'year',
    'body_style': 'body_type',
    'registration_date': 'reg_date',
    'last_v5c_issue_date': 'v5c_date',
    'last_mot_mileage': 'mileage',
    'mileage_issues': 'mileage_problems'
}
