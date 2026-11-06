from flask import Blueprint, request, jsonify, session, render_template
from functools import wraps
from datetime import datetime
from werkzeug.security import check_password_hash
import base64
import hashlib
import json
import os
import string
import random
import re
import time
import pymysql
import urllib.request
import urllib.parse

from app.models.db import get_db_connection
from app.auth.utils import (
    get_network_time, generate_user_id, generate_verification_code,
    send_verification_email, send_sms, hash_password,
    normalize_scopes, parse_restrictions, is_scope_restricted,
    SCOPE_USERINFO, SCOPE_EMAIL, SCOPE_PHONE,
    SCOPE_EMAIL_CODE, SCOPE_PHONE_CODE
)
from app.auth.routes import login_required

developer_bp = Blueprint('developer', __name__)


@developer_bp.route('/developer-docs')
def developer_docs():
    return render_template('developer_docs.html')


@developer_bp.route('/developer-app-management')
def developer_app_management():
    return render_template('developer_app_management.html')


@developer_bp.route('/app-review')
def app_review():
    return render_template('app_review.html')


def is_developer(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return jsonify({'success': False, 'message': '用户未登录'}), 401

        user_id = session.get('user_id')
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_permission WHERE user_id = %s AND type = '开发者'", (user_id,))
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'message': '没有开发者权限'}), 403
                return jsonify({'success': False, 'message': '没有开发者权限'}), 403
            cursor.close()
            conn.close()
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': '权限验证失败'}), 500

        return f(*args, **kwargs)
    return decorated_function


def generate_app_id():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(15))


def _verify_app_secret(stored_secret: str, provided_secret: str) -> bool:
    """
    验证 app_secret
    兼容历史数据：数据库中可能存的是明文，也可能是 bcrypt 哈希
    - bcrypt 哈希格式：以 $2a$ / $2b$ / $2y$ 开头
    - 否则按明文比对
    """
    if stored_secret is None or provided_secret is None:
        return False
    if not stored_secret:
        return False
    if stored_secret.startswith(('$2a$', '$2b$', '$2y$', 'pbkdf2:')):
        try:
            return check_password_hash(stored_secret, provided_secret)
        except Exception:
            return False
    # 明文比对（恒定时间比较以防时序攻击）
    if len(stored_secret) != len(provided_secret):
        return False
    result = 0
    for a, b in zip(stored_secret, provided_secret):
        result |= ord(a) ^ ord(b)
    return result == 0


def generate_app_secret():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(64))


def validate_url(url):
    if not url:
        return True
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None


@developer_bp.route('/api/developer/create-app', methods=['POST'])
@login_required
@is_developer
def create_app():
    try:
        data = request.json
        app_name = data.get('name')
        description = data.get('description')
        owner = data.get('owner')
        website = data.get('website')
        scope = data.get('scope')
        auth_mode = (data.get('auth_mode') or 'native').strip().lower()

        if not app_name:
            return jsonify({'success': False, 'message': '应用名称不能为空'})

        if auth_mode not in ('native', 'oidc'):
            return jsonify({'success': False, 'message': '授权方式无效'})

        if len(app_name) > 100:
            return jsonify({'success': False, 'message': '应用名称不能超过100个字符'})

        if website and not validate_url(website):
            return jsonify({'success': False, 'message': '请输入有效的网址格式'})

        developer_id = session.get('user_id')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM developer_apps WHERE developer_id = %s AND name = %s", (developer_id, app_name))
        if cursor.fetchone()[0] > 0:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '您已创建过同名应用'})

        app_id = generate_app_id()
        while True:
            cursor.execute("SELECT id FROM developer_apps WHERE id = %s", (app_id,))
            if not cursor.fetchone():
                break
            app_id = generate_app_id()

        app_secret = generate_app_secret()
        created_at = get_network_time()
        # 授权方式与权限范围在创建时一次性确定，之后只读
        normalized_scope = normalize_scopes(scope, auth_mode)

        cursor.execute("""
            INSERT INTO developer_apps (id, developer_id, name, description, owner, website, app_secret, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s)
        """, (app_id, developer_id, app_name, description, owner, website, app_secret, created_at))

        cursor.execute("""
            INSERT INTO app_configurations (app_id, scope, auth_mode, updated_at)
            VALUES (%s, %s, %s, %s)
        """, (app_id, json.dumps(normalized_scope), auth_mode, created_at))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': '应用创建成功，等待审核',
            'app': {
                'id': app_id,
                'name': app_name,
                'description': description,
                'owner': owner,
                'website': website,
                'app_secret': app_secret,
                'status': 'pending',
                'created_at': created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })

    except Exception as e:
        print(f"创建应用失败: {e}")
        return jsonify({'success': False, 'message': '创建应用失败，请稍后重试'})


