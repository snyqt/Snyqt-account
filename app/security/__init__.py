from flask import Blueprint

security_bp = Blueprint('security', __name__, url_prefix='')

from app.security import routes