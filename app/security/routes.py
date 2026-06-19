from flask import request, jsonify, session, render_template
import json
import pymysql

from app.models.db import get_db_connection
from app.auth.utils import get_network_time
from app.security import security_bp

PERMISSION_LABELS = {
    'no_userinfo': ('禁止获取用户信息', '允许获取用户信息'),
    'no_email': ('禁止发送邮件', '允许发送邮件'),
    'no_phone': ('禁止获取手机号', '允许获取手机号'),
}

DEFAULT_PERMISSION_RESTRICTIONS = {"no_userinfo": False, "no_email": False, "no_phone": False}


@security_bp.route('/third-party-security')
def third_party_security():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({'success': False, 'message': '用户未登录'}), 401

    user_id = session.get('user_id')

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'}), 500

    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute("""
            SELECT da.id as auth_id, da.app_id, da.created_at, da.status, da.permission_restrictions,
                   dapp.name as app_name, dapp.owner as app_owner, dapp.description as app_description
            FROM developer_authorizations da
            JOIN developer_apps dapp ON da.app_id = dapp.id
            WHERE da.user_id = %s AND da.status = 'active'
            ORDER BY da.created_at DESC
        """, (user_id,))

        authorizations = cursor.fetchall()

        for auth in authorizations:
            if auth['permission_restrictions']:
                try:
                    auth['permission_restrictions'] = json.loads(auth['permission_restrictions'])
                except (json.JSONDecodeError, TypeError):
                    auth['permission_restrictions'] = DEFAULT_PERMISSION_RESTRICTIONS.copy()
            else:
                auth['permission_restrictions'] = DEFAULT_PERMISSION_RESTRICTIONS.copy()

            if auth['created_at']:
                auth['created_at'] = auth['created_at'].strftime('%Y-%m-%d %H:%M:%S')

        cursor.close()
        conn.close()

        return render_template('third_party_security.html', authorizations=authorizations)

    except Exception as e:
        print(f"获取第三方授权列表失败: {e}")
        if conn:
            try:
                conn.close()
            except:
                pass
        return jsonify({'success': False, 'message': '获取授权列表失败，请稍后重试'}), 500


@security_bp.route('/api/third-party-security')
def api_third_party_security():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({'success': False, 'message': '用户未登录'}), 401

    user_id = session.get('user_id')
    status_filter = request.args.get('status', 'active')

    if status_filter not in ('active', 'blacklisted'):
        status_filter = 'active'

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'}), 500

    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute("""
            SELECT da.id as auth_id, da.app_id, da.created_at, da.status, da.permission_restrictions,
                   dapp.name as app_name, dapp.owner as app_owner, dapp.description as app_description
            FROM developer_authorizations da
            JOIN developer_apps dapp ON da.app_id = dapp.id
            WHERE da.user_id = %s AND da.status = %s
            ORDER BY da.created_at DESC
        """, (user_id, status_filter))

        authorizations = cursor.fetchall()

        for auth in authorizations:
            if auth['permission_restrictions']:
                try:
                    auth['permission_restrictions'] = json.loads(auth['permission_restrictions'])
                except (json.JSONDecodeError, TypeError):
                    auth['permission_restrictions'] = DEFAULT_PERMISSION_RESTRICTIONS.copy()
            else:
                auth['permission_restrictions'] = DEFAULT_PERMISSION_RESTRICTIONS.copy()

            if auth['created_at']:
                auth['created_at'] = auth['created_at'].strftime('%Y-%m-%d %H:%M:%S')

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'authorizations': authorizations})

    except Exception as e:
        print(f"获取第三方授权列表失败: {e}")
        if conn:
            try:
                conn.close()
            except:
                pass
        return jsonify({'success': False, 'message': '获取授权列表失败，请稍后重试'}), 500


