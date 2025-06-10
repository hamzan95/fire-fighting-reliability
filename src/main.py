import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager, current_user
from src.models.substation import db, Substation, InspectionTest, ReliabilityMetric
from src.models.user import User, Role
from src.routes.main import main_bp
from src.routes.auth import auth_bp
from datetime import date

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dcd1abf04045fea502c99fdbb7809582")

# PostgreSQL configuration for Render.com
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://")
app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///fire_fighting.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)

# Create tables within app context
with app.app_context():
    db.create_all()
    
    # Create admin user if it doesn't exist
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(username="admin", email="admin@example.com", role=Role.ADMIN)
        admin.set_password("admin123")  # Change this to a secure password
        db.session.add(admin)
        db.session.commit()
        print("Admin user created")
    
    print("Database tables created successfully")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)


