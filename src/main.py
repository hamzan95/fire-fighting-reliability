import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON'T CHANGE THIS !!!

from flask import Flask, render_template
from src.models.substation import db, Substation, InspectionTest, ReliabilityMetric
from src.routes.main import main_bp
from datetime import date
# Assuming you have login_manager, import it here
# from flask_login import LoginManager # Uncomment and add this if you use Flask-Login

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fire_fighting_reliability_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{os.getenv('DB_USERNAME', 'fire_fighting_db_t37y_user')}:{os.getenv('DB_PASSWORD', 'S539wVuldErXytoQweAqrYAxG69PdyoH')}@{os.getenv('DB_HOST', 'postgresql://fire_fighting_db_t37y_user:S539wVuldErXytoQweAqrYAxG69PdyoH@dpg-d13egt3e5dus73em3sag-a/fire_fighting_db_t37y')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'fire_fighting_db_t37y')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# If you are using Flask-Login, initialize it AFTER 'app' is defined
# login_manager = LoginManager() # Uncomment if using Flask-Login
# login_manager.init_app(app)    # Uncomment if using Flask-Login
# login_manager.login_view = 'main.login' # Example, adjust as needed

# Register blueprints
app.register_blueprint(main_bp)

# Create tables within app context
with app.app_context():
    db.create_all()
    print("Database tables created successfully")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
