# Vehicle Data API Documentation

## Overview
Comprehensive UK vehicle data extraction API that provides real-time vehicle information from DVLA sources. The API uses intelligent caching with automatic fallback to VNC browser automation for maximum reliability.

## Base URL
- **Production**: `https://vrnapi.replit.app`
- **Development**: `http://localhost:5000`

## Authentication
No authentication required for public endpoints.

---

## Endpoints

### 1. Vehicle Data Lookup (Recommended)
**Endpoint**: `POST /api/vehicle-data`  
**Purpose**: Primary endpoint for vehicle data retrieval with intelligent caching

#### Request
```json
{
  "registration": "WV08XVZ"
}
```

#### Response Flow
1. **Cache Check**: Returns cached data if available (< 24 hours old)
2. **Fast Scraping**: Attempts high-speed web scraping
3. **VNC Automation**: Fallback to browser automation if scraping blocked
4. **Database Storage**: Stores results for future cache hits

#### Success Response (200 OK)
```json
{
  "success": true,
  "data": {
    "registration": "WV08XVZ",
    "make": "ALFA ROMEO",
    "model": "159",
    "description": "159 Lusso JTDM 20v Auto",
    "color": "Black",
    "fuel_type": "DIESEL",
    "transmission": "Auto 6 Gears",
    "engine_size": "2387 cc",
    "body_style": "Saloon",
    "year": 2008,
    "tax_expiry": "2025-05-28",
    "mot_expiry": "2025-10-16",
    "tax_days_left": -14,
    "mot_days_left": 128,
    "total_keepers": 8,
    "mileage_info": {
      "last_mot_mileage": 89234,
      "average_mileage": 5249,
      "mileage_status": "Normal"
    },
    "performance": {
      "power_bhp": "150",
      "max_speed_mph": "129",
      "torque_ftlb": "236"
    },
    "fuel_economy": {
      "urban_mpg": "32.1",
      "extra_urban_mpg": "54.3",
      "combined_mpg": "42.8"
    },
    "safety_ratings": {
      "adult_safety_rating": "5",
      "child_safety_rating": "4",
      "pedestrian_safety_rating": "3"
    },
    "additional_info": {
      "co2_emissions": "174g/km",
      "tax_12_months": "£415",
      "tax_6_months": "£228",
      "euro_status": "4",
      "type_approval": "M1"
    }
  },
  "source": "live_scraping",
  "scraped_at": "2025-06-11T06:15:00Z",
  "cache_expires": "2025-06-12T06:15:00Z"
}
```

#### Error Responses

**Vehicle Not Found (404)**
```json
{
  "success": false,
  "error": "No vehicle found for registration WV08XVZ",
  "error_type": "vehicle_not_found"
}
```

**Invalid Registration (400)**
```json
{
  "success": false,
  "error": "Invalid registration number format",
  "error_type": "invalid_format"
}
```

**Timeout Error (408)**
```json
{
  "success": false,
  "error": "Request timeout - scraping took too long. Please try again later.",
  "error_type": "timeout"
}
```

**Service Unavailable (503)**
```json
{
  "success": false,
  "error": "Scraping service temporarily unavailable",
  "error_type": "service_error"
}
```

---

### 2. Fast Cache Lookup
**Endpoint**: `GET /api/vehicle/{registration}`  
**Purpose**: Instant cached data retrieval (sub-second response)

#### Request
```
GET /api/vehicle/WV08XVZ
```

#### Success Response (200 OK)
```json
{
  "success": true,
  "vehicle": {
    "registration": "WV08XVZ",
    "make": "ALFA ROMEO",
    "model": "159",
    "description": "159 Lusso JTDM 20v Auto",
    "color": "Black",
    "fuel_type": "DIESEL",
    "transmission": "Auto 6 Gears",
    "engine_size": "2387 cc",
    "tax_expiry": "2025-05-28",
    "mot_expiry": "2025-10-16",
    "total_keepers": 8,
    "created_at": "2025-06-11T05:39:27.676603",
    "updated_at": "2025-06-11T05:39:27.675775"
  }
}
```

#### Error Response (404)
```json
{
  "success": false,
  "error": "Vehicle not found in database"
}
```

---

### 3. VNC Browser Automation (Premium)
**Endpoint**: `POST /api/scrape-vnc`  
**Purpose**: Direct VNC browser automation for maximum reliability

#### Request
```json
{
  "registration": "WV08XVZ"
}
```

#### Success Response (200 OK)
```json
{
  "success": true,
  "data": {
    // Complete vehicle data structure
  },
  "extraction_method": "vnc_automation",
  "processing_time": "23.4s",
  "screenshots_available": true
}
```

---

## Integration Strategy for Third-Party Developers

### Recommended Implementation Flow

