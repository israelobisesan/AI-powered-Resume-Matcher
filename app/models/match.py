from datetime import datetime
from app import db


class Match(db.Model):
    __tablename__ = 'matches'

    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)

    # Score fields
    semantic_score = db.Column(db.Float, default=0.0)  # cosine similarity of embeddings
    skill_score = db.Column(db.Float, default=0.0)
    capability_score = db.Column(db.Float, default=0.0)  # inferred capabilities match
    experience_score = db.Column(db.Float, default=0.0)
    education_score = db.Column(db.Float, default=0.0)
    final_score = db.Column(db.Float, default=0.0)

    # Skill match breakdown
    direct_matches = db.Column(db.Text, nullable=True)  # JSON: skills that directly match
    related_matches = db.Column(db.Text, nullable=True)  # JSON: related skills (e.g. Django→Python)
    transferable_matches = db.Column(db.Text, nullable=True)  # JSON: inferred capabilities
    missing_skills = db.Column(db.Text, nullable=True)  # JSON: skills the candidate lacks

    # Explanation and metadata
    explanation = db.Column(db.Text, nullable=True)  # deterministic, not LLM-generated
    analysis_version = db.Column(db.String(20), nullable=True)  # e.g. "r1_j1" for version tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Legacy fields kept for backward compatibility
    tfidf_score = db.Column(db.Float, default=0.0)
    matched_skills = db.Column(db.Text, nullable=True)  # JSON string (kept for templates)

    __table_args__ = (
        db.UniqueConstraint('resume_id', 'job_id', name='unique_resume_job_match'),
    )

    def __repr__(self):
        return f'<Match {self.id} - Score: {self.final_score}>'
