# -*- coding: utf-8 -*-
"""
Cloudflare Turnstile 验证模块
"""

from flask import Blueprint

turnstile_bp = Blueprint('turnstile', __name__)

from . import routes