```python
import requests
import time

class VehicleDataClient:
    def __init__(self, base_url="https://vrnapi.replit.app"):
        self.base_url = base_url
    
    def get_vehicle_data(self, registration):
        """
        Get vehicle data with intelligent fallback strategy
        """
        registration = registration.upper().replace(' ', '')
        
        # Step 1: Try fast cache lookup first
        cache_response = self._try_cache_lookup(registration)
        if cache_response:
            return cache_response
        
        # Step 2: Use primary endpoint with automatic VNC fallback
        return self._get_live_data(registration)
    
    def _try_cache_lookup(self, registration):
        """Fast cache check (< 1 second)"""
        try:
            response = requests.get(
                f"{self.base_url}/api/vehicle/{registration}",
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'data': data['vehicle'],
                    'source': 'cache',
                    'response_time': '< 1s'
                }
        except:
            pass
        return None
    
    def _get_live_data(self, registration):
        """Live scraping with VNC fallback (15-60 seconds)"""
        try:
            response = requests.post(
                f"{self.base_url}/api/vehicle-data",
                json={'registration': registration},
                timeout=60
            )
            return response.json()
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Request timeout',
                'error_type': 'timeout'
            }

# Usage Example
client = VehicleDataClient()
result = client.get_vehicle_data("WV08XVZ")

if result['success']:
    vehicle = result['data']
    print(f"Make: {vehicle['make']}")
    print(f"Model: {vehicle['model']}")
    print(f"TAX Expiry: {vehicle['tax_expiry']}")
    print(f"MOT Expiry: {vehicle['mot_expiry']}")
else:
    print(f"Error: {result['error']}")
```

---

## Response Times & Caching Strategy

| Endpoint | Cache Hit | Cache Miss | VNC Fallback |
|----------|-----------|------------|--------------|
| `/api/vehicle/{reg}` | < 1s | N/A | N/A |
| `/api/vehicle-data` | < 1s | 5-15s | 15-60s |
| `/api/scrape-vnc` | N/A | N/A | 20-60s |

### Cache Behavior
- **Cache Duration**: 24 hours for complete records
- **Cache Keys**: Normalized registration numbers (uppercase, no spaces)
- **Cache Invalidation**: Automatic after 24 hours or manual refresh
- **Partial Cache**: Incomplete records trigger live scraping

---

## Rate Limits & Best Practices

### Rate Limits
- **Fast Cache**: 1000 requests/minute
- **Live Scraping**: 30 requests/minute
- **VNC Automation**: 10 requests/minute

### Best Practices

1. **Always try cache first** for fastest response
2. **Batch requests** when possible to respect rate limits
3. **Handle timeouts gracefully** with retry logic
4. **Store results locally** to minimize API calls
5. **Use exponential backoff** for failed requests

### Error Handling Example
```python
def robust_vehicle_lookup(registration, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = client.get_vehicle_data(registration)
            if result['success']:
                return result
            
            # Handle specific error types
            error_type = result.get('error_type')
            if error_type == 'vehicle_not_found':
                return result  # Don't retry for invalid registrations
            elif error_type == 'timeout':
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
    
    return {'success': False, 'error': 'Max retries exceeded'}
```

---

## Data Fields Reference

### Core Vehicle Information
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `registration` | string | UK registration number | "WV08XVZ" |
| `make` | string | Vehicle manufacturer | "ALFA ROMEO" |
| `model` | string | Vehicle model | "159" |
| `description` | string | Full model description | "159 Lusso JTDM 20v Auto" |
| `color` | string | Vehicle color | "Black" |
| `fuel_type` | string | Fuel type | "DIESEL" |
| `transmission` | string | Transmission type | "Auto 6 Gears" |
| `engine_size` | string | Engine capacity | "2387 cc" |
| `body_style` | string | Body style | "Saloon" |
| `year` | integer | Manufacture year | 2008 |

### Tax & MOT Information
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `tax_expiry` | string (ISO date) | Tax expiry date | "2025-05-28" |
| `mot_expiry` | string (ISO date) | MOT expiry date | "2025-10-16" |
| `tax_days_left` | integer | Days until tax expires (negative if expired) | -14 |
| `mot_days_left` | integer | Days until MOT expires | 128 |

### Ownership & History
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `total_keepers` | integer | Total number of registered keepers | 8 |
| `registration_date` | string (ISO date) | First registration date | "2008-09-01" |
| `last_v5c_issue_date` | string (ISO date) | Last V5C issue date | "2023-03-15" |

---

## Webhook Support (Coming Soon)

Register webhooks to receive real-time updates when vehicle data changes:

```json
{
  "webhook_url": "https://your-app.com/webhook",
  "events": ["tax_expiry", "mot_expiry", "ownership_change"],
  "registrations": ["WV08XVZ", "AB12CDE"]
}
```

---

## Support & Contact

- **API Status**: Check service status at status page
- **Documentation**: This document (updated regularly)
- **Rate Limit Issues**: Contact support for higher limits
- **Custom Integration**: Available for enterprise clients

---

## Changelog

### v2.1.0 (2025-06-11)
- Added intelligent caching with 24-hour TTL
- Implemented VNC automation fallback
- Enhanced error handling and timeout management
- Added comprehensive vehicle data fields
- Improved response times (< 1s for cached data)

### v2.0.0 (2025-06-10)
- Major rewrite with FastAPI scraper
- Database caching implementation
- Multi-source data validation
- Production deployment on Replit

---

*This API provides comprehensive UK vehicle data extraction with intelligent caching and VNC automation fallback for maximum reliability and performance.*