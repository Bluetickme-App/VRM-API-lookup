"""
Utility functions for the vehicle scraper
"""

import re
import string
from datetime import datetime

def validate_registration(registration):
    """
    Validate UK vehicle registration number format
    Supports various UK formats including current and historical
    """
    if not registration or len(registration.strip()) < 3:
        return False
    
    # Remove spaces and convert to uppercase
    reg = registration.replace(' ', '').upper()
    
    # UK registration patterns
    patterns = [
        r'^[A-Z]{2}[0-9]{2}[A-Z]{3}$',  # Current format: AB12 CDE
        r'^[A-Z][0-9]{1,3}[A-Z]{3}$',   # Prefix format: A123 BCD
        r'^[A-Z]{3}[0-9]{1,3}[A-Z]$',   # Suffix format: ABC 123D
        r'^[0-9]{1,4}[A-Z]{1,3}$',      # Dateless format: 123 AB
        r'^[A-Z]{1,3}[0-9]{1,4}$',      # Early format: AB 1234
    ]
    
    return any(re.match(pattern, reg) for pattern in patterns)

def sanitize_filename(filename):
    """
    Sanitize filename for safe file system usage
    """
    # Remove invalid characters
    valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
    filename = ''.join(c for c in filename if c in valid_chars)
    
    # Remove multiple spaces and trim
    filename = re.sub(r'\s+', '_', filename.strip())
    
    # Limit length
    if len(filename) > 100:
        filename = filename[:100]
    
    return filename

def format_currency(amount_str):
    """
    Format currency strings consistently
    """
    if not amount_str:
        return None
    
    # Extract numbers and currency symbol
    match = re.search(r'[£$€]?(\d+(?:\.\d{2})?)', amount_str)
    if match:
        amount = match.group(1)
        return f"£{amount}"
    
    return amount_str

def parse_date(date_str):
    """
    Parse various date formats to standard format
    """
    if not date_str:
        return None
    
    # Common date patterns
    patterns = [
        r'(\d{1,2})\s+(\w+)\s+(\d{4})',  # 01 Jul 2025
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # 01/07/2025 or 01-07-2025
        r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # 2025/07/01 or 2025-07-01
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_str)
        if match:
            try:
                if len(match.groups()) == 3:
                    day, month, year = match.groups()
                    # Try to parse month name if it's text
                    if month.isalpha():
                        date_obj = datetime.strptime(f"{day} {month} {year}", "%d %B %Y")
                    else:
                        date_obj = datetime.strptime(f"{day}/{month}/{year}", "%d/%m/%Y")
                    return date_obj.strftime("%d %B %Y")
            except ValueError:
                continue
    
    return date_str

def clean_text(text):
    """
    Clean and normalize text content
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\-\.\,\(\)\£\%\/]', '', text)
    
    return text

def extract_numeric_value(text, unit=None):
    """
    Extract numeric value from text, optionally with specific unit
    """
    if not text:
        return None
    
    if unit:
        pattern = rf'(\d+(?:\.\d+)?)\s*{re.escape(unit)}'
    else:
        pattern = r'(\d+(?:\.\d+)?)'
    
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    
    return None

def calculate_vehicle_age(reg_date_str):
    """
    Calculate vehicle age from registration date
    """
    try:
        # Parse the registration date
        reg_date = datetime.strptime(reg_date_str, "%d/%m/%Y")
        today = datetime.now()
        
        # Calculate age
        age_years = today.year - reg_date.year
        age_months = today.month - reg_date.month
        
        if age_months < 0:
            age_years -= 1
            age_months += 12
        
        return f"{age_years} years {age_months} months"
        
    except (ValueError, TypeError):
        return None
