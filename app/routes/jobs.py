from flask import Blueprint, render_template
from flask_login import login_required

jobs_bp = Blueprint('jobs', __name__)


@jobs_bp.route('/jobs')
@login_required
def list_jobs():
    return render_template('seeker/jobs.html')


@jobs_bp.route('/jobs/<int:job_id>')
@login_required
def job_detail(job_id):
    return render_template('seeker/job_detail.html')
