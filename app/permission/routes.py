from flask import Blueprint, request, jsonify, session, redirect, render_template
import os

from app.models.db import get_db_connection
from app.auth.utils import get_network_time
from app.auth.routes import login_required
from app.permission.utils import get_user_avatar_path, is_admin, can_approve_permission, avatar_extensions, is_developer

permission_bp = Blueprint('permission', __name__)


@permission_bp.route('/permission')
def permission():
    if 'logged_in' in session and session['logged_in']:
        return render_template('permission.html')
    else:
        return redirect('/login')


@permission_bp.route('/api/permission-apply', methods=['POST'])
@login_required
def permission_apply():
    try:
        data = request.json
        user_id = data.get('user_id')
        permission_type = data.get('type')

        if not user_id or not permission_type:
            return jsonify({'success': False, 'message': '请求数据不完整'})

        formatted_time = get_network_time().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO user_permission_application (user_id, type, time) VALUES (%s, %s, %s)",
                    (user_id, permission_type, formatted_time)
                )
            conn.commit()
        finally:
            conn.close()

        return jsonify({'success': True, 'message': '权限申请已提交'})
    except Exception as e:
        print(f"权限申请失败: {e}")
        return jsonify({'success': False, 'message': '申请提交失败，请重试'})


@permission_bp.route('/check-admin-permission', methods=['POST'])
@login_required
def check_admin_permission():
    try:
        user_id = session.get('user_id')

        if is_admin(user_id):
            return jsonify({'success': True, 'isAdmin': True})
        else:
            return jsonify({'success': True, 'isAdmin': False})
    except Exception as e:
        print(f"检查管理员权限失败: {e}")
        return jsonify({'success': False, 'message': '检查失败，请重试'})


@permission_bp.route('/check-developer-permission', methods=['POST'])
@login_required
def check_developer_permission():
    try:
        user_id = session.get('user_id')

        if is_developer(user_id):
            return jsonify({'success': True, 'isDeveloper': True})
        else:
            return jsonify({'success': True, 'isDeveloper': False})
    except Exception as e:
        print(f"检查开发者权限失败: {e}")
        return jsonify({'success': False, 'message': '检查失败，请重试'})


@permission_bp.route('/check-user-permission-management-permission', methods=['POST'])
@login_required
def check_user_permission_management_permission():
    try:
        user_id = session.get('user_id')

        if is_admin(user_id):
            return jsonify({'success': True, 'hasPermissionManagementPermission': True})
        else:
            return jsonify({'success': True, 'hasPermissionManagementPermission': False})
    except Exception as e:
        print(f"检查用户权限管理权限失败: {e}")
        return jsonify({'success': False, 'message': '检查失败，请重试'})


