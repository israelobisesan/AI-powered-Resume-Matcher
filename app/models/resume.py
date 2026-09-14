from datetime import datetime
from app import db


class Resume(db.Model):
    __tablename__ = 'resumes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    raw_text = db.Column(db.Text, nullable=True)
    candidate_name = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    skills = db.Column(db.Text, nullable=True)  # JSON string
    education = db.Column(db.Text, nullable=True)  # JSON string
    work_experience = db.Column(db.Text, nullable=True)  # JSON string
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Semantic analysis fields
    content_hash = db.Column(db.String(64), nullable=True)  # SHA-256 for change detection
    analysis_status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    analysis_version = db.Column(db.Integer, default=1)
    analysis_model = db.Column(db.String(100), nullable=True)  # e.g. gemini-3.6-flash
    semantic_analysis = db.Column(db.Text, nullable=True)  # JSON: structured analysis from Gemini
    semantic_embedding = db.Column(db.Text, nullable=True)  # JSON: serialized embedding vector
    analyzed_at = db.Column(db.DateTime, nullable=True)

    matches = db.relationship('Match', backref='resume', lazy=True)

    def __repr__(self):
        return f'<Resume {self.filename}>'
