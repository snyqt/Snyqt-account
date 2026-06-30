from flask import Blueprint, request, jsonify, render_template, session, redirect, current_app
from datetime import timedelta, datetime
import os
import string
import random
import hashlib
import pymysql
from functools import wraps
from urllib.parse import urlencode

import pyotp

from app.auth.utils import (
    hash_password, generate_verification_code, is_password_strong,
    verify_turnstile, parse_user_agent, get_ip_location, check_login_risk,
    send_verification_email, send_2fa_verification_email, send_sms,
    get_network_time, get_network_timestamp, generate_user_id
)
from app.models.db import get_db_connection

try:
    from config import (
        TURNSTILE_CONFIG, VERIFICATION_CODE_EXPIRE,
        REMEMBER_ME_COOKIE_DURATION, EMAIL_CONFIG
    )
    from app.env_config import configure_turnstile
    turnstile_config = configure_turnstile()
    TURNSTILE_ENABLED = turnstile_config.get('enabled', False)
    TURNSTILE_SITEKEY = turnstile_config.get('site_key', '')
except ImportError:
    from config import SECRET_KEY
    TURNSTILE_ENABLED = False
    TURNSTILE_SITEKEY = ''
    VERIFICATION_CODE_EXPIRE = 300
    REMEMBER_ME_COOKIE_DURATION = 7

auth_bp = Blueprint('auth', __name__)

sms_verification_codes = {}

