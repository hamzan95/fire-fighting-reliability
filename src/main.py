import os

from flask import Flask

from src.extensions import db, login_manager  # Import login_manager from extensions

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
        db.create_all()  # <-- This ensures new tables are created if missing

        # TEMPORARY: Add month/year columns if missing (safe to run multiple times)
        from sqlalchemy import text
        # For inspection_test
        try:
            db.session.execute(text("ALTER TABLE inspection_test ADD COLUMN month INTEGER;"))
            print("Added 'month' column to inspection_test.")
        except Exception as e:
            print("month column may already exist or error (inspection_test):", e)
        try:
            db.session.execute(text("ALTER TABLE inspection_test ADD COLUMN year INTEGER;"))
            print("Added 'year' column to inspection_test.")
        except Exception as e:
            print("year column may already exist or error (inspection_test):", e)
        # For reliability_metric
        try:
            db.session.execute(text("ALTER TABLE reliability_metric ADD COLUMN year INTEGER;"))
            print("Added 'year' column to reliability_metric.")
        except Exception as e:
            print("year column may already exist or error (reliability_metric):", e)
        try:
            db.session.execute(text("ALTER TABLE reliability_metric ADD COLUMN month INTEGER;"))
            print("Added 'month' column to reliability_metric.")
        except Exception as e:
            print("month column may already exist or error (reliability_metric):", e)
        db.session.commit()

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



