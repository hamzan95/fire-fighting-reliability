from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Substation(db.Model):
    """Model for substation data"""
    id = db.Column(db.Integer, primary_key=True)
    substation_id = db.Column(db.String(20), nullable=False, unique=True, index=True)
    substation_name = db.Column(db.String(100), nullable=False)
    coverage_status = db.Column(db.String(20), nullable=False)  # Fully Covered, Partially Covered, Not Covered
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Define relationship to inspection tests
    inspections = db.relationship('InspectionTest', backref='substation', lazy=True)
    
    def __repr__(self):
        return f'<Substation {self.substation_id}: {self.substation_name}>'

class InspectionTest(db.Model):
    """Model for inspection and test data"""
    id = db.Column(db.Integer, primary_key=True)
    substation_id = db.Column(db.String(20), db.ForeignKey('substation.substation_id'), nullable=False)
    inspection_status = db.Column(db.String(20), nullable=False)  # Inspected, Not Inspected
    testing_status = db.Column(db.String(20), nullable=False)  # Tested, Not Tested
    inspection_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<InspectionTest for {self.substation_id} on {self.inspection_date}>'

class ReliabilityMetric(db.Model):
    """Model for calculated reliability metrics"""
    id = db.Column(db.Integer, primary_key=True)
    calculation_date = db.Column(db.Date, nullable=False)
    total_substations = db.Column(db.Integer, nullable=False)
    fully_covered_substations = db.Column(db.Integer, nullable=False)
    partially_covered_substations = db.Column(db.Integer, nullable=False)
    not_covered_substations = db.Column(db.Integer, nullable=False)
    inspected_substations = db.Column(db.Integer, nullable=False)
    not_inspected_substations = db.Column(db.Integer, nullable=False)
    tested_substations = db.Column(db.Integer, nullable=False)
    not_tested_substations = db.Column(db.Integer, nullable=False)
    testing_compliance = db.Column(db.Float, nullable=False)
    inspection_compliance = db.Column(db.Float, nullable=False)
    coverage_ratio = db.Column(db.Float, nullable=False)
    effective_reliability = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ReliabilityMetric on {self.calculation_date}: {self.effective_reliability}%>'