@developer_bp.route('/api/developer/apps', methods=['GET'])
@login_required
@is_developer
def get_apps():
    try:
        developer_id = session.get('user_id')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute("""
            SELECT id, name, description, owner, website, status, created_at, approved_at
            FROM developer_apps
            WHERE developer_id = %s
            ORDER BY created_at DESC
        """, (developer_id,))
        apps = cursor.fetchall()

        cursor.close()
        conn.close()

        for app in apps:
            if app['created_at']:
                app['created_at'] = app['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if app['approved_at']:
                app['approved_at'] = app['approved_at'].strftime('%Y-%m-%d %H:%M:%S')

        return jsonify({'success': True, 'apps': apps})

    except Exception as e:
        print(f"获取应用列表失败: {e}")
        return jsonify({'success': False, 'message': '获取应用列表失败'})


@developer_bp.route('/api/developer/delete-app', methods=['DELETE'])
@login_required
@is_developer
def delete_app():
    try:
        data = request.json
        app_id = data.get('app_id')

        if not app_id:
            return jsonify({'success': False, 'message': '应用ID不能为空'})

        developer_id = session.get('user_id')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor()

        cursor.execute("SELECT id FROM developer_apps WHERE id = %s AND developer_id = %s", (app_id, developer_id))
        app = cursor.fetchone()

        if not app:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '应用不存在或无权删除'})

        cursor.execute("DELETE FROM app_configurations WHERE app_id = %s", (app_id,))
        cursor.execute("DELETE FROM developer_authorizations WHERE app_id = %s", (app_id,))
        cursor.execute("DELETE FROM developer_apps WHERE id = %s", (app_id,))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': '应用删除成功'})

    except Exception as e:
        print(f"删除应用失败: {e}")
        return jsonify({'success': False, 'message': '删除应用失败，请稍后重试'})


@developer_bp.route('/api/developer/configure-callback', methods=['POST'])
@login_required
@is_developer
def configure_callback():
    try:
        data = request.json
        app_id = data.get('app_id')
        login_callback_url = data.get('login_callback_url')
        verification_callback_url = data.get('verification_callback_url')
        scope = data.get('scope')
        requested_auth_mode = data.get('auth_mode')
        auth_mode = (requested_auth_mode or 'native').strip().lower()

        if not app_id:
            return jsonify({'success': False, 'message': '应用ID不能为空'})

        if auth_mode not in ('native', 'oidc'):
            return jsonify({'success': False, 'message': '授权方式无效'})

        developer_id = session.get('user_id')

        if login_callback_url and not validate_url(login_callback_url):
            return jsonify({'success': False, 'message': '登录回调地址格式无效'})

        if verification_callback_url and not validate_url(verification_callback_url):
            return jsonify({'success': False, 'message': '验证回调地址格式无效'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor()

        cursor.execute("SELECT id FROM developer_apps WHERE id = %s AND developer_id = %s", (app_id, developer_id))
        app = cursor.fetchone()

        if not app:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '应用不存在或无权配置'})

        updated_at = get_network_time()

        # 授权方式与权限范围只在创建应用时确定，回调配置阶段只读
        cursor.execute("SELECT scope, auth_mode FROM app_configurations WHERE app_id = %s", (app_id,))
        existing_config = cursor.fetchone()

        if existing_config and existing_config[0] and existing_config[1]:
            locked_scope = existing_config[0]
            locked_auth_mode = existing_config[1]
        else:
            # 兼容创建时尚未写入权限的历史应用：固定为基本信息 + 自有 API
            locked_scope = json.dumps(normalize_scopes(None, 'native'))
            locked_auth_mode = 'native'

        if requested_auth_mode is not None and auth_mode != locked_auth_mode:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '授权方式在创建应用时已固定，不可修改。如需调整，请创建新应用。'})

        if scope is not None:
            requested_scope = normalize_scopes(scope, locked_auth_mode)
            try:
                stored_scope = json.loads(locked_scope)
            except (json.JSONDecodeError, TypeError):
                stored_scope = []
            if sorted(requested_scope) != sorted(stored_scope):
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '权限范围在创建应用时已固定，不可修改。如需调整权限，请创建新应用。'})

        cursor.execute("""
            INSERT INTO app_configurations (app_id, login_callback_url, verification_callback_url, scope, auth_mode, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                login_callback_url = VALUES(login_callback_url),
                verification_callback_url = VALUES(verification_callback_url),
                updated_at = VALUES(updated_at)
        """, (app_id, login_callback_url, verification_callback_url, locked_scope, locked_auth_mode, updated_at))

        cursor.execute("""
            UPDATE app_configurations
            SET scope = %s, auth_mode = %s
            WHERE app_id = %s AND (scope IS NULL OR scope = '' OR auth_mode IS NULL OR auth_mode = '')
        """, (locked_scope, locked_auth_mode, app_id))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': '回调配置更新成功（授权方式与权限不可修改）'})

    except Exception as e:
        print(f"配置回调失败: {e}")
        return jsonify({'success': False, 'message': '配置回调失败，请稍后重试'})


