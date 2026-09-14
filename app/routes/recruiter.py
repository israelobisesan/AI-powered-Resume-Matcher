import json
import os
import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from flask_mail import Message
from app import db, mail
from app.models.job import Job
from app.models.resume import Resume
from app.models.application import Application
from app.models.notification import Notification
from app.services.recommendation_service import get_candidate_rankings
from app.services.gemini_service import suggest_skills
from app.utils import role_required

logger = logging.getLogger(__name__)

recruiter_bp = Blueprint('recruiter', __name__)


@recruiter_bp.route('/recruiter/dashboard')
@login_required
@role_required('recruiter')
def dashboard():
    jobs = Job.query.filter_by(recruiter_id=current_user.id).order_by(Job.created_at.desc()).all()
    total_jobs = len(jobs)
    open_jobs = len([j for j in jobs if j.status == 'open'])
    closed_jobs = len([j for j in jobs if j.status == 'closed'])
    total_applications = Application.query.join(Job).filter(Job.recruiter_id == current_user.id).count()
    return render_template('recruiter/dashboard.html', jobs=jobs, total_jobs=total_jobs,
                           open_jobs=open_jobs, closed_jobs=closed_jobs, total_applications=total_applications)


@recruiter_bp.route('/recruiter/jobs')
@login_required
@role_required('recruiter')
def recruiter_jobs():
    jobs = Job.query.filter_by(recruiter_id=current_user.id).order_by(Job.created_at.desc()).all()
    return render_template('recruiter/jobs.html', jobs=jobs)


@recruiter_bp.route('/recruiter/jobs/create', methods=['GET', 'POST'])
@login_required
@role_required('recruiter')
def create_job():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        company = request.form.get('company', '').strip()
        description = request.form.get('description', '').strip()
        required_skills = request.form.get('required_skills', '').strip()
        preferred_skills = request.form.get('preferred_skills', '').strip()
        minimum_experience = request.form.get('minimum_experience', 0, type=int)
        education_requirement = request.form.get('education_requirement', '').strip()
        location = request.form.get('location', '').strip()
        employment_type = request.form.get('employment_type', 'full-time')

        if not title or not company or not description:
            flash('Title, company, and description are required.', 'error')
            return render_template('recruiter/create_job.html')

        req_skills_list = [s.strip() for s in required_skills.split(',') if s.strip()]
        pref_skills_list = [s.strip() for s in preferred_skills.split(',') if s.strip()]

        job = Job(
            recruiter_id=current_user.id,
            title=title,
            company=company,
            description=description,
            required_skills=json.dumps(req_skills_list) if req_skills_list else None,
            preferred_skills=json.dumps(pref_skills_list) if pref_skills_list else None,
            minimum_experience=minimum_experience,
            education_requirement=education_requirement if education_requirement else None,
            location=location if location else None,
            employment_type=employment_type
        )
        db.session.add(job)
        db.session.commit()
        flash('Job posting created successfully!', 'success')
        return redirect(url_for('recruiter.recruiter_jobs'))

    return render_template('recruiter/create_job.html')


@recruiter_bp.route('/recruiter/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('recruiter')
def edit_job(job_id):
    job = Job.query.get_or_404(job_id)
    if job.recruiter_id != current_user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('recruiter.recruiter_jobs'))

    if request.method == 'POST':
        job.title = request.form.get('title', job.title).strip()
        job.company = request.form.get('company', job.company).strip()
        job.description = request.form.get('description', job.description).strip()
        job.minimum_experience = request.form.get('minimum_experience', job.minimum_experience, type=int)
        job.education_requirement = request.form.get('education_requirement', '').strip() or None
        job.location = request.form.get('location', '').strip() or None
        job.employment_type = request.form.get('employment_type', job.employment_type)

        required_skills = request.form.get('required_skills', '').strip()
        preferred_skills = request.form.get('preferred_skills', '').strip()
        req_skills_list = [s.strip() for s in required_skills.split(',') if s.strip()]
        pref_skills_list = [s.strip() for s in preferred_skills.split(',') if s.strip()]
        job.required_skills = json.dumps(req_skills_list) if req_skills_list else None
        job.preferred_skills = json.dumps(pref_skills_list) if pref_skills_list else None

        db.session.commit()
        flash('Job updated successfully!', 'success')
        return redirect(url_for('recruiter.recruiter_jobs'))

    req_skills = json.loads(job.required_skills) if job.required_skills else []
    pref_skills = json.loads(job.preferred_skills) if job.preferred_skills else []
    return render_template('recruiter/edit_job.html', job=job, req_skills=req_skills, pref_skills=pref_skills)


