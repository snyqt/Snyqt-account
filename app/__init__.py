import os
from flask import Flask, render_template
from datetime import timedelta

try:
    from config import SECRET_KEY, REMEMBER_ME_COOKIE_DURATION
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

    from app.auth import auth_bp
    from app.user import user_bp
    from app.admin import admin_bp
    from app.permission import permission_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(permission_bp)

    from app.models.db import check_and_create_tables
    check_and_create_tables()

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
