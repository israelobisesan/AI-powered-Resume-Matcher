from datetime import datetime
from app import db


class SavedJob(db.Model):
    __tablename__ = 'saved_jobs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='saved_job_entries')
    job = db.relationship('Job', backref='saved_by_users')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'job_id', name='unique_user_job'),
    )

    def __repr__(self):
        return f'<SavedJob user={self.user_id} job={self.job_id}>'
