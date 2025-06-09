from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from src.models.substation import db
from datetime import datetime

class Role:
    ADMIN = 'admin'
    INSPECTOR = 'inspector'
    VIEWER = 'viewer'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default=Role.VIEWER)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == Role.ADMIN
    
    def is_inspector(self):
        return self.role == Role.INSPECTOR or self.role == Role.ADMIN
    
    def __repr__(self):
        return f'<User {self.username}>'
