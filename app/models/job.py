from datetime import datetime
from app import db


class Job(db.Model):
    __tablename__ = 'jobs'

    id = db.Column(db.Integer, primary_key=True)
    recruiter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    required_skills = db.Column(db.Text, nullable=True)  # JSON string
    preferred_skills = db.Column(db.Text, nullable=True)  # JSON string
    minimum_experience = db.Column(db.Integer, default=0)
    education_requirement = db.Column(db.String(200), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    employment_type = db.Column(db.String(50), nullable=True)  # full-time, part-time, contract, internship
    status = db.Column(db.String(20), default='open')  # open or closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Semantic analysis fields
    content_hash = db.Column(db.String(64), nullable=True)  # SHA-256 for change detection
    analysis_status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    analysis_version = db.Column(db.Integer, default=1)
    analysis_model = db.Column(db.String(100), nullable=True)
    semantic_analysis = db.Column(db.Text, nullable=True)  # JSON: structured analysis from Gemini
    semantic_embedding = db.Column(db.Text, nullable=True)  # JSON: serialized embedding vector
    analyzed_at = db.Column(db.DateTime, nullable=True)

    matches = db.relationship('Match', backref='job', lazy=True)

    def __repr__(self):
        return f'<Job {self.title}>'