@recruiter_bp.route('/recruiter/jobs/<int:job_id>/close', methods=['POST'])
@login_required
@role_required('recruiter')
def close_job(job_id):
    job = Job.query.get_or_404(job_id)
    if job.recruiter_id != current_user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('recruiter.recruiter_jobs'))

    job.status = 'closed'

    # Update all pending applications to closed_not_chosen and notify
    pending_apps = Application.query.filter_by(job_id=job_id, status='pending').all()
    for app in pending_apps:
        app.status = 'closed_not_chosen'
        # Create notification for each pending applicant
        notif = Notification(
            user_id=app.user_id,
            recruiter_id=current_user.id,
            job_id=job_id,
            message=f'The job "{job.title}" has been closed. Unfortunately, your application was not shortlisted.'
        )
        db.session.add(notif)
        # Send email
        resume = Resume.query.filter_by(user_id=app.user_id).first()
        if resume and resume.email:
            try:
                msg = Message(
                    subject=f'Update on {job.title} - ResumeMatcher',
                    recipients=[resume.email],
                    html=f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <h2 style="color: #dc2626;">Job Application Closed</h2>
                        <p>Dear {resume.candidate_name or 'Applicant'},</p>
                        <p>The position <strong>{job.title}</strong> at <strong>{job.company}</strong> has been filled or closed.</p>
                        <p>Unfortunately, your application was not selected to proceed at this time.</p>
                        <p>We encourage you to browse other open positions on <strong>ResumeMatcher</strong>.</p>
                        <p>Best regards,<br><strong>ResumeMatcher Team</strong></p>
                    </div>
                    """
                )
                mail.send(msg)
            except Exception:
                pass

    db.session.commit()
    flash('Job posting closed. Applicants have been notified.', 'success')
    return redirect(url_for('recruiter.recruiter_jobs'))


@recruiter_bp.route('/recruiter/jobs/<int:job_id>/delete', methods=['POST'])
@login_required
@role_required('recruiter')
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    if job.recruiter_id != current_user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('recruiter.recruiter_jobs'))

    db.session.delete(job)
    db.session.commit()
    flash('Job posting deleted.', 'success')
    return redirect(url_for('recruiter.recruiter_jobs'))


@recruiter_bp.route('/recruiter/jobs/<int:job_id>/candidates')
@login_required
@role_required('recruiter')
def candidates(job_id):
    job = Job.query.get_or_404(job_id)
    if job.recruiter_id != current_user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('recruiter.recruiter_jobs'))

    # Only show applicants who applied for this job
    applications = Application.query.filter_by(job_id=job_id).order_by(Application.applied_at.desc()).all()

    rankings = get_candidate_rankings(job_id)

    # Build a map of user_id -> application status (Application uses user_id, not resume_id)
    app_status_map = {}
    applicant_user_ids = set()
    for a in applications:
        app_status_map[a.user_id] = a.status
        applicant_user_ids.add(a.user_id)

    # Filter rankings to only include applicants (match via resume.user_id)
    rankings = [r for r in rankings if r['resume'].user_id in applicant_user_ids]

    min_score = request.args.get('min_score', 0, type=float)
    search = request.args.get('search', '').strip()

    if min_score > 0:
        rankings = [r for r in rankings if r['match']['final_score'] >= min_score]
    if search:
        search_lower = search.lower()
        rankings = [r for r in rankings if search_lower in (r['resume'].candidate_name or '').lower()
                     or search_lower in (r['resume'].email or '').lower()
                     or any(search_lower in s.lower() for s in r['match'].get('matched_skills', []))]

    req_skills = json.loads(job.required_skills) if job.required_skills else []
    return render_template('recruiter/candidates.html', job=job, rankings=rankings,
                           req_skills=req_skills, min_score=min_score, search=search,
                           app_status_map=app_status_map)


@recruiter_bp.route('/api/shortlist/<int:application_id>', methods=['POST'])
@login_required
@role_required('recruiter')
def shortlist_candidate(application_id):
    """Shortlist a candidate and send notification."""
    application = Application.query.get_or_404(application_id)
    job = application.job
    if job.recruiter_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    application.status = 'shortlisted'

    # Create notification
    notif = Notification(
        user_id=application.user_id,
        recruiter_id=current_user.id,
        job_id=job.id,
        message=f'Congratulations! You have been shortlisted for the position "{job.title}" at {job.company}. Please check your email for next steps.'
    )
    db.session.add(notif)

    # Send email
    resume = Resume.query.filter_by(user_id=application.user_id).first()
    if resume and resume.email:
        try:
            msg = Message(
                subject=f'Great News! You\'ve Been Shortlisted - {job.title}',
                recipients=[resume.email],
                html=f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #16a34a;">You've Been Shortlisted!</h2>
                    <p>Dear {resume.candidate_name or 'Applicant'},</p>
                    <p>Great news! A recruiter has shortlisted your application for <strong>{job.title}</strong> at <strong>{job.company}</strong>.</p>
                    <div style="background: #f0fdf4; border-left: 4px solid #22c55e; padding: 16px; margin: 16px 0;">
                        <p style="margin: 0; color: #16a34a;"><strong>What happens next?</strong></p>
                        <p style="margin: 8px 0 0 0;">Please check your email within the next <strong>24 hours</strong>. We will be reaching out with more details about the next steps in the hiring process.</p>
                    </div>
                    <p>Best regards,<br><strong>ResumeMatcher Team</strong></p>
                </div>
                """
            )
            mail.send(msg)
        except Exception:
            pass

    db.session.commit()
    return jsonify({'success': True, 'message': 'Candidate shortlisted.'})


