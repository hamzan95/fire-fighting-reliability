import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON'T CHANGE THIS !!!

from flask import Flask, render_template
from src.models.substation import db, Substation, InspectionTest, ReliabilityMetric
from src.routes.main import main_bp
from datetime import date

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fire_fighting_reliability_secret_key'

# PostgreSQL configuration for Render.com
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or "sqlite:///fire_fighting.db"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Register blueprints
app.register_blueprint(main_bp)

# Create tables within app context
with app.app_context():
    db.create_all()
    print("Database tables created successfully")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