@permission_bp.route('/api/get-permission-applications', methods=['GET'])
@login_required
def get_permission_applications():
    try:
        user_id = session.get('user_id')

        if not is_admin(user_id):
            return jsonify({'success': False, 'message': '没有管理员权限'})

        search_user_id = request.args.get('user_id', '')
        search_username = request.args.get('username', '')
        search_email = request.args.get('email', '')
        search_permission = request.args.get('permission', '')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        try:
            with conn.cursor() as cursor:
                query = """
                SELECT u.id, u.Name, u.mail, a.type, a.time
                FROM user_permission_application a
                JOIN user_info u ON a.user_id = u.id
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
                if search_permission:
                    query += " AND a.type LIKE %s"
                    params.append(f"%{search_permission}%")

                query += " ORDER BY a.time DESC"

                cursor.execute(query, params)
                applications = cursor.fetchall()

                result = []
                for application in applications:
                    avatar_path = get_user_avatar_path(application[0])
                    result.append({
                        'user_id': application[0],
                        'username': application[1],
                        'email': application[2],
                        'permission_type': application[3],
                        'apply_time': str(application[4]),
                        'avatar': avatar_path
                    })
        finally:
            conn.close()

        return jsonify({'success': True, 'applications': result})
    except Exception as e:
        print(f"获取权限申请列表失败: {e}")
        return jsonify({'success': False, 'message': '获取失败，请重试'})


@permission_bp.route('/api/approve-permission', methods=['POST'])
@login_required
def approve_permission():
    try:
        operator_id = session.get('user_id')
        data = request.json
        user_id = data.get('user_id')
        permission_type = data.get('type')

        if not can_approve_permission(operator_id, permission_type):
            return jsonify({'success': False, 'message': '没有操作权限'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        try:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO user_permission (user_id, type) VALUES (%s, %s)", (user_id, permission_type))
                cursor.execute("DELETE FROM user_permission_application WHERE user_id = %s AND type = %s", (user_id, permission_type))
            conn.commit()
        finally:
            conn.close()

        return jsonify({'success': True, 'message': '权限申请已通过'})
    except Exception as e:
        print(f"通过权限申请失败: {e}")
        return jsonify({'success': False, 'message': '操作失败，请重试'})


@permission_bp.route('/api/reject-permission', methods=['POST'])
@login_required
def reject_permission():
    try:
        operator_id = session.get('user_id')
        data = request.json
        user_id = data.get('user_id')
        permission_type = data.get('type')

        if not can_approve_permission(operator_id, permission_type):
            return jsonify({'success': False, 'message': '没有操作权限'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM user_permission_application WHERE user_id = %s AND type = %s", (user_id, permission_type))
            conn.commit()
        finally:
            conn.close()

        return jsonify({'success': True, 'message': '权限申请已拒绝'})
    except Exception as e:
        print(f"拒绝权限申请失败: {e}")
        return jsonify({'success': False, 'message': '操作失败，请重试'})


@permission_bp.route('/api/batch-approve', methods=['POST'])
@login_required
def batch_approve():
    try:
        operator_id = session.get('user_id')
        data = request.json
        permission_type = data.get('type')

        if not can_approve_permission(operator_id, permission_type):
            return jsonify({'success': False, 'message': '没有操作权限'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT user_id FROM user_permission_application WHERE type = %s", (permission_type,))
                applications = cursor.fetchall()

                for app in applications:
                    cursor.execute("INSERT INTO user_permission (user_id, type) VALUES (%s, %s)", (app[0], permission_type))

                cursor.execute("DELETE FROM user_permission_application WHERE type = %s", (permission_type,))
            conn.commit()
        finally:
            conn.close()

        return jsonify({'success': True, 'message': f'已批量通过所有{permission_type}申请', 'count': len(applications)})
    except Exception as e:
        print(f"批量通过权限申请失败: {e}")
        return jsonify({'success': False, 'message': '操作失败，请重试'})


@permission_bp.route('/api/get-user-permissions', methods=['GET'])
@login_required
def get_user_permissions():
    try:
        current_user_id = session.get('user_id')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT type FROM user_permission WHERE user_id = %s", (current_user_id,))
                permissions = []

                for idx, row in enumerate(cursor.fetchall()):
                    permissions.append({
                        'id': f"{current_user_id}_{row[0]}_{idx}",
                        'type': row[0]
                    })
        finally:
            conn.close()

        return jsonify({'success': True, 'permissions': permissions})
    except Exception as e:
        print(f"获取用户权限列表失败: {e}")
        return jsonify({'success': False, 'message': '获取权限列表失败，请重试'})


@permission_bp.route('/api/delete-permission', methods=['POST'])
@login_required
def delete_permission():
    try:
        data = request.json
        permission_id = data.get('permission_id')

        if not permission_id:
            return jsonify({'success': False, 'message': '权限ID不能为空'})

        try:
            parts = permission_id.split('_')
            if len(parts) < 3:
                return jsonify({'success': False, 'message': '无效的权限ID格式'})

            current_user_id = session.get('user_id')
            parsed_user_id = '_'.join(parts[:-2])
            permission_type = parts[-2]

            if parsed_user_id != current_user_id:
                return jsonify({'success': False, 'message': '无权删除此权限'})
        except Exception as e:
            print(f"解析权限ID失败: {e}")
            return jsonify({'success': False, 'message': '权限ID格式错误'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM user_permission WHERE user_id = %s AND type = %s",
                              (current_user_id, permission_type))

                if cursor.rowcount == 0:
                    return jsonify({'success': False, 'message': '权限不存在或已被删除'})
            conn.commit()
        finally:
            conn.close()

        return jsonify({'success': True, 'message': '权限删除成功'})
    except Exception as e:
        print(f"删除用户权限失败: {e}")
        return jsonify({'success': False, 'message': '删除权限失败，请重试'})


@permission_bp.route('/api/get-all-user-permissions', methods=['GET'])
@login_required
def get_all_user_permissions():
    try:
        admin_id = session.get('user_id')

        if not is_admin(admin_id):
            return jsonify({'success': False, 'message': '没有管理员权限'})

        search_user_id = request.args.get('user_id', '')
        search_username = request.args.get('username', '')
        search_email = request.args.get('email', '')
        search_permission = request.args.get('permission', '')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        try:
            with conn.cursor() as cursor:
                query = """
                SELECT u.id, u.Name, u.mail, p.type
                FROM user_permission p
                JOIN user_info u ON p.user_id = u.id
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
                if search_permission:
                    query += " AND p.type LIKE %s"
                    params.append(f"%{search_permission}%")

                query += " ORDER BY u.Name"

                cursor.execute(query, params)
                permissions = cursor.fetchall()

                result = []
                for perm in permissions:
                    avatar_path = get_user_avatar_path(perm[0])
                    result.append({
                        'user_id': perm[0],
                        'username': perm[1],
                        'email': perm[2],
                        'permission_type': perm[3],
                        'avatar': avatar_path
                    })
        finally:
            conn.close()

        return jsonify({'success': True, 'permissions': result})
    except Exception as e:
        print(f"获取所有用户权限列表失败: {e}")
        return jsonify({'success': False, 'message': '获取失败，请重试'})


@permission_bp.route('/api/admin-delete-permission', methods=['POST'])
@login_required
def admin_delete_permission():
    try:
        admin_id = session.get('user_id')
        data = request.json
        user_id = data.get('user_id')
        permission_type = data.get('type')

        if not is_admin(admin_id):
            return jsonify({'success': False, 'message': '没有管理员权限'})

        if str(admin_id) == str(user_id) and permission_type == '管理员':
            return jsonify({'success': False, 'message': '不能删除自己的管理员权限'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})

        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM user_permission WHERE user_id = %s AND type = %s",
                              (user_id, permission_type))

                if cursor.rowcount == 0:
                    return jsonify({'success': False, 'message': '权限不存在或已被删除'})
            conn.commit()
        finally:
            conn.close()

        return jsonify({'success': True, 'message': '权限删除成功'})
    except Exception as e:
        print(f"管理员删除用户权限失败: {e}")
        return jsonify({'success': False, 'message': '删除权限失败，请重试'})