def check_password_hash(password_hash, password):
    return hashlib.sha256(password.encode()).hexdigest() == password_hash


verification_send_times = {}


@developer_bp.route('/api/oauth/userinfo', methods=['POST'])
def oauth_userinfo():
    try:
        data = request.json
        app_id = data.get('app_id')
        app_secret = data.get('app_secret')
        auth_code = data.get('auth_code')
        delete_code = data.get('delete_code', False)

        if not all([app_id, app_secret, auth_code]):
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT da.app_secret, ac.scope, ac.auth_mode
                FROM developer_apps da
                LEFT JOIN app_configurations ac ON da.id = ac.app_id
                WHERE da.id = %s AND da.status = 'approved'
            """, (app_id,))
            app = cursor.fetchone()

            if not app:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '应用不存在或未通过审核'}), 404

            app_secret_hash, app_scope_raw, app_auth_mode = app

            if not _verify_app_secret(app_secret_hash, app_secret):
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'app_secret验证失败'}), 401

            # 优先使用本地时间，避免在线时间 API 不可达时阻塞请求
            from datetime import datetime as _dt_local
            try:
                current_time = get_network_time()
            except Exception:
                current_time = _dt_local.now()
            # 数据库存的是 naive datetime，统一去掉时区信息
            current_time = current_time.replace(tzinfo=None) if current_time.tzinfo else current_time
            cursor.execute("""
                SELECT id, user_id, expires_at, status, permission_restrictions FROM developer_authorizations
                WHERE app_id = %s AND auth_code = %s
            """, (app_id, auth_code))
            auth_record = cursor.fetchone()

            if not auth_record:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '授权码无效'}), 404

            auth_id, user_id, expires_at, status, permission_restrictions_raw = auth_record

            if expires_at < current_time:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '授权码已过期'}), 401

            if status == 'blacklisted' or status == 'cancelled':
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '该应用已被用户取消授权'}), 403

            permission_restrictions = parse_restrictions(permission_restrictions_raw)

            if is_scope_restricted(permission_restrictions, SCOPE_USERINFO):
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '用户已禁止该应用访问个人信息'}), 403

            cursor.execute("""
                SELECT id, Name, avatar, mail, phone FROM user_info
                WHERE id = %s
            """, (user_id,))
            user = cursor.fetchone()

            if not user:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '用户不存在'}), 404

            scopes = normalize_scopes(app_scope_raw, app_auth_mode)

            # 先写日志，再删 auth_code——避免日志写入失败时 auth_code 已被删除导致重试失败
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            cursor.execute("""
                INSERT INTO authorization_log (user_id, app_id, action, detail, ip, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, app_id, 'access_userinfo', '应用访问了用户信息', ip_address, current_time))

            if delete_code:
                cursor.execute("DELETE FROM developer_authorizations WHERE id = %s", (auth_id,))

            conn.commit()

            cursor.close()
            conn.close()

            user_payload = {
                'user_id': user[0],
                'username': user[1],
                'avatar': user[2]
            }
            # 仅在应用申请了对应权限、且用户未在「第三方安全」页禁用时才返回原文
            if SCOPE_EMAIL in scopes and not is_scope_restricted(permission_restrictions, SCOPE_EMAIL):
                user_payload['email'] = user[3] or ''
            if SCOPE_PHONE in scopes and not is_scope_restricted(permission_restrictions, SCOPE_PHONE):
                user_payload['phone'] = user[4] or ''

            return jsonify({
                'success': True,
                'user': user_payload
            })

        except Exception as e:
            print(f"获取用户信息失败: {e}")
            if conn:
                conn.rollback()
                cursor.close()
                conn.close()
            return jsonify({'success': False, 'message': '获取用户信息失败'}), 500

    except Exception as e:
        print(f"获取用户信息失败: {e}")
        return jsonify({'success': False, 'message': '获取用户信息失败'}), 500


