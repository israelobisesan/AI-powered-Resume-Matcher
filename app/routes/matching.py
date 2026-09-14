from flask import Blueprint
from flask_login import login_required

matching_bp = Blueprint('matching', __name__)


@matching_bp.route('/matches/jobs')
@login_required
def job_matches():
    pass


@matching_bp.route('/matches/job/<int:job_id>')
@login_required
def job_match_detail(job_id):
    pass
