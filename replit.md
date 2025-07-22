# Vehicle Data Scraper - VRN API

## Overview
This is a comprehensive UK vehicle data extraction API that provides real-time vehicle information from DVLA sources. The application combines multiple scraping strategies with intelligent caching and VNC browser automation for maximum reliability.

## User Preferences
Preferred communication style: Simple, everyday language.
Data extraction: Use enhanced scraper exclusively, no fast scraper.
Data quality: All vehicles have complete MOT and mileage history from DVLA sources - no missing data cases.

## Recent Changes
**July 22, 2025 - Complete OpenAI GPT-4o Assistant API with Authentic DVLA Data Integration:**
- Full intelligent vehicle analysis system using OpenAI GPT-4o for comprehensive vehicle assessment
- CRITICAL FIX: Complete MOT defect data extraction from PostgreSQL raw_data field to ChatGPT analysis
- Authentic DVLA MOT analysis working: RE13CEO shows 40% failure risk with brake disc and tyre advisories
- Real defect analysis: "brake disc worn, pitted", "tyre tread depth 2.5mm" directly fed to AI analysis
- Mechanical grading with authentic data: RE13CEO Grade C (moderate risk), DA07BWF Grade C (recurring brake/suspension)
- Trade recommendations based on real defects: Caution with CAP Average pricing for authentic conditions
- Cost estimates from actual defect patterns: £400-800 immediate repairs, £1,300-2,600 total first year
- Data flow fixed: PostgreSQL raw_data → vehicle_analyzer.py → OpenAI GPT-4o → detailed predictions
- Comprehensive MOT test history: 5 tests for RE13CEO, 4 tests for DA07BWF with complete defect details
- Production system confirmed: Authentic Data ✓ Complete Analysis ✓ Real Predictions ✓ Accurate Costs ✓

**July 22, 2025 - PostgreSQL Database Successfully Configured:**
- PostgreSQL database created and fully configured with all required environment variables
- Database tables successfully created with proper schema:
  - `vehicle_data` - Main table for comprehensive vehicle information with 45+ fields
  - `search_history` - Request tracking and analytics
  - `mot_history` - MOT test history with foreign key relationships
- Database connectivity verified with test operations (insert/select/delete)
- JSON field support enabled for flexible raw data storage
- All SQLAlchemy models properly mapped to database tables
- Database caching system ready for 24-hour data retention strategy

**July 22, 2025 - Enhanced Selenium Scraper with MOT and Mileage History:**
- Created new `enhanced_selenium_scraper.py` with comprehensive MOT and mileage history extraction
- Enhanced scraper now navigates to specific MOT history and mileage history pages
- Added robust table parsing and fallback text extraction methods
- Integrated enhanced scraper into VNC API endpoints (`/api/vnc-vehicle` and `/api/fast-vnc`)
- Scraper extracts comprehensive vehicle data including:
  - Basic vehicle information (make, model, year, color, fuel type)
  - MOT test history with dates, results, and mileage readings
  - Mileage history with timeline analysis
  - Summary statistics and trend analysis
- Enhanced error handling and natural human-like browsing behavior
- All API endpoints now provide complete vehicle history data using Selenium automation

## System Architecture
The system uses a **multi-layered scraping approach** with automatic fallback mechanisms:
1. **Fast API Scraping** - Primary lightweight scraping for quick responses
2. **Enhanced Scraping** - BeautifulSoup-based extraction for better reliability  
3. **VNC Browser Automation** - Selenium WebDriver fallback for maximum success rates
4. **Intelligent Caching** - PostgreSQL database with 24-hour cache expiration

The architecture is designed to handle high-volume API requests while maintaining data accuracy and avoiding rate limiting.

## Key Components

### Backend Framework
- **Flask** - Main web application framework
- **SQLAlchemy/Drizzle** - Database ORM for PostgreSQL
- **Flask-CORS** - Cross-origin resource sharing for API access
- **Blueprint routing** - Modular API endpoint organization

### Web Scraping Stack
- **Selenium WebDriver** - Browser automation with Firefox
- **BeautifulSoup** - HTML parsing and data extraction
- **Requests** - HTTP client for direct web requests
- **WebDriver Manager** - Automatic browser driver management

### Database Schema
- **VehicleData** - Main table storing comprehensive vehicle information
- **SearchHistory** - Request logging and analytics
- **JSON field support** - Flexible data storage for complex structures

### API Endpoints
- `/api/vehicle-data` - Primary vehicle lookup with caching
- `/api/quick-vehicle` - Fast response endpoint
- `/api/vnc-vehicle` - VNC browser automation endpoint
- `/api/fast-vnc` - Optimized VNC for external integrations

## Data Flow

1. **Request Processing**
   - API request received with vehicle registration
   - Registration format validation
   - Search history logging

2. **Cache Check**
   - Database lookup for existing data (< 24 hours)
   - Return cached data if available
   - Proceed to scraping if cache miss

3. **Scraping Strategy**
   - **Level 1**: Fast API scraper (requests + BeautifulSoup)
   - **Level 2**: Enhanced scraper with retry logic
   - **Level 3**: VNC browser automation (Selenium)

4. **Data Processing**
   - Extract comprehensive vehicle information
   - Format response using unified API formatter
   - Store results in database for future caching

5. **Response Delivery**
   - Return formatted JSON response
   - Include metadata (source, timestamp, cache status)

## External Dependencies

### Core Libraries
- **Flask** - Web framework
- **SQLAlchemy** - Database ORM
- **Selenium** - Browser automation
- **BeautifulSoup4** - HTML parsing
- **Requests** - HTTP client
- **psutil** - Process management

### Browser Infrastructure
- **Firefox** - Primary browser for automation
- **GeckoDriver** - Firefox WebDriver
- **WebDriver Manager** - Automatic driver updates
- **VNC Display** - Remote desktop for browser automation

### Data Source
- **checkcardetails.co.uk** - Primary vehicle data source
- **DVLA integration** - Government vehicle database access

## Deployment Strategy

### Development Environment
- **Local Flask server** - `python main.py`
- **Development database** - Local PostgreSQL instance
- **Debug mode** - Detailed logging and error handling

### Production Environment
- **Replit deployment** - Cloud hosting platform
- **Production WSGI** - `run.py` entry point
- **Environment variables** - Database URLs and secrets
- **Process management** - Keep-alive scripts for reliability

### Key Configuration
- **Timeout handling** - 25-second response limits for external APIs
- **Rate limiting** - Request delays to avoid blocking
- **Error handling** - Graceful fallbacks and retry logic
- **Security** - No-index meta tags, robots.txt blocking

### Monitoring & Maintenance
- **Search history logging** - Track API usage patterns
- **Performance metrics** - Response times and success rates
- **Database cleanup** - Automatic cache expiration
- **Process monitoring** - Automatic restart on failures

The system is designed to be resilient and scalable, with multiple fallback mechanisms ensuring high availability and data accuracy for vehicle information requests.