@developer_bp.route('/api/oauth/send-verification', methods=['POST'])
def oauth_send_verification():
    try:
        data = request.json
        app_id = data.get('app_id')
        app_secret = data.get('app_secret')
        auth_code = data.get('auth_code')
        verification_type = data.get('type', 'email')

        if not all([app_id, app_secret, auth_code]):
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400

        if verification_type not in ['email', 'phone']:
            return jsonify({'success': False, 'message': 'type参数必须是email或phone'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT da.app_secret, ac.verification_callback_url, ac.scope, ac.auth_mode
                FROM developer_apps da
                LEFT JOIN app_configurations ac ON da.id = ac.app_id
                WHERE da.id = %s AND da.status = 'approved'
            """, (app_id,))
            app = cursor.fetchone()

            if not app:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '应用不存在或未通过审核'}), 404

            app_secret_hash, verification_callback_url, app_scope_raw, app_auth_mode = app

            if not _verify_app_secret(app_secret_hash, app_secret):
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'app_secret验证失败'}), 401

            # OIDC 仅做身份认证，不允许调用本系统代发验证码
            if (app_auth_mode or 'native') == 'oidc':
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'OpenID Connect 接入方式不支持调用本系统验证码接口，请由应用自行发送'}), 403

            app_scopes = normalize_scopes(app_scope_raw, app_auth_mode)
            required_scope = SCOPE_EMAIL_CODE if verification_type == 'email' else SCOPE_PHONE_CODE
            if required_scope not in app_scopes:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '该应用未申请对应的验证码发送权限'}), 403

            # 优先使用本地时间，避免在线时间 API 不可达时阻塞请求
            from datetime import datetime as _dt_local
            try:
                current_time = get_network_time()
            except Exception:
                current_time = _dt_local.now()
            # 数据库存的是 naive datetime，统一去掉时区信息
            current_time = current_time.replace(tzinfo=None) if current_time.tzinfo else current_time
            cursor.execute("""
                SELECT id, user_id, expires_at, status, permission_restrictions FROM developer_authorizations
                WHERE app_id = %s AND auth_code = %s
            """, (app_id, auth_code))
            auth_record = cursor.fetchone()

            if not auth_record:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '授权码无效'}), 404

            auth_id, user_id, expires_at, status, permission_restrictions_raw = auth_record

            if expires_at < current_time:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '授权码已过期'}), 401

            if status == 'blacklisted' or status == 'cancelled':
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '该应用已被用户取消授权'}), 403

            permission_restrictions = parse_restrictions(permission_restrictions_raw)

            if is_scope_restricted(permission_restrictions, required_scope):
                cursor.close()
                conn.close()
                scope_name = '邮件验证码' if required_scope == SCOPE_EMAIL_CODE else '手机验证码'
                return jsonify({'success': False, 'message': f'用户已禁止该应用使用{scope_name}'}), 403

            cursor.execute("""
                SELECT mail, phone FROM user_info
                WHERE id = %s
            """, (user_id,))
            user = cursor.fetchone()

            if not user:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '用户不存在'}), 404

            user_mail, user_phone = user

            rate_limit_key = f"{app_id}_{user_id}"
            current_timestamp = current_time.timestamp()

            if rate_limit_key in verification_send_times:
                last_send_time = verification_send_times[rate_limit_key]
                if current_timestamp - last_send_time < 60:
                    remaining_time = int(60 - (current_timestamp - last_send_time))
                    cursor.close()
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': f'发送频率限制，请{remaining_time}秒后再试'
                    }), 429

            verification_code = generate_verification_code()

            if verification_type == 'email':
                if not user_mail:
                    cursor.close()
                    conn.close()
                    return jsonify({'success': False, 'message': '用户未绑定邮箱'}), 400

                send_success, error_msg = send_verification_email(user_mail, verification_code, purpose='developer')
                if not send_success:
                    cursor.close()
                    conn.close()
                    return jsonify({'success': False, 'message': f'发送验证码失败: {error_msg}'}), 500

            elif verification_type == 'phone':
                if not user_phone:
                    cursor.close()
                    conn.close()
                    return jsonify({'success': False, 'message': '用户未绑定手机'}), 400

                send_success, error_msg, _ = send_sms(user_phone)
                if not send_success:
                    cursor.close()
                    conn.close()
                    return jsonify({'success': False, 'message': f'发送验证码失败: {error_msg}'}), 500

            verification_send_times[rate_limit_key] = current_timestamp

            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            log_action = 'access_email' if verification_type == 'email' else 'access_phone'
            log_detail = '应用访问了邮箱' if verification_type == 'email' else '应用访问了手机'
            cursor.execute("""
                INSERT INTO authorization_log (user_id, app_id, action, detail, ip, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, app_id, log_action, log_detail, ip_address, current_time))

            if verification_callback_url:
                try:
                    callback_data = {
                        'app_id': app_id,
                        'auth_code': auth_code,
                        'type': verification_type,
                        'verification_code': verification_code,
                        'user_id': user_id
                    }
                    callback_params = urllib.parse.urlencode(callback_data)
                    req = urllib.request.Request(
                        f"{verification_callback_url}?{callback_params}",
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    with urllib.request.urlopen(req, timeout=10) as response:
                        callback_response = response.read().decode('utf-8')
                        print(f"回调响应: {callback_response}")
                except Exception as e:
                    print(f"调用回调地址失败: {e}")

            cursor.close()
            conn.close()

            return jsonify({
                'success': True,
                'message': '验证码发送成功',
                'verification_code': verification_code if verification_type == 'email' else None
            })

        except Exception as e:
            print(f"发送验证码失败: {e}")
            if conn:
                conn.rollback()
                cursor.close()
                conn.close()
            return jsonify({'success': False, 'message': '发送验证码失败'}), 500

    except Exception as e:
        print(f"发送验证码失败: {e}")
        return jsonify({'success': False, 'message': '发送验证码失败'}), 500


@developer_bp.route('/api/developer/app-secret/<app_id>', methods=['GET'])
@login_required
@is_developer
def get_app_secret(app_id):
    try:
        developer_id = session.get('user_id')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500

        cursor = conn.cursor()
        cursor.execute("""
            SELECT app_secret FROM developer_apps
            WHERE id = %s AND developer_id = %s AND status = 'approved'
        """, (app_id, developer_id))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if not result:
            return jsonify({'success': False, 'message': '应用不存在或未通过审核'}), 404

        return jsonify({
            'success': True,
            'app_secret': result[0]
        })

    except Exception as e:
        print(f"获取应用密钥失败: {e}")
        return jsonify({'success': False, 'message': '获取应用密钥失败'}), 500


@developer_bp.route('/api/developer/app-config/<app_id>', methods=['GET'])
@login_required
@is_developer
def get_app_config(app_id):
    try:
        developer_id = session.get('user_id')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500

        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        cursor.execute("SELECT id FROM developer_apps WHERE id = %s AND developer_id = %s", (app_id, developer_id))
        app = cursor.fetchone()

        if not app:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '应用不存在或无权访问'}), 404

        cursor.execute("""
            SELECT login_callback_url, verification_callback_url, scope, auth_mode, updated_at
            FROM app_configurations
            WHERE app_id = %s
        """, (app_id,))
        config = cursor.fetchone()

        cursor.close()
        conn.close()

        if not config:
            return jsonify({
                'success': True,
                'config': {
                    'login_callback_url': None,
                    'verification_callback_url': None,
                    'scope': '["userinfo"]',
                    'auth_mode': 'native',
                    'updated_at': None
                }
            })

        import json as _json
        return jsonify({
            'success': True,
            'config': {
                'login_callback_url': config.get('login_callback_url'),
                'verification_callback_url': config.get('verification_callback_url'),
                'scope': config.get('scope') or '["userinfo"]',
                'auth_mode': config.get('auth_mode') or 'native',
                'updated_at': config.get('updated_at').strftime('%Y-%m-%d %H:%M:%S') if config.get('updated_at') else None
            }
        })

    except Exception as e:
        print(f"获取应用配置失败: {e}")
        return jsonify({'success': False, 'message': '获取应用配置失败'}), 500


