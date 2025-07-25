#!/usr/bin/env python3
"""
Script to update MOT fields for all existing vehicle records
"""

from app import app, db
from models import VehicleData
from external_vehicle_api import calculate_mot_fields
import logging

logging.basicConfig(level=logging.INFO)

def update_all_mot_fields():
    """Update MOT fields for all vehicle records"""
    with app.app_context():
        # Get all vehicle records
        records = VehicleData.query.all()
        
        updated_count = 0
        for record in records:
            try:
                # Prepare data for calculation
                data = {
                    'mot_history': record.mot_history or {},
                    'mileage_history': record.mileage_history or {}
                }
                
                # Calculate MOT fields
                mot_expiry_date, mot_days_left, last_mot_mileage, mileage_issues = calculate_mot_fields(data)
                
                # Update record
                record.mot_expiry_date = str(mot_expiry_date) if mot_expiry_date else None
                record.mot_days_left = mot_days_left
                record.last_mot_mileage = last_mot_mileage  
                record.mileage_issues = mileage_issues
                
                logging.info(f"Updated {record.registration}: expiry={mot_expiry_date}, days_left={mot_days_left}, mileage={last_mot_mileage}, issues={mileage_issues}")
                updated_count += 1
                
            except Exception as e:
                logging.error(f"Error updating {record.registration}: {e}")
        
        # Commit all changes
        db.session.commit()
        logging.info(f"Successfully updated {updated_count} vehicle records")

if __name__ == '__main__':
    update_all_mot_fields()