"""
Utility functions for the vehicle data scraper
"""

import re
import string

def validate_registration(registration):
    """
    Validate UK vehicle registration number format
    Supports various UK registration formats including:
    - Current format: AB12 ABC, AB12ABC
    - Previous formats: A123 ABC, AB12 ABC, etc.
    """
    if not registration:
        return False
    
    # Remove spaces and convert to uppercase
    reg = registration.replace(' ', '').upper()
    
    # Check length (should be between 3 and 8 characters)
    if len(reg) < 3 or len(reg) > 8:
        return False
    
    # Basic pattern matching for UK registration formats
    patterns = [
        r'^[A-Z]{2}[0-9]{2}[A-Z]{3}$',  # Current format: AB12ABC
        r'^[A-Z][0-9]{1,3}[A-Z]{3}$',   # A123ABC
        r'^[A-Z]{2}[0-9]{1,4}[A-Z]{1,2}$',  # AB1234A, AB1234AB
        r'^[A-Z]{3}[0-9]{1,3}[A-Z]$',   # ABC123A
        r'^[0-9]{1,4}[A-Z]{1,3}$',      # 1234ABC
        r'^[A-Z]{1,3}[0-9]{1,4}$',      # ABC1234
    ]
    
    return any(re.match(pattern, reg) for pattern in patterns)

def sanitize_filename(filename):
    """
    Sanitize filename by removing or replacing invalid characters
    """
    # Remove invalid characters
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    filename = ''.join(c for c in filename if c in valid_chars)
    
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Remove multiple consecutive underscores
    filename = re.sub(r'_+', '_', filename)
    
    return filename.strip('_')

def format_registration(registration):
    """
    Format registration number consistently
    """
    if not registration:
        return ""
    
    # Remove spaces and convert to uppercase
    reg = registration.replace(' ', '').upper()
    
    # Add space for current format (AB12ABC -> AB12 ABC)
    if len(reg) == 7 and reg[:2].isalpha() and reg[2:4].isdigit() and reg[4:].isalpha():
        return f"{reg[:4]} {reg[4:]}"
    
    return reg