avatar_extensions = ['png', 'jpg', 'jpeg', 'gif']

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return jsonify({'success': False, 'message': '用户未登录'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': '用户未登录'}), 401
            return redirect('/login')
        user_id = session.get('user_id')
        conn = get_db_connection()
        if not conn:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': '数据库连接失败'}), 500
            return "数据库连接失败", 500
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM user_permission WHERE user_id = %s AND (type = 'ROOT' OR type = '管理员')", (user_id,))
                if not cursor.fetchone():
                    if request.path.startswith('/api/'):
                        return jsonify({'success': False, 'message': '没有管理员权限'}), 403
                    return redirect('/')
        finally:
            conn.close()
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/')
def index():
    return render_template('index.html')

@auth_bp.route('/login', methods=['GET'])
def login_page():
    mode = request.args.get('mode', 'login')
    return render_template('login.html', mode=mode, turnstile_enabled=TURNSTILE_ENABLED, turnstile_sitekey=TURNSTILE_SITEKEY)

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        login_method = request.form.get('login_method', 'password')
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        email = request.form.get('email', '')
        email_code = request.form.get('email_code', '')
        phone = request.form.get('phone', '')
        phone_code = request.form.get('phone_code', '')
        is_cookie = int(request.form.get('is_cookie', 0))
        turnstile_response = request.form.get('cf-turnstile-response')

        # ── 人机验证 ──
        if TURNSTILE_ENABLED:
            if not turnstile_response:
                return jsonify({'success': False, 'message': '请完成人机验证'})
            if not verify_turnstile(turnstile_response, request.remote_addr):
                return jsonify({'success': False, 'message': '人机验证失败，请重试'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

        cursor = conn.cursor()
        user = None

        # ── 方式1：用户名 + 密码 ──
        if login_method == 'password':
            if not username or not password:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '请输入用户名和密码'})

            cursor.execute(
                "SELECT id, Name, password, mail, phone, totp_secret, totp_enabled FROM user_info WHERE Name = %s",
                (username,)
            )
            user = cursor.fetchone()
            if not user or hash_password(password) != user[2]:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '用户名或密码错误'})

        # ── 方式2：邮箱 + 验证码 ──
        elif login_method == 'email':
            if not email or not email_code:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '请输入邮箱和验证码'})

            # 验证邮箱验证码
            session_code = session.get(f'verification_code_{email}')
            if not session_code or str(session_code) != str(email_code):
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '邮箱验证码错误或已过期'})
            session.pop(f'verification_code_{email}', None)

            cursor.execute(
                "SELECT id, Name, password, mail, phone, totp_secret, totp_enabled FROM user_info WHERE mail = %s",
                (email,)
            )
            user = cursor.fetchone()
            if not user:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '该邮箱未注册'})

        # ── 方式3：手机号 + 验证码 ──
        elif login_method == 'phone':
            if not phone or not phone_code:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '请输入手机号和验证码'})

            # 验证短信验证码
            pure_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
            if pure_phone not in sms_verification_codes:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '请先获取手机验证码'})

            stored = sms_verification_codes[pure_phone]
            if get_network_timestamp() - stored['timestamp'] > VERIFICATION_CODE_EXPIRE:
                del sms_verification_codes[pure_phone]
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '手机验证码已过期，请重新获取'})

            if stored['code'] != phone_code:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '手机验证码错误'})
            del sms_verification_codes[pure_phone]

            cursor.execute(
                "SELECT id, Name, password, mail, phone, totp_secret, totp_enabled FROM user_info WHERE phone = %s",
                (phone,)
            )
            user = cursor.fetchone()
            if not user:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '该手机号未注册'})

        else:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '未知的登录方式'})

        # ── 用户已验证，获取用户信息 ──
        user_id = user[0]
        user_name = user[1]
        user_mail = user[3]
        user_phone = user[4]
        user_totp_secret = user[5]
        user_totp_enabled = bool(user[6])

        # ── 风控检查 ──
        client_ip = request.remote_addr
        user_agent = request.user_agent.string
        browser_info = parse_user_agent(user_agent)
        place = get_ip_location(client_ip)
        is_danger = check_login_risk(user_id, client_ip, place, conn)

        # ── 读取 FORCE_MFA 配置 ──
        try:
            from config import FORCE_MFA
        except ImportError:
            FORCE_MFA = False

        # ── 判断是否需要 MFA ──
        # FORCE_MFA=True: 用户绑定了 MFA 就每次都验证
        # FORCE_MFA=False: 仅在风控检测到异常（is_danger=1）时才触发 MFA
        mfa_required = False
        mfa_types = []

        if user_totp_enabled and user_totp_secret:
            mfa_types.append('totp')

        cursor_sk = conn.cursor()
        cursor_sk.execute(
            "SELECT COUNT(*) FROM security_keys WHERE user_id = %s",
            (user_id,)
        )
        has_webauthn = cursor_sk.fetchone()[0] > 0
        cursor_sk.close()
        if has_webauthn:
            mfa_types.append('webauthn')

        user_has_mfa = len(mfa_types) > 0

        print(f'[MFA-决策] user={user_name}, FORCE_MFA={FORCE_MFA}, is_danger={is_danger}, user_has_mfa={user_has_mfa}, mfa_types={mfa_types}', flush=True)

        if user_has_mfa and (FORCE_MFA or is_danger == 1):
            mfa_required = True
            print(f'[MFA-决策] 触发MFA验证', flush=True)

        if mfa_required:
            session['pending_user_id'] = user_id
            session['pending_username'] = user_name
            session['pending_is_cookie'] = is_cookie
            session['pending_user_phone'] = user_phone
            session['pending_user_mail'] = user_mail
            session.permanent = True
            current_app.permanent_session_lifetime = timedelta(minutes=5)

            cursor.close()
            conn.close()

            return jsonify({
                'success': True,
                'message': '需要多因子认证',
                'requires_mfa': True,
                'mfa_types': mfa_types
            })

        # ── 无 MFA 时的二次验证（风控异常且未绑定 MFA） ──
        if is_danger == 1 and not user_has_mfa:
            verification_code = generate_verification_code()
            session[f'2fa_code_{user_id}'] = verification_code
            session.permanent = True
            current_app.permanent_session_lifetime = timedelta(minutes=5)

            print(f'[登录二次验证] 开始发送二次验证邮件')
            send_success, error_msg = send_2fa_verification_email(user_mail, verification_code)
            if send_success:
                print(f'[登录二次验证] 邮件发送成功')
            else:
                print(f'[登录二次验证] 邮件发送失败: {error_msg}')

            session['pending_user_id'] = user_id
            session['pending_username'] = user_name
            session['pending_is_cookie'] = is_cookie
            session['pending_user_phone'] = user_phone
            session['pending_user_mail'] = user_mail

            cursor.close()
            conn.close()

            return jsonify({
                'success': True,
                'message': '需要二次验证',
                'requires_2fa': True
            })

        # ── 直接登录 ──
        session['logged_in'] = True
        session['user_id'] = user_id
        session['username'] = user_name

        session.permanent = True
        if is_cookie == 1:
            current_app.permanent_session_lifetime = timedelta(days=7)
        else:
            current_app.permanent_session_lifetime = timedelta(minutes=10)

        log_time = get_network_time().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        cursor.execute("""
            INSERT INTO login_log (`user_id`, ip, time, is_danger, browser, is_cookie, place)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, client_ip, log_time, 0, browser_info, is_cookie, place))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': '登录成功'})

    except Exception as e:
        print(f"登录失败: {e}")
        return jsonify({'success': False, 'message': '登录失败，请稍后重试'})

@auth_bp.route('/verify-2fa', methods=['POST'])
def verify_2fa():
    try:
        email_code = request.form.get('email_code')
        phone_code = request.form.get('phone_code')

        if 'pending_user_id' not in session:
            return jsonify({'success': False, 'message': '验证会话已过期，请重新登录'})

        user_id = session['pending_user_id']
        expected_email_code = session.get(f'2fa_code_{user_id}')
        user_phone = session.get('pending_user_phone')

        if not expected_email_code or email_code != expected_email_code:
            return jsonify({'success': False, 'message': '邮箱验证码错误'})

        if user_phone:
            expected_phone_code = session.get(f'2fa_sms_code_{user_id}')
            if not expected_phone_code or phone_code != expected_phone_code:
                return jsonify({'success': False, 'message': '手机验证码错误'})

        client_ip = request.remote_addr
        user_agent = request.user_agent.string
        browser_info = parse_user_agent(user_agent)
        place = get_ip_location(client_ip)

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            log_time = get_network_time().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            is_cookie = session.get('pending_is_cookie', 0)
            cursor.execute("""
                INSERT INTO login_log (`user_id`, ip, time, is_danger, browser, is_cookie, place)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, client_ip, log_time, 1, browser_info, is_cookie, place))
            conn.commit()
            cursor.close()
            conn.close()

        session['logged_in'] = True
        session['user_id'] = user_id
        session['username'] = session.get('pending_username')

        is_cookie = session.get('pending_is_cookie', 0)
        session.permanent = True
        if is_cookie == 1:
            current_app.permanent_session_lifetime = timedelta(days=7)
        else:
            current_app.permanent_session_lifetime = timedelta(minutes=10)

        session.pop('pending_user_id', None)
        session.pop('pending_username', None)
        session.pop('pending_is_cookie', None)
        session.pop('pending_user_phone', None)
        session.pop('pending_user_mail', None)
        session.pop(f'2fa_code_{user_id}', None)
        session.pop(f'2fa_sms_code_{user_id}', None)

        return jsonify({'success': True, 'message': '验证成功'})

    except Exception as e:
        print(f"二次验证失败: {e}")
        return jsonify({'success': False, 'message': '验证失败，请稍后重试'})

