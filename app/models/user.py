from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'job_seeker' or 'recruiter'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    resume = db.relationship('Resume', backref='user', uselist=False, lazy=True)
    jobs = db.relationship('Job', backref='recruiter', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_recruiter(self):
        return self.role == 'recruiter'

    def is_seeker(self):
        return self.role == 'job_seeker'

    def __repr__(self):
        return f'<User {self.email}>'
