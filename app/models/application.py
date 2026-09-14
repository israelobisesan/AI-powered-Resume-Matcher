from datetime import datetime
from app import db


class Application(db.Model):
    __tablename__ = 'applications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'job_id', name='unique_user_job_application'),
    )

    user = db.relationship('User', backref=db.backref('applications', lazy='dynamic'))
    job = db.relationship('Job', backref=db.backref('applications', lazy='dynamic'))

    def __repr__(self):
        return f'<Application {self.user_id} -> job {self.job_id} ({self.status})>'
