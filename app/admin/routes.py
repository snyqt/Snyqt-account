from flask import Blueprint, request, jsonify, session, redirect, render_template, current_app
import os
import pymysql
import string
import random
from PIL import Image
from werkzeug.security import generate_password_hash

from app.models.db import get_db_connection
from app.auth.utils import hash_password, is_password_strong
from app.auth.routes import login_required, admin_required
from app.admin.utils import avatar_extensions, get_user_avatar_path

admin_bp = Blueprint('admin', __name__)


def get_network_time():
    from datetime import datetime
    return datetime.now()


def generate_app_id():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(15))


def generate_app_secret():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(64))


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


@admin_bp.route('/app-review')
@admin_required
def app_review_page():
    try:
        return render_template('app_review.html')
    except Exception as e:
        print(f"访问应用审核页面失败: {e}")
        return "访问失败，请重试", 500


@admin_bp.route('/app-management')
@admin_required
def app_management_page():
    try:
        return render_template('app_management.html')
    except Exception as e:
        print(f"访问应用管理页面失败: {e}")
        return "访问失败，请重试", 500


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

        query = "SELECT l.*, u.Name as username FROM login_log l LEFT JOIN user_info u ON l.`user_id` = u.id WHERE 1=1"
        params = []

        if user_id:
            query += " AND l.`user_id` = %s"
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
            WHERE `user_id` = %s
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
            cursor.execute("DELETE FROM login_log WHERE `user_id` = %s", (user_id,))
            
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
            conn.rollback()
            raise e
    except Exception as e:
        print(f"管理员删除用户失败: {e}")
        return jsonify({'success': False, 'message': '删除失败，请稍后重试'})


@admin_bp.route('/api/admin/pending-apps', methods=['GET'])
@admin_required
def get_pending_apps():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute("""
            SELECT 
                da.id, 
                da.developer_id, 
                da.name, 
                da.description, 
                da.owner, 
                da.website, 
                da.status, 
                da.created_at,
                u.Name as developer_name
            FROM developer_apps da
            LEFT JOIN user_info u ON da.developer_id = u.id
            WHERE da.status = 'pending'
            ORDER BY da.created_at DESC
        """)

        apps = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'apps': apps})

    except Exception as e:
        print(f"获取待审批应用列表失败: {e}")
        return jsonify({'success': False, 'message': '获取列表失败'})


@admin_bp.route('/api/admin/approve-app', methods=['POST'])
@admin_required
def approve_app():
    try:
        data = request.json
        app_id = data.get('app_id')

        if not app_id:
            return jsonify({'success': False, 'message': '应用ID不能为空'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute("SELECT * FROM developer_apps WHERE id = %s", (app_id,))
        app = cursor.fetchone()

        if not app:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '应用不存在'})

        if app['status'] != 'pending':
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '该应用不在待审批状态'})

        if app['id'] and len(app['id']) == 15:
            final_app_id = app['id']
        else:
            final_app_id = generate_app_id()
            while True:
                cursor.execute("SELECT id FROM developer_apps WHERE id = %s", (final_app_id,))
                if not cursor.fetchone():
                    break
                final_app_id = generate_app_id()

        app_secret = generate_app_secret()
        app_secret_hash = generate_password_hash(app_secret)
        approved_at = get_network_time()

        cursor.execute("""
            UPDATE developer_apps 
            SET id = %s, app_secret = %s, status = 'approved', approved_at = %s
            WHERE id = %s
        """, (final_app_id, app_secret_hash, approved_at, app_id))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': '应用审批通过',
            'app_id': final_app_id,
            'app_secret': app_secret
        })

    except Exception as e:
        print(f"审批应用失败: {e}")
        return jsonify({'success': False, 'message': '审批失败，请稍后重试'})


@admin_bp.route('/api/admin/reject-app', methods=['POST'])
@admin_required
def reject_app():
    try:
        data = request.json
        app_id = data.get('app_id')

        if not app_id:
            return jsonify({'success': False, 'message': '应用ID不能为空'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor()

        try:
            conn.begin()

            cursor.execute("DELETE FROM app_configurations WHERE app_id = %s", (app_id,))
            cursor.execute("DELETE FROM developer_authorizations WHERE app_id = %s", (app_id,))
            cursor.execute("DELETE FROM developer_apps WHERE id = %s", (app_id,))

            if cursor.rowcount == 0:
                conn.rollback()
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '应用不存在'})

            conn.commit()
            cursor.close()
            conn.close()

            return jsonify({'success': True, 'message': '应用已拒绝并删除'})

        except Exception as e:
            conn.rollback()
            raise e

    except Exception as e:
        print(f"拒绝应用失败: {e}")
        return jsonify({'success': False, 'message': '拒绝失败，请稍后重试'})


