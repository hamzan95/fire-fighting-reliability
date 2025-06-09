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
    
    # Relationship to inspections (parent side)
    inspections = db.relationship('InspectionTest', back_populates='substation', lazy=True)
    
    def __repr__(self):
        return f'<Substation {self.substation_id}: {self.substation_name}>'

class InspectionTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    substation_id = db.Column(db.Integer, db.ForeignKey('substation.id'), nullable=False)
    inspection_date = db.Column(db.Date, nullable=False)
    testing_date = db.Column(db.Date, nullable=True)
    inspection_status = db.Column(db.String(20), nullable=False)
    testing_status = db.Column(db.String(20), nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships (child side)
    substation = db.relationship('Substation', back_populates='inspections')
    user = db.relationship('User', backref='inspections')
    
    def __repr__(self):
        return f'<InspectionTest {self.id} for Substation {self.substation_id}>'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # No need to define inspections relationship here as it's handled by backref

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