@recruiter_bp.route('/api/reject/<int:application_id>', methods=['POST'])
@login_required
@role_required('recruiter')
def reject_candidate(application_id):
    """Reject a candidate and send notification."""
    application = Application.query.get_or_404(application_id)
    job = application.job
    if job.recruiter_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    application.status = 'rejected'

    # Create notification
    notif = Notification(
        user_id=application.user_id,
        recruiter_id=current_user.id,
        job_id=job.id,
        message=f'Update on your application for "{job.title}" at {job.company}. Unfortunately, we will not be moving forward with your application at this time.'
    )
    db.session.add(notif)

    # Send email
    resume = Resume.query.filter_by(user_id=application.user_id).first()
    if resume and resume.email:
        try:
            msg = Message(
                subject=f'Update on Your Application - {job.title}',
                recipients=[resume.email],
                html=f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #6b7280;">Application Update</h2>
                    <p>Dear {resume.candidate_name or 'Applicant'},</p>
                    <p>Thank you for your interest in <strong>{job.title}</strong> at <strong>{job.company}</strong>.</p>
                    <p>After careful review, we will not be moving forward with your application at this time.</p>
                    <p>We encourage you to browse other open positions on <strong>ResumeMatcher</strong> that match your skills.</p>
                    <p>Best regards,<br><strong>ResumeMatcher Team</strong></p>
                </div>
                """
            )
            mail.send(msg)
        except Exception:
            pass

    db.session.commit()
    return jsonify({'success': True, 'message': 'Candidate rejected.'})


@recruiter_bp.route('/api/send-message', methods=['POST'])
@login_required
@role_required('recruiter')
def send_message():
    """Send a notification message to a candidate."""
    data = request.get_json()
    resume_id = data.get('resume_id')
    job_id = data.get('job_id')
    custom_message = data.get('message', '').strip()

    if not resume_id or not job_id:
        return jsonify({'error': 'Missing resume_id or job_id'}), 400

    resume = Resume.query.get_or_404(resume_id)
    job = Job.query.get_or_404(job_id)

    if job.recruiter_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    if not custom_message:
        custom_message = f'Check your email within the next 24 hours. We will be reaching out regarding the position "{job.title}" at {job.company}.'

    # Create notification
    notif = Notification(
        user_id=resume.user_id,
        recruiter_id=current_user.id,
        job_id=job.id,
        message=custom_message
    )
    db.session.add(notif)

    # Send email
    if resume.email:
        try:
            msg = Message(
                subject=f'Message from Recruiter - {job.title}',
                recipients=[resume.email],
                html=f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #1e40af;">Message from Recruiter</h2>
                    <p>Dear {resume.candidate_name or 'Applicant'},</p>
                    <p>A recruiter has reached out regarding your application for <strong>{job.title}</strong> at <strong>{job.company}</strong>.</p>
                    <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 16px; margin: 16px 0;">
                        <p style="margin: 0; color: #1e40af;"><strong>Message:</strong></p>
                        <p style="margin: 8px 0 0 0;">{custom_message}</p>
                    </div>
                    <p>Please check your email regularly for further updates.</p>
                    <p>Best regards,<br><strong>ResumeMatcher Team</strong></p>
                </div>
                """
            )
            mail.send(msg)
        except Exception:
            pass

    db.session.commit()
    return jsonify({'success': True, 'message': 'Message sent successfully.'})


