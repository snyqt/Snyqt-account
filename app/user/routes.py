from flask import Blueprint, request, jsonify, session, redirect, current_app, render_template
from datetime import timedelta
import os
import random
import string
from PIL import Image

from app.models.db import get_db_connection
from app.auth.utils import hash_password, is_password_strong, get_network_timestamp
from app.auth.routes import login_required, sms_verification_codes
from app.user.utils import avatar_extensions, get_user_avatar_path

try:
    from config import VERIFICATION_CODE_EXPIRE
except ImportError:
    VERIFICATION_CODE_EXPIRE = 300

user_bp = Blueprint('user', __name__)


@user_bp.route('/get_user_info')
def get_user_info():
    if 'logged_in' in session and session['logged_in']:
        user_id = session.get('user_id')
        avatar_path = get_user_avatar_path(user_id)
        user_info = {
            'id': user_id,
            'username': session.get('username'),
            'avatar': avatar_path
        }
        return jsonify({'success': True, 'user': user_info})
    else:
        return jsonify({'success': False, 'message': '用户未登录'})


@user_bp.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    try:
        avatar = request.files.get('avatar')
        if not avatar or not avatar.filename:
            return jsonify({'success': False, 'message': '请选择文件'})

        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
        extension = avatar.filename.rsplit('.', 1)[1].lower() if '.' in avatar.filename else ''

        if extension not in allowed_extensions:
            return jsonify({'success': False, 'message': '不支持的文件类型'})

        if len(avatar.read()) > 2 * 1024 * 1024:
            return jsonify({'success': False, 'message': '文件大小超过2MB限制'})

        avatar.seek(0)

        temp_dir = 'static/temp'
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        random_filename = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        temp_path = f"/static/temp/{random_filename}.{extension}"

        avatar.save(os.path.join(current_app.config['PROJECT_ROOT'], temp_path[1:]))

        return jsonify({'success': True, 'avatar_url': temp_path})
    except Exception as e:
        print(f"上传头像失败: {e}")
        return jsonify({'success': False, 'message': '上传失败，请稍后重试'})


@user_bp.route('/profile')
def profile():
    if 'logged_in' in session and session['logged_in']:
        return render_template('profile.html')
    else:
        return redirect('/login')


@user_bp.route('/get_user_email')
def get_user_email():
    if 'logged_in' in session and session['logged_in']:
        user_id = session.get('user_id')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

        cursor = conn.cursor()

        cursor.execute("SELECT mail FROM user_info WHERE id = %s", (user_id,))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:
            return jsonify({'success': True, 'email': result[0]})
        else:
            return jsonify({'success': False, 'message': '用户信息不存在'})
    else:
        return jsonify({'success': False, 'message': '用户未登录'})


@user_bp.route('/get_user_phone')
def get_user_phone():
    if 'logged_in' in session and session['logged_in']:
        user_id = session.get('user_id')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

        cursor = conn.cursor()

        cursor.execute("SELECT phone FROM user_info WHERE id = %s", (user_id,))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:
            return jsonify({'success': True, 'phone': result[0]})
        else:
            return jsonify({'success': False, 'message': '用户信息不存在'})
    else:
        return jsonify({'success': False, 'message': '用户未登录'})


@user_bp.route('/update_username', methods=['POST'])
def update_username():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({'success': False, 'message': '用户未登录'})

    try:
        user_id = session.get('user_id')
        new_username = request.form.get('new_username')

        if not new_username or len(new_username) < 2:
            return jsonify({'success': False, 'message': '用户名至少需要2个字符'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM user_info WHERE Name = %s AND id != %s", (new_username, user_id))
        if cursor.fetchone()[0] > 0:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '用户名已存在，请更换用户名'})

        cursor.execute("UPDATE user_info SET Name = %s WHERE id = %s", (new_username, user_id))
        conn.commit()

        session['username'] = new_username

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': '用户名修改成功'})
    except Exception as e:
        print(f"修改用户名失败: {e}")
        return jsonify({'success': False, 'message': '修改失败，请稍后重试'})


@user_bp.route('/verify_email', methods=['POST'])
def verify_email():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({'success': False, 'message': '用户未登录'})

    try:
        email = request.form.get('email')
        verification_code = request.form.get('verification_code')

        if not email or not verification_code:
            return jsonify({'success': False, 'message': '请填写所有必填字段'})

        session_code = session.get(f'verification_code_{email}')
        if not session_code or session_code != verification_code:
            return jsonify({'success': False, 'message': '验证码错误或已过期'})

        user_id = session.get('user_id')
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_info WHERE id = %s AND mail = %s", (user_id, email))

        if cursor.fetchone()[0] == 0:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '邮箱与用户不匹配'})

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': '验证成功'})
    except Exception as e:
        print(f"验证邮箱失败: {e}")
        return jsonify({'success': False, 'message': '验证失败，请稍后重试'})


@user_bp.route('/update_email', methods=['POST'])
def update_email():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({'success': False, 'message': '用户未登录'})

    try:
        user_id = session.get('user_id')
        new_email = request.form.get('new_email')
        verification_code = request.form.get('verification_code')

        if not new_email or not verification_code:
            return jsonify({'success': False, 'message': '请填写所有必填字段'})

        session_code = session.get(f'verification_code_{new_email}')
        if not session_code or session_code != verification_code:
            return jsonify({'success': False, 'message': '验证码错误或已过期'})

        session.pop(f'verification_code_{new_email}', None)

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM user_info WHERE mail = %s AND id != %s", (new_email, user_id))
        if cursor.fetchone()[0] > 0:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '邮箱已被使用，请更换邮箱'})

        cursor.execute("UPDATE user_info SET mail = %s WHERE id = %s", (new_email, user_id))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': '邮箱修改成功'})
    except Exception as e:
        print(f"修改邮箱失败: {e}")
        return jsonify({'success': False, 'message': '修改失败，请稍后重试'})


