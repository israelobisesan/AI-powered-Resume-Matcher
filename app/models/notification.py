from datetime import datetime
from app import db


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recruiter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('notifications', lazy='dynamic'))
    recruiter = db.relationship('User', foreign_keys=[recruiter_id], backref=db.backref('sent_notifications', lazy='dynamic'))
    job = db.relationship('Job', backref=db.backref('notifications', lazy='dynamic'))

    def __repr__(self):
        return f'<Notification to {self.user_id} from {self.recruiter_id} read={self.is_read}>'
