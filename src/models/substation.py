from src.extensions import db
from datetime import datetime

class Substation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    substation_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), unique=True, nullable=False)
    coverage_status = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Substation {self.name}>'

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
    
    substation = db.relationship('Substation', backref=db.backref('inspections', lazy=True))
    user = db.relationship('User', backref=db.backref('inspections', lazy=True))

class ReliabilityMetric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    reliability_score = db.Column(db.Float, nullable=False)
    testing_compliance = db.Column(db.Float, nullable=False)
    inspection_compliance = db.Column(db.Float, nullable=False)
    coverage_ratio = db.Column(db.Float, nullable=False)
    effective_reliability = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ReliabilityMetric {self.date}>'