# ============================================================================
# OpenID Connect 兼容层
# 目的：让只支持标准 OAuth2 / OpenID Connect 的第三方系统（如 Gitea）接入本账户系统
# 说明：
#   1) 授权环节复用本系统的 /oauth/authorize（Gitea 传的是 client_id，不是 app_id）
#   2) 本系统的 auth_code 同时作为 access_token（数据库已有记录，有效期 5 天）
#   3) id_token 使用 alg=none：Gitea 所用的 goth 只解析 payload 并校验 aud/iss/exp，不验签
# ============================================================================

OIDC_TOKEN_TTL = 3600
OIDC_USERINFO_PATH = '/api/oauth/oidc/userinfo'


def _b64url_encode(raw_bytes):
    return base64.urlsafe_b64encode(raw_bytes).decode('ascii').rstrip('=')


def _oidc_issuer():
    """
    本系统对外可访问的基地址。
    优先读环境变量 OIDC_ISSUER；否则按请求头推导（兼容反向代理）。
    """
    configured = (os.getenv('OIDC_ISSUER') or '').strip()
    if configured:
        return configured.rstrip('/')

    proto = (request.headers.get('X-Forwarded-Proto') or request.scheme or 'http').split(',')[0].strip()
    host = (request.headers.get('X-Forwarded-Host') or request.headers.get('Host') or request.host).split(',')[0].strip()
    prefix = (request.headers.get('X-Forwarded-Prefix') or '').strip()
    if prefix and not prefix.startswith('/'):
        prefix = '/' + prefix
    return f'{proto}://{host}{prefix}'.rstrip('/')


