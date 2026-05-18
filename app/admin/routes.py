from flask import Blueprint, request, jsonify, session, redirect, render_template, current_app
import os
import pymysql
from PIL import Image

from app.models.db import get_db_connection
from app.auth.utils import hash_password, is_password_strong
from app.auth.routes import login_required, admin_required
from app.admin.utils import avatar_extensions, get_user_avatar_path

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/user_permission_management')
def user_permission_management():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect('/login')
    try:
        user_id = session.get('user_id')
        conn = get_db_connection()
        if not conn:
            return "数据库连接失败", 500
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_permission WHERE user_id = %s AND (type = 'ROOT' OR type = '管理员')", (user_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if result:
            return render_template('user_permission_management.html')
        else:
            return render_template('403.html'), 403
    except Exception as e:
        print(f"访问用户权限管理页面失败: {e}")
        return "访问失败，请重试", 500


@admin_bp.route('/user_info_management')
@admin_required
def user_info_management():
    try:
        return render_template('user_info_management.html')
    except Exception as e:
        print(f"访问用户信息管理页面失败: {e}")
        return "访问失败，请重试", 500


@admin_bp.route('/admin-login-logs')
@admin_required
def admin_login_logs_page():
    return render_template('admin_login_log.html')


@admin_bp.route('/user-login-logs')
@login_required
def user_login_logs_page():
    return render_template('user_login_log.html')


@admin_bp.route('/api/admin-login-logs', methods=['GET'])
@admin_required
def get_admin_login_logs():
    try:
        user_id = request.args.get('user_id', '')
        start_time = request.args.get('start_time', '')
        end_time = request.args.get('end_time', '')
        ip = request.args.get('ip', '')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        query = "SELECT l.*, u.Name as username FROM login_log l LEFT JOIN user_info u ON l.`user-id` = u.id WHERE 1=1"
        params = []

        if user_id:
            query += " AND l.`user-id` = %s"
            params.append(user_id)

        if start_time:
            query += " AND l.time >= %s"
            params.append(start_time)

        if end_time:
            query += " AND l.time <= %s"
            params.append(end_time)

        if ip:
            query += " AND l.ip = %s"
            params.append(ip)

        query += " ORDER BY l.time DESC LIMIT 100"

        cursor.execute(query, params)
        logs = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'logs': logs})

    except Exception as e:
        print(f"获取登录日志失败: {e}")
        return jsonify({'success': False, 'message': '获取日志失败'})


@admin_bp.route('/api/user-login-logs', methods=['GET'])
@login_required
def get_user_login_logs():
    try:
        user_id = session.get('user_id')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute("""
            SELECT * FROM login_log
            WHERE `user-id` = %s
            ORDER BY time DESC
            LIMIT 50
        """, (user_id,))
        logs = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'logs': logs})

    except Exception as e:
        print(f"获取个人登录日志失败: {e}")
        return jsonify({'success': False, 'message': '获取日志失败'})


@admin_bp.route('/api/get-all-users', methods=['GET'])
@admin_required
def get_all_users():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor()

        search_user_id = request.args.get('user_id', '')
        search_username = request.args.get('username', '')
        search_email = request.args.get('email', '')

        query = """
        SELECT u.id, u.Name, u.mail, u.phone
        FROM user_info u
        WHERE 1=1
        """
        params = []

        if search_user_id:
            query += " AND u.id LIKE %s"
            params.append(f"%{search_user_id}%")
        if search_username:
            query += " AND u.Name LIKE %s"
            params.append(f"%{search_username}%")
        if search_email:
            query += " AND u.mail LIKE %s"
            params.append(f"%{search_email}%")

        query += " ORDER BY u.Name"

        cursor.execute(query, params)
        users = cursor.fetchall()

        result = []
        for user in users:
            avatar_path = get_user_avatar_path(user[0])

            result.append({
                'user_id': user[0],
                'username': user[1],
                'email': user[2],
                'phone': user[3],
                'avatar': avatar_path
            })

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'users': result})
    except Exception as e:
        print(f"获取用户列表失败: {e}")
        return jsonify({'success': False, 'message': '获取失败，请重试'})


@admin_bp.route('/api/admin-update-password', methods=['POST'])
@admin_required
def admin_update_password():
    try:
        data = request.json
        target_user_id = data.get('user_id')
        new_password = data.get('new_password')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor()

        if not is_password_strong(new_password):
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '密码必须超过6位，包含数字、大小写字母及特殊符号'})

        hashed_password = hash_password(new_password)

        cursor.execute("UPDATE user_info SET password = %s WHERE id = %s", (hashed_password, target_user_id))

        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '请输入新密码'})

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': '密码修改成功'})
    except Exception as e:
        print(f"管理员修改用户密码失败: {e}")
        return jsonify({'success': False, 'message': '修改失败，请重试'})


@admin_bp.route('/api/admin-update-username', methods=['POST'])
@admin_required
def admin_update_username():
    try:
        data = request.json
        target_user_id = data.get('user_id')
        new_username = data.get('new_username')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor()

        if not new_username or len(new_username) < 2:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '用户名至少需要2个字符'})

        cursor.execute("SELECT COUNT(*) FROM user_info WHERE Name = %s AND id != %s", (new_username, target_user_id))
        if cursor.fetchone()[0] > 0:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '用户名已存在，请更换用户名'})

        cursor.execute("UPDATE user_info SET Name = %s WHERE id = %s", (new_username, target_user_id))

        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '用户名不能相同'})

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': '用户名修改成功'})
    except Exception as e:
        print(f"管理员修改用户名称失败: {e}")
        return jsonify({'success': False, 'message': '修改失败，请重试'})