@security_bp.route('/api/third-party/cancel-auth', methods=['POST'])
def cancel_auth():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({'success': False, 'message': '用户未登录'}), 401

    try:
        data = request.json
        app_id = data.get('app_id')
        auth_id = data.get('auth_id')
        user_id = session.get('user_id')

        if not app_id or not auth_id:
            return jsonify({'success': False, 'message': '缺少必要参数'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            cursor.execute("""
                SELECT dapp.name as app_name
                FROM developer_authorizations da
                JOIN developer_apps dapp ON da.app_id = dapp.id
                WHERE da.app_id = %s AND da.id = %s AND da.user_id = %s
            """, (app_id, auth_id, user_id))
            auth = cursor.fetchone()

            if not auth:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '授权记录不存在'})

            app_name = auth['app_name']

            cursor.execute("""
                UPDATE developer_authorizations
                SET status = 'cancelled'
                WHERE app_id = %s AND id = %s AND user_id = %s
            """, (app_id, auth_id, user_id))

            conn.commit()

            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            log_time = get_network_time()

            cursor.execute("""
                INSERT INTO authorization_log (user_id, app_id, action, detail, ip, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, app_id, 'cancel', f'取消授权: {app_name}', ip, log_time))
            conn.commit()

            cursor.close()
            conn.close()

            return jsonify({'success': True, 'message': '已取消授权'})

        except Exception as e:
            conn.rollback()
            raise e

    except Exception as e:
        print(f"取消授权失败: {e}")
        if conn:
            try:
                conn.close()
            except:
                pass
        return jsonify({'success': False, 'message': '取消授权失败，请稍后重试'})


@security_bp.route('/api/third-party/blacklist', methods=['POST'])
def blacklist_app():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({'success': False, 'message': '用户未登录'}), 401

    try:
        data = request.json
        app_id = data.get('app_id')
        auth_id = data.get('auth_id')
        user_id = session.get('user_id')

        if not app_id or not auth_id:
            return jsonify({'success': False, 'message': '缺少必要参数'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            cursor.execute("""
                SELECT dapp.name as app_name
                FROM developer_authorizations da
                JOIN developer_apps dapp ON da.app_id = dapp.id
                WHERE da.app_id = %s AND da.id = %s AND da.user_id = %s
            """, (app_id, auth_id, user_id))
            auth = cursor.fetchone()

            if not auth:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '授权记录不存在'})

            app_name = auth['app_name']

            cursor.execute("""
                UPDATE developer_authorizations
                SET status = 'blacklisted'
                WHERE id = %s AND app_id = %s AND user_id = %s
            """, (auth_id, app_id, user_id))

            conn.commit()

            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            log_time = get_network_time()

            cursor.execute("""
                INSERT INTO authorization_log (user_id, app_id, action, detail, ip, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, app_id, 'blacklist', f'拉黑应用: {app_name}', ip, log_time))
            conn.commit()

            cursor.close()
            conn.close()

            return jsonify({'success': True, 'message': '已拉黑应用'})

        except Exception as e:
            conn.rollback()
            raise e

    except Exception as e:
        print(f"拉黑应用失败: {e}")
        if conn:
            try:
                conn.close()
            except:
                pass
        return jsonify({'success': False, 'message': '拉黑应用失败，请稍后重试'})


