import os
from flask import Flask
from flask_login import LoginManager
from src.extensions import db
from src.routes.main import main_bp # Import the blueprint from src.routes.main
from src.routes.auth import auth_bp

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "fire_fighting_reliability_secret_key")

    database_url = os.environ.get("DATABASE_URL")
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///fire_fighting.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        from src.models.user import User
        return User.query.get(int(user_id))

    # Register blueprints (ONLY ONCE)
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    with app.app_context():
        db.create_all()
        from src.models.user import User, Role
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(username="admin", email="admin@example.com", role=Role.ADMIN)
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("Admin user created")
        
        print("Database tables created successfully")

    return app

# If you're running this directly (e.g., with `python main.py`)
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