@admin_bp.route('/api/admin-update-email', methods=['POST'])
@admin_required
def admin_update_email():
    try:
        data = request.json
        target_user_id = data.get('user_id')
        new_email = data.get('new_email')
        verification_code = data.get('verification_code')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor()

        if not new_email or not verification_code:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '请填写所有必填字段'})

        session_code = session.get(f'verification_code_{new_email}')
        if not session_code or session_code != verification_code:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '验证码错误或已过期'})

        session.pop(f'verification_code_{new_email}', None)

        cursor.execute("SELECT COUNT(*) FROM user_info WHERE mail = %s AND id != %s", (new_email, target_user_id))
        if cursor.fetchone()[0] > 0:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '邮箱已被使用，请更换邮箱'})

        cursor.execute("UPDATE user_info SET mail = %s WHERE id = %s", (new_email, target_user_id))

        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '请输入新邮箱'})

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': '邮箱修改成功'})
    except Exception as e:
        print(f"管理员修改用户邮箱失败: {e}")
        return jsonify({'success': False, 'message': '修改失败，请重试'})



@admin_bp.route('/api/admin-update-phone', methods=['POST'])
@admin_required
def admin_update_phone():
    try:
        data = request.json
        target_user_id = data.get('user_id')
        new_phone = data.get('new_phone')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor()

        if not target_user_id:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '用户ID不能为空'})

        if not new_phone:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '手机号不能为空'})

        # 简单的手机号格式验证
        import re
        if not re.match(r'^1[3-9]\d{9}$', new_phone):
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '请输入有效的手机号'})

        # 检查手机号是否已被其他用户使用
        cursor.execute("SELECT COUNT(*) FROM user_info WHERE phone = %s AND id != %s", (new_phone, target_user_id))
        if cursor.fetchone()[0] > 0:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '手机号已被使用，请更换手机号'})

        # 更新用户手机号
        cursor.execute("UPDATE user_info SET phone = %s WHERE id = %s", (new_phone, target_user_id))

        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '未找到该用户'})

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': '手机号修改成功'})
    except Exception as e:
        print(f"管理员修改用户手机号失败: {e}")
        return jsonify({'success': False, 'message': '修改失败，请重试'})


@admin_bp.route('/api/admin-update-avatar', methods=['POST'])
@admin_required
def admin_update_avatar():
    try:
        target_user_id = request.form.get('user_id')
        avatar = request.files.get('avatar')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor()

        if not target_user_id:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '用户ID不能为空'})

        if not avatar or not avatar.filename:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '请选择文件'})

        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
        extension = avatar.filename.rsplit('.', 1)[1].lower() if '.' in avatar.filename else ''

        if extension not in allowed_extensions:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '不支持的文件类型'})

        if len(avatar.read()) > 2 * 1024 * 1024:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '文件大小超过2MB限制'})

        avatar.seek(0)

        upload_dir = 'static/img/user_avatar'
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        for ext in avatar_extensions:
            old_avatar_path = os.path.join(current_app.config['PROJECT_ROOT'], f"static/img/user_avatar/{target_user_id}.{ext}")
            if os.path.exists(old_avatar_path):
                os.remove(old_avatar_path)

        image = Image.open(avatar)
        if not os.path.exists(os.path.join(current_app.config['PROJECT_ROOT'], upload_dir)):
            os.makedirs(os.path.join(current_app.config['PROJECT_ROOT'], upload_dir))

        png_path = f"{target_user_id}.png"
        full_path = os.path.join(current_app.config['PROJECT_ROOT'], upload_dir, png_path)
        image.save(full_path, 'PNG')

        avatar_url = f"/static/img/user_avatar/{png_path}"

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': '头像更新成功', 'avatar_url': avatar_url})
    except Exception as e:
        print(f"管理员修改用户头像失败: {e}")
        return jsonify({'success': False, 'message': '更新失败，请稍后重试'})


@admin_bp.route('/api/delete-login-log', methods=['POST'])
@admin_required
def delete_login_log():
    try:
        data = request.json
        log_id = data.get('id')

        if not log_id:
            return jsonify({'success': False, 'message': '缺少必要参数'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM login_log WHERE id = %s",
            (log_id,)
        )

        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '未找到匹配的日志'})

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': '日志删除成功'})
    except Exception as e:
        print(f"删除登录日志失败: {e}")
        return jsonify({'success': False, 'message': '删除失败，请稍后重试'})


@admin_bp.route('/api/admin-delete-user', methods=['POST'])
@admin_required
def admin_delete_user():
    try:
        data = request.json
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({'success': False, 'message': '用户ID不能为空'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor()
        
        try:
            # 开始事务
            conn.begin()
            
            # 删除用户的登录日志
            cursor.execute("DELETE FROM login_log WHERE `user-id` = %s", (user_id,))
            
            # 删除用户的权限
            cursor.execute("DELETE FROM user_permission WHERE user_id = %s", (user_id,))
            
            # 删除用户的权限申请
            cursor.execute("DELETE FROM user_permission_application WHERE user_id = %s", (user_id,))
            
            # 删除用户信息
            cursor.execute("DELETE FROM user_info WHERE id = %s", (user_id,))
            
            if cursor.rowcount == 0:
                conn.rollback()
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '用户不存在'})
            
            # 提交事务
            conn.commit()
            cursor.close()
            conn.close()

            return jsonify({'success': True, 'message': '用户删除成功'})
        except Exception as e:
            # 发生错误时回滚
            conn.rollback()
            raise e
    except Exception as e:
        print(f"管理员删除用户失败: {e}")
        return jsonify({'success': False, 'message': '删除失败，请稍后重试'})
