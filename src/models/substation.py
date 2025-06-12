from datetime import datetime
from src.extensions import db

class Substation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    coverage_status = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    inspections = db.relationship('InspectionTest', backref='substation', lazy=True)

class InspectionTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    substation_id = db.Column(db.Integer, db.ForeignKey('substation.id'), nullable=False)
    inspection_date = db.Column(db.Date, nullable=True)
    testing_date = db.Column(db.Date, nullable=True)
    inspection_status = db.Column(db.String(64), nullable=False)
    testing_status = db.Column(db.String(64), nullable=False)
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # --- ADDED: month and year for grouping/filtering ---
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)

    def set_month_year(self):
        date = self.inspection_date or self.testing_date
        if date:
            self.month = date.month
            self.year = date.year

class ReliabilityMetric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=True)  # Null for yearly metrics
    effective_reliability = db.Column(db.Float, nullable=False)
    testing_compliance = db.Column(db.Float, nullable=False)
    inspection_compliance = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

