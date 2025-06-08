#!/usr/bin/env python3
"""
Main Flask application for Vehicle Data Scraper
Provides web interface for scraping vehicle data from checkcardetails.co.uk
"""

from flask import Flask, render_template, request, jsonify, send_file
import json
import csv
import io
import os
from datetime import datetime
from enhanced_scraper import EnhancedVehicleScraper
from utils import validate_registration, sanitize_filename

app = Flask(__name__)

@app.route('/')
def index():
    """Main page with vehicle lookup form"""
    return render_template('index.html')

@app.route('/api/scrape', methods=['POST'])
def scrape_vehicle():
    """API endpoint to scrape vehicle data"""
    try:
        data = request.get_json()
        registration = data.get('registration', '').strip().upper()
        
        # Validate registration number
        if not validate_registration(registration):
            return jsonify({
                'success': False,
                'error': 'Invalid registration number format'
            }), 400
        
        # Initialize scraper and extract data
        scraper = VehicleScraper()
        vehicle_data = scraper.scrape_vehicle_data(registration)
        
        if vehicle_data:
            return jsonify({
                'success': True,
                'data': vehicle_data,
                'registration': registration,
                'scraped_at': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No vehicle data found for this registration'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Scraping failed: {str(e)}'
        }), 500

@app.route('/api/export/<format_type>/<registration>')
def export_data(format_type, registration):
    """Export vehicle data in JSON or CSV format"""
    try:
        # Re-scrape data for export (in production, you might want to cache this)
        scraper = VehicleScraper()
        vehicle_data = scraper.scrape_vehicle_data(registration.upper())
        
        if not vehicle_data:
            return jsonify({'error': 'No data found for this registration'}), 404
        
        filename = sanitize_filename(f"{registration}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        if format_type.lower() == 'json':
            # Export as JSON
            json_data = json.dumps(vehicle_data, indent=2, ensure_ascii=False)
            buffer = io.BytesIO()
            buffer.write(json_data.encode('utf-8'))
            buffer.seek(0)
            
            return send_file(
                buffer,
                as_attachment=True,
                download_name=f"{filename}.json",
                mimetype='application/json'
            )
            
        elif format_type.lower() == 'csv':
            # Export as CSV (flatten nested data)
            flattened_data = flatten_dict(vehicle_data)
            
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            
            # Write headers and data
            writer.writerow(['Field', 'Value'])
            for key, value in flattened_data.items():
                writer.writerow([key, value])
            
            output = buffer.getvalue()
            buffer = io.BytesIO()
            buffer.write(output.encode('utf-8'))
            buffer.seek(0)
            
            return send_file(
                buffer,
                as_attachment=True,
                download_name=f"{filename}.csv",
                mimetype='text/csv'
            )
        else:
            return jsonify({'error': 'Invalid format. Use json or csv'}), 400
            
    except Exception as e:
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

def flatten_dict(d, parent_key='', sep='_'):
    """Flatten nested dictionary for CSV export"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    items.extend(flatten_dict(item, f"{new_key}_{i}", sep=sep).items())
                else:
                    items.append((f"{new_key}_{i}", item))
        else:
            items.append((new_key, v))
    return dict(items)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
