import os
from flask import Flask
from flask_login import LoginManager
from src.extensions import db
from src.routes.main import main_bp
from src.routes.auth import auth_bp

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "fire_fighting_reliability_secret_key")

    # PostgreSQL configuration for Render.com
    database_url = os.environ.get("DATABASE_URL")
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///fire_fighting.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize extensions
    db.init_app(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        from src.models.user import User  # Import here to avoid circular imports
        return User.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    # Create tables and admin user within app context
    with app.app_context():
        db.create_all()
        from src.models.user import User, Role
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(username="admin", email="admin@example.com", role=Role.ADMIN)
            admin.set_password("admin123")  # Change this to a secure password
            db.session.add(admin)
            db.session.commit()
            print("Admin user created")
        
        print("Database tables created successfully")

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)

# If you're running this directly (e.g., with `python main.py`)
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
