from flask import Blueprint, request, jsonify, session, render_template
from functools import wraps
from datetime import datetime
import hashlib
import string
import random
import re
import pymysql
import urllib.request
import urllib.parse

from app.models.db import get_db_connection
from app.auth.utils import get_network_time, generate_user_id, generate_verification_code, send_verification_email, send_sms, hash_password
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

        if not app_name:
            return jsonify({'success': False, 'message': '应用名称不能为空'})

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
        app_secret_hash = hash_password(app_secret)
        created_at = get_network_time()

        cursor.execute("""
            INSERT INTO developer_apps (id, developer_id, name, description, owner, website, app_secret, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s)
        """, (app_id, developer_id, app_name, description, owner, website, app_secret_hash, created_at))

        cursor.execute("""
            INSERT INTO app_configurations (app_id, updated_at)
            VALUES (%s, %s)
        """, (app_id, created_at))

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

        if not app_id:
            return jsonify({'success': False, 'message': '应用ID不能为空'})

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

        cursor.execute("""
            INSERT INTO app_configurations (app_id, login_callback_url, verification_callback_url, updated_at)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                login_callback_url = VALUES(login_callback_url),
                verification_callback_url = VALUES(verification_callback_url),
                updated_at = VALUES(updated_at)
        """, (app_id, login_callback_url, verification_callback_url, updated_at))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': '回调配置更新成功'})

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
                SELECT id, app_secret FROM developer_apps
                WHERE id = %s AND status = 'approved'
            """, (app_id,))
            app = cursor.fetchone()

            if not app:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '应用不存在或未通过审核'}), 404

            if not check_password_hash(app[1], app_secret):
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'app_secret验证失败'}), 401

            current_time = get_network_time()
            cursor.execute("""
                SELECT id, user_id, expires_at FROM developer_authorizations
                WHERE app_id = %s AND auth_code = %s
            """, (app_id, auth_code))
            auth_record = cursor.fetchone()

            if not auth_record:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '授权码无效'}), 404

            auth_id, user_id, expires_at = auth_record

            if expires_at < current_time:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '授权码已过期'}), 401

            cursor.execute("""
                SELECT id, Name, avatar FROM user_info
                WHERE id = %s
            """, (user_id,))
            user = cursor.fetchone()

            if not user:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '用户不存在'}), 404

            if delete_code:
                cursor.execute("DELETE FROM developer_authorizations WHERE id = %s", (auth_id,))
                conn.commit()

            cursor.close()
            conn.close()

            return jsonify({
                'success': True,
                'user': {
                    'user_id': user[0],
                    'username': user[1],
                    'avatar': user[2]
                }
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
                SELECT da.app_secret, ac.verification_callback_url
                FROM developer_apps da
                LEFT JOIN app_configurations ac ON da.id = ac.app_id
                WHERE da.id = %s AND da.status = 'approved'
            """, (app_id,))
            app = cursor.fetchone()

            if not app:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '应用不存在或未通过审核'}), 404

            app_secret_hash, verification_callback_url = app

            if not check_password_hash(app_secret_hash, app_secret):
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'app_secret验证失败'}), 401

            current_time = get_network_time()
            cursor.execute("""
                SELECT id, user_id, expires_at FROM developer_authorizations
                WHERE app_id = %s AND auth_code = %s
            """, (app_id, auth_code))
            auth_record = cursor.fetchone()

            if not auth_record:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '授权码无效'}), 404

            auth_id, user_id, expires_at = auth_record

            if expires_at < current_time:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '授权码已过期'}), 401

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

                send_success, error_msg = send_verification_email(user_mail, verification_code)
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
            SELECT login_callback_url, verification_callback_url, updated_at
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
                    'login_callback_url': '',
                    'verification_callback_url': '',
                    'updated_at': None
                }
            })

        if config['updated_at']:
            config['updated_at'] = config['updated_at'].strftime('%Y-%m-%d %H:%M:%S')

        return jsonify({
            'success': True,
            'config': config
        })

    except Exception as e:
        print(f"获取应用配置失败: {e}")
        return jsonify({'success': False, 'message': '获取应用配置失败'}), 500