@user_bp.route('/update_phone', methods=['POST'])
def update_phone():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({'success': False, 'message': '用户未登录'})

    try:
        user_id = session.get('user_id')
        new_phone = request.form.get('new_phone')
        verification_code = request.form.get('verification_code')

        if not new_phone or not verification_code:
            return jsonify({'success': False, 'message': '请填写所有必填字段'})

        pure_phone = ''.join(c for c in new_phone if c.isdigit() or c == '+')

        if pure_phone not in sms_verification_codes:
            return jsonify({'success': False, 'message': '请先获取手机验证码'})

        stored = sms_verification_codes[pure_phone]
        if get_network_timestamp() - stored['timestamp'] > VERIFICATION_CODE_EXPIRE:
            del sms_verification_codes[pure_phone]
            return jsonify({'success': False, 'message': '手机验证码已过期，请重新获取'})

        if stored['code'] != verification_code:
            return jsonify({'success': False, 'message': '手机验证码错误'})

        del sms_verification_codes[pure_phone]

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM user_info WHERE phone = %s AND id != %s", (new_phone, user_id))
        if cursor.fetchone()[0] > 0:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '手机号已被使用，请更换手机号'})

        cursor.execute("UPDATE user_info SET phone = %s WHERE id = %s", (new_phone, user_id))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': '手机号修改成功'})
    except Exception as e:
        print(f"修改手机号失败: {e}")
        return jsonify({'success': False, 'message': '修改失败，请稍后重试'})


@user_bp.route('/verify_password', methods=['POST'])
def verify_password():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({'success': False, 'message': '用户未登录'})

    try:
        user_id = session.get('user_id')
        old_password = request.form.get('old_password')

        if not old_password:
            return jsonify({'success': False, 'message': '请输入当前密码'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

        cursor = conn.cursor()

        cursor.execute("SELECT password FROM user_info WHERE id = %s", (user_id,))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result and hash_password(old_password) == result[0]:
            session['password_verified'] = True
            session.permanent = True
            current_app.permanent_session_lifetime = timedelta(minutes=5)
            return jsonify({'success': True, 'message': '密码验证成功'})
        else:
            return jsonify({'success': False, 'message': '当前密码不正确'})
    except Exception as e:
        print(f"验证密码失败: {e}")
        return jsonify({'success': False, 'message': '验证失败，请稍后重试'})


@user_bp.route('/update_password', methods=['POST'])
def update_password():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({'success': False, 'message': '用户未登录'})

    if not session.get('password_verified'):
        return jsonify({'success': False, 'message': '请先验证当前密码'})

    try:
        user_id = session.get('user_id')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not new_password or not confirm_password:
            return jsonify({'success': False, 'message': '请填写所有必填字段'})

        if new_password != confirm_password:
            return jsonify({'success': False, 'message': '两次输入的密码不一致'})

        if not is_password_strong(new_password):
            return jsonify({'success': False, 'message': '密码必须超过6位，包含数字、大小写字母及特殊符号'})

        hashed_password = hash_password(new_password)

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

        cursor = conn.cursor()

        cursor.execute("UPDATE user_info SET password = %s WHERE id = %s", (hashed_password, user_id))
        conn.commit()

        session.pop('password_verified', None)

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': '密码修改成功'})
    except Exception as e:
        print(f"修改密码失败: {e}")
        return jsonify({'success': False, 'message': '修改失败，请稍后重试'})


@user_bp.route('/update_avatar', methods=['POST'])
def update_avatar():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({'success': False, 'message': '用户未登录'})

    try:
        user_id = session.get('user_id')
        avatar = request.files.get('avatar')

        if not avatar or not avatar.filename:
            return jsonify({'success': False, 'message': '请选择文件'})

        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
        extension = avatar.filename.rsplit('.', 1)[1].lower() if '.' in avatar.filename else ''

        if extension not in allowed_extensions:
            return jsonify({'success': False, 'message': '不支持的文件类型'})

        if len(avatar.read()) > 2 * 1024 * 1024:
            return jsonify({'success': False, 'message': '文件大小超过2MB限制'})

        avatar.seek(0)

        upload_dir = 'static/img/user_avatar'
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        for ext in avatar_extensions:
            old_avatar_path = os.path.join(current_app.config['PROJECT_ROOT'], f"static/img/user_avatar/{user_id}.{ext}")
            if os.path.exists(old_avatar_path):
                os.remove(old_avatar_path)

        image = Image.open(avatar)
        if not os.path.exists(os.path.join(current_app.config['PROJECT_ROOT'], upload_dir)):
            os.makedirs(os.path.join(current_app.config['PROJECT_ROOT'], upload_dir))

        png_path = f"{user_id}.png"
        full_path = os.path.join(current_app.config['PROJECT_ROOT'], upload_dir, png_path)
        image.save(full_path, 'PNG')

        avatar_url = f"/static/img/user_avatar/{png_path}"
        return jsonify({'success': True, 'message': '头像更新成功', 'avatar_url': avatar_url})
    except Exception as e:
        print(f"更新头像失败: {e}")
        return jsonify({'success': False, 'message': '更新失败，请稍后重试'})
