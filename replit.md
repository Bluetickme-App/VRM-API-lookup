# Vehicle Data Scraper - VRN API

## Overview
This project is a comprehensive UK vehicle data extraction API that provides real-time vehicle information from DVLA sources. It combines multiple scraping strategies with intelligent caching and VNC browser automation for maximum reliability. The business vision is to deliver accurate, comprehensive vehicle data for market analysis and consumer insights, aiming for broad market potential in the automotive data sector.

## User Preferences
Preferred communication style: Simple, everyday language.
Data extraction: Use enhanced scraper exclusively, no fast scraper.
Data quality: All vehicles have complete MOT and mileage history from DVLA sources - no missing data cases.
Navigation: Keep interface simple - remove unnecessary dashboard and analysis buttons from navigation.

## System Architecture
The system employs a **multi-layered scraping approach** with automatic fallback mechanisms: Fast API Scraping, BeautifulSoup-based Enhanced Scraping, and Selenium WebDriver VNC Browser Automation. Data is stored in a PostgreSQL database with a 24-hour intelligent caching strategy to handle high-volume API requests, ensure data accuracy, and prevent rate limiting.

**UI/UX Decisions:**
The design emphasizes a clean, corporate aesthetic with a professional color scheme, utilizing white backgrounds, hero sections, and modern gradients. Interface elements like buttons and cards are styled for a contemporary look with proper padding and shadows. Layouts are optimized for wider displays (e.g., 1400px container width) and are fully responsive, incorporating mobile-first design principles with optimized typography and touch-friendly interfaces. Color-coded "traffic light" schemes (green, amber, red) are used for status indicators throughout the application.

**Technical Implementations & Feature Specifications:**
- **Core Data Extraction:** Extracts comprehensive vehicle details (make, model, year, color, fuel, transmission, engine, body, V5C date, registration, total keepers, tax costs).
- **MOT & Mileage History:** Extracts full MOT test histories (up to 16 tests) including dates, results, mileage readings, and detailed defect analysis (major/minor/advisory classifications) with visual distinctions. Automatic mileage history generation from MOT data is supported.
- **Advanced Analysis:** Integrates OpenAI GPT-4o for enhanced MOT failure prediction, component-specific repeat failure likelihood, repair cost estimations, and market analysis (e.g., AutoTrader pricing).
- **Ownership Analysis:** Displays authentic DVLA total keepers and V5C issue dates, with estimated previous owners derived from AI analysis. Includes risk assessment for recent V5C changes.
- **Mileage Anomaly Detection:** Critical mileage rollback detection (>30,000 miles) with severity classifications (CRITICAL, HIGH, MEDIUM) and prominent visual warnings.
- **Recall & Export Status:** Displays outstanding recall and export statuses for vehicles.
- **Sharing Functionality:** Supports sharing vehicle reports via WhatsApp with public link generation.
- **Frontend Interaction:** Features inline analysis display on the main page, dynamic content loading, search history with filtering, and expandable data displays for detailed MOT entries. JavaScript is designed for broad browser compatibility (ES5).

**System Design Choices:**
- **Backend:** Flask web application framework with SQLAlchemy/Drizzle for PostgreSQL ORM.
- **Web Scraping:** Selenium WebDriver (Firefox with GeckoDriver) for browser automation, BeautifulSoup for HTML parsing, and Requests for direct HTTP calls. WebDriver Manager handles driver updates.
- **Database Schema:** `vehicle_data` for comprehensive vehicle information, `search_history` for request tracking, and JSON field support for flexible data storage.
- **API Endpoints:** Modular design with blueprints for various vehicle lookup functionalities, including cached and VNC-driven options.
- **Prioritization System:** Data extraction prioritizes `model_variant` from `vehicle_details`, with `basic_info` as a fallback, ensuring accurate vehicle identification.
- **Optimization:** Includes worker timeout resolution, database schema optimization, and browser optimization (e.g., disabling images for faster execution).

## External Dependencies

- **Flask**: Web framework
- **SQLAlchemy**: Database ORM
- **Selenium**: Browser automation
- **BeautifulSoup4**: HTML parsing
- **Requests**: HTTP client
- **psutil**: Process management
- **PostgreSQL**: Primary database
- **Firefox**: Primary browser for automation
- **GeckoDriver**: Firefox WebDriver
- **WebDriver Manager**: Automatic browser driver management
- **VNC Display**: Remote desktop for browser automation
- **OpenAI API (GPT-4o Vision)**: Exclusive OCR method for registration plate recognition and intelligent analysis (MOT failure prediction, market analysis).
- **checkcardetails.co.uk**: Primary vehicle data source.
- **DVLA (Driver and Vehicle Licensing Agency)**: Government vehicle database (indirect integration through scraping DVLA-sourced data).