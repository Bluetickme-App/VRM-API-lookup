"""
Database models for vehicle data storage
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON

db = SQLAlchemy()

class VehicleData(db.Model):
    """Main vehicle data table"""
    __tablename__ = 'vehicle_data'
    
    id = db.Column(db.Integer, primary_key=True)
    registration = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    # Basic vehicle information
    make = db.Column(db.String(100))
    model = db.Column(db.String(100))
    variant = db.Column(db.String(200))
    description = db.Column(db.Text)
    year = db.Column(db.Integer)
    color = db.Column(db.String(50))
    fuel_type = db.Column(db.String(50))
    transmission = db.Column(db.String(100))
    engine_size = db.Column(db.String(50))
    body_style = db.Column(db.String(50))
    
    # Registration and legal information
    registration_date = db.Column(db.Date)
    registration_place = db.Column(db.String(200))
    last_v5c_issue_date = db.Column(db.Date)
    euro_status = db.Column(db.String(20))
    type_approval = db.Column(db.String(20))
    wheel_plan = db.Column(db.String(100))
    vehicle_age = db.Column(db.String(50))
    
    # MOT and Tax information
    tax_expiry = db.Column(db.Date)
    tax_days_left = db.Column(db.Integer)
    mot_expiry = db.Column(db.Date)
    mot_days_left = db.Column(db.Integer)
    
    # Mileage information
    last_mot_mileage = db.Column(db.Integer)
    mileage_issues = db.Column(db.String(10))
    average_mileage = db.Column(db.Integer)
    mileage_status = db.Column(db.String(20))
    
    # Performance data
    power_bhp = db.Column(db.String(20))
    max_speed_mph = db.Column(db.String(20))
    torque_ftlb = db.Column(db.String(20))
    
    # Fuel economy
    urban_mpg = db.Column(db.String(20))
    extra_urban_mpg = db.Column(db.String(20))
    combined_mpg = db.Column(db.String(20))
    
    # Safety ratings
    child_safety_rating = db.Column(db.String(10))
    adult_safety_rating = db.Column(db.String(10))
    pedestrian_safety_rating = db.Column(db.String(10))
    
    # Additional information
    co2_emissions = db.Column(db.String(20))
    tax_12_months = db.Column(db.String(20))
    tax_6_months = db.Column(db.String(20))
    total_keepers = db.Column(db.Integer)
    v5c_certificate_count = db.Column(db.Integer)
    
    # Raw data storage for future reference
    raw_data = db.Column(JSON)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    data_source = db.Column(db.String(100), default='checkcardetails.co.uk')
    
    def __repr__(self):
        return f'<VehicleData {self.registration}>'
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'registration': self.registration,
            'make': self.make,
            'model': self.model,
            'variant': self.variant,
            'description': self.description,
            'year': self.year,
            'color': self.color,
            'fuel_type': self.fuel_type,
            'transmission': self.transmission,
            'engine_size': self.engine_size,
            'body_style': self.body_style,
            'registration_date': self.registration_date.isoformat() if self.registration_date else None,
            'registration_place': self.registration_place,
            'last_v5c_issue_date': self.last_v5c_issue_date.isoformat() if self.last_v5c_issue_date else None,
            'euro_status': self.euro_status,
            'type_approval': self.type_approval,
            'wheel_plan': self.wheel_plan,
            'vehicle_age': self.vehicle_age,
            'tax_expiry': self.tax_expiry.isoformat() if self.tax_expiry else None,
            'tax_days_left': self.tax_days_left,
            'mot_expiry': self.mot_expiry.isoformat() if self.mot_expiry else None,
            'mot_days_left': self.mot_days_left,
            'last_mot_mileage': self.last_mot_mileage,
            'mileage_issues': self.mileage_issues,
            'average_mileage': self.average_mileage,
            'mileage_status': self.mileage_status,
            'power_bhp': self.power_bhp,
            'max_speed_mph': self.max_speed_mph,
            'torque_ftlb': self.torque_ftlb,
            'urban_mpg': self.urban_mpg,
            'extra_urban_mpg': self.extra_urban_mpg,
            'combined_mpg': self.combined_mpg,
            'child_safety_rating': self.child_safety_rating,
            'adult_safety_rating': self.adult_safety_rating,
            'pedestrian_safety_rating': self.pedestrian_safety_rating,
            'co2_emissions': self.co2_emissions,
            'tax_12_months': self.tax_12_months,
            'tax_6_months': self.tax_6_months,
            'total_keepers': self.total_keepers,
            'v5c_certificate_count': self.v5c_certificate_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'data_source': self.data_source
        }

class SearchHistory(db.Model):
    """Track search history and requests"""
    __tablename__ = 'search_history'
    
    id = db.Column(db.Integer, primary_key=True)
    registration = db.Column(db.String(20), nullable=False, index=True)
    search_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    success = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.Text)
    request_source = db.Column(db.String(50), default='web')  # 'web', 'api', 'vnc'
    
    def __repr__(self):
        return f'<SearchHistory {self.registration} at {self.search_timestamp}>'

class MOTHistory(db.Model):
    """Store MOT history data"""
    __tablename__ = 'mot_history'
    
    id = db.Column(db.Integer, primary_key=True)
    registration = db.Column(db.String(20), nullable=False, index=True)
    test_date = db.Column(db.Date)
    test_result = db.Column(db.String(20))  # PASS, FAIL, etc.
    expiry_date = db.Column(db.Date)
    odometer_value = db.Column(db.Integer)
    odometer_unit = db.Column(db.String(10), default='mi')
    test_number = db.Column(db.String(50))
    test_class = db.Column(db.String(10))
    
    # Foreign key to main vehicle data
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle_data.id'))
    vehicle = db.relationship('VehicleData', backref=db.backref('mot_tests', lazy=True))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<MOTHistory {self.registration} - {self.test_date}>'