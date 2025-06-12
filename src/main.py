from flask import Flask
from flask_login import LoginManager
from src.extensions import db
from src.models.user import User
from src.routes.main import main_bp
from src.routes.auth import auth_bp

login_manager = LoginManager()
login_manager.login_view = "auth.login"

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)
    login_manager.init_app(app)

    # Ensure all tables (and new columns) are created in the database
    with app.app_context():
        db.create_all()

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
else:
    app = create_app()
