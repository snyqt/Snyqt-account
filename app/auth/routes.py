from flask import Blueprint, request, jsonify, render_template, session, redirect, current_app
from datetime import timedelta
import os
import string
import random
import hashlib
import pymysql
from functools import wraps

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
        username = request.form.get('username')
        password = request.form.get('password')
        is_cookie = int(request.form.get('is_cookie', 0))
        turnstile_response = request.form.get('cf-turnstile-response')

        if not username or not password:
            return jsonify({'success': False, 'message': '请输入用户名和密码'})

        if TURNSTILE_ENABLED:
            if not turnstile_response:
                return jsonify({'success': False, 'message': '请完成人机验证'})

            if not verify_turnstile(turnstile_response, request.remote_addr):
                return jsonify({'success': False, 'message': '人机验证失败，请重试'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

        cursor = conn.cursor()

        cursor.execute("SELECT id, Name, password, mail, phone FROM user_info WHERE Name = %s", (username,))
        user = cursor.fetchone()

        if user and hash_password(password) == user[2]:
            user_id = user[0]
            user_mail = user[3]
            user_phone = user[4]

            client_ip = request.remote_addr
            user_agent = request.user_agent.string

            browser_info = parse_user_agent(user_agent)

            place = get_ip_location(client_ip)

            is_danger = check_login_risk(user_id, client_ip, place, conn)

            if is_danger == 1:
                verification_code = generate_verification_code()
                session[f'2fa_code_{user_id}'] = verification_code
                session.permanent = True
                current_app.permanent_session_lifetime = timedelta(minutes=5)

                print(f'[登录二次验证] 开始发送二次验证邮件')
                send_success, error_msg = send_2fa_verification_email(user_mail, verification_code)
                if send_success:
                    print(f'[登录二次验证] 邮件发送成功')
                    log_email_verification(user_mail, verification_code, '2fa', client_ip, 'success')
                else:
                    print(f'[登录二次验证] 邮件发送失败: {error_msg}')
                    log_email_verification(user_mail, verification_code, '2fa', client_ip, 'failed', error_msg)

                session['pending_user_id'] = user_id
                session['pending_username'] = user[1]
                session['pending_is_cookie'] = is_cookie
                session['pending_user_phone'] = user_phone
                session['pending_user_mail'] = user_mail

                return jsonify({
                    'success': True,
                    'message': '需要二次验证',
                    'requires_2fa': True
                })

            session['logged_in'] = True
            session['user_id'] = user_id
            session['username'] = user[1]

            session.permanent = True
            if is_cookie == 1:
                current_app.permanent_session_lifetime = timedelta(days=7)
            else:
                current_app.permanent_session_lifetime = timedelta(minutes=10)

            log_time = get_network_time().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            cursor.execute("""
                INSERT INTO login_log (`user-id`, ip, time, is_danger, browser, is_cookie, place)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, client_ip, log_time, 0, browser_info, is_cookie, place))
            conn.commit()

            cursor.close()
            conn.close()

            return jsonify({'success': True, 'message': '登录成功'})
        else:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '用户名或密码错误'})

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
                INSERT INTO login_log (`user-id`, ip, time, is_danger, browser, is_cookie, place)
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
            if not session_code or session_code != verification_code:
                return jsonify({'success': False, 'message': '验证码错误或已过期'})

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
    session.clear()
    return jsonify({'success': True, 'message': '退出成功'})

def log_email_verification(email, code, type_, ip, status, error_msg=None):
    """记录邮箱验证码发送日志"""
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            log_time = get_network_time().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            cursor.execute("""
                INSERT INTO email_verification_log (email, code, type, ip, time, status, error_msg)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (email, code, type_, ip, log_time, status, error_msg))
            conn.commit()
            cursor.close()
            conn.close()
            print(f"[邮箱验证码日志] 已记录 - 邮箱: {email}, 类型: {type_}, 状态: {status}")
    except Exception as e:
        print(f"[邮箱验证码日志] 记录失败: {e}")

@auth_bp.route('/send_code', methods=['POST'])
def send_code():
    try:
        email = request.json.get('email') if request.is_json else request.form.get('email')
        turnstile_response = request.json.get('cf-turnstile-response') if request.is_json else request.form.get('cf-turnstile-response')
        client_ip = request.remote_addr

        print(f'========== 发送邮箱验证码日志 ==========')
        print(f'请求时间: {get_network_time()}')
        print(f'邮箱地址: {email}')
        print(f'请求IP: {client_ip}')
        print(f'=======================================')

        if not email:
            print(f'[邮箱验证码] 失败：缺少邮箱地址')
            log_email_verification(email or 'unknown', 'N/A', 'register', client_ip, 'failed', '缺少邮箱地址')
            return jsonify({'success': False, 'message': '请输入邮箱地址'})

        if TURNSTILE_ENABLED:
            if not turnstile_response:
                print(f'[邮箱验证码] 失败：未完成人机验证')
                log_email_verification(email, 'N/A', 'register', client_ip, 'failed', '未完成人机验证')
                return jsonify({'success': False, 'message': '请完成人机验证'})

            if not verify_turnstile(turnstile_response, client_ip):
                print(f'[邮箱验证码] 失败：人机验证失败')
                log_email_verification(email, 'N/A', 'register', client_ip, 'failed', '人机验证失败')
                return jsonify({'success': False, 'message': '人机验证失败，请重试'})

        code = generate_verification_code()
        print(f'[邮箱验证码] 生成验证码: {code}')

        session[f'verification_code_{email}'] = code
        session.permanent = True
        current_app.permanent_session_lifetime = timedelta(minutes=5)
        print(f'[邮箱验证码] 验证码已存入Session，有效期5分钟')

        print(f'[邮箱验证码] 开始发送邮件...')
        send_success, error_msg = send_verification_email(email, code)
        
        if send_success:
            print(f'[邮箱验证码] 发送成功！')
            log_email_verification(email, code, 'register', client_ip, 'success')
            return jsonify({'success': True, 'message': '验证码已发送，请查收邮箱'})
        else:
            print(f'[邮箱验证码] 发送失败: {error_msg}')
            log_email_verification(email, code, 'register', client_ip, 'failed', error_msg)
            return jsonify({'success': False, 'message': '发送验证码失败，请稍后重试'})
    except Exception as e:
        print(f'[邮箱验证码] 异常: {e}')
        import traceback
        traceback.print_exc()
        email_for_log = request.json.get('email') if request.is_json else request.form.get('email', 'unknown')
        log_email_verification(email_for_log, 'N/A', 'register', request.remote_addr, 'error', str(e))
        return jsonify({'success': False, 'message': '发送验证码失败，请稍后重试'})

@auth_bp.route('/verify_code', methods=['POST'])
def verify_code():
    try:
        email = request.form.get('email')
        code = request.form.get('code')

        if not email or not code:
            return jsonify({'valid': False})

        session_code = session.get(f'verification_code_{email}')
        if session_code and session_code == code:
            return jsonify({'valid': True})
        else:
            return jsonify({'valid': False})
    except Exception as e:
        print(f"验证验证码失败: {e}")
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
