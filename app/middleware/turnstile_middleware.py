# -*- coding: utf-8 -*-
"""
Cloudflare Turnstile 全局验证中间件
在用户访问任何页面之前验证人机挑战（除 /developer-docs 外）
采用 Cloudflare 托管挑战：用户被 302 到 CF 验证页，通过后回调我们并打标
"""

from flask import session, request, redirect, jsonify, url_for as flask_url_for
from urllib.parse import quote

# 绕过验证的路由列表
EXCLUDED_ROUTES = [
    '/developer-docs',
    '/static/',
    '/favicon.ico',
    '/api/health',
    '/turnstile-verify',
    '/turnstile-verify/',
    '/api/turnstile/',
    '/turnstile/callback',
]

# 绕过验证的路由前缀
EXCLUDED_PREFIXES = [
    '/api/oauth/',
]


def is_turnstile_required():
    """
    检查是否需要 Turnstile 验证
    仅在生产环境和配置启用时生效
    """
    from app.env_config import configure_turnstile
    turnstile_config = configure_turnstile()
    return turnstile_config.get('enabled', False)


def is_route_excluded(path):
    """检查路由是否在排除列表中"""
    if path is None:
        return True
    for excluded in EXCLUDED_ROUTES:
        if path == excluded or path.startswith(excluded):
            return True
    for prefix in EXCLUDED_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def is_turnstile_verified():
    """
    检查 Turnstile 是否已验证且未过期
    与 turnstile/routes.py 中的逻辑保持一致
    """
    from datetime import datetime, timedelta

    turnstile_verified = session.get('turnstile_verified', False)
    if not turnstile_verified:
        return False

    verify_timestamp = session.get('turnstile_verified_at')
    if not verify_timestamp:
        return False

    # 验证有效期（小时）
    VERIFY_DURATION_HOURS = 2

    verify_time = datetime.fromtimestamp(verify_timestamp)
    expire_time = verify_time + timedelta(hours=VERIFY_DURATION_HOURS)

    if datetime.now() > expire_time:
        session.pop('turnstile_verified', None)
        session.pop('turnstile_verified_at', None)
        return False

    return True


def get_verify_url():
    """获取验证页面的 URL"""
    try:
        return flask_url_for('turnstile.verify')
    except Exception:
        return '/turnstile-verify'


def register_global_turnstile_middleware(app):
    """
    注册全局 Turnstile 验证中间件
    在 before_request 中检查所有请求
    """
    @app.before_request
    def check_turnstile_verification():
        # 如果不需要 Turnstile 验证，直接通过
        if not is_turnstile_required():
            return None

        # 检查是否在排除列表中
        if is_route_excluded(request.path):
            return None

        # 静态文件直接通过
        if request.path.startswith('/static/'):
            return None

        # 检查是否已通过验证（带过期检查）
        if is_turnstile_verified():
            return None

        # API 请求返回 JSON 错误
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'message': '请先完成人机验证',
                'require_turnstile': True,
                'verify_url': get_verify_url()
            }), 403

        # 重定向到 Cloudflare 托管挑战页
        # 流程：用户 → /turnstile/managed（CF 托管挑战 iframe）→ 验证通过 → /turnstile/callback?cdata=...&token=...
        # 这里我们用 cdata 把 next 透传，CF Managed Challenge 完成后会用 cdata 回跳我们
        next_url = request.full_path if request.query_string else request.path
        callback = flask_url_for('turnstile.callback', _external=True)
        # 方案：跳转到我们自己的托管挑战入口（带全屏 Turnstile widget + 自动提交）
        verify_url = flask_url_for('turnstile.verify', _external=True)
        # 把 next 编入 verify URL 的 query
        sep = '&' if '?' in verify_url else '?'
        return redirect(f"{verify_url}{sep}next={quote(next_url)}")
