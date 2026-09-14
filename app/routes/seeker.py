import json
import logging
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.resume import Resume
from app.models.job import Job
from app.models.saved_job import SavedJob
from app.models.application import Application
from app.models.notification import Notification
from app.services.recommendation_service import get_job_recommendations, calculate_match
from app.utils import role_required

logger = logging.getLogger(__name__)

seeker_bp = Blueprint('seeker', __name__)


@seeker_bp.route('/seeker/dashboard')
@login_required
@role_required('job_seeker')
def dashboard():
    resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.uploaded_at.desc()).first()
    recommendations = []
    if resume:
        recommendations = get_job_recommendations(current_user.id, limit=5)
    saved_count = SavedJob.query.filter_by(user_id=current_user.id).count()
    applied_count = Application.query.filter_by(user_id=current_user.id).count()
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template('seeker/dashboard.html', resume=resume, recommendations=recommendations,
                           saved_count=saved_count, applied_count=applied_count, unread_count=unread_count)


@seeker_bp.route('/seeker/jobs')
@login_required
@role_required('job_seeker')
def browse_jobs():
    resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.uploaded_at.desc()).first()
    open_jobs = Job.query.filter_by(status='open').order_by(Job.created_at.desc()).all()

    saved_job_ids = {sj.job_id for sj in SavedJob.query.filter_by(user_id=current_user.id).all()}
    applied_job_ids = {a.job_id for a in Application.query.filter_by(user_id=current_user.id).all()}

    jobs_with_scores = []
    for job in open_jobs:
        if resume:
            match_data = calculate_match(resume, job)
            jobs_with_scores.append({
                'job': job,
                'match': match_data,
                'saved': job.id in saved_job_ids,
                'applied': job.id in applied_job_ids
            })
        else:
            jobs_with_scores.append({
                'job': job,
                'match': None,
                'saved': job.id in saved_job_ids,
                'applied': job.id in applied_job_ids
            })

    jobs_with_scores.sort(key=lambda x: x['match']['final_score'] if x['match'] else 0, reverse=True)
    return render_template('seeker/jobs.html', jobs_with_scores=jobs_with_scores, has_resume=resume is not None)


@seeker_bp.route('/jobs/<int:job_id>')
@login_required
@role_required('job_seeker')
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.uploaded_at.desc()).first()

    match_data = None
    if resume:
        match_data = calculate_match(resume, job)

    req_skills = json.loads(job.required_skills) if job.required_skills else []
    pref_skills = json.loads(job.preferred_skills) if job.preferred_skills else []

    is_saved = SavedJob.query.filter_by(user_id=current_user.id, job_id=job.id).first() is not None
    application = Application.query.filter_by(user_id=current_user.id, job_id=job.id).first()

    return render_template('seeker/job_detail.html', job=job, match=match_data,
                           req_skills=req_skills, pref_skills=pref_skills,
                           is_saved=is_saved, application=application)


@seeker_bp.route('/api/save-job/<int:job_id>', methods=['POST'])
@login_required
@role_required('job_seeker')
def save_job(job_id):
    """Toggle save/unsave a job."""
    job = Job.query.get_or_404(job_id)
    existing = SavedJob.query.filter_by(user_id=current_user.id, job_id=job_id).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'saved': False, 'message': 'Job removed from saved list.'})
    else:
        saved = SavedJob(user_id=current_user.id, job_id=job_id)
        db.session.add(saved)
        db.session.commit()
        return jsonify({'saved': True, 'message': 'Job saved successfully!'})


@seeker_bp.route('/api/apply-job/<int:job_id>', methods=['POST'])
@login_required
@role_required('job_seeker')
def apply_job(job_id):
    """Toggle apply/unapply for a job."""
    job = Job.query.get_or_404(job_id)
    if job.status != 'open':
        return jsonify({'error': 'This job is no longer accepting applications.'}), 400

    existing = Application.query.filter_by(user_id=current_user.id, job_id=job_id).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'applied': False, 'message': 'Application withdrawn.'})
    else:
        application = Application(user_id=current_user.id, job_id=job_id, status='pending')
        db.session.add(application)
        db.session.commit()
        return jsonify({'applied': True, 'message': 'Application submitted successfully!'})


@seeker_bp.route('/seeker/applied-jobs')
@login_required
@role_required('job_seeker')
def applied_jobs():
    applications = Application.query.filter_by(user_id=current_user.id).order_by(Application.applied_at.desc()).all()
    resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.uploaded_at.desc()).first()

    apps_with_scores = []
    for app in applications:
        job = app.job
        # Determine effective status
        effective_status = app.status
        if app.status == 'pending' and job.status == 'closed':
            effective_status = 'closed_not_chosen'

        if resume:
            match_data = calculate_match(resume, job)
            apps_with_scores.append({
                'application': app,
                'job': job,
                'match': match_data,
                'effective_status': effective_status
            })
        else:
            apps_with_scores.append({
                'application': app,
                'job': job,
                'match': None,
                'effective_status': effective_status
            })

    return render_template('seeker/applied_jobs.html', apps_with_scores=apps_with_scores)


@seeker_bp.route('/seeker/saved-jobs')
@login_required
@role_required('job_seeker')
def saved_jobs():
    saved_entries = SavedJob.query.filter_by(user_id=current_user.id).order_by(SavedJob.saved_at.desc()).all()
    jobs_with_scores = []
    resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.uploaded_at.desc()).first()

    for entry in saved_entries:
        job = entry.job
        if resume:
            match_data = calculate_match(resume, job)
            jobs_with_scores.append({'job': job, 'match': match_data, 'saved_at': entry.saved_at})
        else:
            jobs_with_scores.append({'job': job, 'match': None, 'saved_at': entry.saved_at})

    return render_template('seeker/saved_jobs.html', jobs_with_scores=jobs_with_scores)


@seeker_bp.route('/seeker/notifications')
@login_required
@role_required('job_seeker')
def notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('seeker/notifications.html', notifications=notifs)


@seeker_bp.route('/api/read-notification/<int:notif_id>', methods=['POST'])
@login_required
@role_required('job_seeker')
def read_notification(notif_id):
    """Mark a notification as read."""
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    notif.is_read = True
    db.session.commit()
    return jsonify({'success': True})


@seeker_bp.route('/seeker/profile')
@login_required
@role_required('job_seeker')
def profile():
    resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.uploaded_at.desc()).first()
    skills = json.loads(resume.skills) if resume and resume.skills else []
    education = json.loads(resume.education) if resume and resume.education else []
    experience = json.loads(resume.work_experience) if resume and resume.work_experience else []
    return render_template('seeker/profile.html', resume=resume, skills=skills, education=education, experience=experience)
