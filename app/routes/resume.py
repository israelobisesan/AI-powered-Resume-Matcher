import os
import json
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.models.resume import Resume
from app.services.resume_parser import extract_text
from app.services.nlp_service import extract_resume_info
from app.utils import role_required

resume_bp = Blueprint('resume', __name__)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@resume_bp.route('/resume/upload', methods=['GET', 'POST'])
@login_required
@role_required('job_seeker')
def upload_resume():
    if request.method == 'POST':
        if 'resume' not in request.files:
            flash('No file selected.', 'error')
            return redirect(request.url)

        file = request.files['resume']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('Only PDF and DOCX files are allowed.', 'error')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower()
        safe_filename = f'resume_{current_user.id}_{int(__import__("time").time())}.{ext}'
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], safe_filename)

        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(file_path)

        raw_text = extract_text(file_path)
        if not raw_text or len(raw_text.strip()) < 10:
            flash('Could not extract text from the document. Please upload a valid resume.', 'error')
            os.remove(file_path)
            return redirect(request.url)

        info = extract_resume_info(raw_text)

        existing_resume = Resume.query.filter_by(user_id=current_user.id).first()
        if existing_resume:
            old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], existing_resume.filename)
            if os.path.exists(old_path):
                os.remove(old_path)
            existing_resume.filename = safe_filename
            existing_resume.file_type = ext
            existing_resume.raw_text = raw_text
            existing_resume.candidate_name = info['candidate_name']
            existing_resume.email = info['email']
            existing_resume.phone = info['phone']
            existing_resume.skills = json.dumps(info['skills'])
            existing_resume.education = json.dumps(info['education'])
            existing_resume.work_experience = json.dumps(info['work_experience'])
            # Reset analysis so Gemini re-analyzes the new content
            existing_resume.analysis_status = 'pending'
            existing_resume.content_hash = None
            existing_resume.semantic_analysis = None
            existing_resume.semantic_embedding = None
        else:
            resume = Resume(
                user_id=current_user.id,
                filename=safe_filename,
                file_type=ext,
                raw_text=raw_text,
                candidate_name=info['candidate_name'],
                email=info['email'],
                phone=info['phone'],
                skills=json.dumps(info['skills']),
                education=json.dumps(info['education']),
                work_experience=json.dumps(info['work_experience']),
                analysis_status='pending'
            )
            db.session.add(resume)

        db.session.commit()
        flash('Resume updated successfully!' if existing_resume else 'Resume uploaded successfully!', 'success')
        return redirect(url_for('resume.view_resume'))

    return render_template('seeker/upload_resume.html')


@resume_bp.route('/resume')
@login_required
@role_required('job_seeker')
def view_resume():
    resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.uploaded_at.desc()).first()
    if not resume:
        flash('No resume found. Please upload one.', 'info')
        return redirect(url_for('resume.upload_resume'))

    skills = json.loads(resume.skills) if resume.skills else []
    education = json.loads(resume.education) if resume.education else []
    experience = json.loads(resume.work_experience) if resume.work_experience else []

    return render_template('seeker/resume.html', resume=resume, skills=skills, education=education, experience=experience)


@resume_bp.route('/resume/edit', methods=['GET', 'POST'])
@login_required
@role_required('job_seeker')
def edit_resume():
    resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.uploaded_at.desc()).first()
    if not resume:
        flash('No resume found.', 'error')
        return redirect(url_for('resume.upload_resume'))

    if request.method == 'POST':
        resume.candidate_name = request.form.get('candidate_name', resume.candidate_name)
        resume.email = request.form.get('email', resume.email)
        resume.phone = request.form.get('phone', resume.phone)

        skills_text = request.form.get('skills', '')
        skills = [s.strip() for s in skills_text.split(',') if s.strip()]
        resume.skills = json.dumps(skills)

        education_raw = request.form.get('education', '[]')
        try:
            education = json.loads(education_raw)
        except (json.JSONDecodeError, TypeError):
            education = []
        resume.education = json.dumps(education)

        experience_raw = request.form.get('experience', '[]')
        try:
            experience = json.loads(experience_raw)
        except (json.JSONDecodeError, TypeError):
            experience = []
        resume.work_experience = json.dumps(experience)

        db.session.commit()
        # Reset analysis so Gemini re-analyzes the updated content
        resume.analysis_status = 'pending'
        resume.content_hash = None
        resume.semantic_analysis = None
        resume.semantic_embedding = None
        db.session.commit()
        flash('Resume updated successfully!', 'success')
        return redirect(url_for('resume.view_resume'))

    skills = json.loads(resume.skills) if resume.skills else []
    education = json.loads(resume.education) if resume.education else []
    experience = json.loads(resume.work_experience) if resume.work_experience else []

    return render_template('seeker/edit_resume.html', resume=resume, skills=skills, education=education, experience=experience)
