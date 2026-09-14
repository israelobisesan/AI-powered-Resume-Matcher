from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.seeker import seeker_bp
    from app.routes.recruiter import recruiter_bp
    from app.routes.resume import resume_bp
    from app.routes.jobs import jobs_bp
    from app.routes.matching import matching_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(seeker_bp)
    app.register_blueprint(recruiter_bp)
    app.register_blueprint(resume_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(matching_bp)

    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    @app.context_processor
    def inject_unread_count():
        from flask_login import current_user
        if current_user.is_authenticated and current_user.is_seeker():
            from app.models.notification import Notification
            unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
            return dict(unread_count=unread_count)
        return dict(unread_count=0)

    with app.app_context():
        db.create_all()

    return app