def _gitea_safe_username(name, user_id):
    """
    Gitea 的用户名只允许字母/数字/._-，且不能以 . _ - 开头。
    中文名直接建号会失败，因此回退成 user_id（15 位字母数字，必定合法）。
    """
    candidate = (name or '').strip()
    if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,38}', candidate):
        return candidate
    return user_id


def _absolute_avatar(avatar):
    if not avatar:
        return ''
    if avatar.startswith(('http://', 'https://')):
        return avatar
    if avatar.startswith('/'):
        return _oidc_issuer() + avatar
    return avatar


def _build_id_token(client_id, user, scopes=None, restrictions=None):
    """签发未签名（alg=none）的 id_token。邮箱/手机号按 scope 与用户限制决定是否下发。"""
    scopes = scopes or []
    restrictions = restrictions or {}
    now = int(time.time())
    header = {'alg': 'none', 'typ': 'JWT'}
    claims = {
        'iss': _oidc_issuer(),
        'aud': client_id,
        'sub': user['id'],
        'iat': now,
        'exp': now + OIDC_TOKEN_TTL,
    }
    if not is_scope_restricted(restrictions, SCOPE_USERINFO):
        username = _gitea_safe_username(user['Name'], user['id'])
        claims['name'] = user['Name']
        claims['nickname'] = username
        claims['preferred_username'] = username
        claims['picture'] = _absolute_avatar(user.get('avatar'))
    if SCOPE_EMAIL in scopes and not is_scope_restricted(restrictions, SCOPE_EMAIL):
        email = user.get('mail') or ''
        claims['email'] = email
        claims['email_verified'] = bool(email)
    if SCOPE_PHONE in scopes and not is_scope_restricted(restrictions, SCOPE_PHONE):
        claims['phone_number'] = user.get('phone') or ''
    header_part = _b64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    claims_part = _b64url_encode(json.dumps(claims, separators=(',', ':')).encode('utf-8'))
    return f'{header_part}.{claims_part}.'


