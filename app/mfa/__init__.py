from flask import Blueprint

mfa_bp = Blueprint('mfa', __name__, url_prefix='/mfa')

from app.mfa import routes