@admin_bp.route('/api/admin/pending-apps-count', methods=['GET'])
@admin_required
def get_pending_apps_count():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM developer_apps WHERE status = 'pending'")
        count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'count': count})

    except Exception as e:
        print(f"获取待审批应用数量失败: {e}")
        return jsonify({'success': False, 'message': '获取数量失败'})


@admin_bp.route('/api/admin/all-apps', methods=['GET'])
@admin_required
def get_all_apps():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute("""
            SELECT 
                da.id, 
                da.developer_id, 
                da.name, 
                da.description, 
                da.owner, 
                da.website, 
                da.status, 
                da.created_at,
                da.approved_at,
                u.Name as developer_name
            FROM developer_apps da
            LEFT JOIN user_info u ON da.developer_id = u.id
            ORDER BY da.created_at DESC
        """)

        apps = cursor.fetchall()

        for app in apps:
            if app['created_at']:
                app['created_at'] = app['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if app['approved_at']:
                app['approved_at'] = app['approved_at'].strftime('%Y-%m-%d %H:%M:%S')

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'apps': apps})

    except Exception as e:
        print(f"获取所有应用列表失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'获取列表失败: {str(e)}'})


@admin_bp.route('/api/admin/update-app', methods=['POST'])
@admin_required
def update_app():
    try:
        data = request.json
        app_id = data.get('app_id')
        name = data.get('name')
        description = data.get('description')
        owner = data.get('owner')
        website = data.get('website')
        status = data.get('status')

        if not app_id:
            return jsonify({'success': False, 'message': '应用ID不能为空'})

        if status == 'rejected':
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': '数据库连接失败'})
            
            try:
                cursor = conn.cursor()
                conn.begin()
                
                cursor.execute("DELETE FROM app_configurations WHERE app_id = %s", (app_id,))
                cursor.execute("DELETE FROM developer_authorizations WHERE app_id = %s", (app_id,))
                cursor.execute("DELETE FROM developer_apps WHERE id = %s", (app_id,))
                
                if cursor.rowcount == 0:
                    conn.rollback()
                    cursor.close()
                    conn.close()
                    return jsonify({'success': False, 'message': '应用不存在'})
                
                conn.commit()
                cursor.close()
                conn.close()
                
                return jsonify({'success': True, 'message': '应用已拒绝并删除'})
            except Exception as e:
                conn.rollback()
                raise e

        if not name or not name.strip():
            return jsonify({'success': False, 'message': '应用名称不能为空'})

        if len(name) > 100:
            return jsonify({'success': False, 'message': '应用名称不能超过100个字符'})

        if website and not validate_url(website):
            return jsonify({'success': False, 'message': '请输入有效的网址格式'})

        if status not in ['pending', 'approved', 'rejected']:
            return jsonify({'success': False, 'message': '无效的应用状态'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute("SELECT id FROM developer_apps WHERE id = %s", (app_id,))
        app = cursor.fetchone()

        if not app:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '应用不存在'})

        cursor.execute("""
            UPDATE developer_apps 
            SET name = %s, description = %s, owner = %s, website = %s, status = %s
            WHERE id = %s
        """, (name.strip(), description, owner, website, status, app_id))

        if status == 'approved':
            cursor.execute("""
                UPDATE developer_apps 
                SET approved_at = %s
                WHERE id = %s AND approved_at IS NULL
            """, (get_network_time(), app_id))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': '应用信息已更新'})

    except Exception as e:
        print(f"更新应用失败: {e}")
        return jsonify({'success': False, 'message': '更新失败，请稍后重试'})


@admin_bp.route('/api/admin/delete-app', methods=['DELETE'])
@admin_required
def admin_delete_app():
    try:
        data = request.json
        app_id = data.get('app_id')

        if not app_id:
            return jsonify({'success': False, 'message': '应用ID不能为空'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        cursor = conn.cursor()

        try:
            conn.begin()

            cursor.execute("DELETE FROM app_configurations WHERE app_id = %s", (app_id,))
            cursor.execute("DELETE FROM developer_authorizations WHERE app_id = %s", (app_id,))
            cursor.execute("DELETE FROM developer_apps WHERE id = %s", (app_id,))

            if cursor.rowcount == 0:
                conn.rollback()
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '应用不存在'})

            conn.commit()
            cursor.close()
            conn.close()

            return jsonify({'success': True, 'message': '应用删除成功'})

        except Exception as e:
            conn.rollback()
            raise e

    except Exception as e:
        print(f"删除应用失败: {e}")
        return jsonify({'success': False, 'message': '删除失败，请稍后重试'})


def validate_url(url):
    import re
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