def _current_naive_time():
    """数据库里存的是 naive datetime，统一去掉时区。"""
    try:
        now = get_network_time()
    except Exception:
        now = datetime.now()
    return now.replace(tzinfo=None) if now.tzinfo else now


def _extract_client_credentials():
    """兼容 client_secret_post 与 client_secret_basic（golang oauth2 会两种都尝试）。"""
    form = request.form.to_dict() if request.form else {}
    payload = request.get_json(silent=True) or {}
    client_id = form.get('client_id') or payload.get('client_id')
    client_secret = form.get('client_secret') or payload.get('client_secret')

    auth_header = request.headers.get('Authorization', '')
    if auth_header.lower().startswith('basic '):
        try:
            decoded = base64.b64decode(auth_header[6:].strip()).decode('utf-8')
            basic_id, _, basic_secret = decoded.partition(':')
            if basic_id:
                client_id = urllib.parse.unquote(basic_id)
            if basic_secret:
                client_secret = urllib.parse.unquote(basic_secret)
        except Exception:
            pass
    return form, payload, client_id, client_secret


@developer_bp.route('/.well-known/openid-configuration', methods=['GET'])
def oidc_discovery():
    issuer = _oidc_issuer()
    return jsonify({
        'issuer': issuer,
        'authorization_endpoint': f'{issuer}/oauth/authorize',
        'token_endpoint': f'{issuer}/oauth/token',
        'userinfo_endpoint': f'{issuer}{OIDC_USERINFO_PATH}',
        'response_types_supported': ['code'],
        'grant_types_supported': ['authorization_code'],
        'subject_types_supported': ['public'],
        'id_token_signing_alg_values_supported': ['none'],
        'scopes_supported': ['openid', 'profile', 'email', 'phone'],
        'claims_supported': [
            'sub', 'iss', 'aud', 'exp', 'iat',
            'name', 'nickname', 'preferred_username',
            'email', 'email_verified', 'phone_number', 'picture'
        ],
        'token_endpoint_auth_methods_supported': ['client_secret_basic', 'client_secret_post']
    })