@auth_bp.route('/verify-mfa-totp', methods=['POST'])
def verify_mfa_totp():
    """登录时验证 TOTP 验证码"""
    try:
        if 'pending_user_id' not in session:
            return jsonify({'success': False, 'message': '验证会话已过期，请重新登录'})

        user_id = session['pending_user_id']
        code = request.form.get('totp_code') or (request.get_json() or {}).get('code', '')

        if not code or len(code) != 6:
            return jsonify({'success': False, 'message': '请输入6位验证码'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500

        cursor = conn.cursor()
        cursor.execute(
            "SELECT totp_secret FROM user_info WHERE id = %s AND totp_enabled = 1",
            (user_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row or not row[0]:
            return jsonify({'success': False, 'message': '未绑定 Authenticator'}), 400

        totp = pyotp.TOTP(row[0])
        if not totp.verify(code, valid_window=1):
            return jsonify({'success': False, 'message': '验证码错误，请重试'})

        return _complete_mfa_login()

    except Exception as e:
        print(f"TOTP验证失败: {e}")
        return jsonify({'success': False, 'message': '验证失败，请稍后重试'})


@auth_bp.route('/verify-mfa-webauthn', methods=['POST'])
def verify_mfa_webauthn():
    """WebAuthn 验证完成后调用此接口完成登录"""
    try:
        if 'pending_user_id' not in session:
            return jsonify({'success': False, 'message': '验证会话已过期，请重新登录'})
        return _complete_mfa_login()
    except Exception as e:
        print(f"WebAuthn登录完成失败: {e}")
        return jsonify({'success': False, 'message': '登录完成失败，请稍后重试'})


def _complete_mfa_login():
    """完成 MFA 登录流程"""
    user_id = session['pending_user_id']

    client_ip = request.remote_addr
    user_agent = request.user_agent.string
    browser_info = parse_user_agent(user_agent)
    place = get_ip_location(client_ip)

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        log_time = get_network_time().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        is_cookie = session.get('pending_is_cookie', 0)
        cursor.execute("""
            INSERT INTO login_log (`user_id`, ip, time, is_danger, browser, is_cookie, place)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, client_ip, log_time, 0, browser_info, is_cookie, place))
        conn.commit()
        cursor.close()
        conn.close()

    session['logged_in'] = True
    session['user_id'] = user_id
    session['username'] = session.get('pending_username')

    is_cookie = session.get('pending_is_cookie', 0)
    session.permanent = True
    if is_cookie == 1:
        current_app.permanent_session_lifetime = timedelta(days=7)
    else:
        current_app.permanent_session_lifetime = timedelta(minutes=10)

    session.pop('pending_user_id', None)
    session.pop('pending_username', None)
    session.pop('pending_is_cookie', None)
    session.pop('pending_user_phone', None)
    session.pop('pending_user_mail', None)

    return jsonify({'success': True, 'message': '登录成功'})

# ════════════════════════════════════════════════════════════════
#  MFA 多因子认证组合接口
# ════════════════════════════════════════════════════════════════

@auth_bp.route('/check-mfa-combos', methods=['GET'])
def check_mfa_combos():
    """返回当前待登录用户可用的 MFA 组合"""
    try:
        if 'pending_user_id' not in session:
            return jsonify({'success': False, 'message': '验证会话已过期，请重新登录'})

        user_id = session['pending_user_id']
        user_mail = session.get('pending_user_mail', '')
        user_phone = session.get('pending_user_phone', '')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500

        cursor = conn.cursor()
        cursor.execute(
            "SELECT totp_secret, totp_enabled FROM user_info WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()
        has_totp = bool(user and user[1] and user[0])

        cursor.execute(
            "SELECT COUNT(*) FROM security_keys WHERE user_id = %s",
            (user_id,)
        )
        has_webauthn = cursor.fetchone()[0] > 0
        cursor.close()
        conn.close()

        has_email = bool(user_mail)
        has_phone = bool(user_phone)

        combos = []
        if has_email and has_totp:
            combos.append('email_totp')
        if has_phone and has_totp:
            combos.append('phone_totp')
        if has_email and has_phone:
            combos.append('email_phone')
        if has_email and has_webauthn:
            combos.append('email_webauthn')
        if has_phone and has_webauthn:
            combos.append('phone_webauthn')

        return jsonify({'success': True, 'combos': combos})

    except Exception as e:
        print(f"获取MFA组合失败: {e}")
        return jsonify({'success': False, 'message': '获取验证选项失败'})


@auth_bp.route('/verify-mfa-combo', methods=['POST'])
def verify_mfa_combo():
    """验证 MFA 组合"""
    try:
        if 'pending_user_id' not in session:
            return jsonify({'success': False, 'message': '验证会话已过期，请重新登录'})

        user_id = session['pending_user_id']
        combo = request.form.get('combo', '')
        email_code = request.form.get('email_code', '')
        phone_code = request.form.get('phone_code', '')
        totp_code = request.form.get('totp_code', '')

        needs_email = combo in ('email_totp', 'email_phone', 'email_webauthn')
        needs_phone = combo in ('phone_totp', 'email_phone', 'phone_webauthn')
        needs_totp = combo in ('email_totp', 'phone_totp')
        needs_webauthn = combo in ('email_webauthn', 'phone_webauthn')

        # ── 验证邮箱验证码 ──
        if needs_email:
            if not email_code or len(email_code) != 6 or not email_code.isdigit():
                return jsonify({'success': False, 'message': '请输入6位邮箱验证码'})
            stored_code = session.get(f'mfa_email_code_{user_id}')
            if not stored_code or str(stored_code) != str(email_code):
                return jsonify({'success': False, 'message': '邮箱验证码错误或已过期'})
            session.pop(f'mfa_email_code_{user_id}', None)

        # ── 验证手机验证码 ──
        if needs_phone:
            if not phone_code or len(phone_code) != 6 or not phone_code.isdigit():
                return jsonify({'success': False, 'message': '请输入6位手机验证码'})
            stored_code = session.get(f'mfa_sms_code_{user_id}')
            if not stored_code or str(stored_code) != str(phone_code):
                return jsonify({'success': False, 'message': '手机验证码错误或已过期'})
            session.pop(f'mfa_sms_code_{user_id}', None)

        # ── 验证 TOTP ──
        if needs_totp:
            if not totp_code or len(totp_code) != 6 or not totp_code.isdigit():
                return jsonify({'success': False, 'message': '请输入6位Authenticator验证码'})

            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': '数据库连接失败'}), 500
            cursor = conn.cursor()
            cursor.execute(
                "SELECT totp_secret FROM user_info WHERE id = %s AND totp_enabled = 1",
                (user_id,)
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if not row or not row[0]:
                return jsonify({'success': False, 'message': '未绑定 Authenticator'})

            totp = pyotp.TOTP(row[0])
            if not totp.verify(totp_code, valid_window=1):
                return jsonify({'success': False, 'message': 'Authenticator 验证码错误'})

        # ── 验证 WebAuthn（必须有 session 标记） ──
        if needs_webauthn:
            if not session.get('mfa_webauthn_verified'):
                return jsonify({'success': False, 'message': '请先完成安全密钥验证'})
            session.pop('mfa_webauthn_verified', None)

        return _complete_mfa_login()

    except Exception as e:
        print(f"MFA组合验证失败: {e}")
        return jsonify({'success': False, 'message': '验证失败，请稍后重试'})


@auth_bp.route('/send-mfa-email-code', methods=['POST'])
def send_mfa_email_code():
    """发送 MFA 邮箱验证码"""
    try:
        if 'pending_user_id' not in session:
            return jsonify({'success': False, 'message': '验证会话已过期，请重新登录'})

        user_id = session['pending_user_id']
        user_mail = session.get('pending_user_mail', '')

        if not user_mail:
            return jsonify({'success': False, 'message': '未绑定邮箱'})

        code = generate_verification_code()
        session[f'mfa_email_code_{user_id}'] = code
        session.permanent = True
        current_app.permanent_session_lifetime = timedelta(minutes=5)

        send_success, error_msg = send_verification_email(user_mail, code, purpose='mfa')
        if send_success:
            return jsonify({'success': True, 'message': '验证码已发送到您的邮箱'})
        else:
            session.pop(f'mfa_email_code_{user_id}', None)
            return jsonify({'success': False, 'message': f'发送失败: {error_msg}'})

    except Exception as e:
        print(f"发送MFA邮箱验证码失败: {e}")
        return jsonify({'success': False, 'message': '发送失败，请稍后重试'})


@auth_bp.route('/send-mfa-sms-code', methods=['POST'])
def send_mfa_sms_code():
    """发送 MFA 手机验证码"""
    try:
        if 'pending_user_id' not in session:
            return jsonify({'success': False, 'message': '验证会话已过期，请重新登录'})

        user_id = session['pending_user_id']
        user_phone = session.get('pending_user_phone', '')

        if not user_phone:
            return jsonify({'success': False, 'message': '未绑定手机号'})

        success, error_msg, code = send_sms(user_phone)
        if success:
            session[f'mfa_sms_code_{user_id}'] = code
            session.permanent = True
            current_app.permanent_session_lifetime = timedelta(minutes=5)
            return jsonify({'success': True, 'message': '验证码已发送到您的手机'})
        else:
            return jsonify({'success': False, 'message': f'发送失败: {error_msg}'})

    except Exception as e:
        print(f"发送MFA短信验证码失败: {e}")
        return jsonify({'success': False, 'message': '发送失败，请稍后重试'})


@auth_bp.route('/check-2fa-phone', methods=['GET'])
def check_2fa_phone():
    try:
        if 'pending_user_id' not in session:
            return jsonify({'success': False, 'message': '验证会话已过期'})

        user_phone = session.get('pending_user_phone')

        if user_phone:
            return jsonify({'success': True, 'has_phone': True, 'phone': user_phone})
        else:
            return jsonify({'success': True, 'has_phone': False})
    except Exception as e:
        print(f"检查手机号失败: {e}")
        return jsonify({'success': False, 'message': '检查失败'})

@auth_bp.route('/send-2fa-sms-code', methods=['POST'])
def send_2fa_sms_code():
    try:
        if 'pending_user_id' not in session:
            return jsonify({'success': False, 'message': '验证会话已过期，请重新登录'})

        data = request.get_json()
        phone = data.get('phone')

        if not phone:
            return jsonify({'success': False, 'message': '请输入手机号码'})

        success, error_msg, code = send_sms(phone)
        print(f'二次验证阿里云返回的验证码: {code}')

        if success:
            session[f'2fa_sms_code_{session["pending_user_id"]}'] = code
            session.permanent = True
            current_app.permanent_session_lifetime = timedelta(minutes=5)
            return jsonify({'success': True, 'message': '验证码发送成功'})
        else:
            return jsonify({'success': False, 'message': f'验证码发送失败: {error_msg}'})
    except Exception as e:
        print(f"发送二次验证短信失败: {e}")
        return jsonify({'success': False, 'message': '发送失败，请稍后重试'})

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('login.html', mode='register', turnstile_enabled=TURNSTILE_ENABLED, turnstile_sitekey=TURNSTILE_SITEKEY)
    else:
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            email = request.form.get('email')
            verification_code = request.form.get('verification_code')
            phone = request.form.get('phone')
            sms_verification_code = request.form.get('sms_verification_code')
            avatar = request.files.get('avatar')
            turnstile_response = request.form.get('cf-turnstile-response')

            if TURNSTILE_ENABLED:
                if not turnstile_response:
                    return jsonify({'success': False, 'message': '请完成人机验证'})

                if not verify_turnstile(turnstile_response, request.remote_addr):
                    return jsonify({'success': False, 'message': '人机验证失败，请重试'})

            session_code = session.get(f'verification_code_{email}')
            print(f'========== 注册验证邮箱验证码 ==========')
            print(f'邮箱: {email}')
            print(f'用户输入验证码: {verification_code} (类型: {type(verification_code)})')
            print(f'Session中验证码: {session_code} (类型: {type(session_code)})')
            
            if not session_code or str(session_code) != str(verification_code):
                print(f'[注册失败] 验证码不匹配')
                return jsonify({'success': False, 'message': '验证码错误或已过期'})
            print(f'[注册验证] 验证码匹配成功')

            session.pop(f'verification_code_{email}', None)

            if not phone:
                return jsonify({'success': False, 'message': '请输入手机号码'})

            if not sms_verification_code:
                return jsonify({'success': False, 'message': '请输入手机验证码'})

            pure_phone = ''.join(c for c in phone if c.isdigit() or c == '+')

            if pure_phone not in sms_verification_codes:
                return jsonify({'success': False, 'message': '请先获取手机验证码'})

            stored = sms_verification_codes[pure_phone]
            if get_network_timestamp() - stored['timestamp'] > VERIFICATION_CODE_EXPIRE:
                del sms_verification_codes[pure_phone]
                return jsonify({'success': False, 'message': '手机验证码已过期，请重新获取'})

            if stored['code'] != sms_verification_code:
                return jsonify({'success': False, 'message': '手机验证码错误'})

            del sms_verification_codes[pure_phone]

            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM user_info WHERE Name = %s", (username,))
            if cursor.fetchone()[0] > 0:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '用户名已存在，请更换用户名'})

            cursor.execute("SELECT COUNT(*) FROM user_info WHERE mail = %s", (email,))
            if cursor.fetchone()[0] > 0:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '邮箱已被注册，请更换邮箱'})

            avatar_path = '/static/img/default_avatar.png'
            hashed_password = hash_password(password)
            
            # 生成唯一的用户ID
            new_user_id = generate_user_id()
            # 确保ID唯一
            while True:
                cursor.execute("SELECT id FROM user_info WHERE id = %s", (new_user_id,))
                if not cursor.fetchone():
                    break
                new_user_id = generate_user_id()

            cursor.execute("""
            INSERT INTO user_info (id, Name, password, mail, phone)
            VALUES (%s, %s, %s, %s, %s)
            """, (new_user_id, username, hashed_password, email, phone))
            
            conn.commit()

            if avatar and avatar.filename:
                upload_dir = 'static/img/user_avatar'
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)

                extension = avatar.filename.rsplit('.', 1)[1].lower() if '.' in avatar.filename else 'png'

                avatar_filename = f"{new_user_id}.{extension}"
                avatar_path = f"/static/img/user_avatar/{avatar_filename}"
                avatar.save(os.path.join(current_app.config['PROJECT_ROOT'], avatar_path[1:]))
                
                # 更新用户头像路径
                cursor.execute("UPDATE user_info SET avatar = %s WHERE id = %s", (avatar_path, new_user_id))
                conn.commit()

            cursor.close()
            conn.close()

            return jsonify({'success': True, 'message': '注册成功'})
        except Exception as e:
            print(f"注册失败: {e}")
            return jsonify({'success': False, 'message': '注册失败，请稍后重试'})

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('forgot_password.html')
    else:
        step = request.form.get('step', 'verify')

        if step == 'verify':
            username = request.form.get('username')
            email = request.form.get('email')
            verification_code = request.form.get('verification_code')

            if not all([username, email, verification_code]):
                return jsonify({'success': False, 'message': '请填写所有必填字段'})

            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

            cursor = conn.cursor()
            cursor.execute("SELECT id FROM user_info WHERE Name = %s AND mail = %s", (username, email))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if not user:
                return jsonify({'success': False, 'message': '用户名或邮箱不正确'})

            session_code = session.get(f'verification_code_{email}')
            if not session_code or session_code != verification_code:
                return jsonify({'success': False, 'message': '验证码不正确'})

            token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
            session['reset_token'] = token
            session['reset_user_id'] = user[0]

            return jsonify({'success': True, 'message': '验证成功，请重置密码', 'token': token})

        elif step == 'reset':
            token = request.form.get('token')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if session.get('reset_token') != token or not session.get('reset_user_id'):
                return jsonify({'success': False, 'message': '验证失败，请重新开始'})

            if new_password != confirm_password:
                return jsonify({'success': False, 'message': '两次输入的密码不一致'})

            if not is_password_strong(new_password):
                return jsonify({'success': False, 'message': '密码必须超过6位，包含数字、大小写字母及特殊符号'})

            user_id = session['reset_user_id']
            hashed_password = hash_password(new_password)

            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE user_info SET password = %s WHERE id = %s", (hashed_password, user_id))
                conn.commit()

                session.pop('reset_token', None)
                session.pop('reset_user_id', None)

                cursor.close()
                conn.close()
                return jsonify({'success': True, 'message': '密码重置成功！'})
            except Exception as e:
                conn.rollback()
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': f'密码重置失败：{str(e)}'})

    return jsonify({'success': False, 'message': '无效的请求'})

@auth_bp.route('/logout')
def logout():
    user_id = session.get('user_id')
    
    cleanup_user_authorizations(user_id)
    
    session.clear()
    return jsonify({'success': True, 'message': '退出成功'})


def cleanup_user_authorizations(user_id):
    """清理用户的所有授权码"""
    if not user_id:
        return
    
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM developer_authorizations WHERE user_id = %s",
                (user_id,)
            )
            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            print(f"[授权清理] 已删除用户 {user_id} 的 {deleted_count} 条授权码")
        else:
            print(f"[授权清理] 数据库连接失败，无法清理用户 {user_id} 的授权码")
    except Exception as e:
        print(f"[授权清理] 清理用户 {user_id} 的授权码时发生错误: {e}")

@auth_bp.route('/send_code', methods=['POST'])
def send_code():
    try:
        email = request.json.get('email') if request.is_json else request.form.get('email')
        purpose = request.json.get('purpose', 'register') if request.is_json else request.form.get('purpose', 'register')
        turnstile_response = request.json.get('cf-turnstile-response') if request.is_json else request.form.get('cf-turnstile-response')
        client_ip = request.remote_addr

        is_logged_in = session.get('logged_in', False)

        print(f'========== 发送邮箱验证码日志 ==========')
        print(f'请求时间: {get_network_time()}')
        print(f'邮箱地址: {email}')
        print(f'用途: {purpose}')
        print(f'请求IP: {client_ip}')
        print(f'已登录: {is_logged_in}')
        print(f'=======================================')
        
        if not email:
            print(f'[邮箱验证码] 失败：缺少邮箱地址')
            print(f'[邮箱验证码日志] 已记录 - 邮箱: unknown, 类型: {purpose}, 状态: failed, 错误: 缺少邮箱地址')
            return jsonify({'success': False, 'message': '请输入邮箱地址'})

        if TURNSTILE_ENABLED and not is_logged_in and purpose != 'login':
            if not turnstile_response:
                print(f'[邮箱验证码] 失败：未完成人机验证')
                print(f'[邮箱验证码日志] 已记录 - 邮箱: {email}, 类型: {purpose}, 状态: failed, 错误: 未完成人机验证')
                return jsonify({'success': False, 'message': '请完成人机验证'})

            if not verify_turnstile(turnstile_response, client_ip):
                print(f'[邮箱验证码] 失败：人机验证失败')
                print(f'[邮箱验证码日志] 已记录 - 邮箱: {email}, 类型: {purpose}, 状态: failed, 错误: 人机验证失败')
                return jsonify({'success': False, 'message': '人机验证失败，请重试'})

        code = generate_verification_code()
        print(f'[邮箱验证码] 生成验证码: {code}')

        session[f'verification_code_{email}'] = code
        session.permanent = True
        current_app.permanent_session_lifetime = timedelta(minutes=5)
        print(f'[邮箱验证码] 验证码已存入Session，有效期5分钟')

        print(f'[邮箱验证码] 开始发送邮件...')
        send_success, error_msg = send_verification_email(email, code, purpose=purpose)

        if send_success:
            print(f'[邮箱验证码] 发送成功！')
            print(f'[邮箱验证码日志] 已记录 - 邮箱: {email}, 类型: {purpose}, 状态: success')
            return jsonify({'success': True, 'message': '验证码已发送，请查收邮箱'})
        else:
            print(f'[邮箱验证码] 发送失败: {error_msg}')
            print(f'[邮箱验证码日志] 已记录 - 邮箱: {email}, 类型: {purpose}, 状态: failed, 错误: {error_msg}')
            return jsonify({'success': False, 'message': '发送验证码失败，请稍后重试'})
    except Exception as e:
        print(f'[邮箱验证码] 异常: {e}')
        import traceback
        traceback.print_exc()
        email_for_log = request.json.get('email') if request.is_json else request.form.get('email', 'unknown')
        print(f'[邮箱验证码日志] 已记录 - 邮箱: {email_for_log}, 类型: {purpose}, 状态: error, 错误: {str(e)}')
        return jsonify({'success': False, 'message': '发送验证码失败，请稍后重试'})

@auth_bp.route('/verify_code', methods=['POST'])
def verify_code():
    try:
        email = request.form.get('email')
        code = request.form.get('code')

        print(f'========== 验证邮箱验证码 ==========')
        print(f'请求时间: {get_network_time()}')
        print(f'邮箱地址: {email}')
        print(f'用户输入验证码: {code} (类型: {type(code)})')

        if not email or not code:
            print(f'[验证失败] 缺少邮箱或验证码')
            return jsonify({'valid': False})

        session_key = f'verification_code_{email}'
        session_code = session.get(session_key)
        print(f'Session键: {session_key}')
        print(f'Session中存储的验证码: {session_code} (类型: {type(session_code)})')
        print(f'当前Session中所有键: {list(session.keys())}')

        if session_code is not None:
            # 确保字符串比较，避免类型问题
            if str(session_code) == str(code):
                print(f'[验证成功] 验证码匹配')
                return jsonify({'valid': True})
            else:
                print(f'[验证失败] 验证码不匹配')
                return jsonify({'valid': False})
        else:
            print(f'[验证失败] Session中未找到验证码')
            return jsonify({'valid': False})
    except Exception as e:
        print(f"验证验证码异常: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'valid': False})

@auth_bp.route('/api/send-sms-code', methods=['POST'])
def send_sms_code():
    data = request.get_json()
    phone = data.get('phone')

    print(f'收到发送验证码请求, 手机号: {phone}')

    if not phone:
        return jsonify({'success': False, 'message': '请输入手机号码'})

    pure_phone = ''.join(c for c in phone if c.isdigit() or c == '+')

    if pure_phone in sms_verification_codes:
        if get_network_timestamp() - sms_verification_codes[pure_phone]['timestamp'] < 60:
            return jsonify({'success': False, 'message': '请60秒后再试'})

    success, error_msg, code = send_sms(phone)

    print(f'========== 发送验证码调试 ==========')
    print(f'原始手机号: {phone}')
    print(f'统一后手机号: {pure_phone}')
    print(f'验证码: {code}')
    print(f'==================================')

    if success:
        sms_verification_codes[pure_phone] = {
            'code': code,
            'timestamp': get_network_timestamp()
        }
        print(f'验证码已存储，当前存储的手机号: {list(sms_verification_codes.keys())}')
        return jsonify({'success': True, 'message': '验证码发送成功'})
    else:
        return jsonify({'success': False, 'message': f'验证码发送失败: {error_msg}'})

@auth_bp.route('/api/verify-sms-code', methods=['POST'])
def verify_sms_code():
    data = request.get_json()
    phone = data.get('phone')
    code = data.get('code')

    print(f'验证验证码 - 手机号: {phone}, 验证码: {code}')

    if not phone or not code:
        return jsonify({'success': False, 'message': '请输入手机号码和验证码'})

    pure_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
    print(f'统一格式后的手机号: {pure_phone}')

    if pure_phone not in sms_verification_codes:
        print(f'未找到验证码记录，当前存储的手机号: {list(sms_verification_codes.keys())}')
        return jsonify({'success': False, 'message': '请先获取验证码'})

    stored = sms_verification_codes[pure_phone]
    print(f'存储的验证码: {stored["code"]}')

    if get_network_timestamp() - stored['timestamp'] > VERIFICATION_CODE_EXPIRE:
        del sms_verification_codes[pure_phone]
        return jsonify({'success': False, 'message': '验证码已过期，请重新获取'})

    if stored['code'] == code:
        stored['verified'] = True
        print(f'验证码已验证通过，标记为verified')
        return jsonify({'success': True, 'message': '验证成功'})
    else:
        return jsonify({'success': False, 'message': '验证码错误'})

@auth_bp.route('/verify_user', methods=['POST'])
def verify_user():
    try:
        username = request.form.get('username')
        email = request.form.get('email')

        if not username or not email:
            return jsonify({'success': False, 'message': '请输入用户名和邮箱'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

        cursor = conn.cursor()

        cursor.execute("SELECT id, Name, mail, phone FROM user_info WHERE Name = %s AND mail = %s", (username, email))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            raw_phone = user[3] if user[3] else ''
            pure_phone = ''.join(c for c in raw_phone if c.isdigit())

            user_info = {
                'user_id': user[0],
                'username': user[1],
                'email': user[2],
                'phone': pure_phone
            }
            return jsonify({'success': True, 'userInfo': user_info})
        else:
            return jsonify({'success': False, 'message': '用户名与邮箱不匹配，请检查输入'})

    except Exception as e:
        print(f"验证用户失败: {e}")
        return jsonify({'success': False, 'message': '验证失败，请稍后重试'})

@auth_bp.route('/reset_password', methods=['POST'])
def reset_password():
    try:
        user_id = request.form.get('user_id')
        username = request.form.get('username')
        new_password = request.form.get('new_password')
        email = request.form.get('email')
        verification_code = request.form.get('verification_code')
        phone = request.form.get('phone')
        sms_verification_code = request.form.get('sms_verification_code')

        print(f"重置密码请求 - user_id: {user_id}, username: {username}, email: {email}, phone: {phone}")

        if not all([username, new_password, email, verification_code, phone, sms_verification_code]):
            print("错误：缺少必填字段")
            return jsonify({'success': False, 'message': '请填写所有必填字段'})

        session_code = session.get(f'verification_code_{email}')
        print(f"邮箱验证码检查 - 输入: {verification_code}, Session中: {session_code}")
        if not session_code or session_code != verification_code:
            print("错误：邮箱验证码错误或已过期")
            return jsonify({'success': False, 'message': '邮箱验证码错误或已过期'})

        pure_phone = ''.join(c for c in phone if c.isdigit() or c == '+')

        print(f'========== 重置密码手机号调试 ==========')
        print(f'原始手机号: {phone}')
        print(f'统一后手机号: {pure_phone}')
        print(f'sms_verification_codes中存储的所有key: {list(sms_verification_codes.keys())}')
        print(f'pure_phone in sms_verification_codes: {pure_phone in sms_verification_codes}')
        if pure_phone in sms_verification_codes:
            print(f'找到的验证码: {sms_verification_codes[pure_phone]}')
        print(f'==========================================')

        if pure_phone not in sms_verification_codes:
            print("错误：未找到手机验证码记录，可能的原因：")
            print("1. 手机号格式不一致")
            print("2. 验证码已过期（有效期5分钟）")
            print("3. Session已过期")
            return jsonify({'success': False, 'message': '请先获取手机验证码'})

        stored = sms_verification_codes[pure_phone]

        if not stored.get('verified'):
            print("错误：手机验证码未验证或验证失败")
            return jsonify({'success': False, 'message': '请先验证手机验证码'})

        if get_network_timestamp() - stored['timestamp'] > VERIFICATION_CODE_EXPIRE:
            del sms_verification_codes[pure_phone]
            print("错误：手机验证码已过期")
            return jsonify({'success': False, 'message': '手机验证码已过期，请重新获取'})

        if stored['code'] != sms_verification_code:
            print(f"错误：手机验证码验证失败，存储的验证码: {stored['code']}，输入的验证码: {sms_verification_code}")
            return jsonify({'success': False, 'message': '手机验证码错误'})

        del sms_verification_codes[pure_phone]

        conn = get_db_connection()
        if not conn:
            print("错误：数据库连接失败")
            return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

        cursor = conn.cursor()

        print(f"查询用户: username={username}, email={email}, phone={phone}")
        cursor.execute("SELECT id, phone FROM user_info WHERE Name = %s AND mail = %s", (username, email))
        user = cursor.fetchone()

        if not user:
            print("错误：用户信息验证失败，未找到用户")
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '用户信息验证失败'})

        db_phone = user[1] if user[1] else ''
        db_pure_phone = ''.join(c for c in db_phone if c.isdigit())
        input_pure_phone = ''.join(c for c in phone if c.isdigit())

        print(f"数据库手机号: {db_phone}, 提取后: {db_pure_phone}")
        print(f"用户输入手机号: {phone}, 提取后: {input_pure_phone}")

        # 比较手机号时，考虑可能的国家代码前缀，只比较后11位（中国手机号长度）
        phone_match = False
        if db_pure_phone and input_pure_phone:
            if len(db_pure_phone) >= 11 and len(input_pure_phone) >= 11:
                phone_match = db_pure_phone[-11:] == input_pure_phone[-11:]
            else:
                phone_match = db_pure_phone == input_pure_phone
        
        if not phone_match:
            print("错误：手机号不匹配")
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '用户信息验证失败'})

        print(f"找到用户ID: {user[0]}")

        if not is_password_strong(new_password):
            print("错误：密码强度不符合要求")
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '密码必须超过6位，包含数字、大小写字母及特殊符号'})

        hashed_password = hash_password(new_password)
        print("密码哈希完成")

        try:
            print(f"准备更新用户 {user[0]} 的密码")
            cursor.execute("UPDATE user_info SET password = %s WHERE id = %s", (hashed_password, user[0]))
            conn.commit()
            print(f"密码更新成功，影响行数: {cursor.rowcount}")

            session.pop(f'verification_code_{email}', None)
            print("验证码会话已清除")

            cursor.close()
            conn.close()
            return jsonify({'success': True, 'message': '密码重置成功！'})
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            print(f"更新密码失败: {e}")
            return jsonify({'success': False, 'message': '更新密码失败，请稍后重试'})

    except Exception as e:
        print(f"重置密码失败: {e}")
        return jsonify({'success': False, 'message': '密码重置失败，请稍后重试'})


@auth_bp.route('/oauth/authorize', methods=['GET'])
def oauth_authorize():
    app_id = request.args.get('app_id')
    redirect_uri = request.args.get('redirect_uri')
    state = request.args.get('state', '')

    if not app_id:
        return jsonify({'success': False, 'message': '缺少app_id参数'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': '数据库连接失败'}), 500

    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("""
            SELECT da.id, da.name, da.description, da.owner, da.website,
                   ac.login_callback_url, ac.verification_callback_url, ac.scope
            FROM developer_apps da
            LEFT JOIN app_configurations ac ON da.id = ac.app_id
            WHERE da.id = %s AND da.status = 'approved'
        """, (app_id,))
        app = cursor.fetchone()
        cursor.close()
        conn.close()

        if not app:
            return jsonify({'success': False, 'message': '应用不存在或未通过审核'}), 404

        app_id_db = app['id']
        app_name = app['name']
        app_description = app['description']
        app_owner = app['owner']
        app_website = app['website']
        login_callback_url = app['login_callback_url']
        verification_callback_url = app['verification_callback_url']
        scope_json = app['scope']

        import json
        try:
            permissions = json.loads(scope_json) if scope_json else ['userinfo']
        except:
            permissions = ['userinfo']

        if redirect_uri and login_callback_url and redirect_uri != login_callback_url:
            return jsonify({'success': False, 'message': 'redirect_uri不匹配'}), 400

        if 'logged_in' not in session or not session['logged_in']:
            return redirect(f'/login?redirect_uri=/oauth/authorize?app_id={app_id}&redirect_uri={redirect_uri or ""}&state={state}')

        user_id = session.get('user_id')
        username = session.get('username')

        return render_template('oauth_authorize.html',
                             app_id=app_id_db,
                             app_name=app_name,
                             app_description=app_description,
                             app_owner=app_owner,
                             app_website=app_website,
                             permissions=permissions,
                             redirect_uri=redirect_uri or login_callback_url or '',
                             state=state)

    except Exception as e:
        print(f"OAuth授权页面加载失败: {e}")
        if conn:
            conn.close()
        return jsonify({'success': False, 'message': '加载授权页面失败'}), 500


@auth_bp.route('/oauth/authorize/confirm', methods=['POST'])
def oauth_authorize_confirm():
    try:
        app_id = request.form.get('app_id')
        redirect_uri = request.form.get('redirect_uri')
        state = request.form.get('state', '')

        if not app_id:
            return jsonify({'success': False, 'message': '缺少app_id参数'}), 400

        if 'logged_in' not in session or not session['logged_in']:
            return jsonify({'success': False, 'message': '用户未登录'}), 401

        user_id = session.get('user_id')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500

        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("""
                SELECT da.id, da.name, ac.login_callback_url, ac.verification_callback_url
                FROM developer_apps da
                LEFT JOIN app_configurations ac ON da.id = ac.app_id
                WHERE da.id = %s AND da.status = 'approved'
            """, (app_id,))
            app = cursor.fetchone()

            if not app:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '应用不存在或未通过审核'}), 404

            app_id_db = app['id']
            app_name = app['name']
            login_callback_url = app['login_callback_url']
            verification_callback_url = app['verification_callback_url']

            if redirect_uri and login_callback_url and redirect_uri != login_callback_url:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'redirect_uri不匹配'}), 400

            cursor.execute("""
                SELECT id FROM developer_authorizations
                WHERE app_id = %s AND user_id = %s AND status = 'blacklisted'
            """, (app_id_db, user_id))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '你已取消该应用的授权，无法重新授权。如需恢复，请先在第三方安全管理中解除黑名单。'}), 403

            cursor.execute("""
                SELECT id, auth_code FROM developer_authorizations
                WHERE app_id = %s AND user_id = %s AND status = 'active' AND expires_at > %s
            """, (app_id_db, user_id, (lambda t: t.replace(tzinfo=None) if t.tzinfo else t)(get_network_time())))
            existing_auth = cursor.fetchone()

            if existing_auth:
                cursor.close()
                conn.close()
                callback_url = redirect_uri or login_callback_url
                result = {
                    'success': True,
                    'message': '已存在有效授权',
                    'auth_code': existing_auth['auth_code']
                }
                if callback_url:
                    params = {'auth_code': existing_auth['auth_code']}
                    if state:
                        params['state'] = state
                    result['redirect_url'] = f"{callback_url}?{urlencode(params)}"
                return jsonify(result)

            auth_code = ''.join(random.choices(string.ascii_letters + string.digits, k=30))
            created_at = (lambda t: t.replace(tzinfo=None) if t.tzinfo else t)(get_network_time())
            expires_at = created_at + timedelta(days=5)

            cursor.execute("""
                INSERT INTO developer_authorizations (app_id, user_id, auth_code, created_at, expires_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (app_id_db, user_id, auth_code, created_at, expires_at))

            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            cursor.execute("""
                INSERT INTO authorization_log (user_id, app_id, action, detail, ip, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, app_id_db, 'authorize', f'授权了应用 {app_name}', ip_address, created_at))

            conn.commit()
            cursor.close()
            conn.close()

            callback_url = redirect_uri or login_callback_url
            result = {'success': True, 'message': '授权成功', 'auth_code': auth_code}
            if callback_url:
                params = {'auth_code': auth_code}
                if state:
                    params['state'] = state
                result['redirect_url'] = f"{callback_url}?{urlencode(params)}"
            return jsonify(result)

        except Exception as e:
            print(f"确认授权失败: {e}")
            conn.rollback()
            if conn:
                cursor.close()
                conn.close()
            return jsonify({'success': False, 'message': '授权失败，请稍后重试'}), 500

    except Exception as e:
        print(f"确认授权失败: {e}")
        return jsonify({'success': False, 'message': '授权失败，请稍后重试'}), 500

