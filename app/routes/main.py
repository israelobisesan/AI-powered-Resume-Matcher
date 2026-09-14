from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_recruiter():
            return redirect(url_for('recruiter.dashboard'))
        return redirect(url_for('seeker.dashboard'))
    return render_template('index.html')