@security_bp.route('/api/third-party/restore-auth', methods=['POST'])
def restore_auth():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({'success': False, 'message': '用户未登录'}), 401

    try:
        data = request.json
        app_id = data.get('app_id')
        auth_id = data.get('auth_id')
        user_id = session.get('user_id')

        if not app_id or not auth_id:
            return jsonify({'success': False, 'message': '缺少必要参数'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            cursor.execute("""
                SELECT dapp.name as app_name
                FROM developer_authorizations da
                JOIN developer_apps dapp ON da.app_id = dapp.id
                WHERE da.app_id = %s AND da.id = %s AND da.user_id = %s
            """, (app_id, auth_id, user_id))
            auth = cursor.fetchone()

            if not auth:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '授权记录不存在'})

            app_name = auth['app_name']

            cursor.execute("""
                DELETE FROM developer_authorizations
                WHERE app_id = %s AND id = %s AND user_id = %s AND status = 'blacklisted'
            """, (app_id, auth_id, user_id))

            conn.commit()

            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            log_time = get_network_time()

            cursor.execute("""
                INSERT INTO authorization_log (user_id, app_id, action, detail, ip, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, app_id, 'unblacklist', f'解除黑名单: {app_name}', ip, log_time))
            conn.commit()

            cursor.close()
            conn.close()

            return jsonify({'success': True, 'message': '已解除黑名单，请重新授权'})

        except Exception as e:
            conn.rollback()
            raise e

    except Exception as e:
        print(f"解除黑名单失败: {e}")
        if conn:
            try:
                conn.close()
            except:
                pass
        return jsonify({'success': False, 'message': '解除黑名单失败，请稍后重试'})


@security_bp.route('/api/third-party/restrict-permission', methods=['POST'])
def restrict_permission():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({'success': False, 'message': '用户未登录'}), 401

    try:
        data = request.json
        app_id = data.get('app_id')
        auth_id = data.get('auth_id')
        permission_type = data.get('permission_type')
        enabled = data.get('enabled')
        user_id = session.get('user_id')

        if not app_id or not auth_id or not permission_type or enabled is None:
            return jsonify({'success': False, 'message': '缺少必要参数'})

        if permission_type not in ('no_userinfo', 'no_email', 'no_phone'):
            return jsonify({'success': False, 'message': '无效的权限类型'})

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            cursor.execute("""
                SELECT permission_restrictions
                FROM developer_authorizations
                WHERE app_id = %s AND id = %s AND user_id = %s
            """, (app_id, auth_id, user_id))
            result = cursor.fetchone()

            if not result:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '授权记录不存在'})

            raw_restrictions = result['permission_restrictions']
            if raw_restrictions:
                try:
                    restrictions = json.loads(raw_restrictions)
                except (json.JSONDecodeError, TypeError):
                    restrictions = DEFAULT_PERMISSION_RESTRICTIONS.copy()
            else:
                restrictions = DEFAULT_PERMISSION_RESTRICTIONS.copy()

            restrictions[permission_type] = enabled

            new_restrictions = json.dumps(restrictions)

            cursor.execute("""
                UPDATE developer_authorizations
                SET permission_restrictions = %s
                WHERE app_id = %s AND id = %s AND user_id = %s
            """, (new_restrictions, app_id, auth_id, user_id))

            conn.commit()

            labels = PERMISSION_LABELS.get(permission_type, ('未知权限', '未知权限'))
            detail = labels[0] if enabled else labels[1]

            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            log_time = get_network_time()

            cursor.execute("""
                INSERT INTO authorization_log (user_id, app_id, action, detail, ip, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, app_id, 'restrict', detail, ip, log_time))
            conn.commit()

            cursor.close()
            conn.close()

            return jsonify({'success': True})

        except Exception as e:
            conn.rollback()
            raise e

    except Exception as e:
        print(f"更新权限限制失败: {e}")
        if conn:
            try:
                conn.close()
            except:
                pass
        return jsonify({'success': False, 'message': '更新权限限制失败，请稍后重试'})


@security_bp.route('/authorization-log')
def authorization_log_page():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({'success': False, 'message': '用户未登录'}), 401

    return render_template('authorization_log.html')


@security_bp.route('/api/authorization-log')
def get_authorization_log():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({'success': False, 'message': '用户未登录'}), 401

    user_id = session.get('user_id')
    search = request.args.get('search', '')

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': '数据库连接失败，请稍后重试'})

    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        query = """
            SELECT al.id, al.app_id, al.action, al.detail, al.ip, al.created_at,
                   dapp.name as app_name
            FROM authorization_log al
            LEFT JOIN developer_apps dapp ON al.app_id = dapp.id
            WHERE al.user_id = %s
        """
        params = [user_id]

        if search:
            query += " AND (dapp.name LIKE %s OR al.action LIKE %s)"
            params.append(f"%{search}%")
            params.append(f"%{search}%")

        query += " ORDER BY al.created_at DESC"

        cursor.execute(query, params)
        logs = cursor.fetchall()

        for log in logs:
            if log['created_at']:
                log['created_at'] = log['created_at'].strftime('%Y-%m-%d %H:%M:%S')

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'logs': logs})

    except Exception as e:
        print(f"获取授权日志失败: {e}")
        if conn:
            try:
                conn.close()
            except:
                pass
        return jsonify({'success': False, 'message': '获取授权日志失败，请稍后重试'})