import os
from flask import Flask, render_template, session
from datetime import timedelta

try:
    from config import SECRET_KEY, REMEMBER_ME_COOKIE_DURATION
    from config import (
        PROJECT_NAME, PROJECT_VERSION, PROJECT_EMAIL, 
        PROJECT_QQ_GROUP, PROJECT_WEBSITE
    )
    from app.env_config import configure_turnstile, configure_risk_control, auto_configure
    from app.permission.utils import is_developer as check_is_developer
except ImportError:
    print("错误：请复制 config.example.py 为 config.py 并配置相关参数！")
    import sys
    sys.exit(1)


def create_app():
    project_root = os.path.dirname(os.path.dirname(__file__))
    static_folder = os.path.join(project_root, 'static')
    app = Flask(__name__, static_folder=static_folder)
    app.config['PROJECT_ROOT'] = project_root

    app.secret_key = SECRET_KEY
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=REMEMBER_ME_COOKIE_DURATION)

    turnstile_config = configure_turnstile()
    risk_control = configure_risk_control()
    env_config = auto_configure()

    from app.auth import auth_bp
    from app.user import user_bp
    from app.admin import admin_bp
    from app.permission import permission_bp
    from app.developer import developer_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(permission_bp)
    app.register_blueprint(developer_bp)

    from app.models.db import check_and_create_tables
    check_and_create_tables()

    @app.context_processor
    def inject_config():
        def is_developer():
            if 'logged_in' in session and session['logged_in']:
                user_id = session.get('user_id')
                return check_is_developer(user_id)
            return False
        
        def is_admin():
            from app.permission.utils import is_admin as check_is_admin
            if 'logged_in' in session and session['logged_in']:
                user_id = session.get('user_id')
                return check_is_admin(user_id)
            return False
        
        return {
            'turnstile_enabled': turnstile_config.get('enabled', False),
            'turnstile_sitekey': turnstile_config.get('site_key', ''),
            'is_production': env_config['is_production'],
            'environment': env_config['environment'],
            'risk_control': risk_control,
            'is_developer': is_developer,
            'is_admin': is_admin,
            'project_name': PROJECT_NAME,
            'project_version': PROJECT_VERSION,
            'project_email': PROJECT_EMAIL,
            'project_qq_group': PROJECT_QQ_GROUP,
            'project_website': PROJECT_WEBSITE
        }

    @app.errorhandler(401)
    def unauthorized(e):
        return render_template('401.html'), 401

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500

    return app
