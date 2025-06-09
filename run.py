#!/usr/bin/env python3
"""
Production entry point for Replit deployment
Runs the Flask app directly without keep-alive for deployment compatibility
"""

import os
from main import app

if __name__ == '__main__':
    # Use Replit's provided PORT or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Run in production mode for deployment
    app.run(
        host='0.0.0.0', 
        port=port, 
        debug=False,
        threaded=True
    )