@recruiter_bp.route('/api/suggest-skills', methods=['POST'])
@login_required
@role_required('recruiter')
def api_suggest_skills():
    """API endpoint to suggest skills from job description using Gemini."""
    data = request.get_json()
    description = data.get('description', '')
    if not description:
        return jsonify({'error': 'No description provided'}), 400
    try:
        result = suggest_skills(description)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@recruiter_bp.route('/recruiter/candidate/<int:resume_id>')
@login_required
@role_required('recruiter')
def candidate_detail(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    skills = json.loads(resume.skills) if resume.skills else []
    education = json.loads(resume.education) if resume.education else []
    experience = json.loads(resume.work_experience) if resume.work_experience else []

    # Find the application for this candidate
    # Application uses user_id, not resume_id, so we look up via resume.user_id
    application = None
    job_id = request.args.get('job_id', type=int)
    if job_id:
        application = Application.query.filter_by(user_id=resume.user_id, job_id=job_id).first()
    if not application:
        # Find most recent application from this recruiter's jobs
        recruiter_job_ids = [j.id for j in Job.query.filter_by(recruiter_id=current_user.id).all()]
        application = Application.query.filter(
            Application.user_id == resume.user_id,
            Application.job_id.in_(recruiter_job_ids)
        ).order_by(Application.applied_at.desc()).first()

    return render_template('recruiter/candidate_detail.html', resume=resume,
                           skills=skills, education=education, experience=experience,
                           application=application)


@recruiter_bp.route('/recruiter/resume/<int:resume_id>/download')
@login_required
@role_required('recruiter')
def download_resume(resume_id):
    """Download or view a candidate's original resume file."""
    resume = Resume.query.get_or_404(resume_id)

    # Verify recruiter has access: candidate must have applied to one of their jobs
    recruiter_job_ids = [j.id for j in Job.query.filter_by(recruiter_id=current_user.id).all()]
    has_access = Application.query.filter(
        Application.user_id == resume.user_id,
        Application.job_id.in_(recruiter_job_ids)
    ).first() is not None

    if not has_access:
        flash('You do not have access to this resume.', 'error')
        return redirect(url_for('recruiter.dashboard'))

    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], resume.filename)
    if not os.path.exists(file_path):
        flash('Resume file not found.', 'error')
        return redirect(url_for('recruiter.candidate_detail', resume_id=resume_id))

    # Set mimetype based on file type
    mimetype = 'application/pdf' if resume.file_type == 'pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

    return send_file(
        file_path,
        mimetype=mimetype,
        as_attachment=False,
        download_name=resume.filename
    )
