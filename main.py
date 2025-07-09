#!/usr/bin/env python3
"""
Main Flask application for Vehicle Data Scraper
Provides web interface for scraping vehicle data from checkcardetails.co.uk
"""

from app import app  # noqa: F401
import main_routes  # noqa: F401

# Import API blueprints if they exist
try:
    from quick_response_api import quick_api
    app.register_blueprint(quick_api)
except ImportError:
    pass

try:
    from vnc_primary_api import vnc_primary
    app.register_blueprint(vnc_primary)
except ImportError:
    pass

try:
    from fast_vnc_api import fast_vnc
    app.register_blueprint(fast_vnc)
except ImportError:
    pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)