@developer_bp.route('/oauth/token', methods=['POST'])
def oidc_token():
    form, payload, client_id, client_secret = _extract_client_credentials()
    grant_type = form.get('grant_type') or payload.get('grant_type')
    code = form.get('code') or payload.get('code')

    if not client_id or not client_secret:
        return jsonify({'error': 'invalid_client', 'error_description': '缺少 client_id 或 client_secret'}), 401
    if grant_type != 'authorization_code':
        return jsonify({'error': 'unsupported_grant_type', 'error_description': '仅支持 authorization_code'}), 400
    if not code:
        return jsonify({'error': 'invalid_request', 'error_description': '缺少 code 参数'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'server_error', 'error_description': '数据库连接失败'}), 500

    cursor = None
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("""
            SELECT da.id, da.app_secret, ac.scope, ac.auth_mode
            FROM developer_apps da
            LEFT JOIN app_configurations ac ON da.id = ac.app_id
            WHERE da.id = %s AND da.status = 'approved'
        """, (client_id,))
        app = cursor.fetchone()
        if not app or not _verify_app_secret(app['app_secret'], client_secret):
            cursor.close()
            conn.close()
            return jsonify({'error': 'invalid_client', 'error_description': 'client_id 或 client_secret 不正确'}), 401

        app_scopes = normalize_scopes(app.get('scope'), app.get('auth_mode') or 'native')

        now = _current_naive_time()
        cursor.execute("""
            SELECT id, user_id, status, expires_at, permission_restrictions
            FROM developer_authorizations
            WHERE app_id = %s AND auth_code = %s
        """, (client_id, code))
        record = cursor.fetchone()

        if not record:
            cursor.close()
            conn.close()
            return jsonify({'error': 'invalid_grant', 'error_description': '授权码无效'}), 400

        if record['status'] in ('blacklisted', 'cancelled'):
            cursor.close()
            conn.close()
            return jsonify({'error': 'invalid_grant', 'error_description': '该应用已被用户取消授权'}), 400

        if not record['expires_at'] or record['expires_at'] <= now:
            cursor.close()
            conn.close()
            return jsonify({'error': 'invalid_grant', 'error_description': '授权码已过期'}), 400

        cursor.execute("SELECT id, Name, mail, phone, avatar FROM user_info WHERE id = %s", (record['user_id'],))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            conn.close()
            return jsonify({'error': 'invalid_grant', 'error_description': '用户不存在'}), 400

        restrictions = parse_restrictions(record.get('permission_restrictions'))

        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        try:
            cursor.execute("""
                INSERT INTO authorization_log (user_id, app_id, action, detail, ip, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (record['user_id'], client_id, 'oidc_token', '第三方应用换取访问令牌', ip_address, now))
            conn.commit()
        except Exception as log_error:
            print(f"写入 OIDC 令牌日志失败: {log_error}")
            conn.rollback()

        cursor.close()
        conn.close()

        expires_in = int((record['expires_at'] - now).total_seconds())
        scope_names = ['openid', 'profile']
        if SCOPE_EMAIL in app_scopes:
            scope_names.append('email')
        if SCOPE_PHONE in app_scopes:
            scope_names.append('phone')
        return jsonify({
            'access_token': code,
            'token_type': 'Bearer',
            'expires_in': max(expires_in, 0),
            'scope': ' '.join(scope_names),
            'id_token': _build_id_token(client_id, user, app_scopes, restrictions)
        })

    except Exception as e:
        print(f"OIDC 换取令牌失败: {e}")
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass
        return jsonify({'error': 'server_error', 'error_description': '换取令牌失败'}), 500


@developer_bp.route(OIDC_USERINFO_PATH, methods=['GET'])
def oidc_userinfo():
    auth_header = request.headers.get('Authorization', '')
    access_token = auth_header[7:].strip() if auth_header.lower().startswith('bearer ') else ''
    if not access_token:
        access_token = request.args.get('access_token', '').strip()
    if not access_token:
        return jsonify({'error': 'invalid_token', 'error_description': '缺少访问令牌'}), 401

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'server_error', 'error_description': '数据库连接失败'}), 500

    cursor = None
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("""
            SELECT user_id, app_id, status, expires_at, permission_restrictions
            FROM developer_authorizations
            WHERE auth_code = %s
        """, (access_token,))
        record = cursor.fetchone()

        if not record:
            cursor.close()
            conn.close()
            return jsonify({'error': 'invalid_token', 'error_description': '访问令牌无效'}), 401

        if record['status'] in ('blacklisted', 'cancelled'):
            cursor.close()
            conn.close()
            return jsonify({'error': 'invalid_token', 'error_description': '授权已被取消'}), 401

        if not record['expires_at'] or record['expires_at'] <= _current_naive_time():
            cursor.close()
            conn.close()
            return jsonify({'error': 'invalid_token', 'error_description': '访问令牌已过期'}), 401

        restrictions = parse_restrictions(record['permission_restrictions'])
        no_userinfo = is_scope_restricted(restrictions, SCOPE_USERINFO)

        app_scopes = []
        cursor.execute("SELECT scope, auth_mode FROM app_configurations WHERE app_id = %s", (record['app_id'],))
        config = cursor.fetchone()
        if config:
            app_scopes = normalize_scopes(config.get('scope'), config.get('auth_mode') or 'native')

        cursor.execute("SELECT id, Name, mail, phone, avatar FROM user_info WHERE id = %s", (record['user_id'],))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user:
            return jsonify({'error': 'invalid_token', 'error_description': '用户不存在'}), 401

        # sub 必须与 id_token 中的 sub 完全一致，否则 goth 会拒绝
        if no_userinfo:
            return jsonify({'sub': user['id']})

        username = _gitea_safe_username(user['Name'], user['id'])
        payload = {
            'sub': user['id'],
            'name': user['Name'],
            'nickname': username,
            'preferred_username': username,
            'picture': _absolute_avatar(user.get('avatar'))
        }
        if SCOPE_EMAIL in app_scopes and not is_scope_restricted(restrictions, SCOPE_EMAIL):
            email = user.get('mail') or ''
            payload['email'] = email
            payload['email_verified'] = bool(email)
        if SCOPE_PHONE in app_scopes and not is_scope_restricted(restrictions, SCOPE_PHONE):
            payload['phone_number'] = user.get('phone') or ''
        return jsonify(payload)

    except Exception as e:
        print(f"OIDC 获取用户信息失败: {e}")
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass
        return jsonify({'error': 'server_error', 'error_description': '获取用户信息失败'}), 500

