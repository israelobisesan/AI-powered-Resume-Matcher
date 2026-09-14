from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user


def role_required(role):
    """Decorator to restrict access to a specific role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role != role:
                flash('You do not have permission to access this page.', 'error')
                if current_user.is_recruiter():
                    return redirect(url_for('recruiter.dashboard'))
                else:
                    return redirect(url_for('seeker.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
