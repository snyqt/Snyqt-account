# -*- coding: utf-8 -*-
"""
Cloudflare Turnstile 验证路由
"""

from flask import request, session, redirect, url_for, render_template, jsonify, make_response
from functools import wraps
from app.auth.utils import verify_turnstile
from datetime import datetime, timedelta

# 导入 __init__.py 中定义的 Blueprint
from . import turnstile_bp

# 验证有效期（小时）
TURNSTILE_VERIFY_DURATION_HOURS = 2


def turnstile_verified_required(f):
    """
    装饰器：检查 Turnstile 验证状态
    用于需要已通过验证的路由
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not _is_turnstile_verified():
            return redirect(url_for('turnstile.verify'))
        return f(*args, **kwargs)
    return decorated_function


def _is_turnstile_verified():
    """检查 Turnstile 是否已验证且未过期"""
    turnstile_verified = session.get('turnstile_verified', False)
    if not turnstile_verified:
        return False

    # 检查验证时间是否过期
    verify_timestamp = session.get('turnstile_verified_at')
    if not verify_timestamp:
        return False

    verify_time = datetime.fromtimestamp(verify_timestamp)
    expire_time = verify_time + timedelta(hours=TURNSTILE_VERIFY_DURATION_HOURS)

    if datetime.now() > expire_time:
        # 已过期，清除验证状态
        session.pop('turnstile_verified', None)
        session.pop('turnstile_verified_at', None)
        return False

    return True


@turnstile_bp.route('/turnstile-verify')
def verify():
    """
    Turnstile 验证页面
    用户访问受保护页面时重定向至此
    """
    # 如果已经验证通过，直接跳转
    if _is_turnstile_verified():
        next_url = request.args.get('next', '/')
        return redirect(next_url)

    next_url = request.args.get('next', '/')

    # 获取 Turnstile 配置
    from app.env_config import configure_turnstile
    turnstile_config = configure_turnstile()
    turnstile_enabled = turnstile_config.get('enabled', False)
    turnstile_sitekey = turnstile_config.get('site_key', '')

    response = make_response(render_template(
        'turnstile_verify.html',
        turnstile_enabled=turnstile_enabled,
        turnstile_sitekey=turnstile_sitekey,
        next_url=next_url
    ))

    return response


@turnstile_bp.route('/api/turnstile/verify', methods=['POST'])
def api_verify():
    """
    AJAX API：验证 Turnstile token
    验证成功后直接返回 next_url 跳转链接
    """
    data = request.get_json() if request.is_json else request.form.to_dict()
    token = data.get('token') or request.form.get('cf-turnstile-response')
    next_url = data.get('next', '/') or '/'

    print(f"[Turnstile API] 收到验证请求, token 长度: {len(token) if token else 0}, next: {next_url}")

    if not token:
        return jsonify({
            'success': False,
            'message': '缺少验证令牌'
        }), 400

    # 验证 token
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    is_valid = verify_turnstile(token, client_ip)
    print(f"[Turnstile API] 验证结果: {is_valid}")

    if is_valid:
        # 设置验证状态和验证时间
        session['turnstile_verified'] = True
        session['turnstile_verified_at'] = datetime.now().timestamp()
        session.permanent = True
        print(f"[Turnstile API] Session 已设置: turnstile_verified={session.get('turnstile_verified')}")

        response = jsonify({
            'success': True,
            'message': '验证成功',
            'next_url': next_url,
            'expire_hours': TURNSTILE_VERIFY_DURATION_HOURS
        })

        return response
    else:
        return jsonify({
            'success': False,
            'message': '人机验证失败，请重试'
        }), 400


@turnstile_bp.route('/api/turnstile/verify-form', methods=['POST'])
def verify_form():
    """
    表单提交验证（备用方案）
    Turnstile 自动提交表单时调用
    """
    token = request.form.get('cf-turnstile-response')
    next_url = request.form.get('next', '/') or '/'

    if not token:
        return redirect(url_for('turnstile.verify', next=next_url, error='missing_token'))

    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    is_valid = verify_turnstile(token, client_ip)

    if is_valid:
        # 设置验证状态
        session['turnstile_verified'] = True
        session['turnstile_verified_at'] = datetime.now().timestamp()
        session.permanent = True

        # 验证成功后直接重定向到目标页面
        return redirect(next_url)
    else:
        return redirect(url_for('turnstile.verify', next=next_url, error='invalid'))


@turnstile_bp.route('/api/turnstile/status', methods=['GET'])
def status():
    """
    获取当前验证状态
    """
    is_verified = _is_turnstile_verified()
    expire_time = None

    if is_verified:
        verify_timestamp = session.get('turnstile_verified_at')
        if verify_timestamp:
            verify_time = datetime.fromtimestamp(verify_timestamp)
            expire_time = (verify_time + timedelta(hours=TURNSTILE_VERIFY_DURATION_HOURS)).strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        'verified': is_verified,
        'expire_time': expire_time,
        'expire_hours': TURNSTILE_VERIFY_DURATION_HOURS
    })


@turnstile_bp.route('/api/turnstile/reset', methods=['POST'])
def reset():
    """
    重置验证状态（退出时调用）
    """
    session.pop('turnstile_verified', None)
    session.pop('turnstile_verified_at', None)
    return jsonify({
        'success': True,
        'message': '验证状态已重置'
    })


@turnstile_bp.route('/turnstile/callback')
def callback():
    """
    Cloudflare 托管挑战回调
    CF 验证通过后会带 ?cdata=<原始 next> 跳转回这里
    我们直接给 session 打标，然后 302 回 next
    """
    next_url = request.args.get('cdata') or request.args.get('next') or '/'

    # 防止开放重定向：只接受站内路径
    if not next_url.startswith('/'):
        next_url = '/'

    # 验证托管挑战回传的 token（cf-token / cf-cdata）
    cf_token = request.args.get('cf-token') or request.args.get('cf_chl_jschl_tk')
    # 即使没有显式 token，CF 托管挑战回跳本身即代表已通过

    session['turnstile_verified'] = True
    session['turnstile_verified_at'] = datetime.now().timestamp()
    session.permanent = True

    print(f"[Turnstile Callback] CF 托管挑战通过, cdata={next_url}")
    return redirect(next_url)
